"""Monthly Reports and Analytics calculation module.
Computes comprehensive monthly summaries for sales performance, forecast accuracy,
ingredient consumption, preparation efficiency, and leftover tracking.
"""

from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime
import pandas as pd
import numpy as np

import config
from database import query_df
from data_store import get_inventory_status, get_food_items


def get_monthly_sales_summary(month_str: str, category: Optional[str] = None) -> Dict[str, Any]:
    """Calculate monthly sales performance metrics for a specific month (YYYY-MM)."""
    sql = """
        SELECT s.record_id, s.date, s.food_id, f.food_name, f.category,
               s.units_sold, s.selling_price, s.revenue, s.event_name
        FROM daily_sales s
        JOIN food_items f ON s.food_id = f.food_id
        WHERE s.date LIKE ?
    """
    params = [f"{month_str}%"]
    if category and category != "All Categories":
        sql += " AND f.category = ?"
        params.append(category)
        
    sql += " ORDER BY s.date ASC;"
    df = query_df(sql, tuple(params))
    
    if df.empty:
        return {
            "total_revenue": 0.0,
            "total_units_sold": 0,
            "total_days": 0,
            "avg_daily_revenue": 0.0,
            "daily_trend": pd.DataFrame(),
            "category_summary": pd.DataFrame(),
            "top_selling_items": pd.DataFrame(),
            "lowest_selling_items": pd.DataFrame(),
            "records": df
        }
        
    tot_rev = float(df["revenue"].sum())
    tot_units = int(df["units_sold"].sum())
    unique_days = df["date"].nunique()
    avg_rev = round(tot_rev / max(1, unique_days), 2)
    
    daily_trend = df.groupby("date").agg({
        "revenue": "sum",
        "units_sold": "sum"
    }).reset_index().sort_values("date")
    
    cat_summary = df.groupby("category").agg({
        "revenue": "sum",
        "units_sold": "sum"
    }).reset_index().sort_values("revenue", ascending=False)
    
    item_perf = df.groupby(["food_id", "food_name", "category"]).agg({
        "revenue": "sum",
        "units_sold": "sum"
    }).reset_index().sort_values("units_sold", ascending=False)
    
    top_items = item_perf.head(8)
    lowest_items = item_perf.tail(8).sort_values("units_sold", ascending=True)
    
    return {
        "total_revenue": round(tot_rev, 2),
        "total_units_sold": tot_units,
        "total_days": unique_days,
        "avg_daily_revenue": avg_rev,
        "daily_trend": daily_trend,
        "category_summary": cat_summary,
        "top_selling_items": top_items,
        "lowest_selling_items": lowest_items,
        "records": df
    }


def get_monthly_forecast_accuracy(month_str: str) -> Dict[str, Any]:
    """Calculate forecast error metrics and comparisons for the selected month."""
    sql = """
        SELECT fc.target_date, fc.food_id, f.food_name, f.category,
               fc.predicted_demand, s.units_sold as actual_demand,
               ABS(fc.predicted_demand - s.units_sold) as absolute_error
        FROM forecasts fc
        JOIN food_items f ON fc.food_id = f.food_id
        JOIN daily_sales s ON fc.target_date = s.date AND fc.food_id = s.food_id
        WHERE fc.target_date LIKE ?
        ORDER BY fc.target_date ASC;
    """
    df = query_df(sql, (f"{month_str}%",))
    
    if df.empty:
        return {
            "overall_mae": 0.0,
            "overall_rmse": 0.0,
            "overall_mape": 0.0,
            "matched_count": 0,
            "daily_comparison": pd.DataFrame(),
            "item_accuracy": pd.DataFrame()
        }
        
    mae = float(df["absolute_error"].mean())
    rmse = float(np.sqrt((df["absolute_error"] ** 2).mean()))
    
    df["percentage_error"] = np.where(
        df["actual_demand"] > 0,
        (df["absolute_error"] / df["actual_demand"]) * 100.0,
        0.0
    ).round(1)
    mape = float(df["percentage_error"].mean())
    
    daily_comp = df.groupby("target_date").agg({
        "predicted_demand": "sum",
        "actual_demand": "sum"
    }).reset_index().sort_values("target_date")
    
    item_acc = df.groupby(["food_id", "food_name", "category"]).agg({
        "predicted_demand": "sum",
        "actual_demand": "sum",
        "absolute_error": "mean",
        "percentage_error": "mean"
    }).reset_index().round(2).sort_values("absolute_error")
    
    return {
        "overall_mae": round(mae, 2),
        "overall_rmse": round(rmse, 2),
        "overall_mape": round(mape, 1),
        "matched_count": len(df),
        "daily_comparison": daily_comp,
        "item_accuracy": item_acc
    }


