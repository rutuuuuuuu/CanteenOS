"""Waste Reduction and Leftover Monitoring module.
Provides factual tracking of prepared food, actual sales, estimated leftovers,
and recorded dispositions without generic or fabricated recommendations.
"""

from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

import config
from database import query_df, get_db_connection
from data_store import get_food_items

__all__ = [
    "get_waste_reduction_kpis",
    "get_waste_monitoring_table",
    "get_high_leftover_items",
    "generate_actionable_recommendations",
    "record_leftover_disposition",
    "get_waste_causes_analysis"
]


def get_waste_reduction_kpis(days: int = 30, date_filter: Optional[str] = None) -> Dict[str, Any]:
    """Calculate key leftover and waste metrics based strictly on saved database records."""
    if date_filter:
        sql = """
            SELECT p.preparation_id, p.date, p.food_id, f.food_name, f.category, f.selling_price,
                   p.planned_quantity, p.prepared_quantity, p.actual_sold_quantity,
                   p.unsold_quantity, p.disposition
            FROM preparations p
            JOIN food_items f ON p.food_id = f.food_id
            WHERE p.date = ? AND p.status IN ('Confirmed', 'Completed');
        """
        params = (date_filter,)
    else:
        cutoff_date = (datetime.now().date() - timedelta(days=days)).strftime("%Y-%m-%d")
        sql = """
            SELECT p.preparation_id, p.date, p.food_id, f.food_name, f.category, f.selling_price,
                   p.planned_quantity, p.prepared_quantity, p.actual_sold_quantity,
                   p.unsold_quantity, p.disposition
            FROM preparations p
            JOIN food_items f ON p.food_id = f.food_id
            WHERE p.date >= ? AND p.status IN ('Confirmed', 'Completed');
        """
        params = (cutoff_date,)
        
    df = query_df(sql, params)
    
    if df.empty:
        return {
            "total_prepared": 0,
            "total_sold": 0,
            "total_leftovers": 0,
            "total_unsold": 0,
            "unsold_rate": 0.0,
            "leftover_rate": 0.0,
            "total_discarded": 0,
            "discarded_rate": 0.0,
            "awaiting_disposition": 0,
            "estimated_loss_value": 0.0,
            "records_count": 0,
            "data": pd.DataFrame()
        }
        
    tot_prep = int(df["prepared_quantity"].sum())
    tot_sold = int(df["actual_sold_quantity"].sum())
    df["calculated_leftover"] = (df["prepared_quantity"] - df["actual_sold_quantity"]).apply(lambda x: max(0, int(x)))
    tot_leftover = int(df["calculated_leftover"].sum())
    
    disc_df = df[df["disposition"] == "Discarded"]
    tot_disc = int(disc_df["unsold_quantity"].sum()) if not disc_df.empty else 0
    
    unrec_df = df[df["disposition"].isin(["Not Recorded", "Pending"])]
    awaiting_disp = int(unrec_df["calculated_leftover"].sum()) if not unrec_df.empty else 0
    
    loss_val = float((df["calculated_leftover"] * df["selling_price"]).sum())
    leftover_rate = round((tot_leftover / max(1, tot_prep)) * 100.0, 1)
    disc_rate = round((tot_disc / max(1, tot_prep)) * 100.0, 1)
    
    return {
        "total_prepared": tot_prep,
        "total_sold": tot_sold,
        "total_leftovers": tot_leftover,
        "total_unsold": tot_leftover,
        "unsold_rate": leftover_rate,
        "leftover_rate": leftover_rate,
        "total_discarded": tot_disc,
        "discarded_rate": disc_rate,
        "awaiting_disposition": awaiting_disp,
        "estimated_loss_value": round(loss_val, 2),
        "records_count": len(df),
        "data": df
    }


def get_waste_monitoring_table(days: int = 30, date_filter: Optional[str] = None) -> pd.DataFrame:
    """Return compact, factual waste monitoring table with required columns:
    | Food Item | Prepared | Sold | Estimated Leftover | Discarded |
    """
    if date_filter:
        sql = """
            SELECT f.food_id, f.food_name, f.category, f.selling_price,
                   SUM(p.prepared_quantity) as prepared_quantity,
                   SUM(p.actual_sold_quantity) as actual_sold_quantity,
                   SUM(MAX(0, p.prepared_quantity - p.actual_sold_quantity)) as estimated_leftover,
                   SUM(CASE WHEN p.disposition = 'Discarded' THEN p.unsold_quantity ELSE 0 END) as discarded_quantity,
                   SUM(CASE WHEN p.disposition IN ('Stored or Reused', 'Donated') THEN p.unsold_quantity ELSE 0 END) as saved_quantity,
                   COUNT(p.preparation_id) as batch_count,
                   COUNT(p.preparation_id) as batches_count
            FROM preparations p
            JOIN food_items f ON p.food_id = f.food_id
            WHERE p.date = ? AND p.status IN ('Confirmed', 'Completed')
            GROUP BY f.food_id, f.food_name, f.category, f.selling_price
            HAVING SUM(p.prepared_quantity) > 0
            ORDER BY estimated_leftover DESC;
        """
        params = (date_filter,)
    else:
        cutoff_date = (datetime.now().date() - timedelta(days=days)).strftime("%Y-%m-%d")
        sql = """
            SELECT f.food_id, f.food_name, f.category, f.selling_price,
                   SUM(p.prepared_quantity) as prepared_quantity,
                   SUM(p.actual_sold_quantity) as actual_sold_quantity,
                   SUM(MAX(0, p.prepared_quantity - p.actual_sold_quantity)) as estimated_leftover,
                   SUM(CASE WHEN p.disposition = 'Discarded' THEN p.unsold_quantity ELSE 0 END) as discarded_quantity,
                   SUM(CASE WHEN p.disposition IN ('Stored or Reused', 'Donated') THEN p.unsold_quantity ELSE 0 END) as saved_quantity,
                   COUNT(p.preparation_id) as batch_count,
                   COUNT(p.preparation_id) as batches_count
            FROM preparations p
            JOIN food_items f ON p.food_id = f.food_id
            WHERE p.date >= ? AND p.status IN ('Confirmed', 'Completed')
            GROUP BY f.food_id, f.food_name, f.category, f.selling_price
            HAVING SUM(p.prepared_quantity) > 0
            ORDER BY estimated_leftover DESC;
        """
        params = (cutoff_date,)
        
    df = query_df(sql, params)
    if not df.empty:
        df["total_prepared"] = df["prepared_quantity"]
        df["total_sold"] = df["actual_sold_quantity"]
        df["total_unsold"] = df["estimated_leftover"]
        df["leftover_pct"] = (df["estimated_leftover"] / df["prepared_quantity"].replace(0, 1) * 100.0).round(1)
        df["estimated_loss_value"] = (df["estimated_leftover"] * df["selling_price"]).round(2)
    return df


