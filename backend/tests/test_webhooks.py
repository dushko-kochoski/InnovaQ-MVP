"""Webhook trigger endpoint tests using a mock workflow in the test DB."""

from backend.models.user import User
from backend.models.workflow import Workflow

MOCK_STEPS = [
    {"step": 1, "type": "trigger", "action_type": "webhook_receive"},
    {"step": 2, "type": "condition", "field": "amount", "operator": "gt", "value": 500},
    {"step": 3, "type": "action", "action_type": "email", "meta": {"template": "invoice_reminder"}},
]


def _make_workflow(db_session, status: str = "active") -> Workflow:
    user = User(email=f"owner-{status}@example.com", hashed_password="x")
    db_session.add(user)
    db_session.flush()
    workflow = Workflow(
        user_id=user.user_id,
        name="Mock invoice reminder",
        niche="accounting",
        status=status,
        steps=MOCK_STEPS,
    )
    db_session.add(workflow)
    db_session.commit()
    return workflow


async def test_webhook_accepts_for_active_workflow(client, db_session):
    workflow = _make_workflow(db_session, status="active")
    async with client:
        response = await client.post(
            f"/v1/triggers/webhook/{workflow.route_key}", json={"amount": 900}
        )
    assert response.status_code == 202
    assert response.json() == {"status": "accepted"}


async def test_webhook_404_for_unknown_route_key(client):
    async with client:
        response = await client.post(
            "/v1/triggers/webhook/no-such-key", json={"amount": 900}
        )
    assert response.status_code == 404


async def test_webhook_404_for_paused_workflow(client, db_session):
    workflow = _make_workflow(db_session, status="paused")
    async with client:
        response = await client.post(
            f"/v1/triggers/webhook/{workflow.route_key}", json={"amount": 900}
        )
    assert response.status_code == 404


async def test_webhook_accepts_non_dict_and_empty_bodies(client, db_session):
    workflow = _make_workflow(db_session, status="active")
    async with client:
        as_list = await client.post(
            f"/v1/triggers/webhook/{workflow.route_key}", json=[1, 2, 3]
        )
        no_body = await client.post(f"/v1/triggers/webhook/{workflow.route_key}")
    assert as_list.status_code == 202
    assert no_body.status_code == 202


async def test_webhook_records_execution(client, db_session):
    from backend.models.execution import WorkflowExecution

    workflow = _make_workflow(db_session, status="active")
    async with client:
        response = await client.post(
            f"/v1/triggers/webhook/{workflow.route_key}", json={"amount": 900}
        )
    assert response.status_code == 202
    executions = db_session.query(WorkflowExecution).all()
    assert len(executions) == 1
    assert executions[0].workflow_id == workflow.workflow_id
    assert executions[0].status == "success"
    assert executions[0].results[-1]["type"] == "action"


async def test_recent_triggers_requires_auth(client):
    async with client:
        response = await client.get("/v1/triggers/recent")
    assert response.status_code == 401


async def test_recent_triggers_returns_user_runs(client, db_session):
    workflow = _make_workflow(db_session, status="active")
    async with client:
        register = await client.post(
            "/auth/register",
            json={"email": "viewer@example.com", "password": "password123"},
        )
        assert register.status_code == 201
        login = await client.post(
            "/auth/login",
            json={"email": "viewer@example.com", "password": "password123"},
        )
        assert login.status_code == 200

        # Fire someone else's workflow — must not appear for this user
        await client.post(
            f"/v1/triggers/webhook/{workflow.route_key}", json={"amount": 900}
        )
        empty = await client.get("/v1/triggers/recent")
        assert empty.status_code == 200
        assert empty.json() == []

        # Create and fire this user's own workflow
        created = await client.post(
            "/v1/workflows",
            json={
                "name": "Mine",
                "niche": "trade",
                "status": "active",
                "steps": MOCK_STEPS,
            },
        )
        assert created.status_code == 201
        await client.post(
            f"/v1/triggers/webhook/{created.json()['route_key']}",
            json={"amount": 900},
        )
        mine = await client.get("/v1/triggers/recent")
    runs = mine.json()
    assert len(runs) == 1
    assert runs[0]["workflow_name"] == "Mine"
    assert runs[0]["status"] == "success"


async def test_webhook_runs_steps_in_background(client, db_session, monkeypatch):
    """The engine must be invoked with the workflow's steps and the request payload."""
    import backend.api.routes.webhooks as webhooks_module

    calls: list[tuple[list, dict]] = []

    def fake_execute(raw_steps, payload):
        calls.append((raw_steps, payload))
        return []

    monkeypatch.setattr(webhooks_module, "execute_workflow", fake_execute)
    workflow = _make_workflow(db_session, status="active")
    async with client:
        response = await client.post(
            f"/v1/triggers/webhook/{workflow.route_key}", json={"amount": 750}
        )
    assert response.status_code == 202
    # httpx ASGITransport runs BackgroundTasks before the client exits
    assert calls == [(MOCK_STEPS, {"amount": 750})]
