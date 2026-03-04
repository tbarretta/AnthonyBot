# Gift Registry — Setup & Operations Guide

## First-Time Setup (What We Did)

These steps were followed once to get the project running from scratch.

### 1. Prerequisites

Install **Docker Desktop for Windows**:
👉 https://www.docker.com/products/docker-desktop/

After installing:
- Open Docker Desktop → **Settings → Resources → WSL Integration**
- Enable integration for your WSL distro
- Click **Apply & Restart**

Open a **fresh WSL terminal** after Docker Desktop installs (required to pick up the `docker` group).

---

### 2. Configure Environment

```bash
cd /home/tbarr/.openclaw/workspace/AnthonyBot/projects/gift-registry
cp .env.example .env
```

Edit `.env` and fill in your values:

| Key | Description |
|---|---|
| `DJANGO_SECRET_KEY` | Any long random string (keep it secret) |
| `MAILGUN_API_KEY` | From your Mailgun dashboard |
| `MAILGUN_SENDER_DOMAIN` | Your verified sending domain (e.g. `mg.yourdomain.com`) |
| `DEFAULT_FROM_EMAIL` | Sender address (e.g. `noreply@mg.yourdomain.com`) |
| `MASTER_ADMIN_EMAIL` | Your email address |
| `SITE_URL` | `http://localhost:8000` for dev |

---

### 3. Build and Start Docker

```bash
docker compose up --build
```

- `--build` compiles the Docker images for the first time
- Starts 5 services: **web**, **db** (PostgreSQL), **redis**, **celery**, **celery-beat**
- Wait until you see: `System check identified no issues (0 silenced)`

---

### 4. Run Database Migrations

Open a **second WSL terminal**, then:

```bash
cd /home/tbarr/.openclaw/workspace/AnthonyBot/projects/gift-registry

# Create migration files for each app (order matters — accounts first)
docker compose exec web python manage.py makemigrations accounts
docker compose exec web python manage.py makemigrations families
docker compose exec web python manage.py makemigrations wishlist
docker compose exec web python manage.py makemigrations access
docker compose exec web python manage.py makemigrations notifications

# Apply all migrations to the database
docker compose exec web python manage.py migrate
```

> **Why the order?** `accounts` defines the custom User model that all other apps depend on.
> `makemigrations` only needs to be run once per app on first setup, or again when you change a model.
> `migrate` applies pending migration files to the database.

---

### 5. Create Your Master Admin Account

```bash
docker compose exec web python manage.py createsuperuser
```

Follow the prompts (name, email, password). This account gets the ⚡ Admin panel.

---

### 6. Open the App

Visit **http://localhost:8000** in your browser and sign in.

---

## Day-to-Day Operations

### Starting the app

```bash
cd /home/tbarr/.openclaw/workspace/AnthonyBot/projects/gift-registry
docker compose up
```

No `--build` needed for normal startups. Docker will reuse the existing images.

### Stopping the app

```bash
docker compose down
```

Your data is safe — PostgreSQL data lives in a Docker volume (`postgres_data`) and persists between restarts.

### Running in the background

```bash
docker compose up -d
```

The `-d` flag runs everything detached (no terminal lock). Use `docker compose down` to stop.

---

## Common Commands Reference

### Docker

| Command | What it does |
|---|---|
| `docker compose up` | Start all services (normal) |
| `docker compose up --build` | Rebuild images + start (use after changing `requirements.txt` or `Dockerfile`) |
| `docker compose up -d` | Start in background (detached) |
| `docker compose down` | Stop and remove containers (data is preserved) |
| `docker compose logs -f` | Stream logs from all services |
| `docker compose logs -f web` | Stream logs from the web service only |
| `docker compose ps` | Show running container status |
| `docker compose restart web` | Restart just the web service |

### Django (run inside the container)

| Command | What it does |
|---|---|
| `docker compose exec web python manage.py makemigrations` | Generate migration files after model changes |
| `docker compose exec web python manage.py migrate` | Apply pending migrations to the database |
| `docker compose exec web python manage.py createsuperuser` | Create a new Master Admin account |
| `docker compose exec web python manage.py shell` | Open an interactive Django shell |
| `docker compose exec web python manage.py collectstatic` | Gather static files (needed for production) |

---

## Application URLs

| URL | Description |
|---|---|
| http://localhost:8000 | Home / login |
| http://localhost:8000/dashboard/ | Your dashboard |
| http://localhost:8000/wishlist/ | Your wishlist |
| http://localhost:8000/accounts/preferences/ | Notification preferences |
| http://localhost:8000/admin/ | Master Admin panel (⚡ link in nav) |
| http://localhost:8000/django-admin/ | Django's built-in admin (debugging/data inspection) |

---

## Project Structure

```
gift-registry/
├── docker-compose.yml          # Defines all services (web, db, redis, celery)
├── Dockerfile                  # How the web/celery image is built
├── requirements.txt            # Python dependencies
├── .env                        # Your local config (never commit this)
├── .env.example                # Template for .env
├── manage.py                   # Django management entry point
├── giftregistry/
│   ├── settings/
│   │   ├── base.py             # Shared settings
│   │   ├── dev.py              # Development overrides
│   │   └── prod.py             # Production overrides
│   ├── celery.py               # Celery configuration
│   └── urls.py                 # Root URL routing
├── apps/
│   ├── accounts/               # Users, auth, registration, preferences
│   ├── families/               # Families, memberships, invitations, themes
│   ├── wishlist/               # Wishlist items, purchases, visibility
│   ├── access/                 # Access requests (approve/deny flow)
│   └── notifications/          # Celery email tasks, activity log, Master Admin
└── templates/
    ├── base.html               # Shared layout + nav + theming
    ├── accounts/               # Login, register, dashboard, preferences, etc.
    ├── families/               # Family detail + admin pages
    ├── wishlist/               # Wishlist views + item forms
    ├── access/                 # Access request/response pages
    ├── admin/                  # Master Admin panel
    └── emails/                 # Transactional email templates
```

---

## Email (Mailgun)

Outbound email is handled by [Mailgun](https://www.mailgun.com) via `django-anymail`.

Emails sent by the app:
- **Verify email** — on registration
- **Invitation** — when a Family Admin invites someone
- **Password reset** — on request
- **Access request** — when a member requests wishlist access
- **Access response** — when approved or declined
- **New item** — when a subscribed member adds a wishlist item

To test email locally without sending real mail, set this in `.env`:
```
MAILGUN_API_KEY=
```
Django will fall back to printing emails to the console. Or set in `dev.py`:
```python
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
```
