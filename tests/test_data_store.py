"""Tests for SQLite data store and CRUD operations.
"""

import pytest
import pandas as pd
from data_store import (
    generate_unique_id,
    get_food_items,
    get_food_ingredients,
    save_food_item_with_ingredients,
    get_ingredients,
    add_or_update_ingredient,
    get_inventory_status,
    append_stock_movement,
    add_or_update_daily_sale,
    get_daily_sales,
    save_forecast_records,
    get_forecasts_for_date
)


def test_unique_id_generation():
    """Test sequential ID generation with proper prefix and zero-padding."""
    existing = ["FOOD_0001", "FOOD_0002", "FOOD_0010"]
    new_id = generate_unique_id("FOOD", existing)
    assert new_id == "FOOD_0011"
    
    empty_new_id = generate_unique_id("ING", [])
    assert empty_new_id == "ING_0001"


def test_food_item_crud_and_ingredients():
    """Test creating, reading, and updating food items with recipe ingredients."""
    initial_foods = get_food_items()
    initial_count = len(initial_foods)
    
    # 1. Get an existing ingredient or create one
    ings = get_ingredients()
    assert not ings.empty
    sample_ing_id = ings.iloc[0]["ingredient_id"]
    
    # 2. Add new food with ingredients
    ing_reqs = [{"ingredient_id": sample_ing_id, "quantity_per_serving": 150.0, "quantity_unit": "g"}]
    success, food_id = save_food_item_with_ingredients(
        food_name="Test Special Thali",
        category="Meals and Thalis",
        selling_price=120.0,
        is_active=True,
        ingredients_list=ing_reqs
    )
    assert success is True
    assert food_id.startswith("FOOD_")
    
    # Verify food retrieved
    updated_foods = get_food_items()
    assert len(updated_foods) == initial_count + 1
    food_row = updated_foods[updated_foods["food_id"] == food_id].iloc[0]
    assert food_row["food_name"] == "Test Special Thali"
    assert float(food_row["selling_price"]) == 120.0
    
    # Verify ingredients retrieved
    recipe_df = get_food_ingredients(food_id)
    assert not recipe_df.empty
    assert recipe_df.iloc[0]["ingredient_id"] == sample_ing_id
    assert float(recipe_df.iloc[0]["quantity_per_serving"]) == 150.0
    
    # 3. Edit food item
    success, _ = save_food_item_with_ingredients(
        food_name="Test Special Thali Deluxe",
        category="Meals and Thalis",
        selling_price=140.0,
        is_active=True,
        ingredients_list=ing_reqs,
        food_id=food_id
    )
    assert success is True
    edited_foods = get_food_items()
    edited_row = edited_foods[edited_foods["food_id"] == food_id].iloc[0]
    assert edited_row["food_name"] == "Test Special Thali Deluxe"
    assert float(edited_row["selling_price"]) == 140.0


def test_ingredient_crud_and_inventory_sync():
    """Test adding ingredients and ensuring auto-inventory initialization."""
    initial_ings = get_ingredients()
    initial_count = len(initial_ings)
    
    success, ing_id = add_or_update_ingredient(
        ingredient_name="Test Cardamom Pods",
        unit="g",
        unit_cost=2.50,
        reorder_level=50.0,
        target_stock=200.0,
        is_active=True
    )
    assert success is True
    assert ing_id.startswith("ING_")
    
    updated_ings = get_ingredients()
    assert len(updated_ings) == initial_count + 1
    
    # Verify in inventory
    inv_df = get_inventory_status()
    match = inv_df[inv_df["ingredient_id"] == ing_id]
    assert not match.empty
    assert match["unit"].values[0] == "g"


def test_daily_sales_persistence_and_revenue():
    """Test recording daily sales and checking Indian Rupee revenue calculation."""
    foods = get_food_items(active_only=True)
    assert not foods.empty
    first_food = foods.iloc[0]
    f_id = first_food["food_id"]
    price = float(first_food["selling_price"])
    
    test_date = "2026-10-01"
    units_sold = 75
    expected_rev = round(units_sold * price, 2)
    
    success, rec_id = add_or_update_daily_sale(
        date_str=test_date,
        food_id=f_id,
        units_sold=units_sold,
        selling_price=price,
        event_name="Regular College Day",
        is_exam_period=False
    )
    assert success is True
    assert rec_id.startswith("REC_")
    
    sales_df = get_daily_sales(start_date=test_date, end_date=test_date, food_id=f_id)
    assert not sales_df.empty
    sale_row = sales_df.iloc[0]
    assert int(sale_row["units_sold"]) == units_sold
    assert float(sale_row["revenue"]) == expected_rev
