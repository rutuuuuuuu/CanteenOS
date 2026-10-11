"""Tests for preparation.py: Recipe requirements, batch confirmation, and leftover tracking.
"""

import pytest
import pandas as pd
from datetime import datetime
from preparation import (
    calculate_ingredient_requirements,
    confirm_preparation_plan,
    record_preparation_actual_sales,
    get_preparations_history
)
from data_store import get_food_items, get_inventory_status


def test_recipe_ingredient_requirements():
    """Test ingredient requirement aggregation across multiple food items."""
    foods = get_food_items(active_only=True)
    assert len(foods) >= 2
    
    f1 = foods.iloc[0]["food_id"]
    f2 = foods.iloc[1]["food_id"]
    
    plan = {f1: 50, f2: 30}
    summary_df, breakdown_df, is_feasible = calculate_ingredient_requirements(plan)
    
    if not summary_df.empty:
        assert "required_quantity" in summary_df.columns
        assert "current_stock" in summary_df.columns
        assert "shortage" in summary_df.columns
        assert (summary_df["required_quantity"] > 0).all()


def test_draft_plan_does_not_modify_inventory():
    """Verify that calculating ingredient requirements for a draft plan does NOT alter inventory."""
    inv_before = get_inventory_status()
    
    foods = get_food_items(active_only=True)
    plan = {foods.iloc[0]["food_id"]: 100}
    
    calculate_ingredient_requirements(plan)
    
    inv_after = get_inventory_status()
    pd.testing.assert_frame_equal(inv_before, inv_after)


def test_preparation_confirmation_and_leftover_recording():
    """Test confirming preparation batch (deducting stock) and recording sales/leftovers."""
    foods = get_food_items(active_only=True)
    f_id = foods.iloc[0]["food_id"]
    
    today_str = datetime.now().strftime("%Y-%m-%d")
    plan = {f_id: 10}
    
    # Confirm preparation
    success, msg, prep_ids = confirm_preparation_plan(today_str, plan)
    assert success is True
    assert len(prep_ids) >= 1
    prep_id = prep_ids[0]
    
    # Record actual sales
    sold_qty = 8
    success_sales, msg_sales = record_preparation_actual_sales(
        preparation_id=prep_id,
        actual_sold_quantity=sold_qty,
        disposition="Stored or Reused"
    )
    assert success_sales is True
    
    # Check history
    history = get_preparations_history(prep_date=today_str)
    assert not history.empty
    prep_row = history[history["preparation_id"] == prep_id].iloc[0]
    assert int(prep_row["prepared_quantity"]) == 10
    assert int(prep_row["actual_sold_quantity"]) == 8
    assert int(prep_row["unsold_quantity"]) == 2
    assert prep_row["disposition"] == "Stored or Reused"
