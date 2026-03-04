# Gift Registry

A family gift registry web application built with Django, PostgreSQL, Celery, and HTMX.

## Quick Start

### 1. Clone & configure environment
```bash
cp .env.example .env
# Edit .env — set DJANGO_SECRET_KEY, MAILGUN_API_KEY, MAILGUN_SENDER_DOMAIN, etc.
```

### 2. Start Docker services
```bash
docker compose up --build
```

### 3. Run migrations & create your Master Admin account
```bash
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
# Follow prompts — this account becomes the Master Admin
```

### 4. Open the app
- App: http://localhost:8000
- Django admin: http://localhost:8000/django-admin/
- Master Admin panel: http://localhost:8000/admin/

---

## Project Structure

```
giftregistry/          Django project (settings, urls, celery)
apps/
  accounts/            Custom user model, auth, registration, preferences
  families/            Family, FamilyMembership, invitations, themes
  wishlist/            WishlistItem, purchases, soft-remove, visibility
  access/              WishlistAccessRequest (request/approve/deny flow)
  notifications/       Celery tasks, email templates, ActivityLog, Master Admin
templates/
  base.html            Themed base layout
  emails/              All transactional email templates
```

## Key Design Decisions

- **No public registration** — users must be invited by a Family Admin
- **One wishlist per user** — items have per-family visibility checkboxes
- **Purchased items hidden from owner** — `PurchasedItem` excluded from owner's own queries
- **Declined access = permanent** — only Master Admin can reset via `/admin/reset-access/<id>/`
- **50 item limit** per wishlist (`WISHLIST_ITEM_LIMIT` in settings)
- **Roles are per-family** — a user can be Admin in one family, Member in another

## Settings

| Setting | Default | Description |
|---|---|---|
| `WISHLIST_ITEM_LIMIT` | 50 | Max items per user wishlist |
| `INVITATION_EXPIRY_DAYS` | 7 | Days before invite link expires |
| `SITE_URL` | http://localhost:8000 | Used in email links |
| `MASTER_ADMIN_EMAIL` | — | Your email (for reference) |
| `USE_S3` | False | Set True to use Cloudflare R2 or AWS S3 |

## Switching to Production

1. Set `DJANGO_SETTINGS_MODULE=giftregistry.settings.prod`
2. Set `USE_S3=True` and fill in storage credentials
3. Set `MAILGUN_API_KEY` and `MAILGUN_SENDER_DOMAIN`
4. Run `python manage.py collectstatic`

## Themes

Family Admins pick a theme from 8 options: Holiday 🎄, Birthday 🎂, Celebration 🎉, Ocean 🌊, Blush 🌸, Midnight 🌙, Royal 💜, Forest 🌿.
Themes apply CSS variable overrides in `base.html` — add new themes by extending `[data-theme]` rules in the style block.
