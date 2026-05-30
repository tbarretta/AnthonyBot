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
- Social Security estimates (both)

### `investments`
- `InvestmentAccount` — individual accounts (401k, Roth IRA, etc.)
- Account types: pre-tax and post-tax tracked explicitly
- Employer match logic per account
- Asset allocation (stocks/bonds %) per account

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

### SocialSecurityEstimate
```
user_profile (FK → UserProfile)
owner (self | spouse)
monthly_benefit_at_62
monthly_benefit_at_67 (FRA)
monthly_benefit_at_70
claim_age (user's intended claim age)
cola_rate (cost-of-living adjustment %, default 2.5%)
```

### InvestmentAccount
```
user_profile (FK → UserProfile)
owner (self | spouse)
name (label, e.g. "Tom's 401k at Fidelity")
account_type (401k | roth_401k | traditional_ira | roth_ira | 403b | 457 | pension | taxable | hsa | other)
is_pre_tax (computed from type; editable for 'other')
current_balance
annual_contribution
employer_match_pct (% of contribution matched)
employer_match_limit_pct (% of income up to which match applies)
asset_allocation_stocks (% in equities, 0–100)
asset_allocation_bonds (% in bonds/fixed income)
expected_pension_annual (for pension type only)
pension_start_age (for pension type only)
is_active (False = stopped contributing, e.g. old job)
```

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
# Full result data (stored as JSON)
result_data (JSONField) — year-by-year rows for deterministic; percentile curves for MC
# Timestamps
started_at
completed_at
```

---

## Simulation Engine Design

### Year-by-Year Loop (shared by both engine types)

For each year from `current_age` to `max(life_expectancies)`:
1. Apply income growth to pre-retirement income sources
2. Apply contributions to each InvestmentAccount (with employer match)
3. Grow each account by its allocated return rate
4. Apply taxes on contributions (pre-tax deferred, post-tax already taxed)
5. At `retirement_age`: stop contributions, start withdrawals
6. Calculate SS benefits at `claim_age`
7. Compute annual spending need (inflation-adjusted)
8. Determine withdrawal gap = spending - SS - pension
9. Withdraw from accounts in order: taxable → pre-tax → Roth (tax-efficient ordering)
10. Apply RMD rules (age 73+) to pre-tax accounts
11. Apply tax on withdrawals based on account type
12. Record year-end balances

### Deterministic Engine (`engine/deterministic.py`)
- Single pass of the year-by-year loop
- Uses fixed expected return rates
- Returns array of annual snapshots

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
- Pension: ordinary income
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
- Income vs spending waterfall (SS + pension + withdrawals vs expenses)
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

| Endpoint | Methods |
|---|---|
| `/api/v1/profiles/` | GET, PATCH |
| `/api/v1/profiles/spouse/` | GET, POST, PATCH, DELETE |
| `/api/v1/profiles/social-security/` | GET, POST, PATCH |
| `/api/v1/investments/accounts/` | GET, POST, PATCH, DELETE |
| `/api/v1/simulations/scenarios/` | GET, POST, PATCH, DELETE |
| `/api/v1/simulations/scenarios/{id}/run/` | POST (triggers run) |
| `/api/v1/simulations/results/{id}/` | GET |
| `/api/v1/simulations/results/{id}/status/` | GET (polling) |

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
│   ├── profiles/              # UserProfile, SpouseProfile, SS estimates
│   ├── investments/           # InvestmentAccount
│   ├── simulations/           # Scenarios, results, engine
│   │   └── engine/
│   │       ├── deterministic.py
│   │       ├── monte_carlo.py
│   │       ├── black_swan.py
│   │       └── tax_engine.py
│   └── api/                   # DRF routers, serializers, JWT
├── templates/
│   ├── base.html
│   ├── components/            # HTMX partials
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
- `result_data` JSON schema is versioned (`schema_version` key) to support migrations