def get_monthly_preparation_and_leftovers(month_str: str) -> Dict[str, Any]:
    """Calculate preparation efficiency and leftover breakdown for the selected month."""
    sql = """
        SELECT p.preparation_id, p.date, p.food_id, f.food_name, f.category,
               p.planned_quantity, p.prepared_quantity, p.actual_sold_quantity,
               p.unsold_quantity, p.disposition, f.selling_price
        FROM preparations p
        JOIN food_items f ON p.food_id = f.food_id
        WHERE p.date LIKE ? AND p.status IN ('Confirmed', 'Completed')
        ORDER BY p.date ASC;
    """
    df = query_df(sql, (f"{month_str}%",))
    
    if df.empty:
        return {
            "total_prepared": 0,
            "total_sold": 0,
            "total_unsold": 0,
            "unsold_percentage": 0.0,
            "total_discarded": 0,
            "daily_trend": pd.DataFrame(),
            "disposition_summary": pd.DataFrame(),
            "item_breakdown": pd.DataFrame()
        }
        
    tot_prep = int(df["prepared_quantity"].sum())
    tot_sold = int(df["actual_sold_quantity"].sum())
    tot_unsold = int(df["unsold_quantity"].sum())
    unsold_pct = round((tot_unsold / max(1, tot_prep)) * 100.0, 1)
    
    disc_df = df[df["disposition"] == "Discarded"]
    tot_disc = int(disc_df["unsold_quantity"].sum()) if not disc_df.empty else 0
    
    daily_trend = df.groupby("date").agg({
        "prepared_quantity": "sum",
        "actual_sold_quantity": "sum",
        "unsold_quantity": "sum"
    }).reset_index().sort_values("date")
    
    disp_summary = df.groupby("disposition").agg({
        "unsold_quantity": "sum"
    }).reset_index().sort_values("unsold_quantity", ascending=False)
    
    item_breakdown = df.groupby(["food_id", "food_name", "category"]).agg({
        "prepared_quantity": "sum",
        "actual_sold_quantity": "sum",
        "unsold_quantity": "sum"
    }).reset_index().sort_values("unsold_quantity", ascending=False)
    
    return {
        "total_prepared": tot_prep,
        "total_sold": tot_sold,
        "total_unsold": tot_unsold,
        "unsold_percentage": unsold_pct,
        "total_discarded": tot_disc,
        "daily_trend": daily_trend,
        "disposition_summary": disp_summary,
        "item_breakdown": item_breakdown
    }


def get_monthly_inventory_movements(month_str: str) -> Dict[str, Any]:
    """Calculate ingredient consumption and purchase receipts for the selected month."""
    sql = """
        SELECT m.movement_id, m.timestamp, m.ingredient_id, i.ingredient_name,
               m.movement_type, m.quantity, m.unit, m.reference_id, m.notes,
               i.unit_cost, (m.quantity * i.unit_cost) as movement_value
        FROM stock_movements m
        JOIN ingredients i ON m.ingredient_id = i.ingredient_id
        WHERE m.timestamp LIKE ?
        ORDER BY m.timestamp DESC;
    """
    df = query_df(sql, (f"{month_str}%",))
    
    if df.empty:
        return {
            "total_purchases_value": 0.0,
            "total_consumed_value": 0.0,
            "type_summary": pd.DataFrame(),
            "top_consumed": pd.DataFrame(),
            "records": df
        }
        
    purchases = df[df["movement_type"] == "Purchase"]
    consumption = df[df["movement_type"] == "Consumption"]
    
    p_val = float(purchases["movement_value"].sum()) if not purchases.empty else 0.0
    c_val = float(consumption["movement_value"].sum()) if not consumption.empty else 0.0
    
    type_summary = df.groupby("movement_type").agg({
        "movement_id": "count",
        "movement_value": "sum"
    }).reset_index().rename(columns={"movement_id": "transaction_count", "movement_value": "total_value"})
    
    if not consumption.empty:
        top_consumed = consumption.groupby(["ingredient_id", "ingredient_name", "unit"]).agg({
            "quantity": "sum",
            "movement_value": "sum"
        }).reset_index().sort_values("quantity", ascending=False).head(8)
    else:
        top_consumed = pd.DataFrame()
        
    return {
        "total_purchases_value": round(p_val, 2),
        "total_consumed_value": round(c_val, 2),
        "type_summary": type_summary,
        "top_consumed": top_consumed,
        "records": df
    }
