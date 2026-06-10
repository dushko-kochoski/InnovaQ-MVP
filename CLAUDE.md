# InnovaQ — Project Constitution

## What this is
B2B automation SaaS for North Macedonia SMEs. One engine, five niche workflow
template libraries: Accounting, Wholesale trade, Real estate, Logistics, Healthcare.

## Stack
- Backend: Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy 2.x, SQLite (dev) → PostgreSQL (prod)
- Auth: JWT (python-jose), httpOnly cookies
- Background tasks: FastAPI BackgroundTasks → APScheduler for scheduled triggers
- Frontend: Plain HTML + TailwindCSS CDN (no build step, no Node.js)
- Tests: pytest + httpx AsyncClient
- Env: python-dotenv, all secrets in .env, never hardcoded

## Directory structure
innovaq/
├── backend/
│   ├── main.py                 # FastAPI app entry point
│   ├── config.py               # Settings via pydantic-settings
│   ├── core/
│   │   ├── workflow_engine.py  # Trigger → Condition → Action executor
│   │   └── workflow_parser.py  # Validates and parses workflow JSON
│   ├── api/
│   │   ├── routes/
│   │   │   ├── webhooks.py     # POST /v1/triggers/webhook/{route_key}
│   │   │   ├── workflows.py    # CRUD /v1/workflows
│   │   │   ├── templates.py    # GET /v1/templates?niche=accounting
│   │   │   └── auth.py         # /auth/register, /auth/login, /auth/logout
│   │   └── deps.py             # get_db, get_current_user dependencies
│   ├── models/                 # SQLAlchemy ORM models
│   ├── schemas/                # Pydantic v2 request/response schemas
│   ├── database/
│   │   ├── session.py
│   │   └── seed.py             # Seeds 15 templates (3 per niche)
│   └── tests/
│       ├── test_webhooks.py
│       └── test_workflow_engine.py
└── frontend/
    ├── index.html
    ├── pricing.html
    ├── about.html
    ├── contact.html
    ├── solutions/
    │   ├── accounting.html
    │   ├── trade.html
    │   ├── real-estate.html
    │   ├── logistics.html
    │   └── healthcare.html
    └── app/
        ├── dashboard.html
        ├── workflows.html
        └── templates.html

## Core workflow JSON model
Every workflow stored as JSON in the DB:
{
  "workflow_id": "uuid",
  "user_id": "uuid",
  "name": "string",
  "niche": "accounting|trade|real_estate|logistics|healthcare",
  "status": "active|paused|draft",
  "steps": [
    {"step": 1, "type": "trigger",   "action_type": "webhook_receive|schedule|http_poll"},
    {"step": 2, "type": "condition", "field": "amount", "operator": "gt", "value": 500},
    {"step": 3, "type": "action",    "action_type": "http_request|viber|email", "meta": {}}
  ]
}

## Template seed data (15 total)
Accounting:   invoice_reminder, document_intake, tax_deadline_alert
Trade:        low_stock_alert, supplier_order_auto, b2b_followup
Real estate:  lead_to_crm, permit_deadline_tracker, contract_reminder
Logistics:    shipment_notify, delivery_confirmation, invoice_reconciliation
Healthcare:   appointment_reminder_viber, no_show_followup, patient_intake

## Coding standards
- Pydantic v2 strict validation on all schemas — no dict passing between layers
- All route handlers: try/except → HTTPException with proper status codes
- Background tasks for all outbound actions (never block the response)
- CORS: allow localhost:3000 and FRONTEND_URL env var
- No hardcoded strings — use config.py for all constants
- Write tests for: webhook endpoint, workflow engine step execution
- Document non-obvious decisions in DECISIONS.md, not in code comments

## Windows environment
- Always write files with UTF-8 encoding
- Use os.path.join or pathlib.Path — never hardcode forward slashes
- .env file in project root

## What NOT to do
- Do not use Flask or Django
- Do not use Node.js or npm for the backend
- Do not create a React app — plain HTML/Tailwind only for frontend
- Do not ask clarifying questions — log decisions to DECISIONS.md and continue