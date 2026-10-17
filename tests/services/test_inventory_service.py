import pytest
import pandas as pd
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_build_heatmap_batches_inventory_query():
    """build_heatmap must issue ONE batch query for all SKUs, eliminating N+1."""
    from api.services.inventory_service import InventoryHeatmapService

    svc = InventoryHeatmapService()

    demand_rows = []
    for sku in ["SKU_1", "SKU_2", "SKU_3", "SKU_4"]:
        for d in range(30):
            demand_rows.append({"id": sku, "d": d, "sales": 10.0, "rolling_std_7": 1.0})
    demand_df = pd.DataFrame(demand_rows)

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()

    with patch("api.services.inventory_service.get_orchestrator") as mock_orch:
        mock_orch.return_value._load_demand_data.return_value = demand_df
        results = await svc.build_heatmap(mock_db)

    assert len(results) == 4
    # Ensure execute was called exactly ONCE with a batch SELECT, not once per SKU
    assert mock_db.execute.call_count == 1