def get_high_leftover_items(days: int = 30) -> pd.DataFrame:
    """Identify foods with recurring leftovers based strictly on historical records."""
    return get_waste_monitoring_table(days=days)


def record_leftover_disposition(
    preparation_id: str,
    disposition: str,
    quantity: int
) -> Tuple[bool, str]:
    """Record the leftover disposition (Stored, Reused, Donated, Discarded) with validation."""
    if disposition not in ["Stored or Reused", "Donated", "Discarded", "Not Recorded"]:
        return False, f"Invalid disposition '{disposition}'."
        
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT prepared_quantity, actual_sold_quantity FROM preparations WHERE preparation_id = ?;", (preparation_id,))
        row = cursor.fetchone()
        if not row:
            return False, f"Preparation record '{preparation_id}' not found."
            
        prep_qty = int(row[0])
        sold_qty = int(row[1])
        max_leftover = max(0, prep_qty - sold_qty)
        
        if quantity > max_leftover:
            return False, f"Disposition quantity ({quantity}) cannot exceed available leftover quantity ({max_leftover})."
            
        cursor.execute("""
            UPDATE preparations
            SET unsold_quantity = ?, disposition = ?
            WHERE preparation_id = ?;
        """, (int(quantity), disposition, preparation_id))
        
        conn.commit()
        return True, f"Leftover disposition recorded: {quantity} servings marked as '{disposition}'."
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        conn.close()


def get_waste_causes_analysis(days: int = 30) -> Dict[str, Any]:
    """Perform factual historical analysis on where and why excess preparation occurred."""
    cutoff_date = (datetime.now().date() - timedelta(days=days)).strftime("%Y-%m-%d")
    sql = """
        SELECT p.preparation_id, p.date, p.food_id, f.food_name, f.category,
               p.planned_quantity, p.prepared_quantity, p.actual_sold_quantity,
               (p.prepared_quantity - p.actual_sold_quantity) as excess_quantity,
               p.disposition
        FROM preparations p
        JOIN food_items f ON p.food_id = f.food_id
        WHERE p.date >= ? AND p.status IN ('Confirmed', 'Completed')
        ORDER BY excess_quantity DESC;
    """
    df = query_df(sql, (cutoff_date,))
    
    if df.empty:
        return {
            "excess_records": pd.DataFrame(),
            "excess_by_food": pd.DataFrame(),
            "excess_by_date": pd.DataFrame(),
            "total_excess_servings": 0
        }
        
    excess_df = df[df["excess_quantity"] > 0].copy()
    
    excess_by_food = excess_df.groupby(["food_id", "food_name", "category"]).agg({
        "excess_quantity": "sum",
        "preparation_id": "count"
    }).reset_index().rename(columns={"preparation_id": "excess_batches_count"}).sort_values("excess_quantity", ascending=False)
    
    excess_by_date = excess_df.groupby("date").agg({
        "excess_quantity": "sum",
        "food_id": "count"
    }).reset_index().rename(columns={"food_id": "items_with_excess"}).sort_values("date", ascending=False)
    
    return {
        "excess_records": excess_df,
        "excess_by_food": excess_by_food,
        "excess_by_date": excess_by_date,
        "total_excess_servings": int(excess_df["excess_quantity"].sum()) if not excess_df.empty else 0
    }


def generate_actionable_recommendations() -> List[Dict[str, str]]:
    """Generate strictly factual operational notices only when supported by database records."""
    notices = []
    
    # 1. Check for recurring excess preparation
    causes = get_waste_causes_analysis(days=21)
    if not causes["excess_by_food"].empty:
        top_excess = causes["excess_by_food"].iloc[0]
        if top_excess["excess_quantity"] > 10:
            notices.append({
                "type": "warning",
                "title": f"Excess Preparation: {top_excess['food_name']}",
                "description": f"Preparation exceeded sales for {top_excess['food_name']} by {top_excess['excess_quantity']} servings across {top_excess['excess_batches_count']} batches in the past 3 weeks."
            })
            
    # 2. Check for unrecorded dispositions
    kpis = get_waste_reduction_kpis(days=14)
    if kpis["awaiting_disposition"] > 0:
        notices.append({
            "type": "info",
            "title": "Leftovers Awaiting Disposition",
            "description": f"{kpis['awaiting_disposition']} leftover servings are recorded as pending disposition. Record whether food was stored, donated, or discarded."
        })
        
    if not notices:
        notices.append({
            "type": "info",
            "title": "Waste Monitoring Active",
            "description": "Prepared quantities, sales, and leftover dispositions are tracked in real-time from database records."
        })
        
    return notices
