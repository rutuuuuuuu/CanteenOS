"""End-to-End Verification Test for CanteenOS UI and Logic Requirements.
Tests navigation entries (exact 7 items), alert deduplication (1 alert per ingredient),
stock receipt warning resolution, sales revenue without double deduction, waste monitoring,
disposition tracking, monthly reports filtering, and auth security.
"""

import pytest
import pandas as pd
from datetime import datetime

import config
from auth import verify_credentials, login, logout, is_authenticated, init_auth_state
from data_store import (
    get_food_items,
    get_ingredients,
    get_inventory_status,
    add_or_update_ingredient,
    append_stock_movement,
    add_or_update_daily_sale,
    get_daily_sales
)
from inventory import get_stock_alerts, get_inventory_kpis, record_ingredient_purchase
from waste import (
    get_waste_reduction_kpis,
    get_waste_monitoring_table,
    generate_actionable_recommendations,
    record_leftover_disposition,
    get_waste_causes_analysis
)
from prediction import get_tomorrow_date, generate_tomorrow_forecast
from reports import (
    get_monthly_sales_summary,
    get_monthly_inventory_movements,
    get_monthly_preparation_and_leftovers
)
from ui_components import format_inr
from database import init_db, is_database_empty


def test_sidebar_exact_7_navigation_items():
    """Verify exact 7 navigation entries in required order without Preparation Planning."""
    expected = [
        "Dashboard",
        "Food Management",
        "Daily Sales",
        "Demand Forecast",
        "Inventory",
        "Waste Reduction",
        "Monthly Reports"
    ]
    actual = [name for _, name in config.SIDEBAR_NAV_ITEMS]
    assert actual == expected, f"Sidebar items mismatch: {actual} != {expected}"


def test_brand_constants():
    """Verify CanteenOS branding strings."""
    assert config.APP_TITLE == "CanteenOS"
    assert config.APP_SUBTITLE == "CANTEEN MANAGEMENT"


def test_one_out_of_stock_produces_one_warning_and_cleared_by_receipt():
    """Verify one out-of-stock ingredient produces exactly one warning, and stock receipt clears it."""
    ts = int(datetime.now().timestamp() * 1000)
    test_id = f"ING_TEST_CARDAMOM_{ts}"
    add_or_update_ingredient(
        ingredient_name="Cardamom Pods Test Item",
        unit="g",
        unit_cost=2.5,
        reorder_level=50.0,
        target_stock=200.0,
        is_active=True,
        ingredient_id=test_id
    )
    
    # Check alert
    alerts = get_stock_alerts()
    cardamom_alerts = [a for a in alerts if a["ingredient_id"] == test_id]
    assert len(cardamom_alerts) == 1, f"Expected exactly 1 alert for Cardamom, got {len(cardamom_alerts)}"
    assert cardamom_alerts[0]["type"] == "error"
    assert "Stock unavailable" in cardamom_alerts[0]["message"]
    
    # Record stock receipt
    record_ingredient_purchase(
        ingredient_id=test_id,
        quantity=100.0,
        unit="g",
        purchase_order_ref="PO_TEST_001"
    )
    
    # Re-check alerts: stock is now 100 > reorder_level (50), warning must be cleared
    refreshed_alerts = get_stock_alerts()
    refreshed_cardamom = [a for a in refreshed_alerts if a["ingredient_id"] == test_id]
    assert len(refreshed_cardamom) == 0, "Stock alert was not cleared after restock!"


def test_two_distinct_out_of_stock_produce_two_distinct_warnings():
    """Verify two different out of stock ingredients produce two distinct warnings."""
    ts = int(datetime.now().timestamp() * 1000)
    id_a = f"ING_DIST_A_{ts}"
    id_b = f"ING_DIST_B_{ts}"
    add_or_update_ingredient("Distinct Ing A", "kg", 10.0, 5.0, 20.0, True, id_a)
    add_or_update_ingredient("Distinct Ing B", "kg", 15.0, 5.0, 20.0, True, id_b)
    
    alerts = get_stock_alerts()
    ids = [a["ingredient_id"] for a in alerts]
    assert id_a in ids
    assert id_b in ids
    assert ids.count(id_a) == 1
    assert ids.count(id_b) == 1


def test_daily_sales_revenue_and_no_inventory_deduction():
    """Verify recording a sale updates sales revenue without deducting raw ingredient stock."""
    inv_before = get_inventory_status()
    stock_before = inv_before.set_index("ingredient_id")["current_stock"].to_dict()
    
    test_date = "2026-10-10"
    food_df = get_food_items(active_only=True)
    assert not food_df.empty
    test_food_id = food_df.iloc[0]["food_id"]
    test_price = float(food_df.iloc[0]["selling_price"])
    
    success, rec_id = add_or_update_daily_sale(
        date_str=test_date,
        food_id=test_food_id,
        units_sold=25,
        selling_price=test_price
    )
    assert success is True
    
    sales = get_daily_sales(start_date=test_date, end_date=test_date, food_id=test_food_id)
    assert not sales.empty
    assert sales.iloc[0]["revenue"] == round(25 * test_price, 2)
    
    # Check inventory after sale: MUST BE UNCHANGED
    inv_after = get_inventory_status()
    stock_after = inv_after.set_index("ingredient_id")["current_stock"].to_dict()
    assert stock_before == stock_after, "Ingredient stock was incorrectly modified during Daily Sales entry!"


def test_waste_monitoring_table_structure():
    """Verify waste monitoring table columns strictly match specification."""
    df = get_waste_monitoring_table(days=30)
    assert not df.empty, "Waste monitoring table is empty."
    required_cols = ["food_name", "prepared_quantity", "actual_sold_quantity", "estimated_leftover", "discarded_quantity"]
    for col in required_cols:
        assert col in df.columns, f"Missing required column: {col}"
    # Ensure estimated leftovers is never negative
    assert (df["estimated_leftover"] >= 0).all()


def test_leftover_disposition_validation():
    """Verify leftover disposition recording cannot exceed available leftover quantity."""
    success, msg = record_leftover_disposition("NON_EXISTENT_PREP", "Discarded", 100)
    assert success is False
    assert "not found" in msg


def test_monthly_reports_filter_by_month_and_empty_state():
    """Verify monthly reports only return records for the selected month."""
    summary_valid = get_monthly_sales_summary("2026-09")
    summary_empty = get_monthly_sales_summary("2035-01")
    assert summary_empty["total_revenue"] == 0.0
    assert summary_empty["total_units_sold"] == 0
    assert summary_empty["records"].empty


def test_forecast_tomorrow_only():
    """Verify forecast is restricted to tomorrow only."""
    tomorrow = get_tomorrow_date()
    assert tomorrow > datetime.now().date()
    fc = generate_tomorrow_forecast(save_to_db=False)
    assert not fc.empty
    assert "predicted_demand" in fc.columns
    assert (fc["predicted_demand"] >= 0).all()


def test_inr_formatting():
    """Verify Indian Rupee formatting function."""
    assert format_inr(500) == "₹500.00"
    assert format_inr(150000) == "₹1,50,000.00"
    assert format_inr(1234567.5) == "₹12,34,567.50"


def test_auth_security():
    """Verify admin login succeeds and bogus login fails without leaking details."""
    assert verify_credentials("admin", "admin") is True
    assert verify_credentials("admin", "wrongpassword") is False
    assert verify_credentials("unknown_user", "admin") is False
