"""Main Streamlit Web Application for Canteen Food Demand Forecasting
and Inventory-Aware Waste Reduction System.
"""

from datetime import datetime, timedelta
import io
import json
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

import config
from auth import is_authenticated, render_login_page, logout
from database import init_db, is_database_empty, backup_database
from seed_data import populate_demo_data
from validation import (
    validate_food_item_input,
    validate_ingredient_input,
    validate_sales_record
)
from data_store import (
    get_food_items,
    get_food_ingredients,
    save_food_item_with_ingredients,
    get_ingredients,
    add_or_update_ingredient,
    get_inventory_status,
    append_stock_movement,
    add_or_update_daily_sale,
    get_daily_sales
)
from prediction import (
    get_tomorrow_date,
    generate_tomorrow_forecast,
    get_forecast_vs_actual_comparison
)
from preparation import (
    calculate_ingredient_requirements,
    confirm_preparation_plan,
    get_preparations_history
)
from inventory import get_stock_alerts, get_stock_movement_history
from waste import (
    get_waste_reduction_kpis,
    get_waste_monitoring_table,
    get_high_leftover_items,
    get_waste_causes_analysis,
    generate_actionable_recommendations,
    record_leftover_disposition
)
from reports import (
    get_monthly_sales_summary,
    get_monthly_forecast_accuracy,
    get_monthly_preparation_and_leftovers,
    get_monthly_inventory_movements
)
from ui_components import (
    apply_custom_styles,
    render_sidebar,
    render_section_header,
    render_kpi_card,
    render_status_badge,
    render_alert,
    format_inr,
    style_plotly_chart
)

