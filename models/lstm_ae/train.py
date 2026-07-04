"""
SupplyMind — LSTM Autoencoder for Supplier Anomaly Detection
Detects irregular patterns in supplier behavior (e.g., lead time volatility)
that traditional models might miss.
"""

from __future__ import annotations

import os
os.environ["MLFLOW_ALLOW_FILE_STORE"] = "true"
import sys
import logging
from pathlib import Path

import mlflow
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
from config import settings

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────
CHECKPOINT_DIR = Path(settings.lstm_ae_model_path).parent
CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)

SEQ_LENGTH = 12
FEATURES = [
    "prev_lead_time", "lead_time_cv", "prev_otd", "defect_rate",
    "financial_stress_score", "capacity_utilization",
    "regional_delay_factor", "port_congestion_index", "weather_alerts",
    "interest_rate", "inflation_index", "raw_material_cost",
    "lead_time_volatility_4w", "lead_time_volatility_12w"
]

# ──────────────────────────────────────────────────────────────
# Data & Dataset
# ──────────────────────────────────────────────────────────────

class SupplierSequenceDataset(Dataset):
    def __init__(self, sequences: torch.Tensor):
        self.sequences = sequences

    def __len__(self):
        return len(self.sequences)

    def __getitem__(self, idx):
        return self.sequences[idx]

def create_sequences(df: pd.DataFrame, scaler: StandardScaler | None = None) -> tuple[torch.Tensor, StandardScaler]:
    """Create rolling sequences per supplier."""
    df_copy = df.copy()
    if not scaler:
        scaler = StandardScaler()
        df_copy[FEATURES] = scaler.fit_transform(df_copy[FEATURES])
    else:
        df_copy[FEATURES] = scaler.transform(df_copy[FEATURES])

    sequences = []
    # Sort and group
    df_copy = df_copy.sort_values(["supplier_id", "week_num"])
    for _, group in df_copy.groupby("supplier_id"):
        vals = group[FEATURES].values
        if len(vals) < SEQ_LENGTH:
            continue
        for i in range(len(vals) - SEQ_LENGTH + 1):
            sequences.append(vals[i : i + SEQ_LENGTH])
            
    if len(sequences) == 0:
        # Return empty tensor with correct dimensions
        seq_tensor = torch.zeros((0, SEQ_LENGTH, len(FEATURES)), dtype=torch.float32)
    else:
        seq_tensor = torch.tensor(np.array(sequences), dtype=torch.float32)
    return seq_tensor, scaler

# ──────────────────────────────────────────────────────────────
# Model Architecture
# ──────────────────────────────────────────────────────────────

class Attention(nn.Module):
    def __init__(self, encoder_dim: int, decoder_dim: int):
        super().__init__()
        self.attn = nn.Linear(encoder_dim + decoder_dim, decoder_dim)
        self.v = nn.Linear(decoder_dim, 1, bias=False)

    def forward(self, decoder_hidden, encoder_outputs):
        # decoder_hidden: (batch, decoder_dim)
        # encoder_outputs: (batch, seq_len, encoder_dim)
        seq_len = encoder_outputs.size(1)
        decoder_hidden_expanded = decoder_hidden.unsqueeze(1).repeat(1, seq_len, 1)
        energy = torch.tanh(self.attn(torch.cat((decoder_hidden_expanded, encoder_outputs), dim=2)))
        attention_scores = self.v(energy).squeeze(2) # (batch, seq_len)
        return torch.softmax(attention_scores, dim=1)

class LSTMAutoencoder(nn.Module):
    def __init__(self, n_features: int, hidden_dim: int = 32, latent_dim: int = 16, num_layers: int = 2, bidirectional: bool = True):
        super().__init__()
        self.n_features = n_features
        self.hidden_dim = hidden_dim
        self.latent_dim = latent_dim
        self.num_layers = num_layers
        self.bidirectional = bidirectional
        
        # Encoder
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
        
        # Decoder LSTM
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

# ──────────────────────────────────────────────────────────────
# Early Stopping Helper & POT Thresholding
# ──────────────────────────────────────────────────────────────

