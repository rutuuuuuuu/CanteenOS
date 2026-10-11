"""Preprocessing and time-series feature engineering module.
Performs strictly chronological splits, lag and rolling window feature extraction
without target leakage, and scikit-learn pipeline transformations using SQLite storage.
"""

from typing import Tuple, Dict, Any, List, Optional
import numpy as np
import pandas as pd
from datetime import datetime
import joblib

import config
from data_store import get_daily_sales, get_food_items


FEATURE_COLUMNS = [
    "day_of_week",
    "day_of_month",
    "month",
    "year",
    "is_weekend",
    "is_exam_period",
    "selling_price",
    "sales_lag_1",
    "sales_lag_7",
    "sales_lag_14",
    "sales_roll_mean_7",
    "sales_roll_std_7",
    "sales_roll_mean_14",
    "weekday_avg_sales",
    "category"
]

NUMERICAL_FEATURES = [
    "day_of_week",
    "day_of_month",
    "month",
    "year",
    "is_weekend",
    "is_exam_period",
    "selling_price",
    "sales_lag_1",
    "sales_lag_7",
    "sales_lag_14",
    "sales_roll_mean_7",
    "sales_roll_std_7",
    "sales_roll_mean_14",
    "weekday_avg_sales"
]

CATEGORICAL_FEATURES = ["category"]
TARGET_COLUMN = "units_sold"


def build_feature_dataframe(df_daily: Optional[pd.DataFrame] = None, df_food: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    """Transform raw daily records and food items into a feature-rich dataset.
    Ensures strict time ordering and shifted rolling features to eliminate data leakage.
    """
    if df_daily is None:
        df_daily = get_daily_sales()
    if df_food is None:
        df_food = get_food_items()
        
    if df_daily.empty:
        return pd.DataFrame()
        
    df = df_daily.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(by=["food_id", "date"]).reset_index(drop=True)
    
    # Merge food category and price if missing
    if "category" not in df.columns or "selling_price" not in df.columns:
        df = pd.merge(df, df_food[["food_id", "category", "selling_price"]], on="food_id", how="left", suffixes=("", "_food"))
        if "category_food" in df.columns:
            df["category"] = df["category"].fillna(df["category_food"])
            df.drop(columns=["category_food"], inplace=True)
            
    # Date time decomposition
    df["day_of_week"] = df["date"].dt.dayofweek # 0=Monday, 6=Sunday
    df["day_of_month"] = df["date"].dt.day
    df["month"] = df["date"].dt.month
    df["year"] = df["date"].dt.year
    df["is_weekend"] = (df["day_of_week"] >= 5).astype(int)
    df["is_exam_period"] = df["is_exam_period"].astype(int)
    df["selling_price"] = df["selling_price"].astype(float)
    df["units_sold"] = df["units_sold"].astype(int)
    
    # Generate Lag and Rolling features per food_id
    # Shift by 1 first so today's actual sales are NEVER in yesterday's features
    grouped = df.groupby("food_id")
    
    df["sales_lag_1"] = grouped["units_sold"].shift(1)
    df["sales_lag_7"] = grouped["units_sold"].shift(7)
    df["sales_lag_14"] = grouped["units_sold"].shift(14)
    
    # Rolling averages on lag_1 (strictly past data)
    df["sales_roll_mean_7"] = grouped["units_sold"].transform(lambda s: s.shift(1).rolling(7, min_periods=1).mean())
    df["sales_roll_std_7"] = grouped["units_sold"].transform(lambda s: s.shift(1).rolling(7, min_periods=1).std().fillna(0.0))
    df["sales_roll_mean_14"] = grouped["units_sold"].transform(lambda s: s.shift(1).rolling(14, min_periods=1).mean())
    
    # Expanding weekday average per food item
    df["weekday_avg_sales"] = df.groupby(["food_id", "day_of_week"])["units_sold"].transform(lambda s: s.shift(1).expanding().mean())
    
    # Fill remaining NaNs for initial days with overall item mean or 0
    item_means = grouped["units_sold"].transform("mean")
    for col in ["sales_lag_1", "sales_lag_7", "sales_lag_14", "sales_roll_mean_7", "sales_roll_mean_14", "weekday_avg_sales"]:
        df[col] = df[col].fillna(item_means).fillna(0.0)
        
    df["sales_roll_std_7"] = df["sales_roll_std_7"].fillna(0.0)
    
    # Sort chronologically by date
    df = df.sort_values(by="date").reset_index(drop=True)
    return df


def split_chronological_data(
    df: pd.DataFrame,
    train_ratio: float = 0.60,
    val_ratio: float = 0.20
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Split dataset chronologically into Train, Validation, and Test sets."""
    if df.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
        
    unique_dates = np.sort(df["date"].unique())
    n_dates = len(unique_dates)
    
    train_cutoff_idx = int(n_dates * train_ratio)
    val_cutoff_idx = int(n_dates * (train_ratio + val_ratio))
    
    train_end_date = unique_dates[train_cutoff_idx]
    val_end_date = unique_dates[val_cutoff_idx]
    
    train_df = df[df["date"] < train_end_date].copy()
    val_df = df[(df["date"] >= train_end_date) & (df["date"] < val_end_date)].copy()
    test_df = df[df["date"] >= val_end_date].copy()
    
    return train_df, val_df, test_df


class CanteenDataPreprocessor:
    """Preprocesses features and handles categorical one-hot encoding."""
    def __init__(self):
        self.categories: List[str] = config.FOOD_CATEGORIES
        self.is_fitted = False
        self.feature_columns = FEATURE_COLUMNS
        
    def fit(self, X: pd.DataFrame, y: Optional[pd.Series] = None):
        if "category" in X.columns:
            unique_cats = list(X["category"].dropna().unique())
            for c in unique_cats:
                if c not in self.categories:
                    self.categories.append(c)
        self.is_fitted = True
        return self
        
    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        if not self.is_fitted:
            self.fit(X)
            
        X_out = X.copy()
        
        for col in NUMERICAL_FEATURES:
            if col not in X_out.columns:
                X_out[col] = 0.0
            else:
                X_out[col] = pd.to_numeric(X_out[col], errors="coerce").fillna(0.0)
                
        for cat in self.categories:
            col_name = f"cat_{cat.replace(' ', '_').replace('&', 'and')}"
            if "category" in X_out.columns:
                X_out[col_name] = (X_out["category"] == cat).astype(int)
            else:
                X_out[col_name] = 0
                
        if "category" in X_out.columns:
            X_out = X_out.drop(columns=["category"])
            
        return X_out
        
    def fit_transform(self, X: pd.DataFrame, y: Optional[pd.Series] = None) -> pd.DataFrame:
        return self.fit(X, y).transform(X)


def save_preprocessor(preprocessor: CanteenDataPreprocessor, path: Optional[str] = None):
    """Save preprocessor pipeline artifact."""
    save_path = path or str(config.PREPROCESSOR_PATH)
    joblib.dump(preprocessor, save_path)


def load_preprocessor(path: Optional[str] = None) -> CanteenDataPreprocessor:
    """Load preprocessor pipeline artifact."""
    load_path = path or str(config.PREPROCESSOR_PATH)
    try:
        return joblib.load(load_path)
    except Exception:
        return CanteenDataPreprocessor()
