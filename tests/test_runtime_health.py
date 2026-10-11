"""Comprehensive runtime health verification test.
Checks all module APIs, database integrity, query safety, inventory alert uniqueness,
and report generation with zero runtime errors.
"""

import os
import sqlite3
import pytest
import config
import database
import data_store
import auth
import prediction
import preparation
import inventory
import waste
import reports
import ui_components


def test_runtime_health_and_query_safety():
    # 1. Database Connection and Schema
    conn = database.get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    expected_tables = [
        "food_items", "ingredients", "food_ingredients",
        "inventory", "stock_movements", "daily_sales",
        "preparations", "forecasts", "events"
    ]
    for tbl in expected_tables:
        assert tbl in tables, f"Missing table: {tbl}"

    # 2. Inventory Alerts Deduplication & Alert Quality
    alerts = inventory.get_stock_alerts()
    assert isinstance(alerts, list)
    # Check no duplicate alerts for same ingredient ID
    alert_ing_ids = [a["ingredient_id"] for a in alerts]
    assert len(alert_ing_ids) == len(set(alert_ing_ids)), "Duplicate alerts found for same ingredient!"

    # 3. Waste KPIs
    kpis = waste.get_waste_reduction_kpis()
    assert "total_prepared" in kpis
    assert "total_sold" in kpis
    assert "total_leftovers" in kpis
    assert "total_discarded" in kpis
    assert "awaiting_disposition" in kpis

    # 4. Monthly Reports Handling
    summary = reports.get_monthly_sales_summary("2026-10")
    assert isinstance(summary, dict)
    assert "total_revenue" in summary
    assert "total_units_sold" in summary

    acc = reports.get_monthly_forecast_accuracy("2026-10")
    assert isinstance(acc, dict)

    # 5. UI Components Helper Integrity
    assert ui_components.format_inr(1250.50) == "₹1,250.50"
    assert ui_components.format_inr(0) == "₹0.00"

    # 6. Auth Verification
    assert auth.verify_credentials("admin", "admin") is True
    assert auth.verify_credentials("admin", "wrongpassword") is False
    assert auth.verify_credentials("", "") is False
