"""Tests for preprocessing.py: Time-series feature engineering, chronological splitting, and leakage prevention.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from preprocessing import (
    build_feature_dataframe,
    split_chronological_data,
    CanteenDataPreprocessor,
    FEATURE_COLUMNS
)


def test_build_feature_dataframe():
    """Test feature engineering without data leakage."""
    # Synthetic small daily records
    dates = pd.date_range("2025-01-01", periods=20, freq="D")
    daily_records = []
    for i, d in enumerate(dates):
        daily_records.append({
            "record_id": f"REC_{i:04d}",
            "date": d.strftime("%Y-%m-%d"),
            "food_id": "FOOD_0001",
            "units_sold": 50 + i,
            "selling_price": 40.0,
            "revenue": (50 + i) * 40.0,
            "is_event_day": False,
            "is_exam_period": False
        })
    df_daily = pd.DataFrame(daily_records)
    df_food = pd.DataFrame([{
        "food_id": "FOOD_0001",
        "food_name": "Test Samosa",
        "category": "Snacks",
        "selling_price": 40.0,
        "is_active": True
    }])
    
    features_df = build_feature_dataframe(df_daily, df_food)
    
    assert not features_df.empty
    assert "sales_lag_1" in features_df.columns
    assert "sales_roll_mean_7" in features_df.columns
    assert "weekday_avg_sales" in features_df.columns
    
    # Check shift: on day index 1 (Jan 2), lag_1 should equal day index 0 sales (50)
    row_1 = features_df.iloc[1]
    assert row_1["sales_lag_1"] == 50


def test_chronological_split():
    """Verify chronological split guarantees train < val < test strictly."""
    dates = pd.date_range("2024-01-01", periods=100, freq="D")
    df = pd.DataFrame({
        "date": dates,
        "food_id": "FOOD_0001",
        "units_sold": np.random.randint(20, 80, size=100),
        "category": "Breakfast",
        "selling_price": 50.0,
        "is_event_day": 0,
        "is_exam_period": 0,
        "day_of_week": dates.dayofweek,
        "day_of_month": dates.day,
        "month": dates.month,
        "year": dates.year,
        "is_weekend": (dates.dayofweek >= 5).astype(int),
        "sales_lag_1": 50.0,
        "sales_lag_7": 50.0,
        "sales_lag_14": 50.0,
        "sales_roll_mean_7": 50.0,
        "sales_roll_std_7": 5.0,
        "sales_roll_mean_14": 50.0,
        "weekday_avg_sales": 50.0
    })
    
    train, val, test = split_chronological_data(df, train_ratio=0.6, val_ratio=0.2)
    
    assert len(train) == 60
    assert len(val) == 20
    assert len(test) == 20
    
    assert train["date"].max() < val["date"].min()
    assert val["date"].max() < test["date"].min()


def test_preprocessor_pipeline():
    """Test CanteenDataPreprocessor fit and transform."""
    df_sample = pd.DataFrame({
        "day_of_week": [0, 1, 2],
        "day_of_month": [1, 2, 3],
        "month": [5, 5, 5],
        "year": [2025, 2025, 2025],
        "is_weekend": [0, 0, 0],
        "is_event_day": [0, 1, 0],
        "is_exam_period": [0, 0, 1],
        "selling_price": [40.0, 50.0, 60.0],
        "sales_lag_1": [30.0, 40.0, 50.0],
        "sales_lag_7": [30.0, 40.0, 50.0],
        "sales_lag_14": [30.0, 40.0, 50.0],
        "sales_roll_mean_7": [30.0, 40.0, 50.0],
        "sales_roll_std_7": [2.0, 3.0, 4.0],
        "sales_roll_mean_14": [30.0, 40.0, 50.0],
        "weekday_avg_sales": [30.0, 40.0, 50.0],
        "category": ["Breakfast", "Snacks", "Beverages"]
    })
    
    prep = CanteenDataPreprocessor()
    transformed = prep.fit_transform(df_sample)
    
    assert "category" not in transformed.columns
    assert any(col.startswith("cat_") for col in transformed.columns)
    assert len(transformed) == 3
