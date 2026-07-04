import io
import csv
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.db import get_db_session
from api.middleware.auth import require_role
from api.models.db_models import ActionLog, SupplierOnboarding

router = APIRouter(prefix="/reports", tags=["Reports"])

@router.get("/download", summary="Download analytical CSV reports")
async def download_report(
    type: str = Query("risk", description="Report type: 'risk' | 'scorecard' | 'actions'"),
    db: AsyncSession = Depends(get_db_session),
    user: dict[str, str] = Depends(require_role(["viewer", "approver", "admin"]))
):
    output = io.StringIO()
    writer = csv.writer(output)
    
    if type == "risk":
        # Weekly Risk Summary
        from api.services.network_service import network_dashboard_service
        dashboard = await network_dashboard_service.build_dashboard(db, agent_triggered=False)
        suppliers = dashboard.get("supplier_risks", [])
        
        writer.writerow([
            "Supplier ID", "Supplier Name", "Geopolitical Factor", 
            "Lead Time Variance", "Quality Failure Rate", "Concentration Ratio", 
            "Risk Score", "Risk Tier", "Is Anomaly"
        ])
        for s in suppliers:
            writer.writerow([
                s.get("supplier_id", ""),
                s.get("supplier_name", ""),
                f"{s.get('geopolitical_factor', 0.0):.4f}",
                f"{s.get('lead_time_variance', 0.0):.4f}",
                f"{s.get('quality_failure_rate', 0.0):.4f}",
                f"{s.get('concentration_ratio', 0.0):.4f}",
                f"{s.get('risk_score', 0.0) * 100:.1f}%",
                s.get("risk_tier", "unknown"),
                "YES" if s.get("is_anomaly", False) else "NO"
            ])
            
    elif type == "scorecard":
        # Supplier Scorecard
        from api.services.network_service import network_dashboard_service
        dashboard = await network_dashboard_service.build_dashboard(db, agent_triggered=False)
        suppliers = dashboard.get("supplier_risks", [])
        
        writer.writerow([
            "Supplier ID", "Supplier Name", "Average Lead Time (Days)", 
            "On-Time Delivery Rate (%)", "PO Acceptance Rate (%)", "Unit Cost Estimate ($)", "Risk Score (%)"
        ])
        for s in suppliers:
            otd = s.get("on_time_delivery_pct")
            otd_str = f"{otd * 100:.1f}%" if otd is not None else "—"
            po_acc = s.get("po_acceptance_rate")
            po_str = f"{po_acc * 100:.1f}%" if po_acc is not None else "—"
            
            writer.writerow([
                s.get("supplier_id", ""),
                s.get("supplier_name", ""),
                s.get("avg_lead_time_days", "—"),
                otd_str,
                po_str,
                f"${s.get('unit_cost_estimate', 0):.2f}" if s.get("unit_cost_estimate") is not None else "—",
                f"{s.get('risk_score', 0.0) * 100:.1f}%"
            ])
            
    elif type == "actions":
        # Agent Actions Audit Log
        stmt = select(ActionLog).order_by(ActionLog.created_at.desc())
        res = await db.execute(stmt)
        actions = res.scalars().all()
        
        writer.writerow([
            "Action ID", "Action Plan ID", "Action Type", "Status", 
            "Trigger Type", "SKU ID", "Supplier ID", "Estimated Cost ($)", 
            "Reasoning", "Timestamp"
        ])
        for a in actions:
            writer.writerow([
                str(a.id),
                a.action_plan_id,
                a.action_type,
                a.status,
                a.trigger_type,
                a.sku_id,
                a.supplier_id,
                f"${a.estimated_cost_usd:.2f}",
                a.reasoning,
                a.created_at.isoformat()
            ])
    else:
        raise HTTPException(status_code=400, detail="Invalid report type specified")

    # Seek back to start of StringIO buffer
    output.seek(0)
    
    filename = f"supplymind_report_{type}.csv"
    headers = {
        'Content-Disposition': f'attachment; filename="{filename}"'
    }
    return StreamingResponse(
        iter([output.getvalue()]), 
        media_type="text/csv", 
        headers=headers
    )
