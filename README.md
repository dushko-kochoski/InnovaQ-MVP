# InnovaQ

B2B workflow automation SaaS for North Macedonia SMEs. One engine, five niche
template libraries: Accounting, Wholesale trade, Real estate, Logistics,
Healthcare.

- Backend: Python 3.11+ / FastAPI / Pydantic v2 / SQLAlchemy 2.x / SQLite (dev)
- Frontend: plain HTML + Tailwind CDN (no build step)
- Architecture decisions: see [DECISIONS.md](DECISIONS.md)

## Setup

```powershell
# from the project root (C:\innovaq), in PowerShell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

> **Important (Windows):** always install with `python -m pip`, not bare `pip`.
> On machines with several Python installations, `pip` and `python` can belong
> to *different* interpreters, so `pip install` puts packages where `python`
> never sees them — the classic `ModuleNotFoundError: No module named 'sqlalchemy'`.
> If activation is blocked by execution policy, run:
> `Set-ExecutionPolicy -Scope Process RemoteSigned` and try again.

## .env template

Create `.env` in the project root (or copy `.env.example`):

```env
DATABASE_URL=sqlite:///./innovaq.db
SECRET_KEY=generate-a-long-random-string
FRONTEND_URL=http://localhost:3000
DEBUG=true
```

## Run

Run from the **project root** (`C:\innovaq`), with the venv activated:

```powershell
.venv\Scripts\Activate.ps1
python -m uvicorn backend.main:app --reload --port 8000
```

`python -m uvicorn` guarantees the server runs in the same environment the
packages were installed into. (Without activating, the equivalent is
`.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --port 8000`.)
The `backend.main:app` import path requires the working directory to be the
project root — don't run it from inside `backend\`.

On startup the app creates all tables and seeds the 15 workflow templates
(idempotent). Interactive API docs: http://127.0.0.1:8000/docs

### Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: No module named 'sqlalchemy'` (or fastapi, jose…) | uvicorn/python is running outside the venv, or packages were installed with a `pip` belonging to a different Python | Activate the venv and reinstall with `python -m pip install -r requirements.txt`; start with `python -m uvicorn …` |
| `Could not import module "backend.main"` | uvicorn started from the wrong directory | `cd C:\innovaq` first, then run the command above |
| `running scripts is disabled on this system` on activation | PowerShell execution policy | `Set-ExecutionPolicy -Scope Process RemoteSigned`, then activate again |

## App dashboard (frontend)

The authenticated UI lives in `frontend/app/` (dashboard, workflows,
template library). Serve the frontend and API on the **same hostname** so the
httpOnly auth cookie flows (`127.0.0.1` for both — see DECISIONS.md D14):

```powershell
# terminal 1 — API
python -m uvicorn backend.main:app --reload --port 8000

# terminal 2 — frontend, served from the frontend\ directory
cd frontend
python -m http.server 3000 --bind 127.0.0.1
```

Then register and log in through the UI at
http://127.0.0.1:3000/auth/register.html — login sets the auth cookie and
drops you on http://127.0.0.1:3000/app/dashboard.html. Unauthenticated
visitors to app pages are redirected to the homepage.

## Tests

```powershell
python -m pytest -q
```

## Deploy

### Backend → Railway

The repo root has a `Procfile` and `railway.json` ready for Railway's
Nixpacks builder.

1. Push the project to GitHub, then in [Railway](https://railway.app):
   **New Project → Deploy from GitHub repo**.
2. Add a PostgreSQL database: **New → Database → PostgreSQL**.
3. In the backend service → **Variables**, set:
   - `DATABASE_URL` = `${{Postgres.DATABASE_URL}}` (reference to the DB —
     `postgres://` URLs are normalized to `postgresql://` automatically)
   - `SECRET_KEY` = output of `python -c "import secrets; print(secrets.token_urlsafe(48))"`
   - `FRONTEND_URL` = your frontend's origin (e.g. `https://innovaq.netlify.app`)
   - `DEBUG` = `false`
4. Deploy. Railway injects `$PORT`; the health check hits `/health`.
   Tables are created and the 15 templates seeded automatically on first boot.
5. Note your service URL (e.g. `https://innovaq-api.up.railway.app`) — the
   frontend needs it next.

Alternatively, with the [Railway CLI](https://docs.railway.app/guides/cli):
`railway login`, `railway init`, `railway up` from `C:\innovaq`.

### Frontend → Netlify

The frontend is plain static files — no build step.

1. Edit `frontend/config.js` and set `PRODUCTION_API` to your Railway URL.
2. Go to [Netlify Drop](https://app.netlify.com/drop) and drag the
   `frontend` folder onto the page. Done.
3. Copy the site URL Netlify assigns and set it as `FRONTEND_URL` on the
   Railway backend service (step 3 above) so CORS and cookies line up.

`config.js` auto-detects the environment: pages served from
`localhost`/`127.0.0.1` use the local API, anything else uses
`PRODUCTION_API`. In production the auth cookie is issued with
`SameSite=None; Secure` because frontend and API live on different domains
(see DECISIONS.md D16).

## Try it with curl

**1. Register, then log in (login sets the JWT httpOnly cookie):**

```bash
curl -X POST http://127.0.0.1:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@firma.mk","password":"password123","company_name":"Demo DOO"}'

curl -c cookies.txt -X POST http://127.0.0.1:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@firma.mk","password":"password123"}'
```

**2. Create an active workflow (note the `route_key` in the response):**

```bash
curl -b cookies.txt -X POST http://127.0.0.1:8000/v1/workflows \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Low stock alert",
    "niche": "trade",
    "status": "active",
    "steps": [
      {"step": 1, "type": "trigger", "action_type": "webhook_receive"},
      {"step": 2, "type": "condition", "field": "stock_level", "operator": "lt", "value": 10},
      {"step": 3, "type": "action", "action_type": "email", "meta": {"template": "low_stock"}}
    ]
  }'
```

**3. Fire the webhook trigger (replace `ROUTE_KEY`; runs steps in the background):**

```bash
curl -X POST http://127.0.0.1:8000/v1/triggers/webhook/ROUTE_KEY \
  -H "Content-Type: application/json" \
  -d '{"stock_level": 3}'
# -> {"status":"accepted"}  (engine result appears in the server log)
```

Bonus — browse the seeded templates (public, optional niche filter):

```bash
curl "http://127.0.0.1:8000/v1/templates?niche=healthcare"
```

## API surface

| Method | Path | Auth | Purpose |
|---|---|---|---|
| POST | `/auth/register` | — | Create account |
| POST | `/auth/login` | — | Sets JWT httpOnly cookie |
| POST | `/auth/logout` | — | Clears cookie |
| GET | `/v1/workflows` | cookie | List my workflows |
| POST | `/v1/workflows` | cookie | Create workflow |
| GET | `/v1/workflows/{id}` | cookie | Get one |
| PUT | `/v1/workflows/{id}` | cookie | Partial update |
| DELETE | `/v1/workflows/{id}` | cookie | Delete |
| GET | `/v1/templates?niche=` | — | Browse template library |
| POST | `/v1/triggers/webhook/{route_key}` | route key | Fire a workflow |
| GET | `/health` | — | Liveness check |
