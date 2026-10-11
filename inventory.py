"""Inventory management and stock calculation module.
Handles stock level tracking, replenishment recommendations, purchases,
adjustments, and stock movement auditing.
"""

from typing import Dict, List, Tuple, Optional, Any
import pandas as pd
from datetime import datetime

import config
from database import query_df, get_db_connection
from data_store import (
    get_inventory_status,
    get_ingredients,
    append_stock_movement,
    add_or_update_ingredient
)
from validation import (
    validate_ingredient_input,
    validate_stock_movement,
    convert_between_units,
    ValidationError
)


def get_inventory_kpis() -> Dict[str, Any]:
    """Calculate key inventory performance indicators from live database records."""
    df = get_inventory_status()
    if df.empty:
        return {
            "total_ingredients": 0,
            "in_stock_count": 0,
            "low_stock_count": 0,
            "out_of_stock_count": 0,
            "total_inventory_value": 0.0,
            "items_needing_reorder": 0
        }
        
    in_stock = (df["stock_status"] == "In Stock").sum()
    low_stock = (df["stock_status"] == "Low Stock").sum()
    out_stock = (df["stock_status"] == "Out of Stock").sum()
    total_val = float(df["stock_value"].sum())
    reorder_count = low_stock + out_stock
    
    return {
        "total_ingredients": len(df),
        "in_stock_count": int(in_stock),
        "low_stock_count": int(low_stock),
        "out_of_stock_count": int(out_stock),
        "total_inventory_value": round(total_val, 2),
        "items_needing_reorder": int(reorder_count)
    }


def get_stock_alerts() -> List[Dict[str, Any]]:
    """Return factual alerts for ingredients that require replenishment.
    Strictly deduplicated by ingredient_id so each distinct ingredient produces exactly one warning.
    Distinguishes zero stock (Out of Stock error) from low stock (warning).
    """
    df = get_inventory_status()
    if df.empty:
        return []
        
    alerts = []
    seen_ids = set()
    
    for _, row in df.iterrows():
        ing_id = row["ingredient_id"]
        if ing_id in seen_ids:
            continue
            
        ing_name = str(row["ingredient_name"]).strip()
        curr_stock = float(row["current_stock"])
        unit = str(row["unit"]).strip()
        reorder_lvl = float(row["reorder_level"])
        
        # Determine real stock issues only
        if curr_stock <= 0:
            seen_ids.add(ing_id)
            alerts.append({
                "ingredient_id": ing_id,
                "ingredient_name": ing_name,
                "current_stock": curr_stock,
                "unit": unit,
                "reorder_level": reorder_lvl,
                "status": "Out of Stock",
                "message": f"Stock unavailable: {ing_name} — 0.00 {unit}. Record a stock receipt before confirming preparation.",
                "type": "error"
            })
        elif curr_stock <= reorder_lvl and reorder_lvl > 0:
            seen_ids.add(ing_id)
            alerts.append({
                "ingredient_id": ing_id,
                "ingredient_name": ing_name,
                "current_stock": curr_stock,
                "unit": unit,
                "reorder_level": reorder_lvl,
                "status": "Low Stock",
                "message": f"Low stock alert: {ing_name} — {curr_stock:.2f} {unit} remaining (Reorder threshold: {reorder_lvl:.2f} {unit}).",
                "type": "warning"
            })
            
    return alerts


def record_ingredient_purchase(
    ingredient_id: str,
    quantity: float,
    unit: str,
    purchase_order_ref: str = "",
    notes: str = ""
) -> Tuple[bool, str]:
    """Record incoming purchase / receipt of stock."""
    errors = validate_stock_movement(ingredient_id, "Purchase", quantity, unit)
    if errors:
        return False, "; ".join(errors)
        
    ref = purchase_order_ref.strip() or f"PO_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    note_text = notes.strip() or "Standard supplier receipt"
    
    success, msg = append_stock_movement(
        ingredient_id=ingredient_id,
        movement_type="Purchase",
        quantity=float(quantity),
        unit=unit,
        reference_id=ref,
        notes=note_text
    )
    return success, msg


def record_stock_adjustment(
    ingredient_id: str,
    quantity_change: float,
    unit: str,
    reason: str = ""
) -> Tuple[bool, str]:
    """Record manual stock adjustment (positive or negative change)."""
    if not ingredient_id:
        return False, "Ingredient must be selected."
    if quantity_change == 0:
        return False, "Adjustment quantity change cannot be zero."
    if not reason or not reason.strip():
        return False, "Reason for stock adjustment is required (e.g., spoilage, count discrepancy)."
        
    ref = f"ADJ_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    # Check current stock to prevent negative inventory
    inv_df = get_inventory_status()
    ing_df = get_ingredients()
    
    ing_row = ing_df[ing_df["ingredient_id"] == ingredient_id]
    if ing_row.empty:
        return False, "Ingredient not found."
    canonical_unit = ing_row["unit"].values[0]
    
    try:
        qty_in_canonical = convert_between_units(quantity_change, unit, canonical_unit)
    except Exception as e:
        return False, str(e)
        
    curr_stock = 0.0
    if not inv_df.empty and ingredient_id in inv_df["ingredient_id"].values:
        curr_stock = float(inv_df[inv_df["ingredient_id"] == ingredient_id]["current_stock"].values[0])
        
    if curr_stock + qty_in_canonical < 0:
        return False, f"Adjustment would result in negative stock ({curr_stock + qty_in_canonical:.2f} {canonical_unit}). Available stock is {curr_stock:.2f} {canonical_unit}."
        
    success, msg = append_stock_movement(
        ingredient_id=ingredient_id,
        movement_type="Adjustment",
        quantity=float(quantity_change),
        unit=unit,
        reference_id=ref,
        notes=f"Adjustment: {reason.strip()}"
    )
    return success, msg


def get_stock_movement_history(ingredient_id: Optional[str] = None, limit: int = 200) -> pd.DataFrame:
    """Retrieve formatted stock movement history joined with ingredient names from SQLite."""
    sql = """
        SELECT sm.movement_id, sm.timestamp, sm.ingredient_id, i.ingredient_name,
               sm.movement_type, sm.quantity, sm.unit, sm.reference_id, sm.notes
        FROM stock_movements sm
        LEFT JOIN ingredients i ON sm.ingredient_id = i.ingredient_id
        WHERE 1=1
    """
    params = []
    if ingredient_id:
        sql += " AND sm.ingredient_id = ?"
        params.append(ingredient_id)
        
    sql += " ORDER BY sm.timestamp DESC LIMIT ?;"
    params.append(limit)
    return query_df(sql, tuple(params))
