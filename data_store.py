"""Data Access Layer interfacing directly with SQLite relational database.
Provides atomic transactions, relational querying, and entity CRUD operations.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
import pandas as pd

import config
from database import (
    get_db_connection,
    query_df,
    execute_non_query,
    init_db
)
from validation import (
    convert_between_units,
    ValidationError
)


def generate_unique_id(prefix: str, existing_ids: List[str]) -> str:
    """Generate sequential formatted ID (e.g., FOOD_0001, ING_0001)."""
    max_num = 0
    prefix_clean = prefix.upper().rstrip("_") + "_"
    for raw_id in existing_ids:
        if isinstance(raw_id, str) and raw_id.startswith(prefix_clean):
            try:
                num_part = int(raw_id[len(prefix_clean):])
                if num_part > max_num:
                    max_num = num_part
            except ValueError:
                continue
    return f"{prefix_clean}{max_num + 1:04d}"


# ==========================================
# 1. FOOD & INGREDIENT RECIPES
# ==========================================

def get_food_items(active_only: bool = False) -> pd.DataFrame:
    """Retrieve all food items with category and pricing."""
    sql = "SELECT food_id, food_name, category, selling_price, is_active FROM food_items"
    if active_only:
        sql += " WHERE is_active = 1"
    sql += " ORDER BY category, food_name;"
    df = query_df(sql)
    if not df.empty:
        df["is_active"] = df["is_active"].astype(int) == 1
    return df


def get_food_ingredients(food_id: str) -> pd.DataFrame:
    """Retrieve ingredients needed per serving for a specific food item."""
    sql = """
        SELECT fi.id, fi.food_id, fi.ingredient_id, i.ingredient_name, 
               fi.quantity_per_serving, fi.quantity_unit, i.unit as canonical_unit,
               i.unit_cost, (fi.quantity_per_serving * i.unit_cost) as serving_cost
        FROM food_ingredients fi
        JOIN ingredients i ON fi.ingredient_id = i.ingredient_id
        WHERE fi.food_id = ?
        ORDER BY i.ingredient_name;
    """
    return query_df(sql, (food_id,))


def save_food_item_with_ingredients(
    food_name: str,
    category: str,
    selling_price: float,
    is_active: bool = True,
    ingredients_list: Optional[List[Dict[str, Any]]] = None,
    food_id: Optional[str] = None
) -> Tuple[bool, str]:
    """Atomically save food item and its ingredient requirements in a single SQLite transaction."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Check if record exists
        if food_id:
            cursor.execute("SELECT food_id FROM food_items WHERE food_id = ?;", (food_id,))
            exists = cursor.fetchone()
        else:
            exists = None

        if not exists:
            if not food_id:
                cursor.execute("SELECT food_id FROM food_items;")
                existing_ids = [row[0] for row in cursor.fetchall()]
                food_id = generate_unique_id("FOOD", existing_ids)
            cursor.execute("""
                INSERT INTO food_items (food_id, food_name, category, selling_price, is_active)
                VALUES (?, ?, ?, ?, ?);
            """, (food_id, food_name.strip(), category.strip(), float(selling_price), 1 if is_active else 0))
        else:
            cursor.execute("""
                UPDATE food_items 
                SET food_name = ?, category = ?, selling_price = ?, is_active = ?
                WHERE food_id = ?;
            """, (food_name.strip(), category.strip(), float(selling_price), 1 if is_active else 0, food_id))
            
        # Update ingredients needed per serving
        cursor.execute("DELETE FROM food_ingredients WHERE food_id = ?;", (food_id,))
        
        if ingredients_list:
            for item in ingredients_list:
                ing_id = item["ingredient_id"]
                qty = float(item["quantity_per_serving"])
                unit = item["quantity_unit"].strip()
                if qty > 0 and ing_id:
                    cursor.execute("""
                        INSERT INTO food_ingredients (food_id, ingredient_id, quantity_per_serving, quantity_unit)
                        VALUES (?, ?, ?, ?);
                    """, (food_id, ing_id, qty, unit))
                    
        conn.commit()
        return True, food_id
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        conn.close()


# ==========================================
# 2. INGREDIENTS & INVENTORY
# ==========================================

def get_ingredients(active_only: bool = False) -> pd.DataFrame:
    """Retrieve raw ingredients catalog."""
    sql = "SELECT ingredient_id, ingredient_name, unit, unit_cost, reorder_level, target_stock, is_active FROM ingredients"
    if active_only:
        sql += " WHERE is_active = 1"
    sql += " ORDER BY ingredient_name;"
    df = query_df(sql)
    if not df.empty:
        df["is_active"] = df["is_active"].astype(int) == 1
    return df


