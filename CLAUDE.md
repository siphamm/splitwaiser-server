# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build & Development

Uses **uv** for dependency management and virtual environment.

```bash
make install    # uv sync — install dependencies
make dev        # Start FastAPI dev server with hot reload (port 8000)
make run        # Start production server (port 8000)
make lint       # Ruff linter
make format     # Ruff formatter
make test       # Run pytest
```

Requires a `.env` file (copy from `.env.example`):
```
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/yoyo
CORS_ORIGINS=http://localhost:5173
```

For local dev with SQLite (no Postgres needed): just omit `DATABASE_URL` and it defaults to `sqlite:///./splitwaiser.db`.

## Architecture

**Stack:** Python 3.12+ · FastAPI · SQLAlchemy ORM · PostgreSQL (SQLite for dev) · uv

### Project Structure
```
app/
├── main.py          # FastAPI app, CORS, routes
├── database.py      # Engine, session, Base
├── models.py        # SQLAlchemy ORM models (Trip, Member, Expense, ExpenseMember, Settlement, User, ExchangeRate)
├── schemas.py       # Pydantic request/response schemas
├── serializers.py   # Model → JSON dict converters (integer IDs → string, snake_case → camelCase)
├── deps.py          # Shared dependencies (get_trip_by_token, verify_creator, get_or_create_user)
├── middleware.py     # CTK cookie middleware — assigns tracking cookie, resolves User
├── exchange.py      # Exchange rate fetching from frankfurter.dev
├── ratelimit.py     # Rate limiting config
└── routes/
    ├── trips.py       # Trip CRUD + rotate-token
    ├── members.py     # Member CRUD (creator-only) + claim endpoint
    ├── expenses.py    # Expense CRUD
    ├── settlements.py # Settlement CRUD
    ├── exchange.py    # Exchange rate endpoint
    └── users.py       # GET /me, GET /me/trips
```

### Auth Model (Server-Derived Identity)
- **No accounts.** `access_token` in URL grants read + write access to a trip.
- **CTK cookie** — automatically assigned by `CTKMiddleware`. Maps to a `User` row via `user_id`.
- **Creator verification** — `verify_creator()` in `deps.py` checks if the request's CTK user matches the trip's `creator_member_id` via `user_id`. No more `X-Creator-Token` header.
- **Identity** — `serialize_trip()` accepts a `user_id` param, scans members to find a match, returns `your_member_id` and `is_creator` in the response.
- **Claim endpoint** — `POST /trips/{access_token}/claim/{member_id}` links a member to the CTK user. Clears any previous claim in the same trip (one user = one member per trip). Uses `get_or_create_user` so first-time visitors can claim.

### Data Model
- All primary keys are **auto-incrementing integers**. Serializers convert them to strings for the JSON API.
- Trip `access_token` is a UUID (`secrets.token_urlsafe`) — not enumerable.
- All amounts stored as integers in smallest currency unit (cents for USD/HKD, yen for JPY).
- `expense_members` junction table stores both involved members and split values.
- `settled_by_id` on Member for settlement grouping.
- Supported currencies: USD, HKD, JPY.
- Routes receive string IDs from the frontend; use `int()` for Python set-membership checks and DB assignments.

### Serialization
`serializers.py` converts SQLAlchemy models to dicts matching the frontend TypeScript types. All integer IDs are wrapped in `str()`. Field names are camelCase (`paidBy`, `splitMethod`, `involvedMembers`, etc.).

### API Endpoints
All under `/api`. Trip access via `access_token` path param. Creator-only endpoints verified via CTK user matching creator member.

```
POST   /api/trips                                → Create trip
GET    /api/trips/{access_token}                  → Full trip data (includes your_member_id, is_creator)
PATCH  /api/trips/{access_token}                  → Update name/settlement currency [CREATOR]
DELETE /api/trips/{access_token}                  → Delete [CREATOR]
POST   /api/trips/{access_token}/rotate-token     → Rotate link [CREATOR]
POST   /api/trips/{access_token}/members          → Add member [CREATOR]
PATCH  /api/trips/{access_token}/members/{id}     → Update member [CREATOR]
DELETE /api/trips/{access_token}/members/{id}     → Remove member [CREATOR]
POST   /api/trips/{access_token}/claim/{id}       → Claim member identity
POST   /api/trips/{access_token}/expenses         → Add expense
PUT    /api/trips/{access_token}/expenses/{id}    → Update expense
DELETE /api/trips/{access_token}/expenses/{id}    → Delete expense
POST   /api/trips/{access_token}/settlements      → Add settlement
DELETE /api/trips/{access_token}/settlements/{id} → Delete settlement
GET    /api/trips/{access_token}/exchange-rates    → Get exchange rates
GET    /api/me                                    → Current user info
GET    /api/me/trips                              → User's trips
```
