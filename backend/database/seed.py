"""Seeds the 15 workflow templates (3 per niche). Idempotent — upserts by slug."""

from sqlalchemy import select

from backend.database.session import SessionLocal, create_all
from backend.models.template import WorkflowTemplate


def _t(slug: str, name: str, niche: str, description: str, steps: list) -> dict:
    return {
        "slug": slug,
        "name": name,
        "niche": niche,
        "description": description,
        "steps": steps,
    }


TEMPLATES: list[dict] = [
    # ── Accounting ──────────────────────────────────────────────────────
    _t(
        "invoice_reminder",
        "Invoice payment reminder",
        "accounting",
        "When an invoice is overdue, email the client a payment reminder.",
        [
            {"step": 1, "type": "trigger", "action_type": "schedule", "meta": {"cron": "0 9 * * *"}},
            {"step": 2, "type": "condition", "field": "days_overdue", "operator": "gt", "value": 0},
            {"step": 3, "type": "action", "action_type": "email", "meta": {"template": "invoice_reminder"}},
        ],
    ),
    _t(
        "document_intake",
        "Client document intake",
        "accounting",
        "Receive uploaded documents via webhook and forward them to the accountant's system.",
        [
            {"step": 1, "type": "trigger", "action_type": "webhook_receive"},
            {"step": 2, "type": "action", "action_type": "http_request", "meta": {"method": "POST"}},
        ],
    ),
    _t(
        "tax_deadline_alert",
        "Tax deadline alert",
        "accounting",
        "Alert clients via Viber before VAT and profit-tax deadlines.",
        [
            {"step": 1, "type": "trigger", "action_type": "schedule", "meta": {"cron": "0 8 * * *"}},
            {"step": 2, "type": "condition", "field": "days_to_deadline", "operator": "lte", "value": 5},
            {"step": 3, "type": "action", "action_type": "viber", "meta": {"template": "tax_deadline"}},
        ],
    ),
    # ── Trade ───────────────────────────────────────────────────────────
    _t(
        "low_stock_alert",
        "Low stock alert",
        "trade",
        "When stock for an item drops below the threshold, notify purchasing via email.",
        [
            {"step": 1, "type": "trigger", "action_type": "webhook_receive"},
            {"step": 2, "type": "condition", "field": "stock_level", "operator": "lt", "value": 10},
            {"step": 3, "type": "action", "action_type": "email", "meta": {"template": "low_stock"}},
        ],
    ),
    _t(
        "supplier_order_auto",
        "Automatic supplier order",
        "trade",
        "When stock hits the reorder point, send a purchase order to the supplier's API.",
        [
            {"step": 1, "type": "trigger", "action_type": "webhook_receive"},
            {"step": 2, "type": "condition", "field": "stock_level", "operator": "lte", "value": 5},
            {"step": 3, "type": "action", "action_type": "http_request", "meta": {"method": "POST"}},
        ],
    ),
    _t(
        "b2b_followup",
        "B2B customer follow-up",
        "trade",
        "Follow up by email with B2B customers who have not ordered in 30 days.",
        [
            {"step": 1, "type": "trigger", "action_type": "schedule", "meta": {"cron": "0 10 * * 1"}},
            {"step": 2, "type": "condition", "field": "days_since_order", "operator": "gte", "value": 30},
            {"step": 3, "type": "action", "action_type": "email", "meta": {"template": "b2b_followup"}},
        ],
    ),
    # ── Real estate ─────────────────────────────────────────────────────
    _t(
        "lead_to_crm",
        "Website lead to CRM",
        "real_estate",
        "Push new property inquiries from the website form into the agency CRM.",
        [
            {"step": 1, "type": "trigger", "action_type": "webhook_receive"},
            {"step": 2, "type": "action", "action_type": "http_request", "meta": {"method": "POST"}},
        ],
    ),
    _t(
        "permit_deadline_tracker",
        "Permit deadline tracker",
        "real_estate",
        "Track construction-permit expiry dates and alert the agent by email.",
        [
            {"step": 1, "type": "trigger", "action_type": "schedule", "meta": {"cron": "0 9 * * *"}},
            {"step": 2, "type": "condition", "field": "days_to_expiry", "operator": "lte", "value": 14},
            {"step": 3, "type": "action", "action_type": "email", "meta": {"template": "permit_deadline"}},
        ],
    ),
    _t(
        "contract_reminder",
        "Contract renewal reminder",
        "real_estate",
        "Remind landlords via Viber before rental contracts expire.",
        [
            {"step": 1, "type": "trigger", "action_type": "schedule", "meta": {"cron": "0 9 * * *"}},
            {"step": 2, "type": "condition", "field": "days_to_renewal", "operator": "lte", "value": 30},
            {"step": 3, "type": "action", "action_type": "viber", "meta": {"template": "contract_renewal"}},
        ],
    ),
    # ── Logistics ───────────────────────────────────────────────────────
    _t(
        "shipment_notify",
        "Shipment status notification",
        "logistics",
        "When a shipment status changes, notify the customer via Viber.",
        [
            {"step": 1, "type": "trigger", "action_type": "webhook_receive"},
            {"step": 2, "type": "action", "action_type": "viber", "meta": {"template": "shipment_status"}},
        ],
    ),
    _t(
        "delivery_confirmation",
        "Delivery confirmation",
        "logistics",
        "On delivery, email the customer a confirmation and proof-of-delivery link.",
        [
            {"step": 1, "type": "trigger", "action_type": "webhook_receive"},
            {"step": 2, "type": "condition", "field": "status", "operator": "eq", "value": "delivered"},
            {"step": 3, "type": "action", "action_type": "email", "meta": {"template": "delivery_confirmation"}},
        ],
    ),
    _t(
        "invoice_reconciliation",
        "Invoice reconciliation",
        "logistics",
        "Poll the carrier API daily and flag invoices that do not match shipment records.",
        [
            {"step": 1, "type": "trigger", "action_type": "http_poll", "meta": {"interval_minutes": 1440}},
            {"step": 2, "type": "condition", "field": "amount_diff", "operator": "ne", "value": 0},
            {"step": 3, "type": "action", "action_type": "email", "meta": {"template": "invoice_mismatch"}},
        ],
    ),
    # ── Healthcare ──────────────────────────────────────────────────────
    _t(
        "appointment_reminder_viber",
        "Appointment reminder via Viber",
        "healthcare",
        "Send patients a Viber reminder 24 hours before their appointment.",
        [
            {"step": 1, "type": "trigger", "action_type": "schedule", "meta": {"cron": "0 */1 * * *"}},
            {"step": 2, "type": "condition", "field": "hours_to_appointment", "operator": "lte", "value": 24},
            {"step": 3, "type": "action", "action_type": "viber", "meta": {"template": "appointment_reminder"}},
        ],
    ),
    _t(
        "no_show_followup",
        "No-show follow-up",
        "healthcare",
        "When a patient misses an appointment, send a rebooking message via Viber.",
        [
            {"step": 1, "type": "trigger", "action_type": "webhook_receive"},
            {"step": 2, "type": "condition", "field": "status", "operator": "eq", "value": "no_show"},
            {"step": 3, "type": "action", "action_type": "viber", "meta": {"template": "no_show_rebook"}},
        ],
    ),
    _t(
        "patient_intake",
        "New patient intake",
        "healthcare",
        "Receive new-patient form submissions and create the record in the clinic system.",
        [
            {"step": 1, "type": "trigger", "action_type": "webhook_receive"},
            {"step": 2, "type": "action", "action_type": "http_request", "meta": {"method": "POST"}},
        ],
    ),
]


def seed_templates() -> int:
    """Insert missing templates; update existing ones in place. Returns row count."""
    create_all()
    with SessionLocal() as db:
        for data in TEMPLATES:
            existing = db.execute(
                select(WorkflowTemplate).where(WorkflowTemplate.slug == data["slug"])
            ).scalar_one_or_none()
            if existing is None:
                db.add(WorkflowTemplate(**data))
            else:
                for key, value in data.items():
                    setattr(existing, key, value)
        db.commit()
        count = len(db.execute(select(WorkflowTemplate)).scalars().all())
    return count


if __name__ == "__main__":
    total = seed_templates()
    print(f"Seeded templates. Total in DB: {total}")