def add_or_update_ingredient(
    ingredient_name: str,
    unit: str,
    unit_cost: float,
    reorder_level: float,
    target_stock: float,
    is_active: bool = True,
    ingredient_id: Optional[str] = None
) -> Tuple[bool, str]:
    """Add or update an ingredient definition and ensure inventory record exists."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Check if record exists
        if ingredient_id:
            cursor.execute("SELECT ingredient_id FROM ingredients WHERE ingredient_id = ?;", (ingredient_id,))
            exists = cursor.fetchone()
        else:
            exists = None

        if not exists:
            if not ingredient_id:
                cursor.execute("SELECT ingredient_id FROM ingredients;")
                existing_ids = [row[0] for row in cursor.fetchall()]
                ingredient_id = generate_unique_id("ING", existing_ids)
            
            cursor.execute("""
                INSERT INTO ingredients (ingredient_id, ingredient_name, unit, unit_cost, reorder_level, target_stock, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?);
            """, (ingredient_id, ingredient_name.strip(), unit.strip(), float(unit_cost), float(reorder_level), float(target_stock), 1 if is_active else 0))
            
            cursor.execute("""
                INSERT INTO inventory (ingredient_id, current_stock, unit, last_updated)
                VALUES (?, 0.0, ?, ?)
                ON CONFLICT(ingredient_id) DO NOTHING;
            """, (ingredient_id, unit.strip(), now_str))
        else:
            cursor.execute("""
                UPDATE ingredients 
                SET ingredient_name = ?, unit = ?, unit_cost = ?, reorder_level = ?, target_stock = ?, is_active = ?
                WHERE ingredient_id = ?;
            """, (ingredient_name.strip(), unit.strip(), float(unit_cost), float(reorder_level), float(target_stock), 1 if is_active else 0, ingredient_id))
            
            cursor.execute("""
                UPDATE inventory SET unit = ? WHERE ingredient_id = ?;
            """, (unit.strip(), ingredient_id))
            
        conn.commit()
        return True, ingredient_id
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        conn.close()


def get_inventory_status() -> pd.DataFrame:
    """Retrieve live inventory status joined with ingredient reorder parameters.
    Guaranteed unique rows per ingredient_id without join duplication.
    """
    sql = """
        SELECT i.ingredient_id, i.ingredient_name, i.unit, 
               COALESCE(inv.current_stock, 0.0) as current_stock,
               i.reorder_level, i.target_stock, i.unit_cost,
               (COALESCE(inv.current_stock, 0.0) * i.unit_cost) as stock_value,
               COALESCE(inv.last_updated, '') as last_updated
        FROM ingredients i
        LEFT JOIN (
            SELECT ingredient_id, MAX(current_stock) as current_stock, MAX(last_updated) as last_updated
            FROM inventory
            GROUP BY ingredient_id
        ) inv ON i.ingredient_id = inv.ingredient_id
        WHERE i.is_active = 1
        GROUP BY i.ingredient_id
        ORDER BY i.ingredient_name;
    """
    df = query_df(sql)
    if df.empty:
        return df
        
    df["current_stock"] = df["current_stock"].fillna(0.0).astype(float).round(2)
    df["reorder_level"] = df["reorder_level"].fillna(0.0).astype(float).round(2)
    df["target_stock"] = df["target_stock"].fillna(0.0).astype(float).round(2)
    df["unit_cost"] = df["unit_cost"].fillna(0.0).astype(float).round(2)
    df["stock_value"] = df["stock_value"].fillna(0.0).astype(float).round(2)
    
    def calc_status(row):
        stock = row["current_stock"]
        reorder = row["reorder_level"]
        if stock <= 0:
            return "Out of Stock"
        elif reorder > 0 and stock <= reorder:
            return "Low Stock"
        return "In Stock"
        
    df["stock_status"] = df.apply(calc_status, axis=1)
    df["suggested_replenishment"] = df.apply(lambda r: max(0.0, round(r["target_stock"] - r["current_stock"], 2)), axis=1)
    return df


def append_stock_movement(
    ingredient_id: str,
    movement_type: str,
    quantity: float,
    unit: str,
    reference_id: str = "",
    notes: str = ""
) -> Tuple[bool, str]:
    """Atomically record stock movement and update current inventory balance in SQLite."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Fetch ingredient canonical unit & current stock
        cursor.execute("SELECT unit, ingredient_name FROM ingredients WHERE ingredient_id = ?;", (ingredient_id,))
        ing_row = cursor.fetchone()
        if not ing_row:
            return False, f"Ingredient '{ingredient_id}' not found."
            
        canonical_unit = ing_row[0]
        ing_name = ing_row[1]
        
        # Convert quantity
        try:
            qty_canonical = convert_between_units(quantity, unit, canonical_unit)
        except Exception as e:
            return False, str(e)
            
        cursor.execute("SELECT current_stock FROM inventory WHERE ingredient_id = ?;", (ingredient_id,))
        inv_row = cursor.fetchone()
        curr_stock = float(inv_row[0]) if inv_row else 0.0
        
        if movement_type in ["Purchase", "Opening Stock"]:
            new_stock = curr_stock + qty_canonical
        elif movement_type in ["Consumption", "Waste"]:
            if curr_stock < qty_canonical:
                return False, f"Insufficient stock for {ing_name}: required {qty_canonical:.2f} {canonical_unit}, available {curr_stock:.2f} {canonical_unit}."
            new_stock = curr_stock - qty_canonical
        elif movement_type == "Adjustment":
            new_stock = curr_stock + qty_canonical
            if new_stock < 0:
                return False, f"Stock adjustment would result in negative inventory ({new_stock:.2f} {canonical_unit}). Available stock is {curr_stock:.2f} {canonical_unit}."
        else:
            return False, f"Unsupported movement type: {movement_type}"
            
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Update or insert inventory
        cursor.execute("""
            INSERT INTO inventory (ingredient_id, current_stock, unit, last_updated)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(ingredient_id) DO UPDATE SET
                current_stock = excluded.current_stock,
                last_updated = excluded.last_updated;
        """, (ingredient_id, new_stock, canonical_unit, now_str))
        
        # Insert movement audit row
        cursor.execute("SELECT movement_id FROM stock_movements;")
        existing_mov_ids = [r[0] for r in cursor.fetchall()]
        mov_id = generate_unique_id("MOV", existing_mov_ids)
        
        cursor.execute("""
            INSERT INTO stock_movements (movement_id, timestamp, ingredient_id, movement_type, quantity, unit, reference_id, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """, (mov_id, now_str, ingredient_id, movement_type, float(quantity), unit, reference_id, notes))
        
        conn.commit()
        return True, mov_id
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        conn.close()


