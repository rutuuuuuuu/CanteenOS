"""Tests for reports.py: Monthly sales, forecast accuracy, inventory movements, and leftover summaries.
"""

import pytest
import pandas as pd
from reports import (
    get_monthly_sales_summary,
    get_monthly_forecast_accuracy,
    get_monthly_inventory_movements,
    get_monthly_preparation_and_leftovers
)


def test_monthly_sales_summary():
    """Test monthly sales aggregation."""
    # Test a month with data from seed_data (e.g. 2026-09 or 2026-08)
    res = get_monthly_sales_summary("2026-09")
    assert "total_revenue" in res
    assert "total_units_sold" in res
    assert "daily_trend" in res
    assert res["total_revenue"] >= 0.0


def test_monthly_forecast_accuracy():
    """Test monthly forecasting error analysis metrics."""
    res = get_monthly_forecast_accuracy("2026-09")
    assert "matched_count" in res
    assert "overall_mae" in res
    assert "overall_rmse" in res
    assert "overall_mape" in res
    assert res["overall_mae"] >= 0.0


def test_monthly_inventory_movements():
    """Test monthly inventory movement analytics."""
    res = get_monthly_inventory_movements("2026-09")
    assert "total_purchases_value" in res
    assert "total_consumed_value" in res
    assert "type_summary" in res
    assert res["total_purchases_value"] >= 0.0


def test_monthly_preparation_and_leftovers():
    """Test monthly preparation and leftover analytics."""
    res = get_monthly_preparation_and_leftovers("2026-09")
    assert "total_prepared" in res
    assert "total_sold" in res
    assert "total_unsold" in res
    assert res["total_prepared"] >= res["total_sold"]
    assert res["unsold_percentage"] >= 0.0


def test_empty_month_handling():
    """Test that querying a future/empty month returns well-formed empty summaries."""
    res = get_monthly_sales_summary("2030-01")
    assert res["total_revenue"] == 0.0
    assert res["total_units_sold"] == 0
    assert res["daily_trend"].empty
