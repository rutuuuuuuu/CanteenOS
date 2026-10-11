"""Seed data generation module for SQLite database.
Populates a small, coherent, realistic demonstration dataset (10 foods, 15 ingredients,
recipes per serving, 4 months of daily sales, inventory, and preparations).
"""

import random
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import numpy as np
import pandas as pd

import config
from database import get_db_connection, init_db, is_database_empty

# Set random seed for reproducibility
random.seed(config.RANDOM_SEED)
np.random.seed(config.RANDOM_SEED)

# 1. Food Catalog (10 core popular canteen items)
DEMO_FOOD_ITEMS = [
    # (food_id, name, category, price)
    ("FOOD_0001", "Masala Dosa", "South Indian", 60.0),
    ("FOOD_0002", "Idli Sambhar (2 pcs)", "South Indian", 40.0),
    ("FOOD_0003", "Samosa (2 pcs)", "Snacks", 30.0),
    ("FOOD_0004", "Vada Pav", "Snacks", 20.0),
    ("FOOD_0005", "Special Veg Thali", "Meals & Thalis", 120.0),
    ("FOOD_0006", "Veg Biryani", "Rice Dishes", 100.0),
    ("FOOD_0007", "Cheese Sandwich", "Fast Food", 45.0),
    ("FOOD_0008", "Veg Hakka Noodles", "Fast Food", 70.0),
    ("FOOD_0009", "Masala Chai", "Beverages", 15.0),
    ("FOOD_0010", "Filter Coffee", "Beverages", 20.0)
]

# 2. Ingredients Catalog (15 canonical ingredients)
DEMO_INGREDIENTS = [
    # (ingredient_id, name, unit, unit_cost, reorder_level, target_stock, initial_stock)
    ("ING_0001", "Basmati Rice", "kg", 75.0, 30.0, 120.0, 95.0),
    ("ING_0002", "Wheat Flour (Atta)", "kg", 42.0, 30.0, 100.0, 80.0),
    ("ING_0003", "Potatoes", "kg", 25.0, 25.0, 100.0, 75.0),
    ("ING_0004", "Onions", "kg", 35.0, 20.0, 80.0, 60.0),
    ("ING_0005", "Tomatoes", "kg", 40.0, 15.0, 60.0, 45.0),
    ("ING_0006", "Refined Cooking Oil", "L", 125.0, 20.0, 80.0, 65.0),
    ("ING_0007", "Fresh Milk", "L", 56.0, 25.0, 100.0, 85.0),
    ("ING_0008", "Sugar", "kg", 45.0, 15.0, 60.0, 50.0),
    ("ING_0009", "Tea Powder", "kg", 320.0, 5.0, 20.0, 16.0),
    ("ING_0010", "Coffee Powder", "kg", 550.0, 3.0, 12.0, 9.0),
    ("ING_0011", "Paneer (Cottage Cheese)", "kg", 340.0, 8.0, 30.0, 22.0),
    ("ING_0012", "Toor Dal (Lentils)", "kg", 145.0, 15.0, 60.0, 48.0),
    ("ING_0013", "Pav & Bread Slices", "pcs", 3.0, 50.0, 250.0, 200.0),
    ("ING_0014", "Spices & Masala Mix", "kg", 260.0, 5.0, 20.0, 15.0),
    ("ING_0015", "Butter & Ghee", "kg", 490.0, 5.0, 20.0, 16.0)
]

# 3. Recipe Ingredients Needed Per Serving
DEMO_RECIPES = {
    "FOOD_0001": [("ING_0001", 0.06), ("ING_0003", 0.08), ("ING_0004", 0.02), ("ING_0006", 0.015), ("ING_0014", 0.005)], # Masala Dosa
    "FOOD_0002": [("ING_0001", 0.07), ("ING_0012", 0.03), ("ING_0005", 0.02), ("ING_0014", 0.005)], # Idli Sambhar
    "FOOD_0003": [("ING_0002", 0.08), ("ING_0003", 0.10), ("ING_0006", 0.03), ("ING_0014", 0.008)], # Samosa
    "FOOD_0004": [("ING_0013", 1.0), ("ING_0003", 0.08), ("ING_0006", 0.02), ("ING_0014", 0.005)],  # Vada Pav
    "FOOD_0005": [("ING_0001", 0.08), ("ING_0002", 0.06), ("ING_0011", 0.05), ("ING_0012", 0.04), ("ING_0015", 0.01), ("ING_0014", 0.008)], # Veg Thali
    "FOOD_0006": [("ING_0001", 0.11), ("ING_0004", 0.03), ("ING_0015", 0.015), ("ING_0014", 0.01)], # Veg Biryani
    "FOOD_0007": [("ING_0013", 2.0), ("ING_0015", 0.01), ("ING_0004", 0.015), ("ING_0005", 0.015)], # Cheese Sandwich
    "FOOD_0008": [("ING_0004", 0.03), ("ING_0005", 0.02), ("ING_0006", 0.02), ("ING_0014", 0.008)], # Hakka Noodles
    "FOOD_0009": [("ING_0007", 0.08), ("ING_0009", 0.005), ("ING_0008", 0.008), ("ING_0014", 0.001)], # Masala Chai
    "FOOD_0010": [("ING_0007", 0.10), ("ING_0010", 0.008), ("ING_0008", 0.008)] # Filter Coffee
}