# ==========================================
# 3. DAILY SALES
# ==========================================

def add_or_update_daily_sale(
    date_str: str,
    food_id: str,
    units_sold: int,
    selling_price: float,
    event_name: str = "Regular College Day",
    is_exam_period: bool = False,
    record_id: Optional[str] = None
) -> Tuple[bool, str]:
    """Add or update a daily sales record.
    Inventory remains completely separate and is NOT deducted during sales entry.
    If a confirmed preparation batch exists for this date and food_id, updates sold & leftover count.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        revenue = round(int(units_sold) * float(selling_price), 2)
        exam_flag = 1 if is_exam_period else 0
        
        if record_id:
            cursor.execute("""
                UPDATE daily_sales 
                SET date = ?, food_id = ?, units_sold = ?, selling_price = ?, revenue = ?, event_name = ?, is_exam_period = ?
                WHERE record_id = ?;
            """, (date_str, food_id, int(units_sold), float(selling_price), revenue, event_name, exam_flag, record_id))
            rec_id = record_id
        else:
            # Check if record for same date and food_id exists
            cursor.execute("SELECT record_id FROM daily_sales WHERE date = ? AND food_id = ?;", (date_str, food_id))
            existing = cursor.fetchone()
            if existing:
                rec_id = existing[0]
                cursor.execute("""
                    UPDATE daily_sales 
                    SET units_sold = ?, selling_price = ?, revenue = ?, event_name = ?, is_exam_period = ?
                    WHERE record_id = ?;
                """, (int(units_sold), float(selling_price), revenue, event_name, exam_flag, rec_id))
            else:
                cursor.execute("SELECT record_id FROM daily_sales;")
                existing_ids = [r[0] for r in cursor.fetchall()]
                rec_id = generate_unique_id("REC", existing_ids)
                cursor.execute("""
                    INSERT INTO daily_sales (record_id, date, food_id, units_sold, selling_price, revenue, event_name, is_exam_period)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """, (rec_id, date_str, food_id, int(units_sold), float(selling_price), revenue, event_name, exam_flag))
                
        # Automatically update preparation batch actual sold / leftovers if preparation was recorded
        cursor.execute("""
            SELECT preparation_id, prepared_quantity FROM preparations
            WHERE date = ? AND food_id = ?;
        """, (date_str, food_id))
        prep_rows = cursor.fetchall()
        for p_row in prep_rows:
            p_id = p_row[0]
            prep_qty = int(p_row[1])
            unsold = max(0, prep_qty - int(units_sold))
            cursor.execute("""
                UPDATE preparations
                SET actual_sold_quantity = ?, unsold_quantity = ?
                WHERE preparation_id = ?;
            """, (int(units_sold), unsold, p_id))
            
        conn.commit()
        return True, rec_id
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        conn.close()


def get_daily_sales(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    category: Optional[str] = None,
    food_id: Optional[str] = None
) -> pd.DataFrame:
    """Retrieve historical daily sales records with food details."""
    sql = """
        SELECT s.record_id, s.date, s.food_id, f.food_name, f.category,
               s.units_sold, s.selling_price, s.revenue, s.event_name, s.is_exam_period
        FROM daily_sales s
        JOIN food_items f ON s.food_id = f.food_id
        WHERE 1=1
    """
    params = []
    if start_date:
        sql += " AND s.date >= ?"
        params.append(start_date)
    if end_date:
        sql += " AND s.date <= ?"
        params.append(end_date)
    if category and category != "All Categories":
        sql += " AND f.category = ?"
        params.append(category)
    if food_id:
        sql += " AND s.food_id = ?"
        params.append(food_id)
        
    sql += " ORDER BY s.date DESC, f.food_name ASC;"
    df = query_df(sql, tuple(params))
    if not df.empty:
        df["is_exam_period"] = df["is_exam_period"].astype(int) == 1
    return df


# ==========================================
# 4. FORECASTS & EVENTS
# ==========================================

def save_forecast_records(forecast_rows: List[Dict[str, Any]]) -> bool:
    """Save generated demand forecast records to SQLite database without duplicating."""
    if not forecast_rows:
        return True
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT forecast_id FROM forecasts;")
        existing_ids = [r[0] for r in cursor.fetchall()]
        
        for row in forecast_rows:
            target_date = row["target_date"]
            food_id = row["food_id"]
            
            cursor.execute("SELECT forecast_id FROM forecasts WHERE target_date = ? AND food_id = ? LIMIT 1;", (target_date, food_id))
            existing = cursor.fetchone()
            
            if existing:
                fc_id = existing[0]
                cursor.execute("""
                    UPDATE forecasts
                    SET generated_at = ?, predicted_demand = ?, event_name = ?, is_exam_period = ?, model_name = ?, model_version = ?
                    WHERE forecast_id = ?;
                """, (
                    row.get("generated_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                    int(row["predicted_demand"]),
                    row.get("event_name", "Regular College Day"),
                    1 if row.get("is_exam_period", False) else 0,
                    row.get("model_name", "Random Forest Regressor"),
                    row.get("model_version", "v2.0"),
                    fc_id
                ))
            else:
                fc_id = generate_unique_id("FC", existing_ids)
                existing_ids.append(fc_id)
                cursor.execute("""
                    INSERT INTO forecasts (forecast_id, generated_at, target_date, food_id, predicted_demand, event_name, is_exam_period, model_name, model_version)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """, (
                    fc_id,
                    row.get("generated_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                    target_date,
                    food_id,
                    int(row["predicted_demand"]),
                    row.get("event_name", "Regular College Day"),
                    1 if row.get("is_exam_period", False) else 0,
                    row.get("model_name", "Random Forest Regressor"),
                    row.get("model_version", "v2.0")
                ))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"Error saving forecast batch: {e}")
        return False
    finally:
        conn.close()


def get_forecasts_for_date(target_date: str) -> pd.DataFrame:
    """Retrieve saved forecasts for a specific target date."""
    sql = """
        SELECT fc.forecast_id, fc.generated_at, fc.target_date, fc.food_id,
               f.food_name, f.category, f.selling_price, fc.predicted_demand,
               fc.event_name, fc.is_exam_period, fc.model_name
        FROM forecasts fc
        JOIN food_items f ON fc.food_id = f.food_id
        WHERE fc.target_date = ?
        ORDER BY fc.predicted_demand DESC;
    """
    return query_df(sql, (target_date,))
