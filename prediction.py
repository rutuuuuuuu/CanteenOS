"""Demand Forecasting module for next-day-only canteen demand predictions.
Calculates tomorrow's demand forecast using time-series models, features,
and human-understandable explanations for canteen staff.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import numpy as np
import pandas as pd

import config
from data_store import (
    get_food_items,
    get_daily_sales,
    save_forecast_records,
    get_forecasts_for_date
)
from preprocessing import (
    FEATURE_COLUMNS,
    load_preprocessor
)
from train_model import load_best_model, train_and_evaluate_models
from database import query_df


def get_tomorrow_date() -> datetime.date:
    """Dynamically determine tomorrow's calendar date."""
    return datetime.now().date() + timedelta(days=1)


def generate_demand_explanation(
    food_name: str,
    predicted_val: int,
    recent_avg: float,
    event_name: str,
    is_exam_period: bool,
    day_of_week_name: str,
    has_sufficient_history: bool = True
) -> Tuple[str, str]:
    """Generate concise, factual explanation and preparation suggestion for canteen staff."""
    diff = predicted_val - recent_avg
    
    # 1. Factual Explanation based strictly on model features & history
    if not has_sufficient_history:
        explanation = "Limited sales history; estimated using category baseline."
    elif is_exam_period:
        explanation = "Adjusted for examination period schedule."
    elif event_name not in ["No Special Event", "Regular College Day"]:
        explanation = f"Campus event scheduled: {event_name}. Demand based on historical {day_of_week_name} patterns."
    elif diff > 5:
        explanation = f"Higher expected demand based on historical {day_of_week_name} patterns."
    elif diff < -5:
        explanation = f"Slightly lower demand based on historical {day_of_week_name} patterns."
    else:
        explanation = f"Steady daily sales pattern for {day_of_week_name}."
        
    # 2. Suggestion
    if not has_sufficient_history:
        suggestion = f"Prepare {predicted_val} servings (baseline estimate; adjust based on daily observation)."
    else:
        rec_min = max(0, int(round(predicted_val * 0.95)))
        rec_max = int(round(predicted_val * 1.05))
        suggestion = f"Prepare {predicted_val} servings (target range: {rec_min}–{rec_max})."
    
    return explanation, suggestion


def extract_features_for_tomorrow(
    event_name: str = "Regular College Day",
    is_exam_period: bool = False
) -> pd.DataFrame:
    """Construct feature matrix for tomorrow's forecast for all active food items."""
    target_dt = get_tomorrow_date()
    target_date_str = target_dt.strftime("%Y-%m-%d")
    
    food_df = get_food_items(active_only=True)
    daily_sales = get_daily_sales()
    
    if food_df.empty:
        return pd.DataFrame()
        
    if not daily_sales.empty:
        daily_sales["date_dt"] = pd.to_datetime(daily_sales["date"])
        # Strictly past data
        history = daily_sales[daily_sales["date_dt"] < pd.to_datetime(target_date_str)].sort_values("date_dt")
    else:
        history = pd.DataFrame()
        
    dow = target_dt.weekday() # 0 = Monday, 6 = Sunday
    dom = target_dt.day
    month = target_dt.month
    year = target_dt.year
    is_weekend = 1 if dow >= 5 else 0
    exam_flag = 1 if is_exam_period else 0
    dow_name = target_dt.strftime("%A")
    
    rows = []
    
    for _, food in food_df.iterrows():
        f_id = food["food_id"]
        f_name = food["food_name"]
        cat = food["category"]
        price = float(food["selling_price"])
        
        item_hist = history[history["food_id"] == f_id] if not history.empty else pd.DataFrame()
        
        has_suff_hist = bool(not item_hist.empty and len(item_hist) >= 7)
        if not item_hist.empty and len(item_hist) >= 1:
            sales_vals = item_hist["units_sold"].values
            lag_1 = float(sales_vals[-1]) if len(sales_vals) >= 1 else 40.0
            lag_7 = float(sales_vals[-7]) if len(sales_vals) >= 7 else lag_1
            lag_14 = float(sales_vals[-14]) if len(sales_vals) >= 14 else lag_7
            
            roll_7 = float(np.mean(sales_vals[-7:])) if len(sales_vals) >= 7 else float(np.mean(sales_vals))
            roll_std_7 = float(np.std(sales_vals[-7:])) if len(sales_vals) >= 7 else 0.0
            roll_14 = float(np.mean(sales_vals[-14:])) if len(sales_vals) >= 14 else roll_7
            
            same_dow = item_hist[item_hist["date_dt"].dt.dayofweek == dow]
            weekday_avg = float(same_dow["units_sold"].mean()) if not same_dow.empty else roll_7
        else:
            cat_hist = history[history["food_id"].isin(food_df[food_df["category"] == cat]["food_id"])] if not history.empty else pd.DataFrame()
            cat_mean = float(cat_hist["units_sold"].mean()) if not cat_hist.empty else 45.0
            lag_1 = lag_7 = lag_14 = roll_7 = roll_14 = weekday_avg = cat_mean
            roll_std_7 = 0.0
            
        rows.append({
            "food_id": f_id,
            "food_name": f_name,
            "category": cat,
            "selling_price": price,
            "target_date": target_date_str,
            "day_of_week": dow,
            "day_of_month": dom,
            "month": month,
            "year": year,
            "is_weekend": is_weekend,
            "is_exam_period": exam_flag,
            "event_name": event_name,
            "sales_lag_1": lag_1,
            "sales_lag_7": lag_7,
            "sales_lag_14": lag_14,
            "sales_roll_mean_7": roll_7,
            "sales_roll_std_7": roll_std_7,
            "sales_roll_mean_14": roll_14,
            "weekday_avg_sales": weekday_avg,
            "recent_avg": round(roll_7, 1),
            "day_of_week_name": dow_name,
            "has_sufficient_history": has_suff_hist
        })
        
    return pd.DataFrame(rows)


