"""Authentication and session management module.
Provides secure password verification, genuine Remember Me persistence,
and an elegant, reference-inspired dark SaaS login interface with underline inputs.
"""

import hashlib
import hmac
import json
import os
import secrets
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
import streamlit as st
import config

# Pre-computed SHA-256 hashes of default administrative credentials
DEFAULT_ADMIN_USER = os.getenv("CANTEEN_ADMIN_USER", "admin")
DEFAULT_ADMIN_PASSWORDS = ["admin", "admin123"]
DEFAULT_ADMIN_HASHES = [
    hashlib.sha256(pwd.encode("utf-8")).hexdigest()
    for pwd in DEFAULT_ADMIN_PASSWORDS
]


def _hash_string(text: str) -> str:
    """Compute SHA-256 hash of an input string."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _get_remember_token_file() -> Path:
    """Get path to the local remember-token storage."""
    target_dir = Path(config.DATA_DIR)
    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir / ".remember_token"


def _save_remember_token(username: str) -> None:
    """Save a cryptographically secure token for Remember Me session persistence."""
    try:
        token_secret = secrets.token_hex(32)
        token_hash = _hash_string(token_secret)
        expires_at = (datetime.now() + timedelta(days=30)).isoformat()
        
        token_data = {
            "username": username,
            "token_hash": token_hash,
            "token_secret": token_secret,
            "expires_at": expires_at
        }
        
        token_file = _get_remember_token_file()
        with open(token_file, "w", encoding="utf-8") as f:
            json.dump(token_data, f)
    except Exception:
        pass


def _verify_remember_token() -> Optional[str]:
    """Verify saved Remember Me token if present and not expired."""
    try:
        token_file = _get_remember_token_file()
        if not token_file.exists():
            return None
            
        with open(token_file, "r", encoding="utf-8") as f:
            token_data = json.load(f)
            
        username = token_data.get("username", "")
        token_hash = token_data.get("token_hash", "")
        token_secret = token_data.get("token_secret", "")
        expires_at_str = token_data.get("expires_at", "")
        
        if not username or not token_hash or not token_secret or not expires_at_str:
            return None
            
        expires_at = datetime.fromisoformat(expires_at_str)
        if datetime.now() > expires_at:
            _clear_remember_token()
            return None
            
        # Verify hash integrity
        expected_hash = _hash_string(token_secret)
        if hmac.compare_digest(token_hash, expected_hash) and hmac.compare_digest(username, DEFAULT_ADMIN_USER):
            return username
            
        return None
    except Exception:
        return None


def _clear_remember_token() -> None:
    """Clear saved Remember Me session token."""
    try:
        token_file = _get_remember_token_file()
        if token_file.exists():
            token_file.unlink()
    except Exception:
        pass


def init_auth_state():
    """Initialize session state variables for authentication, checking Remember Me persistence if needed."""
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    if "username" not in st.session_state:
        st.session_state["username"] = ""
        
    # Auto-login if valid Remember Me token exists
    if not st.session_state["authenticated"]:
        remembered_user = _verify_remember_token()
        if remembered_user:
            st.session_state["authenticated"] = True
            st.session_state["username"] = remembered_user


def is_authenticated() -> bool:
    """Check if the user is currently authenticated."""
    init_auth_state()
    return bool(st.session_state.get("authenticated", False))


def verify_credentials(username_input: str, password_input: str) -> bool:
    """Securely verify submitted username and password using constant-time hash comparison."""
    u = username_input.strip()
    p = password_input.strip()
    
    if not u or not p:
        return False
        
    p_hash = _hash_string(p)
    
    user_match = hmac.compare_digest(u, DEFAULT_ADMIN_USER)
    pass_match = any(hmac.compare_digest(p_hash, h) for h in DEFAULT_ADMIN_HASHES)
    
    return user_match and pass_match


def login(username_input: str, password_input: str, remember_me: bool = False) -> bool:
    """Authenticate the user, set session variables, and handle Remember Me persistence."""
    init_auth_state()
    if verify_credentials(username_input, password_input):
        u = username_input.strip()
        st.session_state["authenticated"] = True
        st.session_state["username"] = u
        
        if remember_me:
            _save_remember_token(u)
        else:
            _clear_remember_token()
            
        return True
    return False


def logout():
    """Clear the authenticated session and persistent token."""
    st.session_state["authenticated"] = False
    st.session_state["username"] = ""
    _clear_remember_token()
    st.rerun()


def render_login_page():
    """Render a compact, centered, reference-inspired dark SaaS login screen with underline inputs,
    proper eye visibility toggle, and Remember Me control.
    """
    init_auth_state()
    
    # Injected CSS scoped specifically to the login screen
    st.markdown(
        """
        <style>
        /* Hide sidebar completely during login */
        [data-testid="stSidebar"],
        [data-testid="stSidebarNav"] {
            display: none !important;
        }
        
        /* Viewport Centering */
        .main .block-container {
            max-width: 100% !important;
            padding-top: 10vh !important;
            padding-bottom: 2.5rem !important;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
            display: flex !important;
            justify-content: center !important;
            align-items: center !important;
        }
        
        /* Compact Card Container (400px - 440px) with subtle glow */
        div[data-testid="stForm"] {
            max-width: 420px !important;
            width: 100% !important;
            margin: 0 auto !important;
            background: linear-gradient(180deg, #111827 0%, #0D131F 100%) !important;
            border: 1px solid rgba(16, 185, 129, 0.22) !important;
            border-radius: 16px !important;
            padding: 36px 30px 30px 30px !important;
            box-shadow: 0 20px 50px rgba(0, 0, 0, 0.65), 0 0 35px rgba(16, 185, 129, 0.08) !important;
        }
        
        /* Form Field Labels */
        div[data-testid="stForm"] label p {
            font-size: 0.85rem !important;
            font-weight: 500 !important;
            color: #CBD5E1 !important;
            margin-bottom: 2px !important;
        }
        
        /* Underline Style Input Fields */
        div[data-testid="stForm"] div[data-baseweb="input"] {
            height: 44px !important;
            min-height: 44px !important;
            background: transparent !important;
            background-color: transparent !important;
            border-top: none !important;
            border-left: none !important;
            border-right: none !important;
            border-bottom: 2px solid rgba(255, 255, 255, 0.22) !important;
            border-radius: 0px !important;
            padding-left: 4px !important;
            padding-right: 6px !important;
            box-shadow: none !important;
            transition: border-bottom-color 0.2s ease !important;
            position: relative !important;
        }
        
        div[data-testid="stForm"] div[data-baseweb="input"]:focus-within {
            border-bottom-color: #10B981 !important;
            border-top: none !important;
            border-left: none !important;
            border-right: none !important;
            box-shadow: none !important;
        }
        
        div[data-testid="stForm"] div[data-baseweb="input"] input {
            color: #F8FAFC !important;
            font-size: 0.95rem !important;
            background: transparent !important;
            padding-right: 36px !important;
        }
        
        /* Professional Eye-Off / Open-Eye Password Visibility Toggle */
        div[data-testid="stForm"] div[data-baseweb="input"] button {
            background: transparent !important;
            background-color: transparent !important;
            border: none !important;
            box-shadow: none !important;
            padding: 0 !important;
            margin: 0 !important;
            color: transparent !important;
            cursor: pointer !important;
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
            outline: none !important;
            font-size: 0 !important;
            line-height: 0 !important;
            text-indent: -9999px !important;
            overflow: hidden !important;
            position: relative !important;
            width: 28px !important;
            height: 28px !important;
            min-width: 28px !important;
            background-repeat: no-repeat !important;
            background-position: center !important;
            background-size: 18px 18px !important;
            transition: opacity 0.15s ease !important;
        }
        
        /* Suppress raw textual ligatures or spans */
        div[data-testid="stForm"] div[data-baseweb="input"] button * {
            display: none !important;
            font-size: 0 !important;
            line-height: 0 !important;
            visibility: hidden !important;
            opacity: 0 !important;
        }
        
        /* 1. When password is HIDDEN (default): show eye-with-a-slash icon */
        div[data-testid="stForm"] div[data-baseweb="input"] button,
        div[data-testid="stForm"] div[data-baseweb="input"]:has(input[type="password"]) button {
            background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='18' height='18' viewBox='0 0 24 24' fill='none' stroke='%2394A3B8' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M9.88 9.88a3 3 0 1 0 4.24 4.24'%3E%3C/path%3E%3Cpath d='M10.73 5.08A10.43 10.43 0 0 1 12 5c7 0 10 7 10 7a13.16 13.16 0 0 1-1.67 2.68'%3E%3C/path%3E%3Cpath d='M6.61 6.61A13.526 13.526 0 0 0 2 12s3 7 10 7a9.74 9.74 0 0 0 5.39-1.61'%3E%3C/path%3E%3Cline x1='2' y1='2' x2='22' y2='22'%3E%3C/line%3E%3C/svg%3E") !important;
        }
        
        div[data-testid="stForm"] div[data-baseweb="input"]:has(input[type="password"]) button:hover {
            background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='18' height='18' viewBox='0 0 24 24' fill='none' stroke='%2310B981' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M9.88 9.88a3 3 0 1 0 4.24 4.24'%3E%3C/path%3E%3Cpath d='M10.73 5.08A10.43 10.43 0 0 1 12 5c7 0 10 7 10 7a13.16 13.16 0 0 1-1.67 2.68'%3E%3C/path%3E%3Cpath d='M6.61 6.61A13.526 13.526 0 0 0 2 12s3 7 10 7a9.74 9.74 0 0 0 5.39-1.61'%3E%3C/path%3E%3Cline x1='2' y1='2' x2='22' y2='22'%3E%3C/line%3E%3C/svg%3E") !important;
        }
        
        /* 2. When password is REVEALED (type="text"): switch to open eye icon */
        div[data-testid="stForm"] div[data-baseweb="input"]:has(input[type="text"]) button {
            background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='18' height='18' viewBox='0 0 24 24' fill='none' stroke='%2310B981' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z'%3E%3C/path%3E%3Ccircle cx='12' cy='12' r='3'%3E%3C/circle%3E%3C/svg%3E") !important;
        }
        
        /* Remember Me Checkbox */
        div[data-testid="stForm"] div[data-testid="stCheckbox"] {
            margin-top: 10px !important;
            margin-bottom: 12px !important;
        }
        
        div[data-testid="stForm"] div[data-testid="stCheckbox"] label span {
            font-size: 0.88rem !important;
            color: #94A3B8 !important;
        }
        
        /* Primary Login Button */
        div[data-testid="stForm"] button[kind="primary"],
        div[data-testid="stForm"] button[data-testid*="FormSubmitButton"] {
            height: 44px !important;
            min-height: 44px !important;
            background: #10B981 !important;
            background-color: #10B981 !important;
            color: #FFFFFF !important;
            font-size: 0.95rem !important;
            font-weight: 600 !important;
            letter-spacing: 0.03em !important;
            border: none !important;
            border-radius: 8px !important;
            box-shadow: 0 4px 14px rgba(16, 185, 129, 0.3) !important;
            transition: background 0.15s ease, transform 0.1s ease !important;
            margin-top: 6px !important;
        }
        
        div[data-testid="stForm"] button[kind="primary"]:hover,
        div[data-testid="stForm"] button[data-testid*="FormSubmitButton"]:hover {
            background: #059669 !important;
            background-color: #059669 !important;
            transform: translateY(-1px) !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )
    
    # Centered column layout
    col_l, col_center, col_r = st.columns([1, 1.2, 1])
    
    with col_center:
        with st.form("canteen_login_form", clear_on_submit=False):
            # Centered Reference LOGIN Heading
            st.markdown(
                """
                <div style="text-align: center; margin-bottom: 24px;">
                    <div style="width: 36px; height: 36px; background: rgba(16, 185, 129, 0.12); border: 1px solid rgba(16, 185, 129, 0.28); border-radius: 8px; display: inline-flex; align-items: center; justify-content: center; margin-bottom: 8px;">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#10B981" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M18 8h1a4 4 0 0 1 0 8h-1"></path>
                            <path d="M2 8h16v9a4 4 0 0 1-4 4H6a4 4 0 0 1-4-4V8z"></path>
                            <line x1="6" y1="1" x2="6" y2="4"></line>
                            <line x1="10" y1="1" x2="10" y2="4"></line>
                            <line x1="14" y1="1" x2="14" y2="4"></line>
                        </svg>
                    </div>
                    <h1 style="font-size: 1.6rem; font-weight: 700; color: #FFFFFF; margin: 0 0 4px 0; letter-spacing: 0.06em;">LOGIN</h1>
                    <p style="font-size: 0.82rem; color: #94A3B8; margin: 0; line-height: 1.35;">CanteenOS Management System</p>
                </div>
                """,
                unsafe_allow_html=True
            )
            
            user_input = st.text_input(
                "Username",
                placeholder="Enter username",
                key="login_user_field"
            )
            
            pass_input = st.text_input(
                "Password",
                type="password",
                placeholder="Enter password",
                key="login_pass_field"
            )
            
            remember_me = st.checkbox("Remember Me", key="login_remember_me", value=False)
            
            submit_btn = st.form_submit_button(
                "Login",
                type="primary",
                width="stretch"
            )
            
            if submit_btn:
                if not user_input.strip() or not pass_input.strip():
                    st.error("Please enter both username and password.")
                elif login(user_input, pass_input, remember_me=remember_me):
                    st.success("Authentication successful. Loading workspace...")
                    st.rerun()
                else:
                    st.error("Invalid username or password. Please check your credentials and try again.")
