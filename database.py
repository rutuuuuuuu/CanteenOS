"""Database module for SQLite relational storage.
Manages connections, schema tables, constraints, foreign keys, indexes, and transactions.
"""

import sqlite3
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import pandas as pd

import config

def get_db_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """Create and return a SQLite connection with foreign keys enabled."""
    target_path = db_path or config.DB_PATH
    target_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(target_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(db_path: Optional[Path] = None) -> None:
    """Initialize SQLite database tables and indexes if they do not exist."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    
    # 1. Food Items Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS food_items (
            food_id TEXT PRIMARY KEY,
            food_name TEXT NOT NULL,
            category TEXT NOT NULL,
            selling_price REAL NOT NULL CHECK(selling_price > 0),
            is_active INTEGER NOT NULL DEFAULT 1
        );
    """)
    
    # 2. Ingredients Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ingredients (
            ingredient_id TEXT PRIMARY KEY,
            ingredient_name TEXT NOT NULL,
            unit TEXT NOT NULL,
            unit_cost REAL NOT NULL DEFAULT 0.0 CHECK(unit_cost >= 0),
            reorder_level REAL NOT NULL DEFAULT 0.0 CHECK(reorder_level >= 0),
            target_stock REAL NOT NULL DEFAULT 0.0 CHECK(target_stock >= 0),
            is_active INTEGER NOT NULL DEFAULT 1
        );
    """)
    
    # 3. Food Ingredients (Recipe per serving) Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS food_ingredients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            food_id TEXT NOT NULL,
            ingredient_id TEXT NOT NULL,
            quantity_per_serving REAL NOT NULL CHECK(quantity_per_serving > 0),
            quantity_unit TEXT NOT NULL,
            FOREIGN KEY (food_id) REFERENCES food_items (food_id) ON DELETE CASCADE,
            FOREIGN KEY (ingredient_id) REFERENCES ingredients (ingredient_id) ON DELETE CASCADE,
            UNIQUE (food_id, ingredient_id)
        );
    """)
    
    # 4. Inventory Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            ingredient_id TEXT PRIMARY KEY,
            current_stock REAL NOT NULL DEFAULT 0.0 CHECK(current_stock >= 0),
            unit TEXT NOT NULL,
            last_updated TEXT NOT NULL,
            FOREIGN KEY (ingredient_id) REFERENCES ingredients (ingredient_id) ON DELETE CASCADE
        );
    """)
    
    # 5. Stock Movements Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stock_movements (
            movement_id TEXT PRIMARY KEY,
            timestamp TEXT NOT NULL,
            ingredient_id TEXT NOT NULL,
            movement_type TEXT NOT NULL,
            quantity REAL NOT NULL,
            unit TEXT NOT NULL,
            reference_id TEXT,
            notes TEXT,
            FOREIGN KEY (ingredient_id) REFERENCES ingredients (ingredient_id) ON DELETE CASCADE
        );
    """)
    
    # 6. Daily Sales Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_sales (
            record_id TEXT PRIMARY KEY,
            date TEXT NOT NULL,
            food_id TEXT NOT NULL,
            units_sold INTEGER NOT NULL CHECK(units_sold >= 0),
            selling_price REAL NOT NULL CHECK(selling_price > 0),
            revenue REAL NOT NULL CHECK(revenue >= 0),
            event_name TEXT NOT NULL DEFAULT 'Regular College Day',
            is_exam_period INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (food_id) REFERENCES food_items (food_id) ON DELETE CASCADE,
            UNIQUE (date, food_id)
        );
    """)
    
    # 7. Preparations & Leftovers Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS preparations (
            preparation_id TEXT PRIMARY KEY,
            date TEXT NOT NULL,
            food_id TEXT NOT NULL,
            planned_quantity INTEGER NOT NULL CHECK(planned_quantity >= 0),
            prepared_quantity INTEGER NOT NULL CHECK(prepared_quantity >= 0),
            actual_sold_quantity INTEGER NOT NULL DEFAULT 0 CHECK(actual_sold_quantity >= 0),
            unsold_quantity INTEGER NOT NULL DEFAULT 0 CHECK(unsold_quantity >= 0),
            status TEXT NOT NULL DEFAULT 'Confirmed',
            disposition TEXT NOT NULL DEFAULT 'Not Recorded',
            confirmed_at TEXT NOT NULL,
            FOREIGN KEY (food_id) REFERENCES food_items (food_id) ON DELETE CASCADE
        );
    """)
    
    # 8. Forecasts History Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS forecasts (
            forecast_id TEXT PRIMARY KEY,
            generated_at TEXT NOT NULL,
            target_date TEXT NOT NULL,
            food_id TEXT NOT NULL,
            predicted_demand INTEGER NOT NULL CHECK(predicted_demand >= 0),
            event_name TEXT,
            is_exam_period INTEGER DEFAULT 0,
            model_name TEXT DEFAULT 'HistGradientBoosting',
            model_version TEXT DEFAULT 'v2.0',
            FOREIGN KEY (food_id) REFERENCES food_items (food_id) ON DELETE CASCADE
        );
    """)
    
    # 9. Campus Events Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            event_id TEXT PRIMARY KEY,
            date TEXT NOT NULL,
            event_name TEXT NOT NULL,
            event_type TEXT NOT NULL,
            is_exam_period INTEGER NOT NULL DEFAULT 0,
            expected_attendance INTEGER DEFAULT 0
        );
    """)
    
    # Create Helpful Indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sales_date ON daily_sales (date);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sales_food ON daily_sales (food_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_prep_date ON preparations (date);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_forecasts_target ON forecasts (target_date);")
    cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_forecasts_target_food ON forecasts (target_date, food_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_movements_ing ON stock_movements (ingredient_id);")
    
    conn.commit()
    conn.close()


def query_df(sql: str, params: Tuple = (), db_path: Optional[Path] = None) -> pd.DataFrame:
    """Execute a SELECT query and return results as a pandas DataFrame."""
    conn = get_db_connection(db_path)
    try:
        df = pd.read_sql_query(sql, conn, params=params)
        return df
    finally:
        conn.close()


def execute_non_query(sql: str, params: Tuple = (), db_path: Optional[Path] = None) -> int:
    """Execute an INSERT/UPDATE/DELETE query and return rows affected."""
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        conn.commit()
        return cursor.rowcount
    finally:
        conn.close()


def backup_database(destination_dir: Optional[Path] = None) -> str:
    """Create a timestamped backup copy of canteen.db."""
    dest = destination_dir or config.BACKUPS_DIR
    dest.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = dest / f"canteen_backup_{timestamp}.db"
    
    if config.DB_PATH.exists():
        shutil.copy(config.DB_PATH, backup_path)
        return str(backup_path)
    return ""


def is_database_empty(db_path: Optional[Path] = None) -> bool:
    """Check if the database is newly created and contains no food items."""
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT count(*) as count FROM sqlite_master WHERE type='table' AND name='food_items';")
        if cursor.fetchone()[0] == 0:
            return True
        cursor.execute("SELECT count(*) as count FROM food_items;")
        return cursor.fetchone()[0] == 0
    except Exception:
        return True
    finally:
        conn.close()
