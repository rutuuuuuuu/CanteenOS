"""Comprehensive End-to-End Page Execution & Error Audit.
Simulates all operations, data flows, and queries across all 7 sections to ensure 0 exceptions.
"""

import os
import sqlite3
import pandas as pd
from datetime import datetime

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


def test_dashboard_data_flow():
    today_str = datetime.now().date().strftime("%Y-%m-%d")
    today_sales = data_store.get_daily_sales(start_date=today_str, end_date=today_str)
    inv_df = data_store.get_inventory_status()
    alerts = inventory.get_stock_alerts()
    tomorrow_fc = prediction.generate_tomorrow_forecast(save_to_db=False)
    
    assert isinstance(today_sales, pd.DataFrame)
    assert isinstance(inv_df, pd.DataFrame)
    assert isinstance(alerts, list)
    assert isinstance(tomorrow_fc, pd.DataFrame)
    assert "predicted_demand" in tomorrow_fc.columns
    assert "estimated_revenue" in tomorrow_fc.columns


def test_food_management_data_flow():
    food_df = data_store.get_food_items()
    ings = data_store.get_ingredients()
    assert isinstance(food_df, pd.DataFrame)
    assert isinstance(ings, pd.DataFrame)
    if not food_df.empty:
        first_food = food_df.iloc[0]["food_id"]
        food_ings = data_store.get_food_ingredients(first_food)
        assert isinstance(food_ings, pd.DataFrame)


def test_daily_sales_data_flow():
    sales = data_store.get_daily_sales()
    assert isinstance(sales, pd.DataFrame)
    assert "revenue" in sales.columns
    assert "units_sold" in sales.columns
    assert "selling_price" in sales.columns


def test_demand_forecast_data_flow():
    fc = prediction.generate_tomorrow_forecast(event_name="Regular College Day", is_exam_period=False, save_to_db=False)
    assert not fc.empty
    assert "predicted_demand" in fc.columns
    assert "estimated_revenue" in fc.columns
    assert "explanation" in fc.columns
    
    plan_dict = {row["food_id"]: int(row["predicted_demand"]) for _, row in fc.iterrows()}
    summary_req, breakdown, is_feasible = preparation.calculate_ingredient_requirements(plan_dict)
    assert isinstance(summary_req, pd.DataFrame)
    assert isinstance(breakdown, pd.DataFrame)
    assert isinstance(is_feasible, bool)


def test_inventory_data_flow():
    kpis = inventory.get_inventory_kpis()
    assert "total_ingredients" in kpis
    assert "in_stock_count" in kpis
    assert "low_stock_count" in kpis
    assert "out_of_stock_count" in kpis
    
    status_df = data_store.get_inventory_status()
    assert "current_stock" in status_df.columns
    assert "reorder_level" in status_df.columns
    assert "stock_status" in status_df.columns


def test_waste_reduction_data_flow():
    kpis = waste.get_waste_reduction_kpis(days=30)
    assert "total_prepared" in kpis
    assert "total_sold" in kpis
    assert "total_leftovers" in kpis
    assert "total_discarded" in kpis
    
    tbl = waste.get_waste_monitoring_table(days=30)
    assert isinstance(tbl, pd.DataFrame)
    
    causes = waste.get_waste_causes_analysis(days=30)
    assert "excess_by_food" in causes
    assert "excess_by_date" in causes


def test_monthly_reports_data_flow():
    cur_month = datetime.now().date().strftime("%Y-%m")
    m_sales = reports.get_monthly_sales_summary(cur_month)
    m_inv = reports.get_monthly_inventory_movements(cur_month)
    m_prep = reports.get_monthly_preparation_and_leftovers(cur_month)
    
    assert "total_revenue" in m_sales
    assert "total_units_sold" in m_sales
    assert "records" in m_inv
    assert "total_prepared" in m_prep
