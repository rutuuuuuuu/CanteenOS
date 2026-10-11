"""Configuration module for CanteenOS Demand Forecasting and Inventory Management System.
Defines system paths, SQLite database settings, constants, and categorical definitions.
"""

from pathlib import Path

# Base Directory
BASE_DIR = Path(__file__).resolve().parent

# Core Directories
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "models"
REPORTS_DIR = BASE_DIR / "reports"
ASSETS_DIR = BASE_DIR / "assets"
BACKUPS_DIR = BASE_DIR / "backups"

# Ensure runtime directories exist
for directory in [DATA_DIR, MODELS_DIR, REPORTS_DIR, ASSETS_DIR, BACKUPS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# SQLite Database Path
DB_PATH = DATA_DIR / "canteen.db"

# Model Artifacts
BEST_MODEL_PATH = MODELS_DIR / "best_demand_model.joblib"
MODEL_METADATA_PATH = MODELS_DIR / "model_metadata.json"
PREPROCESSOR_PATH = MODELS_DIR / "preprocessor.joblib"

# Random Seed for reproducibility
RANDOM_SEED = 42

# Application Branding
APP_TITLE = "CanteenOS"
APP_SUBTITLE = "CANTEEN MANAGEMENT"
APP_VERSION = "2.2.0"

# Demo Credentials
DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = "admin"

# Navigation Sections (exact 7 items in required order)
SIDEBAR_NAV_ITEMS = [
    ("⊞", "Dashboard"),
    ("◈", "Food Management"),
    ("▤", "Daily Sales"),
    ("↗", "Demand Forecast"),
    ("▣", "Inventory"),
    ("↺", "Waste Reduction"),
    ("◫", "Monthly Reports")
]

# Standard Food Categories
FOOD_CATEGORIES = [
    "Breakfast",
    "Snacks",
    "Meals & Thalis",
    "Rice Dishes",
    "South Indian",
    "North Indian",
    "Beverages",
    "Bakery",
    "Fast Food",
    "Desserts"
]

# Standard Measurement Units
VALID_UNITS = ["kg", "g", "L", "ml", "pcs"]

# Unit conversion factors to base canonical units (kg, L, pcs)
UNIT_CONVERSIONS = {
    "g": ("kg", 0.001),
    "kg": ("kg", 1.0),
    "ml": ("L", 0.001),
    "L": ("L", 1.0),
    "pcs": ("pcs", 1.0)
}

# Expanded Campus Event Options
CAMPUS_EVENTS = [
    "No Special Event",
    "Regular College Day",
    "Internal Examination",
    "Semester Examination",
    "Practical Examination",
    "Viva or Project Evaluation",
    "College Festival",
    "Technical Fest",
    "Cultural Event",
    "Sports Day",
    "Workshop or Seminar",
    "Orientation or Induction",
    "Placement or Recruitment Event",
    "Guest Lecture",
    "Holiday or Campus Closure",
    "Other Event"
]

# Stock Movement Types
MOVEMENT_TYPES = ["Opening Stock", "Purchase", "Consumption", "Adjustment", "Waste"]

# Preparation Statuses
PREPARATION_STATUSES = ["Planned", "Confirmed", "Completed", "Cancelled"]

# Leftover Dispositions
DISPOSITION_TYPES = ["Not Recorded", "Stored for later use", "Reused", "Donated", "Discarded"]

DEFAULT_SAFETY_BUFFER = 0.05  # 5% buffer recommendation for preparation
