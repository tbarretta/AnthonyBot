# RetireSim — Retirement Planning Web App

A Django-based retirement planning application with powerful simulation capabilities.

## Features

- **Invite-only** access (like the Gift Registry)
- **User & Spouse Profiles** — income, retirement age, life expectancy
- **Investment Accounts** — 401k, Roth IRA, Traditional IRA, 403b, 457, taxable, HSA, pension
- **Pre-tax & Post-tax** tracking with correct tax treatment
- **Social Security Estimates** — both user and spouse, with COLA
- **Deterministic Simulations** — fast, single-pass projections (~50ms)
- **Monte Carlo Simulations** — probabilistic outcomes with percentile fan charts (async via Celery)
- **Black Swan Events** — configurable probability, severity, and recovery modeling
- **Annual Growth & Withdrawal** modeling including RMDs
- **Spouse Scenario** support (dual incomes, separate retirement ages, separate SS)
- **Multiple Spending Strategies** — fixed, % of portfolio (4% rule), or guardrails
- **REST API** — JWT-authenticated, mobile-ready from day one
- **Interactive Charts** — Chart.js with fan charts, histograms, and income waterfall

## Stack

| Layer | Tech |
|---|---|
| Backend | Django 5.x + PostgreSQL |
| Queue | Celery + Redis |
| Frontend | HTMX + Tailwind CSS |
| Charts | Chart.js |
| REST API | Django REST Framework + JWT |

## Quick Start

```bash
cd AnthonyBot/projects/retirement-planner

# Create virtual env
python -m venv venv && source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your DB/Redis/email credentials

# Start PostgreSQL + Redis (via Docker)
docker-compose up -d db redis

# Run migrations
python manage.py migrate

# Create superuser (Master Admin)
python manage.py createsuperuser

# Start dev server
python manage.py runserver

# Start Celery worker (separate terminal — needed for Monte Carlo)
celery -A retirement_planner worker --loglevel=info
```

## Project Structure

```
retirement-planner/
├── apps/
│   ├── accounts/        # Auth, invite system, custom User model
│   ├── profiles/        # UserProfile, SpouseProfile, SS estimates
│   ├── investments/     # InvestmentAccount (pre-tax + post-tax)
│   ├── simulations/     # Scenarios, results, simulation engine
│   │   └── engine/
│   │       ├── deterministic.py   # Fast single-pass engine
│   │       ├── monte_carlo.py     # Probabilistic N-iteration engine
│   │       ├── black_swan.py      # Black swan event module
│   │       └── tax_engine.py      # Tax treatment by account type
│   └── api/             # DRF REST API (for mobile)
├── templates/
└── DESIGN_DECISIONS.md  # Authoritative architecture reference
```

## API (Mobile Extension)

All features are available via `/api/v1/`. Authenticate with JWT:

```
POST /api/v1/auth/token/   → { access, refresh }
GET  /api/v1/profile/
GET  /api/v1/investments/accounts/
POST /api/v1/simulations/scenarios/{id}/run/
GET  /api/v1/simulations/results/{id}/status/  ← poll this
```

See `DESIGN_DECISIONS.md` for the full API reference.
