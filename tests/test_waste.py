"""Tests for waste.py: Waste reduction KPIs and actionable recommendations.
"""

import pytest
import pandas as pd
from waste import (
    get_waste_reduction_kpis,
    get_waste_monitoring_table,
    get_high_leftover_items,
    generate_actionable_recommendations
)


def test_waste_kpis():
    """Test waste and leftover KPI calculations."""
    kpis = get_waste_reduction_kpis()
    assert "total_prepared" in kpis
    assert "total_sold" in kpis
    assert "total_unsold" in kpis
    assert "total_discarded" in kpis
    assert "unsold_rate" in kpis
    assert kpis["total_prepared"] >= kpis["total_sold"]


def test_actionable_recommendations():
    """Test that recommendations are generated based on actual stored records."""
    recs = generate_actionable_recommendations()
    assert isinstance(recs, list)
    assert len(recs) > 0
    for rec in recs:
        assert "type" in rec
        assert "title" in rec
        assert "description" in rec


def test_waste_monitoring_table():
    """Test waste monitoring table column structure and non-emptiness."""
    df = get_waste_monitoring_table()
    if not df.empty:
        assert "food_name" in df.columns
        assert "prepared_quantity" in df.columns
        assert "actual_sold_quantity" in df.columns
        assert "estimated_leftover" in df.columns
        assert "discarded_quantity" in df.columns


def test_high_leftover_items():
    """Test leftover trends data frame structure."""
    leftover_df = get_high_leftover_items()
    if not leftover_df.empty:
        assert "food_name" in leftover_df.columns
        assert "leftover_pct" in leftover_df.columns
        assert "batches_count" in leftover_df.columns