# Set page config
st.set_page_config(
    page_title="Canteen Management Platform",
    page_icon="🍱",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply modern dark theme styling
apply_custom_styles()

# Ensure database exists and is initialized
init_db()
if is_database_empty():
    populate_demo_data(force=False)

# 1. AUTHENTICATION GATEWAY
if not is_authenticated():
    render_login_page()
    st.stop()

# 2. SIDEBAR NAVIGATION
active_section = render_sidebar()


# ==========================================
# 1. DASHBOARD
# ==========================================
if active_section == "Dashboard":
    today_dt = datetime.now().date()
    today_str = today_dt.strftime("%Y-%m-%d")
    tomorrow_dt = get_tomorrow_date()
    tomorrow_str = tomorrow_dt.strftime("%Y-%m-%d")
    
    render_section_header(
        title="Operations Dashboard",
        description="Real-time overview of daily sales revenue, stock levels, and tomorrow's expected demand.",
        icon="📊",
        date_badge=today_dt.strftime("%A, %d %B %Y")
    )
    
    # Query today's sales
    today_sales = get_daily_sales(start_date=today_str, end_date=today_str)
    today_rev = float(today_sales["revenue"].sum()) if not today_sales.empty else 0.0
    today_units = int(today_sales["units_sold"].sum()) if not today_sales.empty else 0
    
    # Query inventory status
    inv_df = get_inventory_status()
    total_ings = len(inv_df)
    low_stock_count = len(inv_df[inv_df["stock_status"] == "Low Stock"])
    out_stock_count = len(inv_df[inv_df["stock_status"] == "Out of Stock"])
    reorder_count = low_stock_count + out_stock_count
    
    # Calculate tomorrow's forecast total
    try:
        tomorrow_fc = generate_tomorrow_forecast(save_to_db=False)
        tomorrow_demand_tot = int(tomorrow_fc["predicted_demand"].sum()) if not tomorrow_fc.empty else 0
    except Exception:
        tomorrow_fc = pd.DataFrame()
        tomorrow_demand_tot = 0
        
    # Essential 4 KPI Cards in a single row
    kpi_cols = st.columns(4)
    with kpi_cols[0]:
        render_kpi_card("Today's Total Sales", f"{today_units:,} servings", f"Recorded for {today_dt.strftime('%d %b')}", "📦")
    with kpi_cols[1]:
        render_kpi_card("Today's Revenue", format_inr(today_rev), "Sales realization", "💰")
    with kpi_cols[2]:
        reorder_sub = f"{out_stock_count} out of stock, {low_stock_count} low" if reorder_count > 0 else "All stock levels optimal"
        render_kpi_card("Low Stock Alerts", f"{reorder_count} items", reorder_sub, "⚠️" if reorder_count > 0 else "✅")
    with kpi_cols[3]:
        render_kpi_card("Tomorrow's Expected Demand", f"{tomorrow_demand_tot:,} servings", f"Target: {tomorrow_dt.strftime('%d %B %Y')}", "🔮")
        
    st.markdown("<div style='margin-top: 14px;'></div>", unsafe_allow_html=True)
    
    # Operational Stock Warnings
    stock_alerts = get_stock_alerts()
    if stock_alerts:
        for alert_item in stock_alerts:
            render_alert(alert_item["message"], alert_item["type"])
            
    st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
    
    # Charts Row
    c_dash1, c_dash2 = st.columns([3, 2])
    
    with c_dash1:
        st.markdown("#### 📈 Sales Revenue Trend (Recent 14 Days)")
        past_14d = (today_dt - timedelta(days=14)).strftime("%Y-%m-%d")
        recent_sales = get_daily_sales(start_date=past_14d, end_date=today_str)
        
        if not recent_sales.empty:
            daily_rev = recent_sales.groupby("date")["revenue"].sum().reset_index()
            fig_trend = px.line(
                daily_rev,
                x="date",
                y="revenue",
                labels={"date": "Date", "revenue": "Revenue (₹)"},
                color_discrete_sequence=["#10B981"]
            )
            fig_trend.update_traces(line=dict(width=2.5), mode="lines+markers")
            style_plotly_chart(fig_trend)
            st.plotly_chart(fig_trend, width="stretch")
        else:
            render_alert("No sales recorded in the past 14 days.", "info")
            
    with c_dash2:
        st.markdown("#### 🍱 Tomorrow's Demand by Category")
        if not tomorrow_fc.empty:
            cat_fc = tomorrow_fc.groupby("category")["predicted_demand"].sum().reset_index()
            fig_cat = px.bar(
                cat_fc,
                x="predicted_demand",
                y="category",
                orientation="h",
                color="predicted_demand",
                color_continuous_scale=["#065F46", "#10B981", "#6EE7B7"],
                labels={"predicted_demand": "Predicted Servings", "category": "Category"}
            )
            fig_cat.update_layout(yaxis=dict(autorange="reversed"))
            style_plotly_chart(fig_cat)
            st.plotly_chart(fig_cat, width="stretch")
        else:
            render_alert("Tomorrow's forecast not yet generated.", "info")
            
    # Recent Sales Table
    st.markdown("### 📋 Today's Sales Records")
    if not today_sales.empty:
        display_today = today_sales[["record_id", "food_name", "category", "units_sold", "selling_price", "revenue"]].copy()
        display_today["selling_price"] = display_today["selling_price"].apply(format_inr)
        display_today["revenue"] = display_today["revenue"].apply(format_inr)
        
        st.dataframe(
            display_today.rename(columns={
                "record_id": "Record ID",
                "food_name": "Food Item",
                "category": "Category",
                "units_sold": "Units Sold",
                "selling_price": "Price",
                "revenue": "Revenue"
            }),
            width="stretch",
            hide_index=True
        )
    else:
        render_alert("No sales recorded for today yet. Navigate to 'Daily Sales' to add entries.", "info")


# ==========================================
# 2. FOOD MANAGEMENT
# ==========================================
elif active_section == "Food Management":
    render_section_header(
        title="Food Menu & Recipe Management",
        description="Register food items, manage prices, and configure raw ingredient requirements per serving.",
        icon="🍲"
    )
    
    tab_list, tab_create = st.tabs(["📋 Food Items Catalog", "➕ Add / Edit Food Item & Recipe"])
    
    food_df = get_food_items()
    all_ingredients = get_ingredients(active_only=True)
    
    with tab_list:
        if not food_df.empty:
            c_f1, c_f2 = st.columns([3, 2])
            with c_f1:
                search_term = st.text_input("🔍 Search Food Items", placeholder="e.g. Dosa, Thali, Chai...")
            with c_f2:
                cat_filter = st.selectbox("Filter Category", ["All Categories"] + config.FOOD_CATEGORIES)
                
            filtered_food = food_df.copy()
            if search_term:
                filtered_food = filtered_food[filtered_food["food_name"].str.contains(search_term, case=False, na=False)]
            if cat_filter != "All Categories":
                filtered_food = filtered_food[filtered_food["category"] == cat_filter]
                
            display_df = filtered_food.copy()
            display_df["selling_price"] = display_df["selling_price"].apply(format_inr)
            display_df["status"] = display_df["is_active"].apply(lambda a: "Active" if a else "Inactive")
            
            st.dataframe(
                display_df[["food_id", "food_name", "category", "selling_price", "status"]].rename(columns={
                    "food_id": "Food ID",
                    "food_name": "Food Name",
                    "category": "Category",
                    "selling_price": "Selling Price",
                    "status": "Status"
                }),
                width="stretch",
                hide_index=True
            )
            
            # View Recipe Details
            st.markdown("#### 🔍 Recipe & Ingredient Requirements")
            food_options = {f"{r['food_name']} ({r['category']})": r["food_id"] for _, r in food_df.iterrows()}
            selected_food_key = st.selectbox("Select Food Item to View Recipe", list(food_options.keys()))
            
            if selected_food_key:
                selected_food_id = food_options[selected_food_key]
                recipe_df = get_food_ingredients(selected_food_id)
                
                if not recipe_df.empty:
                    disp_rcp = recipe_df[["ingredient_name", "quantity_per_serving", "quantity_unit", "unit_cost", "serving_cost"]].copy()
                    disp_rcp["unit_cost"] = disp_rcp["unit_cost"].apply(format_inr)
                    disp_rcp["serving_cost"] = disp_rcp["serving_cost"].apply(format_inr)
                    
                    st.dataframe(
                        disp_rcp.rename(columns={
                            "ingredient_name": "Ingredient",
                            "quantity_per_serving": "Qty / Serving",
                            "quantity_unit": "Unit",
                            "unit_cost": "Cost/Unit",
                            "serving_cost": "Cost/Serving"
                        }),
                        width="stretch",
                        hide_index=True
                    )
                else:
                    render_alert("No recipe ingredients defined for this item yet.", "warning")
        else:
            render_alert("No food items registered in the database.", "info")
            
    with tab_create:
        st.markdown("#### Register or Update Food Item")
        
        edit_mode = st.checkbox("Edit Existing Food Item")
        selected_edit_id = None
        
        if edit_mode and not food_df.empty:
            edit_options = {f"{r['food_id']} - {r['food_name']}": r["food_id"] for _, r in food_df.iterrows()}
            edit_sel = st.selectbox("Select Food Item to Edit", list(edit_options.keys()))
            selected_edit_id = edit_options[edit_sel]
            curr_record = food_df[food_df["food_id"] == selected_edit_id].iloc[0]
            def_name = curr_record["food_name"]
            def_cat = curr_record["category"]
            def_price = float(curr_record["selling_price"])
            def_active = bool(curr_record["is_active"])
        else:
            def_name = ""
            def_cat = "Breakfast"
            def_price = 50.0
            def_active = True
            
        with st.form("food_item_form"):
            col_fi1, col_fi2 = st.columns(2)
            with col_fi1:
                food_name_in = st.text_input("Food Item Name *", value=def_name, placeholder="e.g. Masala Dosa")
                cat_in = st.selectbox("Category *", config.FOOD_CATEGORIES, index=config.FOOD_CATEGORIES.index(def_cat) if def_cat in config.FOOD_CATEGORIES else 0)
            with col_fi2:
                price_in = st.number_input("Selling Price (₹) *", min_value=1.0, max_value=5000.0, value=def_price, step=5.0)
                active_in = st.checkbox("Active on Menu", value=def_active)
                
            st.markdown("##### 🌾 Recipe Ingredients Required per Serving")
            st.caption("Select up to 4 ingredients needed per serving for this food item:")
            
            recipe_items = []
            if not all_ingredients.empty:
                ing_map = {f"{r['ingredient_name']} ({r['unit']})": (r["ingredient_id"], r["unit"]) for _, r in all_ingredients.iterrows()}
                ing_keys = ["-- None --"] + list(ing_map.keys())
                
                cols_r1, cols_r2 = st.columns(2)
                for idx in range(4):
                    target_col = cols_r1 if idx < 2 else cols_r2
                    with target_col:
                        sel_ing = st.selectbox(f"Ingredient #{idx+1}", ing_keys, key=f"rec_ing_{idx}")
                        if sel_ing != "-- None --":
                            ing_id, ing_u = ing_map[sel_ing]
                            qty_val = st.number_input(f"Quantity per serving ({ing_u})", min_value=0.001, max_value=100.0, value=0.05, step=0.01, format="%.3f", key=f"rec_qty_{idx}")
                            recipe_items.append({
                                "ingredient_id": ing_id,
                                "quantity_per_serving": qty_val,
                                "quantity_unit": ing_u
                            })
                            
            submitted = st.form_submit_button("Save Food Item & Recipe", type="primary")
            
            if submitted:
                errors = validate_food_item_input(food_name_in, cat_in, price_in)
                if errors:
                    for e in errors:
                        st.error(e)
                else:
                    success, res_msg = save_food_item_with_ingredients(
                        food_name=food_name_in,
                        category=cat_in,
                        selling_price=price_in,
                        is_active=active_in,
                        ingredients_list=recipe_items,
                        food_id=selected_edit_id
                    )
                    if success:
                        st.success(f"Food item '{food_name_in}' ({res_msg}) saved successfully!")
                        st.rerun()
                    else:
                        st.error(f"Error saving food item: {res_msg}")


# ==========================================
# 3. DAILY SALES
# ==========================================
elif active_section == "Daily Sales":
    render_section_header(
        title="Daily Sales Entry & History",
        description="Record daily food sales with automated revenue calculation. Inventory is updated separately via confirmed preparation or restock.",
        icon="📝"
    )
    
    col_entry, col_kpis = st.columns([3, 2])
    food_list = get_food_items(active_only=True)
    
    with col_entry:
        with st.form("sales_entry_form", clear_on_submit=False):
            st.markdown("#### ➕ Record Daily Sale")
            
            c_s1, c_s2 = st.columns(2)
            with c_s1:
                sale_date = st.date_input("Sales Date", datetime.now().date())
            with c_s2:
                if not food_list.empty:
                    food_options = {f"{r['food_name']} ({format_inr(r['selling_price'])})": r["food_id"] for _, r in food_list.iterrows()}
                    selected_food_label = st.selectbox("Food Item *", list(food_options.keys()))
                    selected_food_id = food_options[selected_food_label]
                    curr_food = food_list[food_list["food_id"] == selected_food_id].iloc[0]
                    default_price = float(curr_food["selling_price"])
                else:
                    selected_food_id = None
                    default_price = 40.0
                    
            c_s3, c_s4 = st.columns(2)
            with c_s3:
                units_sold = st.number_input("Units Sold (Servings) *", min_value=0, max_value=5000, value=45, step=1)
            with c_s4:
                sale_price = st.number_input("Selling Price per Serving (₹) *", min_value=1.0, value=default_price, step=5.0)
                
            c_s5, c_s6 = st.columns(2)
            with c_s5:
                event_name = st.selectbox("Campus Event Today", config.CAMPUS_EVENTS)
            with c_s6:
                is_exam = st.checkbox("Examination Period", value=False)
                
            calc_rev = round(units_sold * sale_price, 2)
            st.markdown(f"**Total Revenue:** <span style='font-size: 1.25rem; font-weight: 700; color: #10B981;'>{format_inr(calc_rev)}</span>", unsafe_allow_html=True)
            
            submit_sale = st.form_submit_button("Save Sales Entry", type="primary", width="stretch")
            
            if submit_sale:
                if not selected_food_id:
                    st.error("Please select a food item.")
                else:
                    date_str = sale_date.strftime("%Y-%m-%d")
                    errs = validate_sales_record(date_str, selected_food_id, units_sold, sale_price)
                    if errs:
                        for e in errs:
                            st.error(e)
                    else:
                        success, rec_id = add_or_update_daily_sale(
                            date_str=date_str,
                            food_id=selected_food_id,
                            units_sold=units_sold,
                            selling_price=sale_price,
                            event_name=event_name,
                            is_exam_period=is_exam
                        )
                        if success:
                            st.success(f"Sales record '{rec_id}' saved successfully! ({units_sold} servings, {format_inr(calc_rev)})")
                            st.rerun()
                        else:
                            st.error(f"Failed to record sale: {rec_id}")
                            
    with col_kpis:
        st.markdown("#### 📊 Operations Snapshot")
        all_sales = get_daily_sales()
        if not all_sales.empty:
            today_str = datetime.now().strftime("%Y-%m-%d")
            today_records = all_sales[all_sales["date"] == today_str]
            today_rev = float(today_records["revenue"].sum()) if not today_records.empty else 0.0
            today_units = int(today_records["units_sold"].sum()) if not today_records.empty else 0
            
            render_kpi_card("Today's Recorded Sales", format_inr(today_rev), f"{today_units} servings sold today", "📅")
            st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
            render_kpi_card("Total Historical Sales", format_inr(all_sales["revenue"].sum()), f"{len(all_sales)} total recorded transactions", "🧾")
        else:
            render_alert("No sales recorded in the database yet.", "info")
            
    st.markdown("---")
    
    # Historical Sales Search & Table
    st.markdown("### 📜 Historical Sales Log")
    col_hf1, col_hf2, col_hf3 = st.columns([2, 2, 2])
    with col_hf1:
        date_range_sel = st.date_input("Date Range", [datetime.now().date() - timedelta(days=30), datetime.now().date()])
    with col_hf2:
        cat_sel = st.selectbox("Category", ["All Categories"] + config.FOOD_CATEGORIES, key="sales_cat_filter")
    with col_hf3:
        search_f = st.text_input("Search Food Item", placeholder="e.g. Chai, Thali...")
        
    if isinstance(date_range_sel, (list, tuple)) and len(date_range_sel) == 2:
        s_start = date_range_sel[0].strftime("%Y-%m-%d")
        s_end = date_range_sel[1].strftime("%Y-%m-%d")
    else:
        s_start = (datetime.now().date() - timedelta(days=30)).strftime("%Y-%m-%d")
        s_end = datetime.now().date().strftime("%Y-%m-%d")
        
    sales_df = get_daily_sales(start_date=s_start, end_date=s_end, category=cat_sel)
    if search_f and not sales_df.empty:
        sales_df = sales_df[sales_df["food_name"].str.contains(search_f, case=False, na=False)]
        
    if not sales_df.empty:
        tot_filtered_rev = sales_df["revenue"].sum()
        tot_filtered_units = sales_df["units_sold"].sum()
        st.markdown(f"**Showing {len(sales_df)} records** | Total Units: **{tot_filtered_units:,}** | Total Revenue: **{format_inr(tot_filtered_rev)}**")
        
        display_sales = sales_df.copy()
        display_sales["selling_price"] = display_sales["selling_price"].apply(format_inr)
        display_sales["revenue"] = display_sales["revenue"].apply(format_inr)
        display_sales["is_exam_period"] = display_sales["is_exam_period"].apply(lambda e: "Yes" if e else "No")
        
        st.dataframe(
            display_sales.rename(columns={
                "record_id": "Record ID",
                "date": "Date",
                "food_name": "Food Item",
                "category": "Category",
                "units_sold": "Units Sold",
                "selling_price": "Price",
                "revenue": "Revenue",
                "event_name": "Campus Event",
                "is_exam_period": "Exams"
            }),
            width="stretch",
            hide_index=True
        )
    else:
        render_alert("No sales records found matching the selected filters.", "info")


# ==========================================
# 4. DEMAND FORECAST (TOMORROW ONLY)
# ==========================================
elif active_section == "Demand Forecast":
    tomorrow_dt = get_tomorrow_date()
    tomorrow_str = tomorrow_dt.strftime("%Y-%m-%d")
    
    render_section_header(
        title="Tomorrow's Food Demand Forecast",
        description=f"Automated next-day demand forecasting for {tomorrow_dt.strftime('%A, %d %B %Y')} with ingredient requirement estimation.",
        icon="🔮",
        date_badge=f"Target: {tomorrow_dt.strftime('%d %b %Y')}"
    )
    
    c_fc_param1, c_fc_param2 = st.columns([2, 2])
    with c_fc_param1:
        ev_choice = st.selectbox("Campus Event Tomorrow", config.CAMPUS_EVENTS, index=1)
    with c_fc_param2:
        is_ex_choice = st.checkbox("Examination Scheduled Tomorrow", value=False)
        
    st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
    
    # Generate Forecast
    fc_df = generate_tomorrow_forecast(
        event_name=ev_choice,
        is_exam_period=is_ex_choice,
        save_to_db=True
    )
    
    if not fc_df.empty:
        if "selling_price" not in fc_df.columns:
            food_df = get_food_items()
            fc_df = pd.merge(fc_df, food_df[["food_id", "selling_price"]], on="food_id", how="left")
            fc_df["selling_price"] = fc_df["selling_price"].fillna(0.0)
            
        if "estimated_revenue" not in fc_df.columns:
            fc_df["estimated_revenue"] = (fc_df["predicted_demand"] * fc_df.get("selling_price", 0.0)).round(2)
            
        if "explanation" not in fc_df.columns:
            fc_df["explanation"] = fc_df.get("demand_explanation", "Steady daily sales trend")
            
        tot_fc = int(fc_df["predicted_demand"].sum())
        est_rev = float(fc_df["estimated_revenue"].sum())
        
        c_kfc1, c_kfc2, c_kfc3 = st.columns(3)
        with c_kfc1:
            render_kpi_card("Tomorrow's Target Date", tomorrow_dt.strftime("%d %B %Y"), tomorrow_dt.strftime("%A"), "📅")
        with c_kfc2:
            render_kpi_card("Total Expected Demand", f"{tot_fc:,} servings", "Across all active items", "🍽️")
        with c_kfc3:
            render_kpi_card("Estimated Revenue", format_inr(est_rev), "Expected sales realization", "💰")
            
        st.markdown("<div style='margin-top: 18px;'></div>", unsafe_allow_html=True)
        
        # Predicted Demand Table
        st.markdown("### 📋 Predicted Demand by Food Item")
        disp_fc = fc_df[["food_id", "food_name", "category", "predicted_demand", "selling_price", "estimated_revenue", "explanation"]].copy()
        disp_fc["selling_price"] = disp_fc["selling_price"].apply(format_inr)
        disp_fc["estimated_revenue"] = disp_fc["estimated_revenue"].apply(format_inr)
        
        st.dataframe(
            disp_fc.rename(columns={
                "food_id": "Food ID",
                "food_name": "Food Item",
                "category": "Category",
                "predicted_demand": "Predicted Servings",
                "selling_price": "Price",
                "estimated_revenue": "Expected Revenue",
                "explanation": "Demand Driver"
            }),
            width="stretch",
            hide_index=True
        )
        
        # Aggregate Ingredient Requirements Preview
        st.markdown("---")
        st.markdown("### 🌾 Estimated Ingredient Requirements for Tomorrow")
        plan_dict = {row["food_id"]: int(row["predicted_demand"]) for _, row in fc_df.iterrows()}
        summary_req, _, is_feasible = calculate_ingredient_requirements(plan_dict)
        
        if not summary_req.empty:
            if not is_feasible:
                render_alert("Inventory Shortage Detected: Some ingredients need to be restocked before tomorrow's preparation.", "warning")
            else:
                render_alert("Inventory Feasible: All required ingredients are in stock for tomorrow's predicted demand.", "success")
                
            disp_req = summary_req[["ingredient_name", "required_quantity", "current_stock", "canonical_unit", "shortage", "status", "estimated_cost"]].copy()
            disp_req["estimated_cost"] = disp_req["estimated_cost"].apply(format_inr)
            
            st.dataframe(
                disp_req.rename(columns={
                    "ingredient_name": "Ingredient",
                    "required_quantity": "Required Qty",
                    "current_stock": "Current Stock",
                    "canonical_unit": "Unit",
                    "shortage": "Shortage Qty",
                    "status": "Stock Status",
                    "estimated_cost": "Estimated Cost"
                }),
                width="stretch",
                hide_index=True
            )
            
            # Confirm Preparation Batch
            st.markdown("---")
            st.markdown("### 🍳 Confirm Kitchen Preparation Batch")
            st.caption("Confirming preparation creates cooking batches and automatically deducts required ingredients from inventory.")
            
            with st.form("confirm_prep_batch_form"):
                col_pb1, col_pb2 = st.columns([3, 1])
                with col_pb1:
                    batch_notes = st.text_input("Batch Preparation Notes (Optional)", placeholder="e.g. Morning preparation batch for campus schedule")
                with col_pb2:
                    st.write("")
                    st.write("")
                    submit_prep = st.form_submit_button("Confirm Batch & Deduct Stock", type="primary", disabled=not is_feasible)
                    
                if submit_prep:
                    if not is_feasible:
                        st.error("Cannot confirm preparation: Insufficient ingredient stock.")
                    else:
                        success, prep_msg, prep_ids = confirm_preparation_plan(tomorrow_str, plan_dict, batch_notes=batch_notes)
                        if success:
                            st.success(prep_msg)
                            st.rerun()
                        else:
                            st.error(f"Preparation confirmation failed: {prep_msg}")
    else:
        render_alert("No active food items found to generate demand forecast.", "warning")


# ==========================================
# 5. INVENTORY
# ==========================================
elif active_section == "Inventory":
    render_section_header(
        title="Inventory & Stock Management",
        description="Track raw ingredient stock balances, view reorder recommendations, and record stock receipts and adjustments.",
        icon="📦"
    )
    
    inv_df = get_inventory_status()
    
    if not inv_df.empty:
        total_items = len(inv_df)
        in_stock_cnt = len(inv_df[inv_df["stock_status"] == "In Stock"])
        low_stock_cnt = len(inv_df[inv_df["stock_status"] == "Low Stock"])
        out_stock_cnt = len(inv_df[inv_df["stock_status"] == "Out of Stock"])
        tot_val = float(inv_df["stock_value"].sum())
        
        k_i1, k_i2, k_i3, k_i4 = st.columns(4)
        with k_i1:
            render_kpi_card("Total Ingredients", f"{total_items} items", f"Valuation: {format_inr(tot_val)}", "🌾")
        with k_i2:
            render_kpi_card("In Stock", f"{in_stock_cnt} items", "Sufficient stock balance", "✅")
        with k_i3:
            render_kpi_card("Low Stock", f"{low_stock_cnt} items", "At or below reorder level", "⚠️")
        with k_i4:
            render_kpi_card("Out of Stock", f"{out_stock_cnt} items", "Zero balance available", "❌")
            
        st.markdown("<div style='margin-top: 14px;'></div>", unsafe_allow_html=True)
        
        # Stock Status Alerts (Factual, deduplicated strictly by ingredient_id)
        stock_alerts = get_stock_alerts()
        if stock_alerts:
            for alert_item in stock_alerts:
                render_alert(alert_item["message"], alert_item["type"])
            
        # Inventory Table
        st.markdown("### 📋 Raw Ingredients Stock Table")
        
        c_is1, c_is2 = st.columns([3, 2])
        with c_is1:
            search_ing = st.text_input("🔍 Search Ingredient", placeholder="e.g. Rice, Milk, Cooking Oil...")
        with c_is2:
            status_filter = st.selectbox("Stock Status Filter", ["All Statuses", "In Stock", "Low Stock", "Out of Stock"])
            
        filtered_inv = inv_df.copy()
        if search_ing:
            filtered_inv = filtered_inv[filtered_inv["ingredient_name"].str.contains(search_ing, case=False, na=False)]
        if status_filter != "All Statuses":
            filtered_inv = filtered_inv[filtered_inv["stock_status"] == status_filter]
            
        display_inv = filtered_inv.copy()
        display_inv["unit_cost"] = display_inv["unit_cost"].apply(format_inr)
        display_inv["stock_value"] = display_inv["stock_value"].apply(format_inr)
        
        st.dataframe(
            display_inv[[
                "ingredient_id", "ingredient_name", "current_stock", "unit",
                "reorder_level", "target_stock", "suggested_replenishment",
                "stock_status", "unit_cost", "stock_value"
            ]].rename(columns={
                "ingredient_id": "ID",
                "ingredient_name": "Ingredient Name",
                "current_stock": "Current Stock",
                "unit": "Unit",
                "reorder_level": "Reorder Level",
                "target_stock": "Target Stock",
                "suggested_replenishment": "Suggested Order",
                "stock_status": "Status",
                "unit_cost": "Cost/Unit",
                "stock_value": "Total Value"
            }),
            width="stretch",
            hide_index=True
        )
    else:
        render_alert("No inventory records found. Register ingredients below.", "info")
        
    st.markdown("---")
    
    # Restock, Adjust, New Ingredient, and Movement History Tabs
    tab_purchase, tab_adjust, tab_new_ing, tab_history = st.tabs([
        "📥 Record Stock Receipt / Restock",
        "⚙️ Manual Stock Adjustment",
        "➕ Register New Ingredient",
        "📜 Movement Audit Log"
    ])
    
    all_raw_ings = get_ingredients(active_only=True)
    
    # TAB 1: RESTOCK / PURCHASE RECEIPT
    with tab_purchase:
        st.markdown("#### Record Received Ingredient Delivery")
        if not all_raw_ings.empty:
            with st.form("purchase_stock_form", clear_on_submit=True):
                col_p1, col_p2 = st.columns(2)
                ing_select_dict = {f"{r['ingredient_name']} ({r['unit']})": r["ingredient_id"] for _, r in all_raw_ings.iterrows()}
                with col_p1:
                    sel_p_ing = st.selectbox("Ingredient Received *", list(ing_select_dict.keys()), key="purch_ing_sel")
                    sel_p_ing_id = ing_select_dict[sel_p_ing]
                    purch_qty = st.number_input("Quantity Received *", min_value=0.1, value=20.0, step=1.0)
                with col_p2:
                    curr_ing_row = all_raw_ings[all_raw_ings["ingredient_id"] == sel_p_ing_id].iloc[0]
                    p_unit = curr_ing_row["unit"]
                    st.text_input("Unit of Measurement", value=p_unit, disabled=True)
                    purch_ref = st.text_input("Purchase Ref / Bill No.", placeholder="e.g. BILL-2026-101")
                    
                purch_notes = st.text_input("Notes (Optional)", placeholder="e.g. Regular weekly restock")
                submit_purch = st.form_submit_button("Confirm Stock Receipt", type="primary")
                
                if submit_purch:
                    success, msg = append_stock_movement(
                        ingredient_id=sel_p_ing_id,
                        movement_type="Purchase",
                        quantity=purch_qty,
                        unit=p_unit,
                        reference_id=purch_ref,
                        notes=purch_notes
                    )
                    if success:
                        st.success(f"Stock receipt recorded! Movement ID: {msg}")
                        st.rerun()
                    else:
                        st.error(f"Error recording receipt: {msg}")
        else:
            render_alert("No active ingredients found.", "info")
            
    # TAB 2: MANUAL ADJUSTMENT
    with tab_adjust:
        st.markdown("#### Record Stock Adjustment (Spoilage, Audit Count)")
        if not all_raw_ings.empty:
            with st.form("adjust_stock_form", clear_on_submit=True):
                col_a1, col_a2 = st.columns(2)
                ing_adj_dict = {f"{r['ingredient_name']} ({r['unit']})": r["ingredient_id"] for _, r in all_raw_ings.iterrows()}
                with col_a1:
                    sel_a_ing = st.selectbox("Ingredient to Adjust *", list(ing_adj_dict.keys()), key="adj_ing_sel")
                    sel_a_ing_id = ing_adj_dict[sel_a_ing]
                    adj_qty = st.number_input("Quantity Change (Positive or Negative) *", value=-2.0, step=0.5)
                with col_a2:
                    curr_a_row = all_raw_ings[all_raw_ings["ingredient_id"] == sel_a_ing_id].iloc[0]
                    a_unit = curr_a_row["unit"]
                    st.text_input("Unit", value=a_unit, disabled=True, key="adj_unit_field")
                    adj_reason = st.text_input("Reason for Adjustment *", placeholder="e.g. Quality spoilage discard")
                    
                submit_adj = st.form_submit_button("Apply Stock Adjustment", type="primary")
                
                if submit_adj:
                    if not adj_reason.strip():
                        st.error("Please enter a valid reason for the stock adjustment.")
                    else:
                        from inventory import record_stock_adjustment
                        success, msg = record_stock_adjustment(
                            ingredient_id=sel_a_ing_id,
                            quantity_change=adj_qty,
                            unit=a_unit,
                            reason=adj_reason
                        )
                        if success:
                            st.success(f"Stock adjustment applied! ({msg})")
                            st.rerun()
                        else:
                            st.error(f"Failed to apply adjustment: {msg}")
        else:
            render_alert("No active ingredients found.", "info")
            
    # TAB 3: REGISTER NEW INGREDIENT
    with tab_new_ing:
        st.markdown("#### Register New Raw Ingredient")
        with st.form("new_ingredient_form", clear_on_submit=True):
            col_ni1, col_ni2 = st.columns(2)
            with col_ni1:
                new_ing_name = st.text_input("Ingredient Name *", placeholder="e.g. Cardamom Pods")
                new_ing_unit = st.selectbox("Standard Measurement Unit *", config.VALID_UNITS)
                new_ing_cost = st.number_input("Unit Cost (₹) *", min_value=0.0, value=50.0, step=5.0)
            with col_ni2:
                new_reorder = st.number_input("Reorder Level *", min_value=0.0, value=10.0, step=1.0)
                new_target = st.number_input("Target Stock *", min_value=0.0, value=50.0, step=5.0)
                new_active = st.checkbox("Active in Inventory", value=True)
                
            submit_new_ing = st.form_submit_button("Register Ingredient", type="primary")
            
            if submit_new_ing:
                errs = validate_ingredient_input(new_ing_name, new_ing_unit, new_ing_cost, new_reorder, new_target)
                if errs:
                    for e in errs:
                        st.error(e)
                else:
                    success, res_ing_id = add_or_update_ingredient(
                        ingredient_name=new_ing_name,
                        unit=new_ing_unit,
                        unit_cost=new_ing_cost,
                        reorder_level=new_reorder,
                        target_stock=new_target,
                        is_active=new_active
                    )
                    if success:
                        st.success(f"Ingredient '{new_ing_name}' ({res_ing_id}) registered successfully!")
                        st.rerun()
                    else:
                        st.error(f"Error registering ingredient: {res_ing_id}")
                        
    # TAB 4: STOCK MOVEMENT AUDIT LOG
    with tab_history:
        st.markdown("#### Complete Stock Movement Audit Log")
        mov_df = get_stock_movement_history(limit=100)
        if not mov_df.empty:
            disp_mov = mov_df.copy()
            st.dataframe(
                disp_mov.rename(columns={
                    "movement_id": "Movement ID",
                    "timestamp": "Timestamp",
                    "ingredient_id": "Ingredient ID",
                    "ingredient_name": "Ingredient Name",
                    "movement_type": "Movement Type",
                    "quantity": "Quantity",
                    "unit": "Unit",
                    "reference_id": "Reference ID",
                    "notes": "Notes"
                }),
                width="stretch",
                hide_index=True
            )
        else:
            render_alert("No stock movements recorded yet.", "info")


# ==========================================
# 6. WASTE REDUCTION
# ==========================================
elif active_section == "Waste Reduction":
    render_section_header(
        title="Food Waste Monitoring & Leftover Management",
        description="Track prepared food quantities, actual sales, estimated leftovers, and recorded dispositions from database records.",
        icon="♻️"
    )
    
    # Period Filter
    col_w_f1, col_w_f2 = st.columns([2, 2])
    with col_w_f1:
        timeframe_sel = st.selectbox(
            "Reporting Timeframe",
            ["Past 30 Days", "Past 14 Days", "Past 7 Days", "Specific Date"]
        )
    with col_w_f2:
        if timeframe_sel == "Specific Date":
            target_w_date = st.date_input("Select Date", datetime.now().date())
            date_filter_str = target_w_date.strftime("%Y-%m-%d")
            days_int = 30
        else:
            date_filter_str = None
            days_map = {"Past 7 Days": 7, "Past 14 Days": 14, "Past 30 Days": 30}
            days_int = days_map.get(timeframe_sel, 30)
            
    st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
    
    waste_kpis = get_waste_reduction_kpis(days=days_int, date_filter=date_filter_str)
    
    # 5 Summary Metrics supported by available database records
    k_w1, k_w2, k_w3, k_w4, k_w5 = st.columns(5)
    with k_w1:
        render_kpi_card("Food Prepared", f"{waste_kpis['total_prepared']:,} servings", "Confirmed batches", "🍳")
    with k_w2:
        render_kpi_card("Food Sold", f"{waste_kpis['total_sold']:,} servings", "Actual sales", "📦")
    with k_w3:
        render_kpi_card("Estimated Leftovers", f"{waste_kpis['total_leftovers']:,} servings", f"{waste_kpis['leftover_rate']}% leftover rate", "📉")
    with k_w4:
        render_kpi_card("Recorded Waste", f"{waste_kpis['total_discarded']:,} servings", "Marked as discarded", "🗑️")
    with k_w5:
        render_kpi_card("Awaiting Disposition", f"{waste_kpis['awaiting_disposition']:,} servings", "Pending record", "⏳")
        
    st.markdown("---")
    
    # 1. Compact Waste Monitoring Table
    st.markdown(f"### 📋 Waste Monitoring Table ({timeframe_sel})")
    st.caption("Factual comparison between prepared quantities and recorded sales across confirmed batches.")
    
    waste_table = get_waste_monitoring_table(days=days_int, date_filter=date_filter_str)
    
    if not waste_table.empty:
        disp_tbl = waste_table[[
            "food_name", "prepared_quantity", "actual_sold_quantity", 
            "estimated_leftover", "discarded_quantity"
        ]].copy()
        
        st.dataframe(
            disp_tbl.rename(columns={
                "food_name": "Food Item",
                "prepared_quantity": "Prepared",
                "actual_sold_quantity": "Sold",
                "estimated_leftover": "Estimated Leftover",
                "discarded_quantity": "Discarded"
            }),
            width="stretch",
            hide_index=True
        )
    else:
        render_alert("No preparation and sales records are available for this date.", "info")
        
    st.markdown("<div style='margin-top: 18px;'></div>", unsafe_allow_html=True)
    
    # 2. Record Leftover Disposition Section
    st.markdown("### 📥 Record Leftover Disposition")
    st.caption("Update whether remaining leftover servings were stored for reuse, donated, or discarded.")
    
    recent_preps = get_preparations_history()
    if not recent_preps.empty:
        # Filter batches that have leftovers
        leftover_batches = recent_preps[recent_preps["unsold_quantity"] > 0]
        if not leftover_batches.empty:
            with st.form("leftover_disp_form", clear_on_submit=True):
                c_ld1, c_ld2, c_ld3 = st.columns([3, 2, 2])
                batch_dict = {f"{r['date']} - {r['food_name']} ({r['unsold_quantity']} leftovers remaining) [Status: {r['disposition']}]": r["preparation_id"] for _, r in leftover_batches.iterrows()}
                with c_ld1:
                    sel_batch_label = st.selectbox("Select Batch *", list(batch_dict.keys()))
                    sel_batch_id = batch_dict[sel_batch_label]
                    selected_batch_row = leftover_batches[leftover_batches["preparation_id"] == sel_batch_id].iloc[0]
                    max_leftover = int(selected_batch_row["unsold_quantity"])
                with c_ld2:
                    disp_type = st.selectbox("Leftover Disposition *", ["Stored or Reused", "Donated", "Discarded", "Not Recorded"])
                with c_ld3:
                    disp_qty = st.number_input("Quantity (Servings) *", min_value=1, max_value=max(1, max_leftover), value=max(1, max_leftover), step=1)
                    
                submit_disp = st.form_submit_button("Save Leftover Disposition", type="primary")
                if submit_disp:
                    success, disp_msg = record_leftover_disposition(sel_batch_id, disp_type, disp_qty)
                    if success:
                        st.success(disp_msg)
                        st.rerun()
                    else:
                        st.error(disp_msg)
        else:
            render_alert("No pending leftover batches require disposition recording.", "success")
    else:
        render_alert("No preparation batches found in the database.", "info")
        
    st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)
    
    # 3. Why Waste Occurs (Factual Analysis from Records)
    st.markdown("### 🔍 Historical Waste & Leftover Analysis")
    waste_causes = get_waste_causes_analysis(days=days_int)
    
    if not waste_causes["excess_by_food"].empty:
        c_wc1, c_wc2 = st.columns(2)
        with c_wc1:
            st.markdown("#### Items with Repeated Excess Preparation")
            st.dataframe(
                waste_causes["excess_by_food"].rename(columns={
                    "food_name": "Food Item",
                    "category": "Category",
                    "excess_quantity": "Total Excess (Servings)",
                    "excess_batches_count": "Batches with Excess"
                }),
                width="stretch",
                hide_index=True
            )
        with c_wc2:
            st.markdown("#### Dates When Preparation Exceeded Sales")
            st.dataframe(
                waste_causes["excess_by_date"].rename(columns={
                    "date": "Date",
                    "excess_quantity": "Total Excess Servings",
                    "items_with_excess": "Affected Food Items"
                }),
                width="stretch",
                hide_index=True
            )
    else:
        render_alert("No excess food preparation recorded for the selected period.", "info")


