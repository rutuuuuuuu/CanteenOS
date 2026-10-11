"""Preparation planning, recipe-based ingredient requirement calculations,
stock feasibility checking, preparation confirmation, and leftover tracking.
"""

from typing import Dict, List, Tuple, Optional, Any
import pandas as pd
from datetime import datetime

import config
from database import get_db_connection, query_df
from data_store import (
    get_food_items,
    get_ingredients,
    get_inventory_status,
    generate_unique_id
)
from validation import (
    convert_between_units,
    validate_preparation_sales_update,
    ValidationError
)


def calculate_ingredient_requirements(
    plan_dict: Dict[str, int]  # food_id -> planned_servings
) -> Tuple[pd.DataFrame, pd.DataFrame, bool]:
    """Calculate aggregate ingredient requirements from food_ingredients and verify stock feasibility.
    
    Returns:
        (summary_df, item_breakdown_df, is_feasible)
    """
    if not plan_dict or sum(plan_dict.values()) <= 0:
        return pd.DataFrame(), pd.DataFrame(), True
        
    conn = get_db_connection()
    try:
        breakdown_rows = []
        
        for food_id, servings in plan_dict.items():
            if servings <= 0:
                continue
                
            cursor = conn.cursor()
            cursor.execute("SELECT food_name FROM food_items WHERE food_id = ?;", (food_id,))
            f_row = cursor.fetchone()
            food_name = f_row[0] if f_row else food_id
            
            cursor.execute("""
                SELECT fi.ingredient_id, i.ingredient_name, fi.quantity_per_serving,
                       fi.quantity_unit, i.unit as canonical_unit, i.unit_cost
                FROM food_ingredients fi
                JOIN ingredients i ON fi.ingredient_id = i.ingredient_id
                WHERE fi.food_id = ?;
            """, (food_id,))
            ing_rows = cursor.fetchall()
            
            if not ing_rows:
                breakdown_rows.append({
                    "food_id": food_id,
                    "food_name": food_name,
                    "planned_servings": servings,
                    "ingredient_id": "NONE",
                    "ingredient_name": "No Ingredients Defined (Warning)",
                    "qty_per_serving": 0.0,
                    "quantity_unit": "-",
                    "total_required_canonical": 0.0,
                    "canonical_unit": "-",
                    "unit_cost": 0.0,
                    "has_recipe": False
                })
                continue
                
            for r in ing_rows:
                ing_id = r["ingredient_id"]
                ing_name = r["ingredient_name"]
                qty_per_serving = float(r["quantity_per_serving"])
                rcp_unit = r["quantity_unit"]
                canonical_unit = r["canonical_unit"]
                unit_cost = float(r["unit_cost"])
                
                qty_in_canonical = convert_between_units(qty_per_serving, rcp_unit, canonical_unit)
                total_req = qty_in_canonical * servings
                
                breakdown_rows.append({
                    "food_id": food_id,
                    "food_name": food_name,
                    "planned_servings": servings,
                    "ingredient_id": ing_id,
                    "ingredient_name": ing_name,
                    "qty_per_serving": qty_per_serving,
                    "quantity_unit": rcp_unit,
                    "total_required_canonical": total_req,
                    "canonical_unit": canonical_unit,
                    "unit_cost": unit_cost,
                    "has_recipe": True
                })
                
        if not breakdown_rows:
            return pd.DataFrame(), pd.DataFrame(), True
            
        df_breakdown = pd.DataFrame(breakdown_rows)
        valid_breakdown = df_breakdown[df_breakdown["has_recipe"] == True]
        
        if valid_breakdown.empty:
            return pd.DataFrame(), df_breakdown, True
            
        # Aggregate by ingredient_id
        grouped = valid_breakdown.groupby(["ingredient_id", "ingredient_name", "canonical_unit", "unit_cost"])["total_required_canonical"].sum().reset_index()
        grouped.rename(columns={"total_required_canonical": "required_quantity"}, inplace=True)
        
        # Merge with live inventory
        inv_df = get_inventory_status()
        if not inv_df.empty:
            grouped = pd.merge(grouped, inv_df[["ingredient_id", "current_stock"]], on="ingredient_id", how="left")
            grouped["current_stock"] = grouped["current_stock"].fillna(0.0)
        else:
            grouped["current_stock"] = 0.0
            
        grouped["required_quantity"] = grouped["required_quantity"].round(3)
        grouped["current_stock"] = grouped["current_stock"].round(3)
        grouped["shortage"] = (grouped["required_quantity"] - grouped["current_stock"]).apply(lambda x: max(0.0, round(x, 3)))
        grouped["status"] = grouped["shortage"].apply(lambda s: "Sufficient" if s <= 0 else "Insufficient")
        grouped["estimated_cost"] = (grouped["required_quantity"] * grouped["unit_cost"]).round(2)
        
        is_feasible = bool((grouped["shortage"] <= 0).all())
        return grouped, df_breakdown, is_feasible
    finally:
        conn.close()


