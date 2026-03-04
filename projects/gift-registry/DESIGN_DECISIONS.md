# Gift Registry — Design Decisions

_Locked in: 2026-03-02. These are confirmed decisions, not suggestions._

---

## Roles

| Role | Capabilities |
|---|---|
| **Master Admin** (Tom) | Full system access: raw data, manual pw reset, delete accounts, change emails, undo declined access |
| **Family Admin** | Invite/remove members, pick family theme, manage family roster + full Member capabilities (wishlist, access requests, etc.) |
| **Family Member** | Manage own wishlist, request/grant/deny access to others' wishlists, mark items purchased |

---

## Access Control (Wishlist Viewing)

- Access is **opt-in and explicit** — you must request access; it's not automatic for family members
- Access states: `none → pending → approved` or `none → pending → denied`
- **Declined access is permanent** — the requesting member cannot re-request
  - This prevents notification spam
  - Only the **Master Admin** can reset a denied access request, and only at the Family Admin's request
- Accept/Decline available via: (a) email one-click link, (b) app Family page
- Accepting or declining sends an email notification to the requester

---

## Purchase Tracking

- Any family member with approved access can mark a wishlist item as **Purchased**
- The **wishlist owner does NOT see** which items are marked purchased on their own list
  - They see their full list with no purchase status at all
- Other family members **see that an item was purchased** but **NOT who purchased it**
  - Avoids awkwardness, keeps gifting a surprise
- Purchase can be undone (in case of mis-click) — only by the person who marked it

---

## Themes (Fixed Set)

Themes are selected by the Family Admin and apply to the family's registry view for all members.

| Theme | Emoji | Palette |
|---|---|---|
| Holiday | 🎄 | Deep green + crimson red |
| Birthday | 🎂 | Purple + hot pink |
| Celebration | 🎉 | Amber/gold + warm brown |
| Ocean | 🌊 | Navy + teal |
| Blush | 🌸 | Rose + soft pink |
| Midnight | 🌙 | Dark slate + cool gray |
| Royal | 💜 | Indigo + violet |
| Forest | 🌿 | Emerald green |

---

## Registration Flow

1. Family Admin sends invite → system emails unique tokenized link (expires 7 days)
2. New user clicks link → registration form (name, email, password)
3. On submit → account created (inactive) → verification email sent
4. User clicks verification link → account activated → redirected to login
5. Family Admin + Master Admin receive notification email when member completes registration

### Password Rules
- Minimum 8 characters
- Must contain at least one letter AND at least one number
- No other complexity requirements (keep it simple)

### Email
- Must be unique across the entire system
- Uniqueness checked on submit (with real-time validation optional)
- Email not confirmed as existing on forgot-password page (security best practice)

---

## Notifications (Email)

| Event | Who gets notified |
|---|---|
| Access request sent | Wishlist owner |
| Access request accepted | Requester |
| Access request declined | Requester |
| Registration completed | Family Admin + Master Admin |
| New wishlist item added | Opted-in family members (per-member opt-in setting) |
| Password reset requested | Requesting user |

Notification opt-in for new wishlist items is **per-member** — you choose which family members trigger notifications for you.

---

## Tech Stack

| Layer | Choice | Reason |
|---|---|---|
| Framework | Django | Built-in auth, admin panel, ORM, mature ecosystem |
| Database | PostgreSQL | Relational, scales to SaaS, excellent Django support |
| Image storage | Cloudflare R2 or AWS S3 | django-storages plug-in |
| Email | SendGrid or AWS SES | SES cheapest at scale |
| Async tasks | Celery + Redis | Non-blocking email delivery |
| CSS | Tailwind CSS | Theme system via CSS variables |
| Frontend interactivity | HTMX | Server-side Python, no React overhead |
| Dev database | SQLite → PostgreSQL | Switch before any real testing |

---

## Purchased Items — Visibility

- **Show ALL items** regardless of purchased status
- Items marked purchased show a "Purchased" badge
- Rationale: a user may list similar items; a family member seeing one is purchased may reconsider buying a duplicate
- The badge does not reveal who purchased it

---

## Soft-Remove ("No Longer Wanted")

Wishlist owners can mark their own item as **"No longer wanted / Already have"** instead of deleting it.

- Use cases: they bought it themselves, received it outside the system, or changed their mind
- Item remains visible to family members with a muted "No longer needed" indicator
- Owner can undo the soft-remove at any time
- Item is NOT deleted — preserves purchase history/coordination
- Hard delete remains available as a separate action

---

## Multi-Family Membership

- **Users can belong to more than one family**
- If an existing user receives a family invite, the system recognizes them and **adds them to the new family** — no new account needed
- The invite link checks email: if account exists → auto-join flow; if new → registration flow
- A user's wishlist is **shared across all their families** (one wishlist, multiple audiences)
  - OR each family gets a separate wishlist — **TBD, decide before build**
- Dashboard shows a family switcher if the user belongs to multiple families

---

## Master Admin Activity Log

No email notifications for registrations — instead, the Master Admin panel has a **live activity log** showing:

| Event type | Example |
|---|---|
| Registration | "Sarah Johnson joined Smith Family" |
| Invitation sent | "Jane Smith invited lisa@example.com to Smith Family" |
| Password reset | "Password reset requested for mike@example.com" |
| Access granted/denied | "Tom Johnson granted access to Jane Smith's wishlist" |
| Account deleted | "Account deleted: old@example.com" |
| Email changed | "Email updated: old@example.com → new@example.com" |
| Soft-remove | "Sarah Johnson marked 'Sony Headphones' as no longer wanted" |

Log is paginated, filterable by event type and date range.

---

## Multi-Family Wishlist Visibility

- **One wishlist per user** — no separate lists per family
- Each wishlist item has a **per-item family visibility selector**
  - On Add/Edit Item: checkboxes for each family the user belongs to
  - Default: all families checked (visible to all)
  - A family member only sees items that include their family
- This allows natural control: "I want my coworkers (Family B) to see my tech wishlist but not my personal items"
- Data model: `WishlistItem` has a many-to-many with `Family` (visibility join table)

## Roles Are Per Family Membership

- A user's **role is tied to their membership in a specific family**, not their account globally
- Example: Sarah can be Family Admin of the Smith Family and a regular Member of the Johnson Family
- The `FamilyMembership` join table carries the role: `user | family | role (admin|member)`

## Wishlist Item Limit

- **50 items maximum** per user wishlist
- Show a count indicator (e.g. "32 / 50 items") on the wishlist page
- When limit is reached: "Add Item" button is disabled with a tooltip explaining the cap
- Soft-removed items still count toward the limit (they're not deleted)