# Demand parameters for realistic generation
DEMAND_BASE = {
    "FOOD_0001": 70, # Masala Dosa
    "FOOD_0002": 60, # Idli Sambhar
    "FOOD_0003": 120, # Samosa
    "FOOD_0004": 110, # Vada Pav
    "FOOD_0005": 75, # Veg Thali
    "FOOD_0006": 65, # Veg Biryani
    "FOOD_0007": 50, # Cheese Sandwich
    "FOOD_0008": 55, # Hakka Noodles
    "FOOD_0009": 150, # Masala Chai
    "FOOD_0010": 95  # Filter Coffee
}


def populate_demo_data(force: bool = False, db_path=None) -> bool:
    """Seed small, realistic demo records into SQLite database."""
    init_db(db_path)
    
    if not force and not is_database_empty(db_path):
        # Already populated, preserve existing data
        return False
        
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    
    # Clear tables if forcing
    if force:
        cursor.execute("DELETE FROM food_ingredients;")
        cursor.execute("DELETE FROM stock_movements;")
        cursor.execute("DELETE FROM inventory;")
        cursor.execute("DELETE FROM preparations;")
        cursor.execute("DELETE FROM forecasts;")
        cursor.execute("DELETE FROM daily_sales;")
        cursor.execute("DELETE FROM ingredients;")
        cursor.execute("DELETE FROM food_items;")
        cursor.execute("DELETE FROM events;")
        
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 1. Insert Food Items
    for f_id, name, cat, price in DEMO_FOOD_ITEMS:
        cursor.execute("""
            INSERT OR REPLACE INTO food_items (food_id, food_name, category, selling_price, is_active)
            VALUES (?, ?, ?, ?, 1);
        """, (f_id, name, cat, price))
        
    # 2. Insert Ingredients & Initial Inventory
    for ing_id, name, unit, cost, reorder, target, init_stock in DEMO_INGREDIENTS:
        cursor.execute("""
            INSERT OR REPLACE INTO ingredients (ingredient_id, ingredient_name, unit, unit_cost, reorder_level, target_stock, is_active)
            VALUES (?, ?, ?, ?, ?, ?, 1);
        """, (ing_id, name, unit, cost, reorder, target))
        
        cursor.execute("""
            INSERT OR REPLACE INTO inventory (ingredient_id, current_stock, unit, last_updated)
            VALUES (?, ?, ?, ?);
        """, (ing_id, init_stock, unit, now_str))
        
        # Opening movement
        cursor.execute("""
            INSERT OR REPLACE INTO stock_movements (movement_id, timestamp, ingredient_id, movement_type, quantity, unit, reference_id, notes)
            VALUES (?, ?, ?, 'Opening Stock', ?, ?, 'INIT_001', 'Opening stock balance');
        """, (f"MOV_INIT_{ing_id[-4:]}", now_str, ing_id, init_stock, unit))
        
    # 3. Insert Food Ingredients Needed Per Serving
    for f_id, ing_list in DEMO_RECIPES.items():
        for ing_id, qty in ing_list:
            unit = next(item[2] for item in DEMO_INGREDIENTS if item[0] == ing_id)
            cursor.execute("""
                INSERT OR REPLACE INTO food_ingredients (food_id, ingredient_id, quantity_per_serving, quantity_unit)
                VALUES (?, ?, ?, ?);
            """, (f_id, ing_id, qty, unit))
            
    # 4. Generate ~120 days (4 months) of realistic daily sales
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=120)
    
    curr = start_date
    rec_counter = 1
    
    while curr <= end_date:
        d_str = curr.strftime("%Y-%m-%d")
        weekday = curr.weekday() # 0 = Monday, 6 = Sunday
        month = curr.month
        
        # Determine event
        if weekday == 6:
            event_name = "Holiday or Campus Closure"
            is_exam = 0
            event_mult = 0.3
        elif curr.day in [14, 15] and month in [2, 10]:
            event_name = "College Festival"
            is_exam = 0
            event_mult = 1.4
        elif curr.day in [20, 21, 22, 23, 24] and month in [4, 11]:
            event_name = "Semester Examination"
            is_exam = 1
            event_mult = 1.15
        elif curr.day == 5 and month == 9:
            event_name = "Cultural Event"
            is_exam = 0
            event_mult = 1.3
        else:
            event_name = "Regular College Day"
            is_exam = 0
            event_mult = 1.0
            
        day_mult = 0.5 if weekday == 5 else (0.2 if weekday == 6 else 1.0)
        
        for f_id, name, cat, price in DEMO_FOOD_ITEMS:
            base_demand = DEMAND_BASE.get(f_id, 50)
            
            # Category multipliers
            if "Chai" in name or "Coffee" in name:
                ex_boost = 1.35 if is_exam else 1.0
            else:
                ex_boost = 0.9 if is_exam else 1.0
                
            mu = base_demand * day_mult * event_mult * ex_boost
            
            if weekday == 6 and event_name == "Holiday or Campus Closure":
                units = random.randint(0, 5)
            else:
                noise = np.random.normal(0, max(2.0, mu * 0.10))
                units = max(0, int(round(mu + noise)))
                
            revenue = round(units * price, 2)
            
            cursor.execute("""
                INSERT OR REPLACE INTO daily_sales (record_id, date, food_id, units_sold, selling_price, revenue, event_name, is_exam_period)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """, (f"REC_{rec_counter:06d}", d_str, f_id, units, price, revenue, event_name, is_exam))
            rec_counter += 1
            
        curr += timedelta(days=1)
        
    # 5. Generate recent preparations history (past 30 days)
    prep_start = end_date - timedelta(days=30)
    curr_p = prep_start
    p_counter = 1
    
    while curr_p <= end_date:
        d_str = curr_p.strftime("%Y-%m-%d")
        for f_id, name, cat, price in DEMO_FOOD_ITEMS[:6]:
            cursor.execute("SELECT units_sold FROM daily_sales WHERE date = ? AND food_id = ?;", (d_str, f_id))
            row = cursor.fetchone()
            actual_sold = int(row[0]) if row else 40
            
            buffer = random.randint(2, 6)
            planned = actual_sold + buffer
            prepared = planned
            unsold = max(0, prepared - actual_sold)
            
            disp = "Not Recorded"
            if unsold > 0:
                disp = random.choice(["Stored or Reused", "Donated", "Discarded", "Stored or Reused"])
                
            cursor.execute("""
                INSERT OR REPLACE INTO preparations (preparation_id, date, food_id, planned_quantity, prepared_quantity, actual_sold_quantity, unsold_quantity, status, disposition, confirmed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'Completed', ?, ?);
            """, (f"PREP_{p_counter:05d}", d_str, f_id, planned, prepared, actual_sold, unsold, disp, f"{d_str} 07:30:00"))
            p_counter += 1
            
        curr_p += timedelta(days=1)
        
    # 6. Sample Forecasts (past 15 days)
    fc_start = end_date - timedelta(days=15)
    curr_fc = fc_start
    fc_counter = 1
    
    while curr_fc <= end_date:
        d_str = curr_fc.strftime("%Y-%m-%d")
        gen_time = (curr_fc - timedelta(days=1)).strftime("%Y-%m-%d 18:00:00")
        
        for f_id, name, cat, price in DEMO_FOOD_ITEMS:
            cursor.execute("SELECT units_sold, event_name, is_exam_period FROM daily_sales WHERE date = ? AND food_id = ?;", (d_str, f_id))
            row = cursor.fetchone()
            actual_sold = int(row[0]) if row else 50
            ev_name = row[1] if row else "Regular College Day"
            is_ex = row[2] if row else 0
            
            err = np.random.normal(0, 3)
            pred = max(1, int(round(actual_sold + err)))
            
            cursor.execute("""
                INSERT OR REPLACE INTO forecasts (forecast_id, generated_at, target_date, food_id, predicted_demand, event_name, is_exam_period, model_name, model_version)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'HistGradientBoosting', 'v2.0');
            """, (f"FC_{fc_counter:05d}", gen_time, d_str, f_id, pred, ev_name, is_ex))
            fc_counter += 1
            
        curr_fc += timedelta(days=1)
        
    conn.commit()
    conn.close()
    return True


if __name__ == "__main__":
    populate_demo_data(force=True)
    print("Database initialization and demo seeding complete!")
