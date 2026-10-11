# CanteenOS — Canteen Demand Forecasting and Inventory Management System

> **Production-Style Operations Platform for Daily Food Demand Forecasting, Inventory Control, and Leftover Reduction**

CanteenOS is an operations platform designed for everyday use by college canteen staff and administrators. Built with Python, Streamlit, and SQLite, it pairs machine-learning demand forecasting with inventory control, recipe management, and leftover monitoring.

---

## Table of Contents
1. [Project Overview](#project-overview)
2. [Main Features](#main-features)
3. [Technology Stack](#technology-stack)
4. [Project Structure](#project-structure)
5. [Installation & Setup (Windows)](#installation--setup-windows)
6. [Database Initialization](#database-initialization)
7. [Running the Application](#running-the-application)
8. [Automated Testing](#automated-testing)
9. [Team Roles & Responsibilities](#team-roles--responsibilities)
10. [GitHub Collaboration Workflow](#github-collaboration-workflow)
11. [Deployment Notes](#deployment-notes)

---

## Project Overview

College canteens face three core operational challenges:
- **Over-preparation**: Leads to unsold leftovers, avoidable food spoilage, and operational losses.
- **Under-preparation**: Leads to stockouts during peak hours, lost revenue, and student dissatisfaction.
- **Disconnected inventory planning**: Causes unexpected raw ingredient shortages mid-service.

CanteenOS solves these challenges through next-day demand forecasting, relational SQLite persistence, recipe-based ingredient requirement calculations, real-time inventory tracking, and leftover monitoring.

---

## Main Features

- 📊 **Operations Dashboard**: Real-time summary of daily sales revenue, stock levels, and tomorrow's expected food demand.
- 🍱 **Food Management**: Complete catalog of food items, selling prices, categories, and per-serving recipe ingredient requirements.
- 📋 **Daily Sales Recording**: Fast daily transaction entry with automated ₹ revenue calculation and searchable historical logs.
- 🔮 **Next-Day Demand Forecasting**: Next-day-only demand predictions powered by trained scikit-learn models factoring in day-of-week patterns, rolling averages, selling prices, and examination schedules. Transparent category baseline fallbacks are applied for items with limited history.
- 📦 **Inventory & Reorder Tracking**: Live tracking of raw ingredients, reorder threshold alerts, supplier delivery receipts, and manual adjustments.
- 🍳 **Kitchen Preparation & Feasibility**: Pre-cooking feasibility checks against current stock, with atomic SQLite transactions that deduct raw ingredients upon batch confirmation.
- ♻️ **Factual Waste Monitoring**: Precise tracking of prepared servings, actual sales, estimated leftovers, and recorded dispositions (stored, donated, discarded).
- 📈 **Monthly Reporting**: Monthly financial, operational, and inventory movement analytics with direct CSV export.

---

## Technology Stack

| Layer | Component | Description |
| :--- | :--- | :--- |
| **Frontend UI** | Streamlit | Clean, accessible dashboard interface with responsive controls |
| **Database** | SQLite (`data/canteen.db`) | Relational persistence with foreign keys and atomic transactions |
| **Data Processing** | pandas, NumPy, SciPy | Time-series feature engineering and operational analytics |
| **Machine Learning**| scikit-learn, joblib | Supervised regression demand forecasting models |
| **Visualizations** | Plotly Express | Interactive charts formatted for Indian Rupee (₹) currency |
| **Testing** | pytest | 59 automated unit, integration, and operational tests |

---

## Project Structure

```
CanteenOS/
├── app.py                  # Main Streamlit web application & navigation
├── auth.py                 # Authentication, session state & security
├── ui_components.py        # Styling, layout cards, and SVG icons
├── prediction.py           # Next-day demand forecasting & explanations
├── preprocessing.py        # Feature engineering & chronological splits
├── train_model.py          # Model training, comparison & selection pipeline
├── database.py             # SQLite schema, connections & transaction helpers
├── data_store.py           # Core CRUD operations & database queries
├── inventory.py            # Inventory tracking, KPIs & stock alerts
├── preparation.py          # Recipe explosion, feasibility & stock deduction
├── waste.py                # Leftover tracking & factual waste analytics
├── reports.py              # Monthly reports & CSV export generation
├── validation.py           # Input validation rules & unit conversions
├── seed_data.py            # Starter baseline data initialization
├── config.py               # Paths, constants, and global configuration
├── requirements.txt        # Python dependency manifest
├── CONTRIBUTING.md         # Team contribution guidelines & workflow
├── README.md               # Project documentation
├── .gitignore              # Repository exclusions (databases, secrets, etc.)
├── assets/                 # Brand assets and styling files
├── backups/                # Local database backup storage (.gitkeep)
├── data/                   # SQLite database directory (.gitkeep)
├── models/                 # Trained model artifacts & preprocessors
│   ├── best_demand_model.joblib
│   ├── model_metadata.json
│   └── preprocessor.joblib
├── reports/                # Generated report exports (.gitkeep)
└── tests/                  # Automated pytest test suites
    ├── conftest.py
    ├── test_all_pages_dataflow.py
    ├── test_audit_requirements.py
    ├── test_auth.py
    ├── test_data_store.py
    ├── test_e2e_verification.py
    ├── test_inventory.py
    ├── test_prediction.py
    ├── test_preparation.py
    ├── test_preprocessing.py
    ├── test_reports.py
    ├── test_runtime_health.py
    └── test_waste.py
```

---

## Installation & Setup (Windows)

### 1. Clone the Repository
```powershell
git clone https://github.com/rutuuuuuuu/CanteenOS.git
cd CanteenOS
```

### 2. Create and Activate a Virtual Environment
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

> *If PowerShell script execution is restricted on your machine, run:*
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

### 3. Install Required Dependencies
```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

---

## Database Initialization

CanteenOS uses a local SQLite database located at `data/canteen.db`.

- Live databases and operational logs are ignored by Git (`.gitignore`) to keep private transactions secure.
- When launching the application for the first time on a fresh clone, CanteenOS automatically initializes the relational schema (`database.py`) and loads starter data (`seed_data.py`).
- Each team member works against their own independent local database, preventing conflicts and accidental data overwrites.

To manually re-initialize or verify the database from the terminal:
```powershell
python -c "import database, seed_data; database.init_db(); seed_data.populate_demo_data(force=False)"
```

---

## Running the Application

Start the Streamlit application:
```powershell
python -m streamlit run app.py
```

Open your browser at **`http://localhost:8501`**.

---

## Automated Testing

All features, dataflows, calculations, and security safeguards are tested using `pytest`. Tests run inside isolated temporary SQLite databases so the local development database is never modified.

Run the test suite:
```powershell
python -m pytest -v
```

All 59 test cases should pass:
```
============================= 59 passed in 3.66s ==============================
```

---

## Team Roles & Responsibilities

The CanteenOS project is developed by a four-member team:

| Team Member | GitHub Username | Core Responsibility & Ownership |
| :--- | :--- | :--- |
| **Team Leader** | `rutuuuuuuu` | Project ownership, Operations Dashboard, system integration, code reviews, PR approvals, and releases |
| **Developer** | `AnushkaGit5` | Food Management module, menu catalog, recipe ingredient mappings (`food_ingredients`), and pricing |
| **Developer** | `ketki-colab` | Daily Sales module, transaction processing, revenue calculations, and sales history |
| **Developer** | *Username pending* | Demand Forecasting, Inventory Management, Waste Reduction, or Monthly Reporting *(to be finalized)* |

---

## GitHub Collaboration Workflow

To maintain a clean and reliable codebase:

1. **`main` Branch**: Contains stable code. Direct commits to `main` are restricted.
2. **Feature Branches**: All work is completed on dedicated feature branches (e.g., `feature/food-management`).
3. **Pull Requests**: Changes are merged into `main` only through peer-reviewed Pull Requests after all tests pass.
4. **Detailed Guidelines**: Refer to [`CONTRIBUTING.md`](./CONTRIBUTING.md) for full branch naming, commit formatting, and merge instructions.

---

## Deployment Notes

CanteenOS is architected for local deployment or containerized hosting on a local canteen network:
- Can be hosted on a local canteen intranet using `streamlit run app.py --server.port 8501 --server.address 0.0.0.0`.
- Supports cloud-based hosting on Streamlit Community Cloud or Linux VM instances with Python 3.10+.
- Environment variables (`CANTEEN_ADMIN_USER`, `CANTEEN_ADMIN_HASH`) can be configured in `.env` for production environments.
