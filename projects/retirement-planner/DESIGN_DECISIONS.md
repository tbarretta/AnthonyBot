# Retirement Planner — Design Decisions

_Last updated: 2026-05-29_

---

## Overview

A Django-based retirement planning web application with simulation capabilities. Designed API-first for future mobile extension. Invite-only access model.

---

## Stack

| Layer | Technology |
|---|---|
| Backend | Django 5.x |
| Database | PostgreSQL |
| Task Queue | Celery + Redis |
| Frontend | HTMX + Tailwind CSS |
| Charts | Chart.js |
| REST API | Django REST Framework (DRF) |
| Auth (mobile) | JWT via djangorestframework-simplejwt |
| Storage | Cloudflare R2 (S3-compatible, for exports/reports) |
| Email | Mailgun |

---

## Architecture: API-First

All business logic lives in service/engine layers, NOT in views.
- Web views (HTMX) and API views (DRF) call the same service functions
- This ensures mobile can consume the same backend with no duplication
- Simulation engine is completely view-agnostic

```
User (Browser) → HTMX Views → Services → Models / Celery
User (Mobile)  → DRF API   → Services → Models / Celery
```

---

## Apps

### `accounts`
- Custom User model
- Invite-only registration (Invitation model, token-based links)
- Master Admin can create invitations
- JWT token endpoint for mobile (DRF)

### `profiles`
- `UserProfile` — primary user financial data
- `SpouseProfile` — spouse financial data (optional; linked to UserProfile)
- Pre-retirement income sources (both user and spouse)

### `investments`
- `InvestmentAccount` — individual accounts (401k, Roth IRA, etc.)
- Account types: pre-tax and post-tax tracked explicitly
- Employer match logic per account
- Asset allocation (stocks/bonds %) per account
- `IncomeSource` — guaranteed/recurring income streams (SS, pension, rental, IUL, etc.)

### `simulations`
- `Scenario` — named simulation configuration
- `SimulationResult` — stored output (JSON blob + summary stats)
- Simulation engine: `engine/deterministic.py`, `engine/monte_carlo.py`
- Black swan module: `engine/black_swan.py`
- Tax engine: `engine/tax_engine.py`
- Celery task for Monte Carlo (async, long-running)

### `api`
- DRF routers + serializers for all models
- JWT auth
- Versioned: `/api/v1/`
- Designed for future mobile consumption

---

## Access Model

- **Invite-only** — no public registration
- **Master Admin** — Tom; can create invitations, view all users
- **User** — can manage their own profile, accounts, and scenarios
- Users can invite a spouse/partner who shares their household context (separate account)

---

## Data Model Summary

### UserProfile
```
user (OneToOne → User)
birth_date
target_retirement_age
current_state (for tax bracket estimates)
filing_status (single | married_filing_jointly | married_filing_separately | head_of_household)
risk_tolerance (conservative | moderate | aggressive)
annual_income
income_growth_rate (% annual raise assumption)
income_end_age (expected last working year)
has_spouse (bool)
created_at, updated_at
```

### SpouseProfile
```
user_profile (OneToOne → UserProfile)
first_name
birth_date
target_retirement_age
annual_income
income_growth_rate
income_end_age
```

### InvestmentAccount
```
user_profile (FK → UserProfile)
owner (self | spouse)
name (label, e.g. "Tom's 401k at Fidelity")
account_type (401k | roth_401k | traditional_ira | roth_ira | 403b | 457 | taxable | hsa | other_pretax | other_posttax)
is_pre_tax (computed from type; editable for 'other')
is_taxable (bool)
is_hsa (bool)
current_balance
annual_contribution
employer_match_pct (% of contribution matched)
employer_match_limit_pct (% of income up to which match applies)
asset_allocation_stocks (% in equities, 0–100)
asset_allocation_bonds (% in bonds/fixed income)
is_active (False = stopped contributing, e.g. old job)
```

**Note:** Pension is no longer an InvestmentAccount type. Pension income is modeled as an `IncomeSource` with `source_type = "pension"`.

