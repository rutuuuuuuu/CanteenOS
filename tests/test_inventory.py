"""Tests for inventory.py: Stock tracking, purchase receipts, adjustments, and unit conversions.
"""

import pytest
from validation import convert_between_units, ValidationError
from inventory import (
    get_inventory_kpis,
    record_ingredient_purchase,
    record_stock_adjustment,
    get_stock_movement_history
)
from data_store import get_inventory_status


def test_unit_conversions():
    """Test standard unit conversions (g to kg, ml to L)."""
    assert convert_between_units(500, "g", "kg") == 0.5
    assert convert_between_units(2.5, "kg", "g") == 2500.0
    assert convert_between_units(250, "ml", "L") == 0.25
    assert convert_between_units(10, "pcs", "pcs") == 10.0
    
    with pytest.raises(ValidationError):
        convert_between_units(100, "g", "L")


def test_inventory_purchase_and_kpis():
    """Test that recording a purchase increases stock and logs movement."""
    inv_before = get_inventory_status()
    assert not inv_before.empty
    
    first_ing = inv_before.iloc[0]
    ing_id = first_ing["ingredient_id"]
    stock_before = float(first_ing["current_stock"])
    unit = first_ing["unit"]
    
    success, msg = record_ingredient_purchase(
        ingredient_id=ing_id,
        quantity=10.0,
        unit=unit,
        purchase_order_ref="TEST_PO_01",
        notes="Automated test purchase"
    )
    assert success is True
    assert msg.startswith("MOV_")
    
    inv_after = get_inventory_status()
    stock_after = float(inv_after[inv_after["ingredient_id"] == ing_id]["current_stock"].values[0])
    assert stock_after == pytest.approx(stock_before + 10.0, rel=1e-3)
    
    # Test KPIs calculation
    kpis = get_inventory_kpis()
    assert kpis["total_ingredients"] > 0
    assert kpis["total_inventory_value"] >= 0.0


def test_negative_stock_rejection():
    """Verify that stock adjustments leading to negative inventory are rejected."""
    inv = get_inventory_status()
    first_ing = inv.iloc[0]
    ing_id = first_ing["ingredient_id"]
    stock = float(first_ing["current_stock"])
    unit = first_ing["unit"]
    
    # Try deducting more than available
    excess_deduct = -(stock + 5000.0)
    success, msg = record_stock_adjustment(
        ingredient_id=ing_id,
        quantity_change=excess_deduct,
        unit=unit,
        reason="Test over-deduction"
    )
    assert success is False
    assert "negative stock" in msg.lower()
