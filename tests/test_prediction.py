"""Tests for prediction.py: Tomorrow-only demand forecasting and explanations.
"""

import pytest
import pandas as pd
from datetime import datetime, timedelta

from prediction import (
    get_tomorrow_date,
    extract_features_for_tomorrow,
    generate_tomorrow_forecast,
    generate_demand_explanation,
    get_forecast_vs_actual_comparison
)


def test_tomorrow_date_calculation():
    """Verify that forecasting date is dynamically computed as next calendar day."""
    tomorrow = get_tomorrow_date()
    expected = datetime.now().date() + timedelta(days=1)
    assert tomorrow == expected


def test_generate_tomorrow_forecast():
    """Test generating forecasts for tomorrow with event and exam flags."""
    fc_df = generate_tomorrow_forecast(
        event_name="Regular College Day",
        is_exam_period=False,
        save_to_db=True
    )
    
    assert not fc_df.empty
    assert "predicted_demand" in fc_df.columns
    assert "demand_explanation" in fc_df.columns
    assert "preparation_suggestion" in fc_df.columns
    assert (fc_df["predicted_demand"] >= 0).all()
    assert (fc_df["predicted_demand"] % 1 == 0).all()  # Whole numbers
    assert fc_df["target_date"].values[0] == get_tomorrow_date().strftime("%Y-%m-%d")


def test_demand_explanation_generator():
    """Test generation of staff-friendly demand explanations."""
    exp1, sug1 = generate_demand_explanation(
        food_name="Samosa",
        predicted_val=80,
        recent_avg=60.0,
        event_name="College Festival",
        is_exam_period=False,
        day_of_week_name="Friday"
    )
    assert "Festival" in exp1
    assert "80" in sug1
    
    exp2, sug2 = generate_demand_explanation(
        food_name="Filter Coffee",
        predicted_val=90,
        recent_avg=50.0,
        event_name="Semester Examination",
        is_exam_period=True,
        day_of_week_name="Monday"
    )
    assert "exam" in exp2.lower() or "quick-service" in exp2.lower()


def test_historical_forecast_comparison():
    """Test matching historical forecasts with actual sales."""
    comparison_df = get_forecast_vs_actual_comparison()
    if not comparison_df.empty:
        assert "predicted_demand" in comparison_df.columns
        assert "actual_demand" in comparison_df.columns
        assert "absolute_error" in comparison_df.columns
        assert (comparison_df["absolute_error"] >= 0).all()