### IncomeSource
```
user_profile (FK → UserProfile)
owner (self | spouse)
name (label, e.g. "Tom's Pension", "Rental — 123 Main St")
source_type (social_security | pension | annuity | iul | rental | business | part_time | other)

# Social Security only (leave null for other types)
ss_monthly_at_62 (monthly benefit from SSA statement)
ss_monthly_at_67 (monthly benefit at FRA)
ss_monthly_at_70 (monthly benefit if delayed to 70)
ss_cola_rate (annual COLA %, default 2.5%; per-source, not scenario-wide)

# All other types (leave at 0 for SS)
annual_amount (annual payout in today's dollars)
start_age (age at which income begins)
end_age (age at which income ends; null = lifetime)

# Growth
is_inflation_adjusted (bool; True = grows annually with inflation)
inflation_rate_override (override inflation %; null = use scenario rate)

# Tax
is_taxable (bool; False = tax-free e.g. Roth, IUL, HSA medical)
tax_rate_override (override tax rate %; null = use scenario retirement rate)

# Pension
survivor_benefit_pct (% paid to spouse after owner dies; pension only)

notes
created_at, updated_at
```

**Design rationale for IncomeSource:**
- Social Security benefit *amounts* (at 62/67/70) are stable facts from the SSA statement → live on `IncomeSource`
- SS *claim age* is the planning variable that differs per scenario → lives on `Scenario`
- `services.py` calls `IncomeSource.monthly_ss_at_claim_age(claim_age)` to interpolate before passing to the engine
- Pension fields (previously on `InvestmentAccount`) are now a first-class income source
- IUL distributions are modeled in the distribution phase only (no accumulation/premium logic)

### Scenario
```
user_profile (FK → UserProfile)
name
description
simulation_type (deterministic | monte_carlo)
# Returns
expected_annual_return_stocks (%)
expected_annual_return_bonds (%)
inflation_rate (%)
# Spending in retirement
annual_retirement_spending (in today's dollars)
spending_growth_rate (% annual increase; default = inflation)
spending_strategy (fixed | percent_of_portfolio | guardrails)
# Monte Carlo specific
mc_iterations (default 1000)
mc_confidence_level (default 85 %)
mc_return_std_dev_stocks (volatility; default 15%)
mc_return_std_dev_bonds (volatility; default 5%)
# Black swan
black_swan_enabled (bool)
black_swan_annual_probability (%, e.g. 3%)
black_swan_min_loss_pct (e.g. 20%)
black_swan_max_loss_pct (e.g. 50%)
black_swan_recovery_years (avg years to recover, e.g. 3)
# Social Security claim strategy (amounts now on IncomeSource)
ss_claim_age_self (age at which user claims SS, 62–70)
ss_claim_age_spouse (age at which spouse claims SS, 62–70)
# Longevity
user_life_expectancy_age
spouse_life_expectancy_age
# Tax assumptions
effective_tax_rate_working (% on ordinary income while working)
effective_tax_rate_retirement (% on taxable withdrawals in retirement)
capital_gains_rate (for taxable accounts)
# Timestamp
created_at, updated_at
```

### SimulationResult
```
scenario (FK → Scenario)
status (pending | running | complete | failed)
error_message (if failed)
# Summary stats
success_probability (% of MC runs that don't run out of money; null for deterministic)
median_balance_at_retirement
median_balance_at_end
deterministic_final_balance
# Full result data (stored as JSON, schema_version 2)
result_data (JSONField) — year-by-year rows for deterministic; percentile curves for MC
# Timestamps
started_at
completed_at
```

---

## Simulation Engine Design

### IncomeSourceInput Dataclass

The engine never touches Django models. Services layer converts `IncomeSource` ORM objects
into `IncomeSourceInput` dataclasses before calling the engine:

```python
@dataclass
class IncomeSourceInput:
    id: int
    name: str
    source_type: str          # "social_security", "pension", etc.
    owner: str                # "self" or "spouse"

    # SS (pre-interpolated by services.py)
    ss_monthly_at_claim_age: float = 0.0
    ss_cola_rate: float = 2.5
    ss_claim_age: int = 67

    # Non-SS
    annual_amount: float = 0.0
    start_age: int = 65
    end_age: Optional[int] = None
    is_inflation_adjusted: bool = False
    inflation_rate_override: Optional[float] = None
    is_taxable: bool = True
    tax_rate_override: Optional[float] = None
    survivor_benefit_pct: Optional[float] = None
```

### Year-by-Year Loop (deterministic engine)

For each year from `current_age` to `max(life_expectancies)`:
1. Compute employment income (self + spouse, while not yet retired)
2. **Per-source income computation** for each `IncomeSourceInput`:
   - **Social Security**: active when `owner_age >= ss_claim_age`; applies COLA from claim age
   - **All others**: active when `owner_age >= start_age` AND `owner_age <= end_age` (or no end_age)
   - Apply inflation adjustment if `is_inflation_adjusted` (from start_age, not from year 0)
3. Record per-source breakdown in year row: `{id, name, source_type, annual_income, is_active, years_until_start}`
4. Apply contributions to each InvestmentAccount (with employer match, while owner not yet retired)
5. Grow each account by its blended return rate (optionally suppressed by black swan)
6. Apply RMDs (age 73+) from pre-tax accounts
7. At retirement: compute spending target (strategy-dependent)
8. Withdrawal gap = spending − sum(active income sources)
9. Withdraw from accounts in order: taxable → pre-tax → Roth (tax-efficient)
10. Record year-end snapshot

### Result Schema (v2)

Year rows include:
```json
{
  "income_sources": [
    {"id": 1, "name": "Tom's SS", "source_type": "social_security",
     "annual_income": 28800.0, "is_active": true},
    {"id": 2, "name": "Rental", "source_type": "rental",
     "annual_income": 0.0, "is_active": false, "years_until_start": 5}
  ],
  "total_guaranteed_income": 28800.0,
  "ss_income": 28800.0,         // legacy alias for template compat
  "pension_income": 0.0,        // legacy alias
  ...
}
```

### Deterministic Engine (`engine/deterministic.py`)
- Single pass of the year-by-year loop
- Uses fixed expected return rates
- Returns array of annual snapshots (schema_version 2)

### Monte Carlo Engine (`engine/monte_carlo.py`)
- Runs N iterations of the year-by-year loop
- Each year's return is sampled: `random.gauss(mean, std_dev)` per account allocation
- Collects percentile distributions (10th, 25th, 50th, 75th, 90th)
- Success = portfolio never hits zero
- Returns percentile curves + success probability
- Run as Celery background task (can take 5–15s for 1000 iterations)

### Black Swan Module (`engine/black_swan.py`)
- Each year: draw `random.random() < annual_probability`
- If triggered: apply portfolio loss of `random.uniform(min_loss, max_loss)` percent
- Recovery: gradual return over `recovery_years` (suppressed returns during recovery)
- Can hit multiple times; each event is independent

### Tax Engine (`engine/tax_engine.py`)
- Pre-tax (401k, trad IRA): contributions reduce taxable income; withdrawals are ordinary income
- Post-tax (Roth): contributions already taxed; growth and withdrawals tax-free
- Taxable: contributions after-tax; dividends/gains taxed annually at capital_gains_rate
- HSA: triple tax-advantaged if used for healthcare
- Pension income: modeled as ordinary income via IncomeSource (is_taxable=True default)
- IUL distributions: tax-free modeled via IncomeSource (is_taxable=False)
- SS: up to 85% taxable depending on combined income (simplified model)

---

## Spending Strategies

| Strategy | Description |
|---|---|
| `fixed` | Spend a fixed amount (inflation-adjusted) each year |
| `percent_of_portfolio` | Spend X% of current portfolio (e.g. 4% rule) |
| `guardrails` | Spend target amount; reduce 10% if portfolio drops >20%; restore if recovers |

---

## Chart Data (returned via API + HTMX partial)