def confirm_preparation_plan(
    prep_date_str: str,
    plan_dict: Dict[str, int],  # food_id -> planned_servings
    batch_notes: str = ""
) -> Tuple[bool, str, List[str]]:
    """Atomically confirm preparation plan in SQLite, deduct ingredients,
    and record preparation rows and stock movements in a single transaction.
    """
    if not plan_dict or sum(plan_dict.values()) <= 0:
        return False, "Plan is empty. Please enter positive planned servings.", []
        
    summary_df, _, is_feasible = calculate_ingredient_requirements(plan_dict)
    
    if summary_df.empty:
        return False, "No recipe ingredients found for planned food items.", []
        
    if not is_feasible:
        shortages = summary_df[summary_df["shortage"] > 0]
        short_msgs = [f"{row['ingredient_name']}: short by {row['shortage']} {row['canonical_unit']}" for _, row in shortages.iterrows()]
        return False, "Cannot confirm preparation. Insufficient inventory for:\n" + "\n".join(short_msgs), []
        
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        batch_ref = f"PREP_{prep_date_str.replace('-', '')}_{datetime.now().strftime('%H%M%S')}"
        
        # 1. Recheck live stock right before committing
        for _, row in summary_df.iterrows():
            ing_id = row["ingredient_id"]
            req_qty = float(row["required_quantity"])
            cursor.execute("SELECT current_stock FROM inventory WHERE ingredient_id = ?;", (ing_id,))
            curr_row = cursor.fetchone()
            curr_stock = float(curr_row[0]) if curr_row else 0.0
            
            if curr_stock < req_qty:
                conn.rollback()
                return False, f"Live stock discrepancy for {row['ingredient_name']}: Required {req_qty}, available {curr_stock}.", []
                
        # 2. Perform inventory deductions & stock movements
        cursor.execute("SELECT movement_id FROM stock_movements;")
        existing_mov_ids = [r[0] for r in cursor.fetchall()]
        
        for _, row in summary_df.iterrows():
            ing_id = row["ingredient_id"]
            req_qty = float(row["required_quantity"])
            canonical_unit = row["canonical_unit"]
            
            cursor.execute("""
                UPDATE inventory 
                SET current_stock = current_stock - ?, last_updated = ?
                WHERE ingredient_id = ?;
            """, (req_qty, now_str, ing_id))
            
            mov_id = generate_unique_id("MOV", existing_mov_ids)
            existing_mov_ids.append(mov_id)
            cursor.execute("""
                INSERT INTO stock_movements (movement_id, timestamp, ingredient_id, movement_type, quantity, unit, reference_id, notes)
                VALUES (?, ?, ?, 'Consumption', ?, ?, ?, ?);
            """, (mov_id, now_str, ing_id, req_qty, canonical_unit, batch_ref, f"Consumed for prep batch {batch_ref} on {prep_date_str}. {batch_notes}".strip()))
            
        # 3. Insert preparation records
        cursor.execute("SELECT preparation_id FROM preparations;")
        existing_prep_ids = [r[0] for r in cursor.fetchall()]
        created_prep_ids = []
        
        for food_id, servings in plan_dict.items():
            if servings <= 0:
                continue
            prep_id = generate_unique_id("PREP", existing_prep_ids)
            existing_prep_ids.append(prep_id)
            created_prep_ids.append(prep_id)
            
            cursor.execute("""
                INSERT INTO preparations (preparation_id, date, food_id, planned_quantity, prepared_quantity, actual_sold_quantity, unsold_quantity, status, disposition, confirmed_at)
                VALUES (?, ?, ?, ?, ?, 0, ?, 'Confirmed', 'Not Recorded', ?);
            """, (prep_id, prep_date_str, food_id, int(servings), int(servings), int(servings), now_str))
            
        conn.commit()
        return True, f"Preparation batch '{batch_ref}' confirmed successfully! Raw ingredients deducted from inventory.", created_prep_ids
    except Exception as e:
        conn.rollback()
        return False, str(e), []
    finally:
        conn.close()


def record_preparation_actual_sales(
    preparation_id: str,
    actual_sold_quantity: int,
    disposition: str = "Not Recorded"
) -> Tuple[bool, str]:
    """Record actual sold servings for a confirmed preparation batch and calculate leftovers."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT prepared_quantity FROM preparations WHERE preparation_id = ?;", (preparation_id,))
        row = cursor.fetchone()
        if not row:
            return False, f"Preparation record '{preparation_id}' not found."
            
        prepared_qty = int(row[0])
        
        errors = validate_preparation_sales_update(prepared_qty, actual_sold_quantity)
        if errors:
            return False, "; ".join(errors)
            
        unsold_qty = max(0, prepared_qty - int(actual_sold_quantity))
        
        cursor.execute("""
            UPDATE preparations
            SET actual_sold_quantity = ?, unsold_quantity = ?, disposition = ?, status = 'Completed'
            WHERE preparation_id = ?;
        """, (int(actual_sold_quantity), unsold_qty, disposition, preparation_id))
        
        conn.commit()
        return True, f"Actual sales recorded ({actual_sold_quantity}/{prepared_qty} sold). Leftovers: {unsold_qty} servings ({disposition})."
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        conn.close()


def get_preparations_history(prep_date: Optional[str] = None) -> pd.DataFrame:
    """Retrieve historical preparation records joined with food details."""
    sql = """
        SELECT p.preparation_id, p.date, p.food_id, f.food_name, f.category,
               p.planned_quantity, p.prepared_quantity, p.actual_sold_quantity,
               p.unsold_quantity, p.status, p.disposition, p.confirmed_at,
               f.selling_price, (p.actual_sold_quantity * f.selling_price) as realized_revenue
        FROM preparations p
        JOIN food_items f ON p.food_id = f.food_id
        WHERE 1=1
    """
    params = []
    if prep_date:
        sql += " AND p.date = ?"
        params.append(prep_date)
        
    sql += " ORDER BY p.confirmed_at DESC, p.date DESC;"
    return query_df(sql, tuple(params))
