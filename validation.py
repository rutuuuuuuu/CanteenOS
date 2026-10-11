"""Validation module for data integrity, business rules, and input verification.
Provides robust checks to prevent invalid, malformed, or corrupting transactions.
"""

from datetime import datetime
from typing import Tuple, List, Optional, Any, Dict
import pandas as pd
from config import VALID_UNITS, UNIT_CONVERSIONS, MOVEMENT_TYPES, PREPARATION_STATUSES, DISPOSITION_TYPES


class ValidationError(Exception):
    """Custom exception raised when validation fails."""
    pass


def validate_positive_number(value: Any, field_name: str, allow_zero: bool = False) -> Tuple[bool, str]:
    """Validate that a value is a valid positive float or integer."""
    try:
        val = float(value)
        if allow_zero and val < 0:
            return False, f"{field_name} must be greater than or equal to 0."
        if not allow_zero and val <= 0:
            return False, f"{field_name} must be strictly greater than 0."
        return True, ""
    except (ValueError, TypeError):
        return False, f"{field_name} must be a valid numerical value."


def validate_integer_quantity(value: Any, field_name: str, allow_zero: bool = False) -> Tuple[bool, str]:
    """Validate that a value is a valid non-negative or positive integer."""
    try:
        val = int(value)
        if allow_zero and val < 0:
            return False, f"{field_name} cannot be negative."
        if not allow_zero and val <= 0:
            return False, f"{field_name} must be at least 1."
        return True, ""
    except (ValueError, TypeError):
        return False, f"{field_name} must be a valid integer."


def validate_date_string(date_str: str) -> Tuple[bool, str]:
    """Validate ISO format date (YYYY-MM-DD)."""
    if not date_str or not isinstance(date_str, str):
        return False, "Date string is required."
    try:
        datetime.strptime(date_str.strip(), "%Y-%m-%d")
        return True, ""
    except ValueError:
        return False, "Date must be in YYYY-MM-DD format."


def validate_unit(unit: str) -> Tuple[bool, str]:
    """Validate if the measurement unit is standard."""
    if not unit or unit not in VALID_UNITS:
        return False, f"Unit '{unit}' is invalid. Allowed units: {', '.join(VALID_UNITS)}"
    return True, ""


def convert_to_base_unit(quantity: float, unit: str) -> Tuple[float, str]:
    """Convert quantity to its base unit (kg, L, or pcs).
    Returns (converted_quantity, base_unit).
    """
    if unit not in UNIT_CONVERSIONS:
        raise ValidationError(f"Unsupported unit for conversion: {unit}")
    base_unit, factor = UNIT_CONVERSIONS[unit]
    return quantity * factor, base_unit


def convert_between_units(quantity: float, from_unit: str, to_unit: str) -> float:
    """Convert quantity between compatible units (e.g., g to kg, ml to L)."""
    base_qty_1, base_unit_1 = convert_to_base_unit(quantity, from_unit)
    _, base_unit_2 = convert_to_base_unit(1.0, to_unit)
    
    if base_unit_1 != base_unit_2:
        raise ValidationError(f"Incompatible unit conversion from {from_unit} to {to_unit}")
    
    # from base to target
    _, factor_to_target = UNIT_CONVERSIONS[to_unit]
    return base_qty_1 / factor_to_target


def validate_food_item_input(food_name: str, category: str, selling_price: float) -> List[str]:
    """Validate input fields for creating or editing a food item."""
    errors = []
    if not food_name or not food_name.strip():
        errors.append("Food name cannot be empty.")
    if not category or not category.strip():
        errors.append("Category must be selected.")
    
    valid_price, price_err = validate_positive_number(selling_price, "Selling price", allow_zero=False)
    if not valid_price:
        errors.append(price_err)
    return errors


def validate_ingredient_input(ingredient_name: str, unit: str, unit_cost: float, reorder_level: float, target_stock: float) -> List[str]:
    """Validate input fields for creating or editing an ingredient."""
    errors = []
    if not ingredient_name or not ingredient_name.strip():
        errors.append("Ingredient name cannot be empty.")
    
    valid_unit, unit_err = validate_unit(unit)
    if not valid_unit:
        errors.append(unit_err)
        
    valid_cost, cost_err = validate_positive_number(unit_cost, "Unit cost", allow_zero=True)
    if not valid_cost:
        errors.append(cost_err)
        
    valid_reorder, reorder_err = validate_positive_number(reorder_level, "Reorder level", allow_zero=True)
    if not valid_reorder:
        errors.append(reorder_err)
        
    valid_target, target_err = validate_positive_number(target_stock, "Target stock", allow_zero=True)
    if not valid_target:
        errors.append(target_err)
        
    if valid_reorder and valid_target and float(target_stock) < float(reorder_level):
        errors.append("Target stock should be greater than or equal to the reorder level.")
        
    return errors


def validate_recipe_entry(food_id: str, ingredient_id: str, quantity_per_serving: float, quantity_unit: str) -> List[str]:
    """Validate adding or modifying a recipe component."""
    errors = []
    if not food_id or not str(food_id).strip():
        errors.append("Food item ID is required.")
    if not ingredient_id or not str(ingredient_id).strip():
        errors.append("Ingredient ID is required.")
    valid_qty, qty_err = validate_positive_number(quantity_per_serving, "Quantity per serving", allow_zero=False)
    if not valid_qty:
        errors.append(qty_err)
    valid_unit, unit_err = validate_unit(quantity_unit)
    if not valid_unit:
        errors.append(unit_err)
    return errors


def validate_sales_record(date_str: str, food_id: str, units_sold: int, selling_price: float) -> List[str]:
    """Validate daily sales record entry."""
    errors = []
    v_date, d_err = validate_date_string(date_str)
    if not v_date:
        errors.append(d_err)
    if not food_id or not str(food_id).strip():
        errors.append("Food item is required.")
    v_units, u_err = validate_integer_quantity(units_sold, "Units sold", allow_zero=True)
    if not v_units:
        errors.append(u_err)
    v_price, p_err = validate_positive_number(selling_price, "Selling price", allow_zero=False)
    if not v_price:
        errors.append(p_err)
    return errors


def validate_stock_movement(ingredient_id: str, movement_type: str, quantity: float, unit: str) -> List[str]:
    """Validate a stock transaction entry."""
    errors = []
    if not ingredient_id or not str(ingredient_id).strip():
        errors.append("Ingredient ID is required.")
    if movement_type not in MOVEMENT_TYPES:
        errors.append(f"Invalid movement type '{movement_type}'. Allowed: {', '.join(MOVEMENT_TYPES)}")
    v_qty, q_err = validate_positive_number(quantity, "Movement quantity", allow_zero=False)
    if not v_qty:
        errors.append(q_err)
    v_unit, u_err = validate_unit(unit)
    if not v_unit:
        errors.append(u_err)
    return errors


def validate_preparation_sales_update(prepared_quantity: int, actual_sold_quantity: int) -> List[str]:
    """Validate updating actual sales for a preparation batch."""
    errors = []
    v_sold, s_err = validate_integer_quantity(actual_sold_quantity, "Actual sold quantity", allow_zero=True)
    if not v_sold:
        errors.append(s_err)
    elif actual_sold_quantity > prepared_quantity:
        errors.append(f"Actual sold quantity ({actual_sold_quantity}) cannot exceed prepared quantity ({prepared_quantity}).")
    return errors
