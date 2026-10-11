"""UI Components and Styling module for CanteenOS Streamlit application.
Provides a modern, minimal, dark SaaS design inspired by Spotify and Linear principles.
Features transparent, compact sidebar navigation, clean typography,
INR currency formatting, metric cards, status badges, and Plotly chart theming.
"""

from typing import Dict, List, Optional, Any
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px

import config
from auth import logout

# Modern CanteenOS Dark Theme CSS
CUSTOM_CSS = """
<style>
    /* Google Fonts Import including Material Symbols Rounded */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@500;600;700&family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200&display=swap');
    
    /* Global Reset & Typography Baseline */
    *, *::before, *::after {
        text-shadow: none !important;
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
    }
    
    :root {
        --bg-main: #0B0F19;
        --bg-surface: #121826;
        --bg-surface-elevated: #182238;
        --bg-sidebar: #080C14;
        --border-subtle: rgba(255, 255, 255, 0.07);
        --border-hover: rgba(255, 255, 255, 0.14);
        --accent-emerald: #10B981;
        --accent-emerald-light: #34D399;
        --accent-emerald-bg: rgba(16, 185, 129, 0.12);
        --text-primary: #F8FAFC;
        --text-secondary: #94A3B8;
        --text-muted: #64748B;
        --radius-sm: 6px;
        --radius-md: 10px;
        --radius-lg: 14px;
    }
    
    html, body, .stApp {
        font-family: 'Plus Jakarta Sans', 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
        background-color: var(--bg-main) !important;
        color: var(--text-primary) !important;
        letter-spacing: normal !important;
    }
    
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Plus Jakarta Sans', 'Inter', sans-serif !important;
        font-weight: 600 !important;
        color: #FFFFFF !important;
        letter-spacing: -0.01em !important;
        text-shadow: none !important;
        margin-top: 0 !important;
    }
    
    p, label {
        font-family: 'Plus Jakarta Sans', 'Inter', sans-serif !important;
        text-shadow: none !important;
    }

    /* Preserve Material Symbols ligatures and prevent icon text display */
    .material-symbols-rounded,
    .material-symbols-outlined,
    .material-symbols-sharp,
    [class*="material-symbols"],
    span[data-testid="stIconMaterial"] {
        font-family: 'Material Symbols Rounded', 'Material Icons' !important;
        font-style: normal;
        font-weight: normal;
        display: inline-block;
        line-height: 1;
        text-transform: none;
        letter-spacing: normal;
        word-wrap: normal;
        white-space: nowrap;
        direction: ltr;
        -webkit-font-feature-settings: 'liga';
        font-feature-settings: 'liga';
        -webkit-font-smoothing: antialiased;
    }

    /* Bulletproof Clean SVG Chevron for Sidebar Collapse & Expand Controls */
    [data-testid="stSidebarCollapsedControl"] button,
    [data-testid="stSidebarCollapseButton"] button {
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        overflow: hidden !important;
    }

    [data-testid="stSidebarCollapsedControl"] button span,
    [data-testid="stSidebarCollapseButton"] button span {
        font-size: 0 !important;
        line-height: 0 !important;
        text-indent: -9999px !important;
        color: transparent !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        width: 20px !important;
        height: 20px !important;
        position: relative !important;
        overflow: hidden !important;
    }

    [data-testid="stSidebarCollapsedControl"] button span::after {
        content: '' !important;
        position: absolute !important;
        top: 2px !important;
        left: 2px !important;
        width: 16px !important;
        height: 16px !important;
        text-indent: 0 !important;
        background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='%2394A3B8' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='13 17 18 12 13 7'%3E%3C/polyline%3E%3Cpolyline points='6 17 11 12 6 7'%3E%3C/polyline%3E%3C/svg%3E") !important;
        background-repeat: no-repeat !important;
        background-position: center !important;
    }

    [data-testid="stSidebarCollapseButton"] button span::after {
        content: '' !important;
        position: absolute !important;
        top: 2px !important;
        left: 2px !important;
        width: 16px !important;
        height: 16px !important;
        text-indent: 0 !important;
        background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='%2394A3B8' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='11 17 6 12 11 7'%3E%3C/polyline%3E%3Cpolyline points='18 17 13 12 18 7'%3E%3C/polyline%3E%3C/svg%3E") !important;
        background-repeat: no-repeat !important;
        background-position: center !important;
    }
    
    /* Main Content Container Spacing */
    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 2.5rem !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
        max-width: 1360px !important;
    }
    
    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: var(--bg-sidebar) !important;
        border-right: 1px solid var(--border-subtle) !important;
        min-width: 245px !important;
        max-width: 275px !important;
    }
    
    section[data-testid="stSidebar"] > div:first-child {
        background-color: var(--bg-sidebar) !important;
        padding-top: 0.85rem !important;
        padding-left: 0.65rem !important;
        padding-right: 0.65rem !important;
    }
    
    /* Brand Header in Sidebar */
    .sidebar-brand-container {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 4px 6px 14px 6px;
        border-bottom: 1px solid var(--border-subtle);
        margin-bottom: 10px;
    }
    
    .sidebar-brand-icon-box {
        width: 32px;
        height: 32px;
        background: var(--accent-emerald-bg);
        border: 1px solid rgba(16, 185, 129, 0.25);
        border-radius: 7px;
        display: flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
    }
    
    .sidebar-brand-text {
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    
    .sidebar-brand-name {
        font-size: 1.05rem;
        font-weight: 600;
        color: #F8FAFC !important;
        line-height: 1.15;
        margin: 0;
        letter-spacing: -0.01em;
        white-space: nowrap;
    }
    
    .sidebar-brand-sub {
        font-size: 0.62rem;
        color: var(--text-muted) !important;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-weight: 600;
        margin: 2px 0 0 0;
        line-height: 1.1;
    }
    
    /* Sidebar Navigation - Clean, Minimal SaaS Nav */
    section[data-testid="stSidebar"] div.stButton {
        margin: 0 !important;
        padding: 0 !important;
    }
    
    section[data-testid="stSidebar"] div.stButton > button,
    section[data-testid="stSidebar"] button[data-testid*="baseButton"],
    section[data-testid="stSidebar"] button[data-testid*="stBaseButton"],
    section[data-testid="stSidebar"] .stButton > button {
        width: 100% !important;
        height: 40px !important;
        min-height: 40px !important;
        max-height: 40px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: flex-start !important;
        text-align: left !important;
        padding: 0 12px !important;
        margin: 1px 0 !important;
        background: transparent !important;
        background-color: transparent !important;
        border: none !important;
        border-radius: var(--radius-sm) !important;
        box-shadow: none !important;
        outline: none !important;
        color: var(--text-secondary) !important;
        font-size: 0.88rem !important;
        font-weight: 500 !important;
        letter-spacing: normal !important;
        text-shadow: none !important;
        transition: background 0.12s ease, color 0.12s ease !important;
    }
    
    /* Inactive Nav Hover */
    section[data-testid="stSidebar"] div.stButton > button:hover,
    section[data-testid="stSidebar"] button[data-testid*="baseButton-secondary"]:hover,
    section[data-testid="stSidebar"] button[data-testid*="stBaseButton-secondary"]:hover {
        background: rgba(255, 255, 255, 0.04) !important;
        background-color: rgba(255, 255, 255, 0.04) !important;
        color: var(--text-primary) !important;
        border: none !important;
        box-shadow: none !important;
    }
    
    /* Active Nav Item - Highlight only selected page with dark teal/emerald */
    section[data-testid="stSidebar"] div.stButton > button[kind="primary"],
    section[data-testid="stSidebar"] button[data-testid*="baseButton-primary"],
    section[data-testid="stSidebar"] button[data-testid*="stBaseButton-primary"] {
        background: var(--accent-emerald-bg) !important;
        background-color: var(--accent-emerald-bg) !important;
        color: var(--accent-emerald-light) !important;
        font-weight: 600 !important;
        border: none !important;
        border-left: 3px solid var(--accent-emerald) !important;
        border-radius: 0 var(--radius-sm) var(--radius-sm) 0 !important;
        box-shadow: none !important;
    }
    
    /* Inner text formatting in sidebar nav buttons */
    section[data-testid="stSidebar"] div.stButton > button p {
        margin: 0 !important;
        padding: 0 !important;
        font-size: 0.88rem !important;
        text-shadow: none !important;
        letter-spacing: normal !important;
    }
    
    section[data-testid="stSidebar"] div.stButton > button[kind="primary"] p,
    section[data-testid="stSidebar"] button[data-testid*="baseButton-primary"] p,
    section[data-testid="stSidebar"] button[data-testid*="stBaseButton-primary"] p {
        color: var(--accent-emerald-light) !important;
        font-weight: 600 !important;
    }
    
    section[data-testid="stSidebar"] div.stButton > button[kind="secondary"] p,
    section[data-testid="stSidebar"] button[data-testid*="baseButton-secondary"] p,
    section[data-testid="stSidebar"] button[data-testid*="stBaseButton-secondary"] p {
        color: var(--text-secondary) !important;
        font-weight: 500 !important;
    }
    
    section[data-testid="stSidebar"] div.stButton > button:hover p {
        color: var(--text-primary) !important;
    }
    
    /* Compact User Account Section */
    .sidebar-account-container {
        padding-top: 10px;
        margin-top: 14px;
        border-top: 1px solid var(--border-subtle);
    }
    
    .sidebar-account-row {
        display: flex;
        align-items: center;
        gap: 9px;
        padding: 4px 4px 8px 4px;
    }
    
    .sidebar-account-avatar {
        width: 26px;
        height: 26px;
        background: var(--accent-emerald-bg);
        color: var(--accent-emerald);
        border: 1px solid rgba(16, 185, 129, 0.28);
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 700;
        font-size: 0.75rem;
        flex-shrink: 0;
    }
    
    .sidebar-account-details {
        flex: 1;
        line-height: 1.2;
    }
    
    .sidebar-account-name {
        font-size: 0.8rem;
        font-weight: 600;
        color: var(--text-primary);
        margin: 0;
    }
    
    .sidebar-account-status {
        font-size: 0.68rem;
        color: var(--accent-emerald);
        margin: 1px 0 0 0;
        display: flex;
        align-items: center;
        gap: 4px;
        font-weight: 500;
    }
    
    /* Metric Cards */
    .metric-card {
        background: var(--bg-surface);
        border: 1px solid var(--border-subtle);
        border-radius: var(--radius-md);
        padding: 16px 18px;
        transition: transform 0.12s ease, border-color 0.12s ease;
        height: 100%;
    }
    
    .metric-card:hover {
        border-color: var(--border-hover);
        transform: translateY(-1px);
    }
    
    .metric-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 8px;
    }
    
    .metric-title {
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        color: var(--text-secondary);
    }
    
    .metric-icon {
        font-size: 1.1rem;
        opacity: 0.85;
    }
    
    .metric-value {
        font-size: 1.55rem;
        font-weight: 700;
        color: #FFFFFF;
        letter-spacing: -0.02em;
        line-height: 1.15;
        margin-bottom: 4px;
    }
    
    .metric-subtitle {
        font-size: 0.75rem;
        color: var(--text-muted);
        font-weight: 400;
    }
    
    /* Section Headings */
    .page-header-container {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        margin-bottom: 18px;
        padding-bottom: 12px;
        border-bottom: 1px solid var(--border-subtle);
    }
    
    .page-title {
        font-size: 1.3rem;
        font-weight: 700;
        color: #FFFFFF;
        letter-spacing: -0.01em;
        margin: 0 0 4px 0;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    
    .page-subtitle {
        font-size: 0.84rem;
        color: var(--text-secondary);
        margin: 0;
        line-height: 1.4;
    }
    
    .page-date-badge {
        font-size: 0.78rem;
        color: var(--text-secondary);
        background: var(--bg-surface);
        border: 1px solid var(--border-subtle);
        padding: 5px 12px;
        border-radius: var(--radius-sm);
        font-weight: 500;
        display: inline-flex;
        align-items: center;
        gap: 6px;
    }
    
    /* Status Badges */
    .status-badge {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        padding: 3px 8px;
        border-radius: 9999px;
        font-size: 0.72rem;
        font-weight: 600;
    }
    
    .badge-instock { 
        background-color: rgba(16, 185, 129, 0.12); 
        color: #34D399; 
        border: 1px solid rgba(16, 185, 129, 0.25); 
    }
    
    .badge-lowstock { 
        background-color: rgba(245, 158, 11, 0.12); 
        color: #FBBF24; 
        border: 1px solid rgba(245, 158, 11, 0.25); 
    }
    
    .badge-outofstock { 
        background-color: rgba(239, 68, 68, 0.12); 
        color: #F87171; 
        border: 1px solid rgba(239, 68, 68, 0.25); 
    }
    
    /* Alert Banners */
    .alert-banner {
        border-radius: var(--radius-md);
        padding: 12px 16px;
        margin: 10px 0;
        font-size: 0.85rem;
        line-height: 1.45;
        display: flex;
        align-items: flex-start;
        gap: 10px;
        border: 1px solid transparent;
    }
    
    .alert-info { 
        background: rgba(14, 165, 233, 0.08); 
        border-color: rgba(14, 165, 233, 0.22); 
        color: #7DD3FC; 
    }
    
    .alert-success { 
        background: rgba(16, 185, 129, 0.08); 
        border-color: rgba(16, 185, 129, 0.22); 
        color: #6EE7B7; 
    }
    
    .alert-warning { 
        background: rgba(245, 158, 11, 0.08); 
        border-color: rgba(245, 158, 11, 0.22); 
        color: #FCD34D; 
    }
    
    .alert-error { 
        background: rgba(239, 68, 68, 0.08); 
        border-color: rgba(239, 68, 68, 0.22); 
        color: #FCA5A5; 
    }
    
    /* Streamlit Tabs Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: transparent !important;
        border-bottom: 1px solid var(--border-subtle);
        padding-bottom: 2px;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 36px;
        background-color: transparent !important;
        border: none !important;
        border-radius: var(--radius-sm) var(--radius-sm) 0 0 !important;
        color: var(--text-secondary) !important;
        font-size: 0.86rem !important;
        font-weight: 500 !important;
        padding: 0 14px !important;
    }
    
    .stTabs [aria-selected="true"] {
        color: var(--accent-emerald) !important;
        border-bottom: 2px solid var(--accent-emerald) !important;
        font-weight: 600 !important;
    }
    
    /* Form Inputs & Selectboxes */
    div[data-baseweb="input"],
    div[data-baseweb="select"] > div {
        background-color: var(--bg-surface) !important;
        border-color: var(--border-subtle) !important;
        border-radius: var(--radius-sm) !important;
        color: var(--text-primary) !important;
    }
    
    div[data-baseweb="input"]:focus-within,
    div[data-baseweb="select"]:focus-within {
        border-color: var(--accent-emerald) !important;
        box-shadow: 0 0 0 1px var(--accent-emerald) !important;
    }
</style>
"""