class EarlyStopping:
    def __init__(self, patience: int = 5, min_delta: float = 0.0):
        self.patience = patience
        self.min_delta = min_delta
        self.counter = 0
        self.best_loss = None
        self.early_stop = False

    def __call__(self, val_loss):
        if self.best_loss is None:
            self.best_loss = val_loss
        elif val_loss > self.best_loss - self.min_delta:
            self.counter += 1
            if self.counter >= self.patience:
                self.early_stop = True
        else:
            self.best_loss = val_loss
            self.counter = 0

def fit_pot_threshold(errors: np.ndarray, quantile: float = 0.90, extreme_quantile: float = 0.95) -> float:
    """
    Fits a Generalized Pareto Distribution (GPD) to the excesses above a given quantile
    and returns the threshold corresponding to the extreme quantile.
    """
    from scipy.stats import genpareto
    initial_threshold = np.quantile(errors, quantile)
    excesses = errors[errors > initial_threshold] - initial_threshold
    if len(excesses) < 10:
        return float(np.quantile(errors, extreme_quantile))
    
    try:
        c, _, scale = genpareto.fit(excesses, floc=0)
        n = len(errors)
        n_t = len(excesses)
        prob = 1 - extreme_quantile
        if abs(c) < 1e-6:
            extreme_threshold = initial_threshold + scale * np.log(n_t / (n * prob))
        else:
            extreme_threshold = initial_threshold + (scale / c) * (((n * prob) / n_t) ** (-c) - 1)
        
        if not np.isfinite(extreme_threshold) or extreme_threshold < initial_threshold:
            return float(np.quantile(errors, extreme_quantile))
        return float(extreme_threshold)
    except Exception:
        return float(np.quantile(errors, extreme_quantile))

# ──────────────────────────────────────────────────────────────
# Training Loop
# ──────────────────────────────────────────────────────────────

