# CanteenOS — Team Contribution Guidelines

Welcome to the **CanteenOS** project repository. These guidelines ensure our four-member team works smoothly and consistently using a standard GitHub workflow.

---

## 1. Team Structure & Ownership

| Team Member | GitHub Username | Domain & Focus Area |
| :--- | :--- | :--- |
| **Team Leader** | `rutuuuuuuu` | Architecture, Dashboard, System Integration, Code Review & Releases |
| **Developer** | `AnushkaGit5` | Food Management, Menu Catalog, Recipe Ingredients (`food_ingredients`) |
| **Developer** | `ketki-colab` | Daily Sales, Transaction Logging, Sales Revenue Calculations |
| **Developer** | *Username pending* | Demand Forecasting, Inventory Control, Waste Monitoring, or Reports *(placeholder)* |

> **Note on Fourth Member**: The fourth member will join the repository later. They will follow the exact same branch and PR workflow detailed below without requiring any repository restructuring.

---

## 2. Branching Strategy

Our repository uses a feature-branch workflow. **Direct commits to `main` are strictly prohibited.**

### Branch Naming Conventions
Always create a branch from the latest `main` branch using one of the following prefixes:

- `feature/<module-name>` — For new features or feature enhancements.
  - `feature/dashboard` (Owned by `rutuuuuuuu`)
  - `feature/food-management` (Owned by `AnushkaGit5`)
  - `feature/daily-sales` (Owned by `ketki-colab`)
  - `feature/forecast-inventory` (Owned by Fourth Member / assigned developer)
  - `feature/waste-reduction`
  - `feature/monthly-reports`
- `fix/<bug-description>` — For bug fixes and logic patches (e.g., `fix/negative-stock-check`, `fix/forecast-date-range`).
- `test/<test-description>` — For adding or updating test cases (e.g., `test/sales-dataflow`).
- `docs/<doc-update>` — For updating documentation (e.g., `docs/update-team-roles`).

---

## 3. Step-by-Step Developer Workflow

### Step 1: Clone the Repository & Configure Git
```powershell
git clone https://github.com/rutuuuuuuu/CanteenOS.git
cd CanteenOS
```

Ensure your Git identity matches your GitHub username:
```powershell
git config user.name "YourGitHubUsername"
git config user.email "your_email@example.com"
```

### Step 2: Sync with Latest `main`
Always pull the latest changes before starting new work:
```powershell
git checkout main
git pull origin main
```

### Step 3: Create Your Feature Branch
```powershell
git checkout -b feature/food-management
```
*(Replace `feature/food-management` with your assigned branch name)*

### Step 4: Develop, Test, and Verify Locally
Make your changes in the relevant files. Verify all automated tests pass before committing:
```powershell
python -m pytest -v
```

### Step 5: Stage and Commit Changes
Follow descriptive, conventional commit messages:
```powershell
git add <specific_files>
git commit -m "feat: add ingredient unit conversion validator"
```

### Step 6: Push to Your Remote Branch
```powershell
git push -u origin feature/food-management
```

### Step 7: Open a Pull Request (PR)
1. Go to the GitHub repository page (`https://github.com/rutuuuuuuu/CanteenOS`).
2. Click **Compare & pull request**.
3. Set the base branch to **`main`** and the compare branch to your feature branch.
4. Provide a clear description:
   - What changes were made.
   - Which module or feature was updated.
   - Confirmation that `pytest -v` passed locally with zero failures.
5. Request a review from the Team Leader (`rutuuuuuuu`).

---

## 4. Commit Message Conventions

Commit messages should be concise and use the imperative mood:

- `feat: <description>` — A new feature or enhancement.
- `fix: <description>` — A bug fix.
- `refactor: <description>` — Code restructuring without feature changes.
- `test: <description>` — Adding or updating test cases.
- `docs: <description>` — Documentation improvements.

### Examples:
- `feat: add recipe unit conversion validator in validation.py`
- `fix: prevent duplicate inventory alerts in inventory.py`
- `test: add end-to-end sales persistence test`
- `docs: update setup instructions in README.md`

---

## 5. Code Review & Merge Standards

Before any Pull Request is approved and merged into `main`:

1. **Automated Tests**: All 59 pytest tests must pass (`pytest -v`).
2. **Zero Breaking Changes**: Existing APIs, database schemas, and data structures must remain compatible.
3. **Clean Code**: No leftover debugging code (`print()`, commented-out blocks, temporary scratch scripts).
4. **Approval Required**: At least one review approval from `rutuuuuuuu` is required before merging.
5. **Merge Strategy**: Use **Squash and Merge** or **Rebase and Merge** to maintain a clean linear commit history on `main`.

---

## 6. Database & Secret Security

- **Never Commit `data/canteen.db`**: Live SQLite databases contain local state. The `.gitignore` file excludes `data/*.db` automatically.
- **Never Commit Secrets**: Do not commit API tokens, passwords, `.env` files, or `.streamlit/secrets.toml`.
- **Local Development Databases**:
  - Each developer maintains their own local development database (`data/canteen.db`).
  - A fresh clone automatically initializes the schema via `init_db()` and populates baseline starter data via `populate_demo_data()`.
  - Schema changes must be applied cleanly in `database.py` so all team members receive schema updates automatically.

---

## 7. Handling Merge Conflicts

If another team member merged changes into `main` while you were working on your branch:

1. Fetch and rebase against the updated `main`:
   ```powershell
   git checkout main
   git pull origin main
   git checkout feature/your-branch
   git merge main
   ```
2. Open conflicted files in VS Code / IDE and resolve the conflicts.
3. Run automated tests to verify stability:
   ```powershell
   python -m pytest -v
   ```
4. Commit the resolved changes and push:
   ```powershell
   git add .
   git commit -m "merge: resolve conflicts with main"
   git push origin feature/your-branch
   ```

---

## 8. Questions & Support

For architecture questions, code reviews, or merge assistance, open an **Issue** on the GitHub repository or reach out directly to the Team Leader (`rutuuuuuuu`).
