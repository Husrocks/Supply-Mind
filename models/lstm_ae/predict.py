"""
SupplyMind — LSTM Autoencoder Predictor (Colab Compatible)
Loads the trained anomaly detection model (trained on Colab) and evaluates reconstruction errors.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd
import numpy as np
import torch
import torch.nn as nn
from pydantic import BaseModel

from config import settings

logger = logging.getLogger(__name__)

# Constants matching the updated training configuration
SEQ_LENGTH = 12
FEATURES = [
    "prev_lead_time", "lead_time_cv", "prev_otd", "defect_rate",
    "financial_stress_score", "capacity_utilization",
    "regional_delay_factor", "port_congestion_index", "weather_alerts",
    "interest_rate", "inflation_index", "raw_material_cost",
    "lead_time_volatility_4w", "lead_time_volatility_12w"
]

class AnomalyPrediction(BaseModel):
    supplier_id: str
    reconstruction_error: float
    is_anomaly: bool
    threshold_used: float

class Attention(nn.Module):
    def __init__(self, encoder_dim: int, decoder_dim: int):
        super().__init__()
        self.attn = nn.Linear(encoder_dim + decoder_dim, decoder_dim)
        self.v = nn.Linear(decoder_dim, 1, bias=False)

    def forward(self, decoder_hidden, encoder_outputs):
        seq_len = encoder_outputs.size(1)
        decoder_hidden_expanded = decoder_hidden.unsqueeze(1).repeat(1, seq_len, 1)
        energy = torch.tanh(self.attn(torch.cat((decoder_hidden_expanded, encoder_outputs), dim=2)))
        attention_scores = self.v(energy).squeeze(2)
        return torch.softmax(attention_scores, dim=1)

class LSTMAutoencoder(nn.Module):
    def __init__(self, n_features: int, hidden_dim: int = 32, latent_dim: int = 16, num_layers: int = 2, bidirectional: bool = True):
        super().__init__()
        self.n_features = n_features
        self.hidden_dim = hidden_dim
        self.latent_dim = latent_dim
        self.num_layers = num_layers
        self.bidirectional = bidirectional
        
        self.encoder = nn.LSTM(
            input_size=n_features,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            dropout=0.2 if num_layers > 1 else 0.0,
            bidirectional=bidirectional,
            batch_first=True
        )
        
        encoder_out_dim = hidden_dim * 2 if bidirectional else hidden_dim
        self.bottleneck = nn.Linear(encoder_out_dim, latent_dim)
        
        self.decoder_hidden_init = nn.Linear(latent_dim, hidden_dim)
        self.decoder_cell_init = nn.Linear(latent_dim, hidden_dim)
        
        self.decoder = nn.LSTM(
            input_size=n_features + encoder_out_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            dropout=0.2 if num_layers > 1 else 0.0,
            batch_first=True
        )
        
        self.attention = Attention(encoder_dim=encoder_out_dim, decoder_dim=hidden_dim)
        self.reconstruct = nn.Linear(hidden_dim, n_features)

    def forward(self, x):
        batch_size, seq_len, _ = x.size()
        enc_out, (hn, cn) = self.encoder(x)
        
        if self.bidirectional:
            last_hn = torch.cat((hn[-2], hn[-1]), dim=1)
        else:
            last_hn = hn[-1]
            
        latent = self.bottleneck(last_hn)
        
        dec_h = self.decoder_hidden_init(latent).unsqueeze(0).repeat(self.num_layers, 1, 1)
        dec_c = self.decoder_cell_init(latent).unsqueeze(0).repeat(self.num_layers, 1, 1)
        
        outputs = []
        dec_input = torch.zeros(batch_size, 1, self.n_features, device=x.device)
        
        for t in range(seq_len):
            attn_weights = self.attention(dec_h[-1], enc_out)
            context = torch.bmm(attn_weights.unsqueeze(1), enc_out)
            decoder_input_combined = torch.cat((dec_input, context), dim=2)
            dec_out, (dec_h, dec_c) = self.decoder(decoder_input_combined, (dec_h, dec_c))
            reconstruction = self.reconstruct(dec_out)
            outputs.append(reconstruction)
            dec_input = reconstruction
            
        reconstructed_seq = torch.cat(outputs, dim=1)
        return reconstructed_seq

class AnomalyPredictor:
    def __init__(self, model_path: str | Path | None = None):
        self.model_path = Path(model_path or settings.lstm_ae_model_path)
        self.model = None
        self.scaler = None
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.criterion = nn.MSELoss(reduction='none')
        self.anomaly_threshold = 0.5  # Default threshold fallback
        self._load_model()

    def _load_model(self):
        if not self.model_path.exists():
            raise FileNotFoundError(f"LSTM-AE model not found at: {self.model_path}")
            
        logger.info("Loading LSTM-AE model from %s", self.model_path)
        self.model = LSTMAutoencoder(n_features=len(FEATURES)).to(self.device)
        self.model.load_state_dict(torch.load(self.model_path, map_location=self.device))
        self.model.eval()
        
        # Load scaler
        scaler_path = self.model_path.parent / "scaler.joblib"
        import joblib
        if scaler_path.exists():
            logger.info("Loading scaler from %s", scaler_path)
            self.scaler = joblib.load(scaler_path)
            
        # Load POT threshold
        threshold_path = self.model_path.parent / "threshold.json"
        import json
        if threshold_path.exists():
            try:
                with open(threshold_path, "r") as f:
                    self.anomaly_threshold = json.load(f).get("anomaly_threshold", 0.5)
                logger.info("Loaded POT threshold: %.6f", self.anomaly_threshold)
            except Exception:
                logger.warning("Could not read threshold.json, using default 0.5")

    def predict(self, df: pd.DataFrame) -> list[AnomalyPrediction]:
        """
        Evaluate sequences for reconstruction error.
        Requires df to contain at least SEQ_LENGTH rows per supplier_id, sorted temporally.
        """
        df = df.sort_values(["supplier_id", "week_num"])
        last_seq_df = df.groupby("supplier_id").tail(SEQ_LENGTH)
        
        counts = last_seq_df["supplier_id"].value_counts()
        valid_suppliers = counts[counts == SEQ_LENGTH].index.tolist()
        last_seq_df = last_seq_df[last_seq_df["supplier_id"].isin(valid_suppliers)].copy()
        
        if last_seq_df.empty:
            return []

        # Scale features
        if self.scaler:
            last_seq_df[FEATURES] = self.scaler.transform(last_seq_df[FEATURES])

        sequences = []
        supplier_ids_in_order = []
        for sup_id, group in last_seq_df.groupby("supplier_id", sort=True):
            vals = group[FEATURES].values
            sequences.append(vals)
            supplier_ids_in_order.append(sup_id)

        seq_tensor = torch.tensor(np.array(sequences), dtype=torch.float32).to(self.device)
        
        with torch.no_grad():
            reconstructed = self.model(seq_tensor)
            errors = self.criterion(reconstructed, seq_tensor).mean(dim=(1, 2)).cpu().numpy()
            
        results = []
        for i, sup_id in enumerate(supplier_ids_in_order):
            err = float(errors[i])
            results.append(AnomalyPrediction(
                supplier_id=sup_id,
                reconstruction_error=err,
                is_anomaly=err > self.anomaly_threshold,
                threshold_used=self.anomaly_threshold
            ))
            
        return results

# Singleton
_predictor = None

def get_predictor() -> AnomalyPredictor:
    global _predictor
    if _predictor is None:
        _predictor = AnomalyPredictor()
    return _predictor
