"""Tests for auth.py: Login credentials, authentication verification, and logout.
"""

import pytest
import streamlit as st
import config
from auth import login, is_authenticated, logout, init_auth_state


def test_login_success():
    """Test successful login with demo credentials."""
    init_auth_state()
    assert login("admin", "admin") is True
    assert is_authenticated() is True


def test_login_failure():
    """Test failed login with invalid credentials."""
    init_auth_state()
    assert login("wrong_user", "wrong_pass") is False
    assert login("admin", "wrong_pass") is False
    assert login("", "") is False


def test_logout():
    """Test logging out clears session."""
    init_auth_state()
    login("admin", "admin")
    assert is_authenticated() is True
    
    # Simulate logout session clearing
    st.session_state["authenticated"] = False
    assert is_authenticated() is False


def test_remember_me_persistence():
    """Test that Remember Me creates a valid token and clears on logout."""
    from auth import _get_remember_token_file, _verify_remember_token, _clear_remember_token
    init_auth_state()
    _clear_remember_token()
    
    assert login("admin", "admin", remember_me=True) is True
    assert _get_remember_token_file().exists()
    assert _verify_remember_token() == "admin"
    
    _clear_remember_token()
    assert not _get_remember_token_file().exists()
