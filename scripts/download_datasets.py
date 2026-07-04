"""
SupplyMind — Dataset Downloader
This script downloads the required Kaggle datasets for Phase 1.
You must have your Kaggle credentials set in your .env file or
in ~/.kaggle/kaggle.json.
"""

import os
import zipfile
from pathlib import Path
from loguru import logger
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

RAW_DATA_DIR = Path("data/raw")

DATASETS = [
    {
        "id": "c/m5-forecasting-accuracy",
        "name": "m5-forecasting-accuracy",
        "description": "Walmart hierarchical sales data (Demand Model)"
    },
    {
        "id": "d/shashwatwork/dataco-smart-supply-chain-for-big-data-analysis",
        "name": "dataco-smart-supply-chain",
        "description": "DataCo Supply Chain (Supplier Features)"
    }
]

def download_dataset(dataset_info: dict):
    dataset_id = dataset_info["id"]
    name = dataset_info["name"]
    
    target_dir = RAW_DATA_DIR / name
    target_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Downloading {dataset_info['description']}...")
    
    try:
        from kaggle.api.kaggle_api_extended import KaggleApi
        api = KaggleApi()
        api.authenticate()
        
        if dataset_id.startswith("c/"):
            comp_name = dataset_id.split("/")[1]
            logger.info(f"Downloading competition files for {comp_name}...")
            api.competition_download_files(comp_name, path=str(target_dir))
            zip_path = target_dir / f"{comp_name}.zip"
        else:
            ds_name = dataset_id.split("/", 1)[1]
            logger.info(f"Downloading dataset files for {ds_name}...")
            api.dataset_download_files(dataset_id[2:], path=str(target_dir), unzip=False)
            zip_path = target_dir / f"{dataset_id.split('/')[-1]}.zip"
            
        # Unzip if the zip file was created
        if zip_path.exists():
            logger.info(f"Extracting {zip_path.name}...")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(target_dir)
            zip_path.unlink()
            logger.info(f"✅ Successfully prepared {name}")
        else:
            # Check if Kaggle API downloaded and unzipped directly (sometimes it does if requested, or files are single)
            # Find if there are any files downloaded
            files = list(target_dir.glob("*"))
            if files:
                logger.info(f"✅ Successfully downloaded files directly: {[f.name for f in files]}")
            else:
                logger.warning(f"⚠️ Could not find expected files in {target_dir}")
            
    except Exception as e:
        logger.error(f"❌ Failed to download {name}: {str(e)}")
        logger.info("Ensure your KAGGLE_USERNAME and KAGGLE_KEY are set in .env")

def main():
    logger.info("Starting dataset acquisition...")
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    # Check for credentials
    if not os.environ.get("KAGGLE_USERNAME") and not (Path.home() / ".kaggle" / "kaggle.json").exists():
        logger.error("Kaggle credentials not found. Please set KAGGLE_USERNAME and KAGGLE_KEY in .env")
        return
        
    for ds in DATASETS:
        download_dataset(ds)
        
    logger.info("Dataset acquisition complete.")

if __name__ == "__main__":
    main()