**Deterministic:**
- Balance over time (stacked by account)
- Income vs spending waterfall (all income sources + withdrawals vs expenses)
- Income source breakdown per year (from `income_sources` array in year rows)
- Account composition at retirement

**Monte Carlo:**
- Fan chart: 10/25/50/75/90th percentile balance curves
- Success probability gauge
- Histogram of final portfolio values
- Black swan event overlay (if enabled)

---

## API Design (v1)

Base: `/api/v1/`
Auth: JWT (`/api/v1/auth/token/`, `/api/v1/auth/token/refresh/`)

| Endpoint | Methods | Notes |
|---|---|---|
| `/api/v1/profile/` | GET, PATCH | Includes nested `income_sources` (read-only) |
| `/api/v1/profile/spouse/` | GET, POST, PATCH, DELETE | |
| `/api/v1/investments/accounts/` | GET, POST, PATCH, DELETE | InvestmentAccount CRUD |
| `/api/v1/investments/income/` | GET, POST | IncomeSource list/create |
| `/api/v1/investments/income/<pk>/` | GET, PATCH, DELETE | IncomeSource detail |
| `/api/v1/simulations/scenarios/` | GET, POST, PATCH, DELETE | |
| `/api/v1/simulations/scenarios/<id>/run/` | POST | Triggers run |
| `/api/v1/simulations/results/<id>/` | GET | |
| `/api/v1/simulations/results/<id>/status/` | GET | Polling |

---

## Invite System

- Master Admin creates `Invitation(email, token, expires_at)`
- Invitation email sent via Mailgun with a unique link
- `/accounts/register/<token>/` — validates token, creates User + UserProfile
- Token expires after 7 days
- One-time use (marked used after registration)

---

## Mobile Extension Path

When extending to mobile:
1. DRF API endpoints are already live from day one
2. Add `corsheaders` for mobile origin (already in requirements)
3. JWT auth already configured
4. Simulation results stored in DB — mobile polls `/results/{id}/status/`
5. Chart data returned as structured JSON — mobile renders its own charts
6. Income Sources available at `/api/v1/investments/income/`

No backend changes needed for mobile beyond CORS/auth config.

---

## Folder Structure

```
retirement-planner/
├── DESIGN_DECISIONS.md
├── README.md
├── manage.py
├── requirements.txt
├── .env.example
├── docker-compose.yml
├── retirement_planner/        # Django project config
│   ├── settings/
│   │   ├── base.py
│   │   ├── local.py
│   │   └── production.py
│   ├── urls.py
│   ├── celery.py
│   ├── wsgi.py
│   └── asgi.py
├── apps/
│   ├── accounts/              # Auth, invites, User model
│   ├── profiles/              # UserProfile, SpouseProfile
│   ├── investments/           # InvestmentAccount, IncomeSource
│   ├── simulations/           # Scenarios, results, engine
│   │   └── engine/
│   │       ├── deterministic.py
│   │       ├── monte_carlo.py
│   │       ├── black_swan.py
│   │       └── tax_engine.py
│   └── api/                   # DRF routers, serializers, JWT
├── templates/
│   ├── base.html
│   ├── accounts/
│   ├── profiles/
│   ├── investments/
│   └── simulations/
├── static/
│   ├── css/
│   └── js/
└── tests/
```

---

## Key Constraints & Rules

- All simulation logic lives in `apps/simulations/engine/` — never in views or models
- Views are thin: validate input → call service/engine → return response
- Monte Carlo always runs as a Celery task (never synchronously in a web request)
- Deterministic can run synchronously (fast enough, ~50ms)
- Pre-tax vs post-tax distinction is enforced at the account level, not scenario level
- Spouse data is always optional; engine handles single vs dual scenarios gracefully
- All monetary values stored as `DecimalField` (never `FloatField`) for precision
- All percentages stored as decimal (e.g. 7.5 means 7.5%, not 0.075)
- `result_data` JSON schema is versioned (`schema_version` key); current version is 2
- SS benefit amounts belong on `IncomeSource`; SS claim ages belong on `Scenario`
- Pension income is always an `IncomeSource`, never an `InvestmentAccount`