def train(
    data_path: str | Path | None = None,
    epochs: int = 30,
    batch_size: int = 256,
) -> Path:
    data_path = data_path or settings.data_processed_dir
    mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
    mlflow.set_experiment(f"{settings.mlflow_experiment_name}/lstm_ae_anomaly")

    logger.info("Loading processed data for LSTM-AE...")
    train_df = pd.read_parquet(Path(data_path) / "supplier_train.parquet")
    val_df = pd.read_parquet(Path(data_path) / "supplier_val.parquet")
    
    # Train only on 'healthy' periods (e.g. not disrupted)
    train_df = train_df[train_df["disruption_flag"] == 0].copy()
    val_df = val_df[val_df["disruption_flag"] == 0].copy() # use healthy validation sequences for loss monitoring

    train_seqs, scaler = create_sequences(train_df)
    val_seqs, _ = create_sequences(val_df, scaler)
    
    logger.info("Train seqs: %s | Val seqs: %s", train_seqs.shape, val_seqs.shape)

    train_loader = DataLoader(SupplierSequenceDataset(train_seqs), batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(SupplierSequenceDataset(val_seqs), batch_size=batch_size)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = LSTMAutoencoder(n_features=len(FEATURES)).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=2e-3, weight_decay=1e-5)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='min', factor=0.5, patience=3)
    early_stopping = EarlyStopping(patience=5)
    criterion = nn.MSELoss()

    with mlflow.start_run(run_name="lstm_ae_training"):
        best_loss = float("inf")
        best_model_state = None

        for epoch in range(epochs):
            model.train()
            train_loss = 0.0
            for batch in train_loader:
                batch = batch.to(device)
                optimizer.zero_grad()
                reconstructed = model(batch)
                loss = criterion(reconstructed, batch)
                loss.backward()
                optimizer.step()
                train_loss += loss.item() * batch.size(0)
            
            train_loss /= len(train_loader.dataset)
            
            # Validation
            model.eval()
            val_loss = 0.0
            with torch.no_grad():
                for batch in val_loader:
                    batch = batch.to(device)
                    reconstructed = model(batch)
                    loss = criterion(reconstructed, batch)
                    val_loss += loss.item() * batch.size(0)
            val_loss /= len(val_loader.dataset)

            logger.info("Epoch %d/%d | Train Loss: %.4f | Val Loss (Anomalies): %.4f | LR: %.6f", 
                        epoch+1, epochs, train_loss, val_loss, optimizer.param_groups[0]['lr'])
            mlflow.log_metrics({"train_loss": train_loss, "val_anomaly_loss": val_loss}, step=epoch)

            scheduler.step(train_loss)
            early_stopping(train_loss)

            if train_loss < best_loss:
                best_loss = train_loss
                best_model_state = model.state_dict()

            if early_stopping.early_stop:
                logger.info("Early stopping triggered.")
                break

        # Save model
        ckpt_path = CHECKPOINT_DIR / "best.pt"
        torch.save(best_model_state, ckpt_path)
        
        # Save scaler for inference
        import joblib
        joblib.dump(scaler, CHECKPOINT_DIR / "scaler.joblib")
        
        # --- POT Anomaly Threshold Tuning (Optimization Sweep) ---
        model.load_state_dict(best_model_state)
        model.eval()
        
        # Load validation dataset containing anomalies
        val_full_df = pd.read_parquet(Path(data_path) / "supplier_val.parquet")
        
        # We need sequences with ground truth flags
        # A sequence is labeled as an anomaly if any step in it has disruption_flag == 1
        val_seqs_full, _ = create_sequences(val_full_df, scaler)
        
        # Get ground truth anomaly label for each sequence
        val_labels = []
        val_full_df = val_full_df.sort_values(["supplier_id", "week_num"])
        for _, group in val_full_df.groupby("supplier_id"):
            flags = group["disruption_flag"].values
            if len(flags) < SEQ_LENGTH:
                continue
            for i in range(len(flags) - SEQ_LENGTH + 1):
                # Anomaly if any step is disrupted
                val_labels.append(1 if np.any(flags[i : i + SEQ_LENGTH] == 1) else 0)
        
        val_labels = np.array(val_labels)
        
        # Compute reconstruction errors on full validation set
        val_errors = []
        if len(val_seqs_full) > 0:
            val_full_loader = DataLoader(SupplierSequenceDataset(val_seqs_full), batch_size=batch_size, shuffle=False)
            with torch.no_grad():
                for batch in val_full_loader:
                    batch = batch.to(device)
                    reconstructed = model(batch)
                    err = nn.MSELoss(reduction='none')(reconstructed, batch).mean(dim=(1, 2))
                    val_errors.extend(err.cpu().numpy())
        val_errors = np.array(val_errors)
        
        # Compute training errors for threshold fitting base
        train_errors = []
        with torch.no_grad():
            for batch in train_loader:
                batch = batch.to(device)
                reconstructed = model(batch)
                err = nn.MSELoss(reduction='none')(reconstructed, batch).mean(dim=(1, 2))
                train_errors.extend(err.cpu().numpy())
        train_errors = np.array(train_errors)

        # Sweep extreme_quantile to optimize F1 score
        best_f1 = -1.0
        best_threshold = 0.5
        best_q = 0.95
        
        # If there are anomalies in validation set, tune. Otherwise fallback.
        if len(val_errors) > 0 and len(val_labels) > 0 and np.sum(val_labels) > 0:
            for q in [0.90, 0.93, 0.95, 0.97, 0.99]:
                threshold = fit_pot_threshold(train_errors, quantile=0.90, extreme_quantile=q)
                preds = (val_errors > threshold).astype(int)
                from sklearn.metrics import f1_score
                f1 = f1_score(val_labels, preds)
                logger.info(f"Threshold Sweep q={q:.2f} | threshold={threshold:.6f} | F1-Score={f1:.4f}")
                if f1 > best_f1:
                    best_f1 = f1
                    best_threshold = threshold
                    best_q = q
            anomaly_threshold = best_threshold
            logger.info(f"Optimal threshold chosen via sweep: {anomaly_threshold:.6f} (q={best_q:.2f}, F1={best_f1:.4f})")
        else:
            percentile = settings.anomaly_reconstruction_percentile
            anomaly_threshold = fit_pot_threshold(train_errors, quantile=0.90, extreme_quantile=percentile/100.0)
            logger.info(f"No validation anomalies found or empty set. Using default percentile: {anomaly_threshold:.6f}")
        
        import json
        with open(CHECKPOINT_DIR / "threshold.json", "w") as f:
            json.dump({"anomaly_threshold": anomaly_threshold}, f)
        
        logger.info("Fitted POT threshold: %.6f", anomaly_threshold)
        mlflow.log_metric("pot_anomaly_threshold", anomaly_threshold)
        mlflow.log_artifact(str(ckpt_path))
        logger.info("Saved LSTM-AE to %s", ckpt_path)

    return ckpt_path

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    train()