# ==========================================
# 7. MONTHLY REPORTS
# ==========================================
elif active_section == "Monthly Reports":
    render_section_header(
        title="Monthly Reports",
        description="Review monthly summaries for food sales, revenue in INR, and inventory movements.",
        icon="📈"
    )
    
    # Month Selector (Strictly monthly)
    col_m1, col_m2 = st.columns([2, 2])
    with col_m1:
        curr_m_date = datetime.now().date()
        month_options = []
        for i in range(6):
            m_dt = curr_m_date - timedelta(days=i * 30)
            month_options.append(m_dt.strftime("%Y-%m"))
            
        month_options = sorted(list(set(month_options)), reverse=True)
        selected_month = st.selectbox("Select Report Month (YYYY-MM) *", month_options, index=0)
        
    with col_m2:
        selected_rep_cat = st.selectbox("Filter Category", ["All Categories"] + config.FOOD_CATEGORIES)
        
    st.markdown("---")
    
    tab_rep_sales, tab_rep_inv, tab_rep_waste, tab_rep_fc = st.tabs([
        "💰 Sales Summary",
        "🌾 Inventory Movements",
        "♻️ Preparation & Leftovers",
        "🔮 Forecast Accuracy"
    ])
    
    # 1. MONTHLY SALES
    with tab_rep_sales:
        st.markdown(f"### Monthly Sales Report — {selected_month}")
        m_sales = get_monthly_sales_summary(selected_month, category=selected_rep_cat)
        
        if m_sales["total_units_sold"] > 0:
            k_ms1, k_ms2, k_ms3 = st.columns(3)
            with k_ms1:
                render_kpi_card("Total Sales Revenue", format_inr(m_sales["total_revenue"]), f"Across {m_sales['total_days']} operating days", "💰")
            with k_ms2:
                render_kpi_card("Total Food Items Sold", f"{m_sales['total_units_sold']:,} servings", "All menu items", "📦")
            with k_ms3:
                render_kpi_card("Average Daily Revenue", format_inr(m_sales["avg_daily_revenue"]), "Per operating day", "📊")
                
            st.markdown("<div style='margin-top: 14px;'></div>", unsafe_allow_html=True)
            
            c_ms1, c_ms2 = st.columns(2)
            with c_ms1:
                st.markdown("#### 📈 Daily Sales Totals in Month")
                fig_ms_trend = px.line(
                    m_sales["daily_trend"],
                    x="date",
                    y="revenue",
                    labels={"date": "Date", "revenue": "Daily Revenue (₹)"},
                    color_discrete_sequence=["#10B981"]
                )
                style_plotly_chart(fig_ms_trend)
                st.plotly_chart(fig_ms_trend, width="stretch")
                
            with c_ms2:
                st.markdown("#### 🍱 Revenue by Food Category")
                fig_ms_cat = px.bar(
                    m_sales["category_summary"],
                    x="revenue",
                    y="category",
                    orientation="h",
                    color="revenue",
                    color_continuous_scale=["#065F46", "#10B981", "#6EE7B7"],
                    labels={"revenue": "Revenue (₹)", "category": "Category"}
                )
                fig_ms_cat.update_layout(yaxis=dict(autorange="reversed"))
                style_plotly_chart(fig_ms_cat)
                st.plotly_chart(fig_ms_cat, width="stretch")
                
            # Sales by Food Item Table
            st.markdown("#### 📋 Sales by Food Item")
            if not m_sales["top_selling_items"].empty:
                disp_top = m_sales["top_selling_items"].copy()
                disp_top["revenue"] = disp_top["revenue"].apply(format_inr)
                st.dataframe(
                    disp_top.rename(columns={
                        "food_id": "Food ID",
                        "food_name": "Food Item",
                        "category": "Category",
                        "units_sold": "Units Sold",
                        "revenue": "Total Revenue"
                    }),
                    width="stretch",
                    hide_index=True
                )
                
            # Export CSV
            csv_buf = io.StringIO()
            m_sales["records"].to_csv(csv_buf, index=False)
            st.download_button(
                label=f"⬇️ Export Monthly Sales CSV ({selected_month})",
                data=csv_buf.getvalue(),
                file_name=f"monthly_sales_{selected_month}.csv",
                mime="text/csv"
            )
        else:
            render_alert("No records available for this month.", "info")
            
    # 2. MONTHLY INVENTORY
    with tab_rep_inv:
        st.markdown(f"### Monthly Inventory & Restocking — {selected_month}")
        m_inv = get_monthly_inventory_movements(selected_month)
        
        if not m_inv["records"].empty:
            k_mi1, k_mi2 = st.columns(2)
            with k_mi1:
                render_kpi_card("Total Restocking Purchases", format_inr(m_inv["total_purchases_value"]), "Stock receipts in month", "📥")
            with k_mi2:
                render_kpi_card("Total Ingredient Consumption", format_inr(m_inv["total_consumed_value"]), "Consumed for preparation", "🍳")
                
            st.markdown("<div style='margin-top: 14px;'></div>", unsafe_allow_html=True)
            
            if not m_inv["top_consumed"].empty:
                st.markdown("#### 🌾 Top Consumed Ingredients")
                disp_tc = m_inv["top_consumed"].copy()
                disp_tc["movement_value"] = disp_tc["movement_value"].apply(format_inr)
                st.dataframe(
                    disp_tc.rename(columns={
                        "ingredient_id": "ID",
                        "ingredient_name": "Ingredient Name",
                        "unit": "Unit",
                        "quantity": "Quantity Consumed",
                        "movement_value": "Estimated Value"
                    }),
                    width="stretch",
                    hide_index=True
                )
        else:
            render_alert("No records available for this month.", "info")
            
    # 3. MONTHLY PREPARATION & LEFTOVERS
    with tab_rep_waste:
        st.markdown(f"### Monthly Food Prepared, Sold & Leftovers — {selected_month}")
        m_prep = get_monthly_preparation_and_leftovers(selected_month)
        
        if m_prep["total_prepared"] > 0:
            k_mp1, k_mp2, k_mp3, k_mp4 = st.columns(4)
            with k_mp1:
                render_kpi_card("Prepared Servings", f"{m_prep['total_prepared']:,}", "Confirmed batches", "🍳")
            with k_mp2:
                render_kpi_card("Actual Sold", f"{m_prep['total_sold']:,}", f"{round((m_prep['total_sold']/max(1, m_prep['total_prepared']))*100, 1)}% sold", "📈")
            with k_mp3:
                render_kpi_card("Estimated Leftovers", f"{m_prep['total_unsold']:,}", f"{m_prep['unsold_percentage']}% leftover rate", "📉")
            with k_mp4:
                render_kpi_card("Discarded Waste", f"{m_prep['total_discarded']:,}", "Marked as discarded", "🗑️")
                
            st.markdown("<div style='margin-top: 14px;'></div>", unsafe_allow_html=True)
            
            if not m_prep["daily_trend"].empty:
                st.markdown("#### 📊 Daily Prepared vs. Sold Quantity")
                fig_prep_bar = px.bar(
                    m_prep["daily_trend"],
                    x="date",
                    y=["actual_sold_quantity", "unsold_quantity"],
                    labels={"value": "Servings", "date": "Date", "variable": "Status"},
                    color_discrete_map={"actual_sold_quantity": "#10B981", "unsold_quantity": "#EF4444"}
                )
                style_plotly_chart(fig_prep_bar)
                st.plotly_chart(fig_prep_bar, width="stretch")
        else:
            render_alert("No records available for this month.", "info")
            
    # 4. MONTHLY FORECAST ACCURACY
    with tab_rep_fc:
        st.markdown(f"### Monthly Forecast Accuracy & Evaluation — {selected_month}")
        m_fc = get_monthly_forecast_accuracy(selected_month)
        
        if m_fc["matched_count"] > 0:
            k_fc1, k_fc2, k_fc3 = st.columns(3)
            with k_fc1:
                render_kpi_card("Mean Absolute Error (MAE)", f"{m_fc['overall_mae']} servings", "Average deviation from actual", "🎯")
            with k_fc2:
                render_kpi_card("Root Mean Sq. Error (RMSE)", f"{m_fc['overall_rmse']} servings", "Penalty-weighted variance", "📐")
            with k_fc3:
                render_kpi_card("Mean Percentage Error", f"{m_fc['overall_mape']}%", f"{m_fc['matched_count']} matched predictions", "📊")
                
            st.markdown("<div style='margin-top: 14px;'></div>", unsafe_allow_html=True)
            
            if not m_fc["daily_comparison"].empty:
                st.markdown("#### 📈 Predicted vs. Actual Demand Totals")
                fig_fc_comp = px.line(
                    m_fc["daily_comparison"],
                    x="target_date",
                    y=["predicted_demand", "actual_demand"],
                    labels={"value": "Total Servings", "target_date": "Date", "variable": "Metric"},
                    color_discrete_map={"predicted_demand": "#3B82F6", "actual_demand": "#10B981"}
                )
                style_plotly_chart(fig_fc_comp)
                st.plotly_chart(fig_fc_comp, width="stretch")
                
            if not m_fc["item_accuracy"].empty:
                st.markdown("#### 📋 Accuracy Breakdown by Food Item")
                st.dataframe(
                    m_fc["item_accuracy"].rename(columns={
                        "food_id": "Food ID",
                        "food_name": "Food Item",
                        "category": "Category",
                        "predicted_demand": "Total Predicted",
                        "actual_demand": "Total Actual",
                        "absolute_error": "Avg Absolute Error",
                        "percentage_error": "Avg Error %"
                    }),
                    width="stretch",
                    hide_index=True
                )
        else:
            render_alert("No forecast and sales matches found for this month.", "info")
            
    # Database Backup
    st.markdown("---")
    st.markdown("### 💾 Local SQLite Database Backup")
    st.write(f"The SQLite database is stored persistently at `{config.DB_PATH}`.")
    
    if st.button("📦 Create Timestamped Database Backup", type="secondary"):
        backup_file = backup_database()
        if backup_file:
            st.success(f"Database backed up successfully to `{backup_file}`!")
        else:
            st.error("Failed to create database backup.")
