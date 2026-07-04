"""
Optuna tuning script for the TFT Model.
"""
import sys
import logging
import optuna
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from pytorch_forecasting.models.temporal_fusion_transformer.tuning import optimize_hyperparameters
from models.tft.train import load_and_prepare, create_datasets
from config import settings

logger = logging.getLogger(__name__)

def tune():
    data_path = Path(settings.data_synthetic_dir) / "demand_series.parquet"
    df = load_and_prepare(data_path)
    train_dataset, val_dataset = create_datasets(df)

    train_dataloader = train_dataset.to_dataloader(train=True, batch_size=128, num_workers=0)
    val_dataloader = val_dataset.to_dataloader(train=False, batch_size=128, num_workers=0)

    # Use the built-in optimizer which correctly sets up the trainer
    study, best_model_path = optimize_hyperparameters(
        train_dataloader,
        val_dataloader,
        model_path="models/tft/optuna_tune",
        n_trials=3,
        max_epochs=3,
        gradient_clip_val_range=(0.01, 1.0),
        hidden_size_range=(16, 64),
        hidden_continuous_size_range=(8, 32),
        attention_head_size_range=(1, 2),
        learning_rate_range=(0.001, 0.1),
        dropout_range=(0.1, 0.3),
        trainer_kwargs=dict(limit_train_batches=100, accelerator="auto"),
        reduce_on_plateau_patience=2,
        use_learning_rate_finder=False,
    )

    print("Number of finished trials: ", len(study.trials))
    print("Best trial:")
    trial = study.best_trial
    print("  Value: ", trial.value)
    print("  Params: ")
    for key, value in trial.params.items():
        print(f"    {key}: {value}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    tune()