def generate_tomorrow_forecast(
    event_name: str = "Regular College Day",
    is_exam_period: bool = False,
    save_to_db: bool = True
) -> pd.DataFrame:
    """Generate and save next-day-only demand forecast for all active food items."""
    model, preprocessor, metadata = load_best_model()
    
    if model is None or preprocessor is None:
        model, preprocessor, metadata = train_and_evaluate_models()
        
    features_df = extract_features_for_tomorrow(
        event_name=event_name,
        is_exam_period=is_exam_period
    )
    
    if features_df.empty:
        return pd.DataFrame()
        
    # Transform and Predict strictly using trained model
    X_input = preprocessor.transform(features_df[FEATURE_COLUMNS])
    raw_preds = model.predict(X_input)
    clean_preds = [max(0, int(round(p))) for p in raw_preds]
    features_df["predicted_demand"] = clean_preds
    
    # Add factual explanations & suggestions
    explanations = []
    suggestions = []
    
    for _, row in features_df.iterrows():
        exp, sug = generate_demand_explanation(
            food_name=row["food_name"],
            predicted_val=row["predicted_demand"],
            recent_avg=row["recent_avg"],
            event_name=event_name,
            is_exam_period=is_exam_period,
            day_of_week_name=row["day_of_week_name"],
            has_sufficient_history=row.get("has_sufficient_history", True)
        )
        explanations.append(exp)
        suggestions.append(sug)
        
    features_df["demand_explanation"] = explanations
    features_df["explanation"] = explanations
    features_df["preparation_suggestion"] = suggestions
    features_df["est_revenue"] = (features_df["predicted_demand"] * features_df["selling_price"]).round(2)
    features_df["estimated_revenue"] = features_df["est_revenue"]
    
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    features_df["generated_at"] = now_str
    
    if save_to_db:
        save_rows = features_df[["target_date", "food_id", "predicted_demand", "event_name", "is_exam_period", "generated_at"]].to_dict(orient="records")
        for r in save_rows:
            r["model_name"] = metadata.get("best_model_name", "Random Forest Regressor") if metadata else "Random Forest Regressor"
            r["model_version"] = "v2.0"
        save_forecast_records(save_rows)
        
    return features_df


def get_forecast_vs_actual_comparison(month_str: Optional[str] = None) -> pd.DataFrame:
    """Compare saved forecasts with actual recorded sales for evaluation."""
    sql = """
        SELECT fc.target_date, fc.food_id, f.food_name, f.category,
               fc.predicted_demand, s.units_sold as actual_demand,
               ABS(fc.predicted_demand - s.units_sold) as absolute_error,
               fc.event_name
        FROM forecasts fc
        JOIN food_items f ON fc.food_id = f.food_id
        JOIN daily_sales s ON fc.target_date = s.date AND fc.food_id = s.food_id
        WHERE 1=1
    """
    params = []
    if month_str:
        sql += " AND fc.target_date LIKE ?"
        params.append(f"{month_str}%")
        
    sql += " ORDER BY fc.target_date DESC, f.food_name ASC;"
    df = query_df(sql, tuple(params))
    
    if not df.empty:
        df["percentage_error"] = np.where(
            df["actual_demand"] > 0,
            (df["absolute_error"] / df["actual_demand"]) * 100.0,
            0.0
        ).round(1)
    return df
