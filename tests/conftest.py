"""Pytest configuration and test isolation fixtures.
Ensures that all test suites run against an isolated temporary test database,
preventing any mutation or pollution of the user's real database (data/canteen.db).
"""

import os
import shutil
import tempfile
from pathlib import Path
import pytest
import config
import database

ORIGINAL_DB_PATH = config.DB_PATH


@pytest.fixture(scope="session", autouse=True)
def isolate_test_database():
    """Copy current canteen.db to a temporary directory for tests, preventing live database pollution."""
    temp_dir = tempfile.mkdtemp(prefix="canteen_test_")
    temp_db_path = Path(temp_dir) / "test_canteen.db"
    
    if ORIGINAL_DB_PATH.exists():
        shutil.copy2(ORIGINAL_DB_PATH, temp_db_path)
    else:
        database.init_db(temp_db_path)
        
    config.DB_PATH = temp_db_path
    
    yield temp_db_path
    
    # Restore original path
    config.DB_PATH = ORIGINAL_DB_PATH
    try:
        shutil.rmtree(temp_dir, ignore_errors=True)
    except Exception:
        pass
