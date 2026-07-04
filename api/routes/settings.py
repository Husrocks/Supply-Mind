import os
import json
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from config import get_settings, settings
from api.middleware.auth import require_role

router = APIRouter(prefix="/settings", tags=["Settings"])

class SettingsResponse(BaseModel):
    risk_high_threshold: float
    risk_critical_threshold: float
    stockout_warning_days: int
    autonomous_budget_usd: float
    anomaly_reconstruction_percentile: int
    manager_email: str

class SettingsUpdate(BaseModel):
    risk_high_threshold: float = Field(..., ge=0.0, le=1.0)
    risk_critical_threshold: float = Field(..., ge=0.0, le=1.0)
    stockout_warning_days: int = Field(..., ge=1)
    autonomous_budget_usd: float = Field(..., ge=0.0)
    anomaly_reconstruction_percentile: int = Field(..., ge=1, le=100)
    manager_email: str

@router.get("", response_model=SettingsResponse, summary="Get dynamic configuration settings")
async def get_current_settings(
    user: dict[str, str] = Depends(require_role(["viewer", "approver", "admin"]))
):
    s = get_settings()
    return SettingsResponse(
        risk_high_threshold=s.risk_high_threshold,
        risk_critical_threshold=s.risk_critical_threshold,
        stockout_warning_days=s.stockout_warning_days,
        autonomous_budget_usd=s.autonomous_budget_usd,
        anomaly_reconstruction_percentile=s.anomaly_reconstruction_percentile,
        manager_email=s.manager_email
    )

@router.put("", response_model=SettingsResponse, summary="Update configuration settings")
async def update_settings(
    payload: SettingsUpdate,
    user: dict[str, str] = Depends(require_role(["admin"]))
):
    json_dir = "data"
    json_path = os.path.join(json_dir, "settings.json")
    os.makedirs(json_dir, exist_ok=True)
    
    # Read existing settings from JSON file if it exists
    existing_data = {}
    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
        except Exception:
            pass
            
    # Update with new values
    new_vals = payload.model_dump()
    existing_data.update(new_vals)
    
    # Save back to JSON file
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(existing_data, f, indent=2, ensure_ascii=False)
        
    # Clear settings cache so it loads the new file on next call
    get_settings.cache_clear()
    
    # Mutate the active singleton settings object in-place so all imported instances update immediately
    active_settings = get_settings()
    for k, v in new_vals.items():
        if hasattr(settings, k):
            setattr(settings, k, v)
            
    return SettingsResponse(
        risk_high_threshold=active_settings.risk_high_threshold,
        risk_critical_threshold=active_settings.risk_critical_threshold,
        stockout_warning_days=active_settings.stockout_warning_days,
        autonomous_budget_usd=active_settings.autonomous_budget_usd,
        anomaly_reconstruction_percentile=active_settings.anomaly_reconstruction_percentile,
        manager_email=active_settings.manager_email
    )
