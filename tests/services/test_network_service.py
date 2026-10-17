import time
import pandas as pd
import pytest
from api.services.network_service import _concentration_ratio, _build_concentration_map


def make_supplier_df(n_suppliers: int = 5, n_weeks: int = 4) -> pd.DataFrame:
    rows = []
    for s in range(n_suppliers):
        for w in range(n_weeks):
            rows.append({
                "supplier_id": f"SUP-{s:04d}",
                "week_num": w,
                "country": "USA",
                "regional_delay_factor": 0.1,
            })
    return pd.DataFrame(rows)


def test_concentration_ratio_uses_latest_week_only():
    """With 4 equal suppliers active in latest week, each should have 25% concentration."""
    df = make_supplier_df(n_suppliers=4, n_weeks=6)
    ratio = _concentration_ratio("SUP-0000", df)
    assert abs(ratio - 0.25) < 0.01, f"Expected ~0.25, got {ratio}"


def test_concentration_map_matches_individual_ratios():
    """_build_concentration_map must match _concentration_ratio for all suppliers."""
    df = make_supplier_df(n_suppliers=5, n_weeks=6)
    cmap = _build_concentration_map(df)
    for s in range(5):
        sid = f"SUP-{s:04d}"
        indiv = _concentration_ratio(sid, df)
        assert abs(cmap[sid] - indiv) < 1e-4, f"Mismatch for {sid}: map={cmap[sid]} vs indiv={indiv}"


def test_concentration_map_performance():
    """Vectorized calculation on 50 suppliers × 1000 weeks must finish in <0.1s."""
    big_df = make_supplier_df(n_suppliers=50, n_weeks=1000)
    t0 = time.perf_counter()
    cmap = _build_concentration_map(big_df)
    elapsed = time.perf_counter() - t0
    assert len(cmap) == 50
    assert elapsed < 0.2, f"Vectorized concentration took {elapsed:.2f}s, expected <0.2s"
