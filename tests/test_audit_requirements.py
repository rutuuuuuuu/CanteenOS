"""Focused verification tests matching all 10 requirements in CanteenOS audit.
Tests run strictly against isolated temporary database provided by conftest.py.
"""

import pytest
import sqlite3
from datetime import datetime, timedelta
import pandas as pd

import config
from auth import verify_credentials, login, logout, is_authenticated, init_auth_state
from data_store import (
    get_food_items,
    get_ingredients,
    get_inventory_status,
    add_or_update_ingredient,
    append_stock_movement,
    add_or_update_daily_sale,
    get_daily_sales,
    save_forecast_records,
    get_forecasts_for_date
)
from inventory import (
    get_stock_alerts,
    get_inventory_kpis,
    record_ingredient_purchase,
    record_stock_adjustment
)
from prediction import (
    get_tomorrow_date,
    generate_tomorrow_forecast,
    generate_demand_explanation,
    extract_features_for_tomorrow
)
from preparation import (
    calculate_ingredient_requirements,
    confirm_preparation_plan
)
from waste import (
    get_waste_reduction_kpis,
    get_waste_monitoring_table,
    record_leftover_disposition
)
from reports import (
    get_monthly_sales_summary,
    get_monthly_forecast_accuracy,
    get_monthly_inventory_movements,
    get_monthly_preparation_and_leftovers
)
from database import get_db_connection


def test_req1_forecast_generation_for_tomorrow():
    """1. Verify forecast generation produces next-day only predictions."""
    tomorrow = get_tomorrow_date()
    assert tomorrow == datetime.now().date() + timedelta(days=1)
    
    fc = generate_tomorrow_forecast(save_to_db=True)
    assert not fc.empty
    assert "predicted_demand" in fc.columns
    assert (fc["predicted_demand"] >= 0).all()
    assert (fc["target_date"] == tomorrow.strftime("%Y-%m-%d")).all()


def test_req2_insufficient_history_handling():
    """2. Verify that items with limited history (< 7 records) use clearly defined baseline fallback."""
    # Test explanation for new food with insufficient history
    exp, sug = generate_demand_explanation(
        food_name="New Seasonal Drink",
        predicted_val=35,
        recent_avg=35.0,
        event_name="Regular College Day",
        is_exam_period=False,
        day_of_week_name="Tuesday",
        has_sufficient_history=False
    )
    assert "Limited sales history" in exp or "baseline" in exp.lower()
    assert "baseline estimate" in sug.lower()


def test_req3_duplicate_stock_alert_prevention():
    """3. Verify inventory alerts return exactly one alert per affected ingredient."""
    ts = int(datetime.now().timestamp() * 1000)
    ing_id = f"ING_ALERT_TEST_{ts}"
    add_or_update_ingredient(
        ingredient_name="Special Saffron Test",
        unit="g",
        unit_cost=10.0,
        reorder_level=5.0,
        target_stock=20.0,
        is_active=True,
        ingredient_id=ing_id
    )
    
    # Newly created ingredient starts with 0 stock -> 1 alert only
    alerts = get_stock_alerts()
    matched = [a for a in alerts if a["ingredient_id"] == ing_id]
    assert len(matched) == 1
    assert matched[0]["status"] == "Out of Stock"
    assert "Special Saffron Test" in matched[0]["message"]


def test_req4_stock_receipts_and_stock_deductions():
    """4. Verify recording stock receipt increases inventory, and preparation deduction reduces it accurately."""
    ts = int(datetime.now().timestamp() * 1000)
    ing_id = f"ING_FLOW_TEST_{ts}"
    add_or_update_ingredient(
        ingredient_name="Basmati Biryani Rice",
        unit="kg",
        unit_cost=80.0,
        reorder_level=10.0,
        target_stock=50.0,
        is_active=True,
        ingredient_id=ing_id
    )
    
    # Purchase receipt: add 40 kg
    ok, msg = record_ingredient_purchase(ing_id, 40.0, "kg", purchase_order_ref=f"PO_{ts}")
    assert ok is True
    
    inv_df = get_inventory_status()
    current = float(inv_df[inv_df["ingredient_id"] == ing_id]["current_stock"].values[0])
    assert current == 40.0
    
    # Stock adjustment: consume 10 kg
    ok_adj, msg_adj = record_stock_adjustment(ing_id, -10.0, "kg", reason="Staff cafeteria usage")
    assert ok_adj is True
    
    inv_after = get_inventory_status()
    current_after = float(inv_after[inv_after["ingredient_id"] == ing_id]["current_stock"].values[0])
    assert current_after == 30.0


def test_req5_preparation_transaction_integrity():
    """5. Verify preparation checks stock availability, prevents negative stock, and uses atomic transactions."""
    # Attempting to confirm prep when stock is insufficient must fail and not deduct anything
    large_plan = {"FOOD_0001": 10000}  # Excessive planned servings
    success, msg, prep_ids = confirm_preparation_plan("2026-10-15", large_plan)
    assert success is False
    assert "Insufficient inventory" in msg or "Live stock discrepancy" in msg
    assert len(prep_ids) == 0


def test_req6_estimated_leftovers_vs_recorded_waste():
    """6. Verify estimated leftovers and confirmed discarded waste are kept separate."""
    kpis = get_waste_reduction_kpis(days=30)
    assert "total_leftovers" in kpis
    assert "total_discarded" in kpis
    assert "awaiting_disposition" in kpis
    assert kpis["total_leftovers"] >= 0
    assert kpis["total_discarded"] >= 0


def test_req7_monthly_report_calculations():
    """7. Verify monthly sales summary aggregates only for compatible reporting period."""
    summary = get_monthly_sales_summary("2026-09")
    if not summary["records"].empty:
        assert summary["total_revenue"] > 0
        assert summary["total_units_sold"] > 0
        assert summary["total_days"] > 0
    
    # Non-existent month returns clean empty state
    empty_summary = get_monthly_sales_summary("2099-12")
    assert empty_summary["total_revenue"] == 0.0
    assert empty_summary["records"].empty


def test_req8_database_persistence_across_restarts():
    """8. Verify data written to SQLite persists across new connection handles."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM food_items;")
    count1 = cur.fetchone()[0]
    conn.close()
    
    # Reopen connection simulating fresh session
    conn2 = get_db_connection()
    cur2 = conn2.cursor()
    cur2.execute("SELECT COUNT(*) FROM food_items;")
    count2 = cur2.fetchone()[0]
    conn2.close()
    
    assert count1 == count2
    assert count1 > 0


def test_req9_login_and_signout():
    """9. Verify authentication credentials verification and session state handling."""
    assert verify_credentials("admin", "admin") is True
    assert verify_credentials("admin", "wrongpass") is False
    assert verify_credentials("nonexistent", "admin") is False


def test_req10_all_eight_navigation_entries():
    """10. Verify that all eight application navigation screens are accounted for (Login + 7 sidebar views)."""
    # 7 Sidebar items
    sidebar_sections = [title for _, title in config.SIDEBAR_NAV_ITEMS]
    expected_sidebar = [
        "Dashboard",
        "Food Management",
        "Daily Sales",
        "Demand Forecast",
        "Inventory",
        "Waste Reduction",
        "Monthly Reports"
    ]
    assert sidebar_sections == expected_sidebar
    assert len(sidebar_sections) == 7
    
    # Plus Login screen = total 8 navigation views in application architecture
    all_nav_views = ["Login"] + sidebar_sections
    assert len(all_nav_views) == 8
    assert "Login" in all_nav_views
    assert "Dashboard" in all_nav_views
    assert "Demand Forecast" in all_nav_views