def apply_custom_styles():
    """Inject custom CSS styling into Streamlit app."""
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def format_inr(amount: float) -> str:
    """Format a monetary amount in Indian Rupees (₹) using Indian numbering system."""
    try:
        val = float(amount)
        if abs(val) < 1000:
            return f"₹{val:,.2f}"
            
        s, *d = f"{val:.2f}".split(".")
        negative = s.startswith("-")
        if negative:
            s = s[1:]
        digits = s[:-3]
        last_three = s[-3:]
        
        if digits:
            parts = []
            while len(digits) > 2:
                parts.insert(0, digits[-2:])
                digits = digits[:-2]
            if digits:
                parts.insert(0, digits)
            formatted = ",".join(parts) + "," + last_three
        else:
            formatted = last_three
            
        sign = "-" if negative else ""
        return f"{sign}₹{formatted}.{d[0]}"
    except Exception:
        return f"₹{amount}"


def render_sidebar() -> str:
    """Render the CanteenOS left sidebar navigation with a compact, minimal SaaS layout."""
    with st.sidebar:
        # 1. Refined Brand Header with Line Icon and Semi-bold Sans-serif Typography
        st.markdown(
            f"""
            <div class="sidebar-brand-container">
                <div class="sidebar-brand-icon-box">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#10B981" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M18 8h1a4 4 0 0 1 0 8h-1"></path>
                        <path d="M2 8h16v9a4 4 0 0 1-4 4H6a4 4 0 0 1-4-4V8z"></path>
                        <line x1="6" y1="1" x2="6" y2="4"></line>
                        <line x1="10" y1="1" x2="10" y2="4"></line>
                        <line x1="14" y1="1" x2="14" y2="4"></line>
                    </svg>
                </div>
                <div class="sidebar-brand-text">
                    <span class="sidebar-brand-name">CanteenOS</span>
                    <span class="sidebar-brand-sub">CANTEEN MANAGEMENT</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        
        # Initialize active navigation in session state
        nav_names = [name for _, name in config.SIDEBAR_NAV_ITEMS]
        if "active_nav" not in st.session_state or st.session_state["active_nav"] not in nav_names:
            st.session_state["active_nav"] = "Dashboard"
            
        current_nav = st.session_state["active_nav"]
        
        # 2. Minimal Line Navigation Rows (Transparent inactive, dark emerald active)
        for icon, name in config.SIDEBAR_NAV_ITEMS:
            is_active = (name == current_nav)
            button_label = f"{icon}   {name}"
            btn_type = "primary" if is_active else "secondary"
            
            if st.button(button_label, key=f"nav_btn_{name}", type=btn_type):
                if current_nav != name:
                    st.session_state["active_nav"] = name
                    st.rerun()
                    
        # 3. Compact Account Area at Bottom
        username = st.session_state.get("username", "admin")
        initial = username[0].upper() if username else "A"
        
        st.markdown(
            f"""
            <div class="sidebar-account-container">
                <div class="sidebar-account-row">
                    <div class="sidebar-account-avatar">{initial}</div>
                    <div class="sidebar-account-details">
                        <div class="sidebar-account-name">Administrator</div>
                        <div class="sidebar-account-status">● Signed in</div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        
        if st.button("🚪 Sign Out", key="sidebar_sign_out_btn", type="secondary"):
            logout()
            
    return st.session_state["active_nav"]


def render_section_header(title: str, description: str, icon: str = "", date_badge: Optional[str] = None):
    """Render a standardized section header with optional date badge."""
    icon_html = f"<span>{icon}</span>" if icon else ""
    date_html = f"<div class='page-date-badge'>📅 {date_badge}</div>" if date_badge else ""
    
    st.markdown(
        f"""
        <div class="page-header-container">
            <div>
                <h1 class="page-title">{icon_html} {title}</h1>
                <p class="page-subtitle">{description}</p>
            </div>
            {date_html}
        </div>
        """,
        unsafe_allow_html=True
    )


def render_kpi_card(title: str, value: str, subtitle: str = "", icon: str = "📊"):
    """Render a clean metric KPI card."""
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-header">
                <div class="metric-title">{title}</div>
                <div class="metric-icon">{icon}</div>
            </div>
            <div class="metric-value">{value}</div>
            <div class="metric-subtitle">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


def render_status_badge(status: str) -> str:
    """Return HTML for a stock status badge."""
    s_clean = status.lower().replace(" ", "")
    badge_class = f"badge-{s_clean}" if f"badge-{s_clean}" in ["badge-instock", "badge-lowstock", "badge-outofstock"] else "badge-instock"
    return f"<span class='status-badge {badge_class}'>{status}</span>"


def render_alert(message: str, alert_type: str = "info"):
    """Render a styled alert banner (info, success, warning, error)."""
    type_icons = {
        "info": "ℹ️",
        "success": "✅",
        "warning": "⚠️",
        "error": "❌"
    }
    icon = type_icons.get(alert_type, "ℹ️")
    st.markdown(
        f"""
        <div class="alert-banner alert-{alert_type}">
            <span style="font-size: 1.05rem; line-height: 1;">{icon}</span>
            <div>{message}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


def style_plotly_chart(fig: go.Figure, title: str = "", height: int = 320) -> go.Figure:
    """Apply consistent modern dark styling to Plotly charts."""
    fig.update_layout(
        title={
            "text": title,
            "font": {"size": 13, "color": "#F8FAFC", "family": "Plus Jakarta Sans, Inter, sans-serif"},
            "x": 0.02,
            "y": 0.95
        } if title else None,
        font={"family": "Plus Jakarta Sans, Inter, sans-serif", "color": "#94A3B8", "size": 11},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#121826",
        margin=dict(l=35, r=25, t=40 if title else 15, b=35),
        height=height,
        hoverlabel=dict(
            bgcolor="#1E293B",
            font_size=11,
            font_family="Plus Jakarta Sans, Inter, sans-serif",
            font_color="#FFFFFF"
        ),
        xaxis=dict(
            gridcolor="rgba(255,255,255,0.06)",
            showline=True,
            linecolor="rgba(255,255,255,0.12)",
            zeroline=False
        ),
        yaxis=dict(
            gridcolor="rgba(255,255,255,0.06)",
            showline=True,
            linecolor="rgba(255,255,255,0.12)",
            zeroline=False
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1.0,
            font={"color": "#94A3B8"}
        )
    )
    return fig
