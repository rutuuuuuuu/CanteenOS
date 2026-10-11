"""Model training, evaluation, and selection pipeline.
Implements candidate regressors (Baseline, Linear Regression, Random Forest, Gradient Boosting),
evaluates them strictly on chronological validation split, selects the champion model,
evaluates on held-out test data, and saves model artifacts and metadata.
"""

from datetime import datetime
import json
from typing import Dict, Any, Tuple, Optional
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, RegressorMixin
from sklearn.linear_model import Ridge, LinearRegression
from sklearn.ensemble import RandomForestRegressor, HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import joblib

import config
from preprocessing import (
    build_feature_dataframe,
    split_chronological_data,
    CanteenDataPreprocessor,
    save_preprocessor,
    load_preprocessor,
    FEATURE_COLUMNS,
    TARGET_COLUMN
)


class HistoricalWeekdayBaseline(BaseEstimator, RegressorMixin):
    """Baseline regressor predicting the historical mean for a given food_id and day_of_week."""
    def __init__(self):
        self.lookup_table: Dict[Tuple[int, int], float] = {}
        self.global_mean: float = 0.0

    def fit(self, X: pd.DataFrame, y: Any):
        df = X.copy()
        y_arr = np.asarray(y)
        df["target"] = y_arr
        self.global_mean = float(np.mean(y_arr)) if len(y_arr) > 0 else 0.0
        
        # Group by day_of_week and category / item features
        if "day_of_week" in df.columns:
            group_means = df.groupby("day_of_week")["target"].mean().to_dict()
            self.lookup_table = group_means
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        if "day_of_week" in X.columns:
            preds = X["day_of_week"].map(self.lookup_table).fillna(self.global_mean).values
            return np.maximum(0.0, preds.astype(float))
        return np.full(len(X), self.global_mean)


def calculate_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    """Calculate MAE, RMSE, and R2 metrics."""
    y_pred_clean = np.maximum(0.0, y_pred) # Enforce non-negative
    mae = float(mean_absolute_error(y_true, y_pred_clean))
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred_clean)))
    try:
        r2 = float(r2_score(y_true, y_pred_clean))
    except Exception:
        r2 = 0.0
    return {
        "mae": round(mae, 3),
        "rmse": round(rmse, 3),
        "r2": round(r2, 3)
    }


def train_and_evaluate_models(
    df_features: Optional[pd.DataFrame] = None
) -> Tuple[Any, CanteenDataPreprocessor, Dict[str, Any]]:
    """Complete ML Pipeline: Chronological split, model comparison, champion selection, and persistence."""
    if df_features is None or df_features.empty:
        df_features = build_feature_dataframe()
        
    if df_features.empty:
        raise ValueError("Cannot train models: Feature dataset is empty.")
        
    # Chronological Split
    train_df, val_df, test_df = split_chronological_data(df_features)
    
    # Fit Preprocessor ONLY on training data
    preprocessor = CanteenDataPreprocessor()
    preprocessor.fit(train_df[FEATURE_COLUMNS])
    
    # Transform splits
    X_train = preprocessor.transform(train_df[FEATURE_COLUMNS])
    y_train = train_df[TARGET_COLUMN].values
    
    X_val = preprocessor.transform(val_df[FEATURE_COLUMNS])
    y_val = val_df[TARGET_COLUMN].values
    
    X_test = preprocessor.transform(test_df[FEATURE_COLUMNS])
    y_test = test_df[TARGET_COLUMN].values
    
    # Candidate Models
    candidate_models = {
        "Historical Weekday Baseline": HistoricalWeekdayBaseline(),
        "Linear Regression (Ridge)": Ridge(alpha=1.0),
        "Random Forest Regressor": RandomForestRegressor(n_estimators=50, max_depth=10, random_state=config.RANDOM_SEED, n_jobs=-1),
        "HistGradientBoosting Regressor": HistGradientBoostingRegressor(max_iter=50, max_depth=6, random_state=config.RANDOM_SEED)
    }
    
    model_results = {}
    best_val_mae = float("inf")
    best_model_name = None
    best_model = None
    
    # Train and evaluate each candidate on Validation set
    for name, model in candidate_models.items():
        model.fit(X_train, y_train)
        val_preds = model.predict(X_val)
        val_metrics = calculate_metrics(y_val, val_preds)
        
        # Also train metrics for overfitting check
        train_preds = model.predict(X_train)
        train_metrics = calculate_metrics(y_train, train_preds)
        
        model_results[name] = {
            "validation_metrics": val_metrics,
            "train_metrics": train_metrics
        }
        
        # Selection criterion: Validation MAE
        if val_metrics["mae"] < best_val_mae:
            best_val_mae = val_metrics["mae"]
            best_model_name = name
            best_model = model
            
    # Evaluate champion model on held-out Test set
    test_preds = best_model.predict(X_test)
    test_metrics = calculate_metrics(y_test, test_preds)
    
    # Metadata assembly
    metadata = {
        "best_model_name": best_model_name,
        "model_version": "v1.0",
        "trained_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_records": len(df_features),
        "date_ranges": {
            "train": [str(train_df["date"].min().date()), str(train_df["date"].max().date())],
            "val": [str(val_df["date"].min().date()), str(val_df["date"].max().date())],
            "test": [str(test_df["date"].min().date()), str(test_df["date"].max().date())]
        },
        "candidate_comparisons": model_results,
        "champion_validation_mae": best_val_mae,
        "champion_test_metrics": test_metrics,
        "feature_columns": list(X_train.columns)
    }
    
    # Save artifacts
    joblib.dump(best_model, config.BEST_MODEL_PATH)
    save_preprocessor(preprocessor)
    with open(config.MODEL_METADATA_PATH, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
        
    return best_model, preprocessor, metadata


def load_best_model() -> Tuple[Optional[Any], Optional[CanteenDataPreprocessor], Optional[Dict[str, Any]]]:
    """Load the trained champion model, preprocessor, and metadata from disk."""
    if not config.BEST_MODEL_PATH.exists() or not config.MODEL_METADATA_PATH.exists():
        return None, None, None
    try:
        model = joblib.load(config.BEST_MODEL_PATH)
        preprocessor = load_preprocessor()
        with open(config.MODEL_METADATA_PATH, "r", encoding="utf-8") as f:
            metadata = json.load(f)
        return model, preprocessor, metadata
    except Exception as e:
        print(f"Error loading trained model: {e}")
        return None, None, None


if __name__ == "__main__":
    print("Starting ML Model training pipeline...")
    best_m, prep, meta = train_and_evaluate_models()
    print(f"Best Model Selected: {meta['best_model_name']}")
    print(f"Validation MAE: {meta['champion_validation_mae']}")
    print(f"Held-out Test MAE: {meta['champion_test_metrics']['mae']}, RMSE: {meta['champion_test_metrics']['rmse']}, R2: {meta['champion_test_metrics']['r2']}")
