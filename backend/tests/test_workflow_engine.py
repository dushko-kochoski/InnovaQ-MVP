"""Direct unit tests for the workflow engine's step execution logic."""

import pytest

from backend.core.workflow_engine import (
    evaluate_condition,
    execute_action,
    execute_workflow,
)
from backend.core.workflow_parser import WorkflowParseError, parse_steps
from backend.schemas.workflow import WorkflowStep


def _condition(field="amount", operator="gt", value=500) -> WorkflowStep:
    return WorkflowStep(step=2, type="condition", field=field, operator=operator, value=value)


class TestConditionEvaluation:
    def test_gt_true(self):
        assert evaluate_condition(_condition(), {"amount": 900}) is True

    def test_gt_false(self):
        assert evaluate_condition(_condition(), {"amount": 100}) is False

    def test_missing_field_is_false(self):
        assert evaluate_condition(_condition(), {"other": 1}) is False

    def test_type_mismatch_is_false_not_error(self):
        assert evaluate_condition(_condition(), {"amount": "not-a-number"}) is False

    @pytest.mark.parametrize(
        "operator,actual,expected,result",
        [
            ("eq", "delivered", "delivered", True),
            ("ne", 5, 0, True),
            ("gte", 30, 30, True),
            ("lt", 5, 10, True),
            ("lte", 24, 24, True),
            ("contains", "hello world", "world", True),
            ("contains", "hello", "xyz", False),
        ],
    )
    def test_all_operators(self, operator, actual, expected, result):
        cond = _condition(field="f", operator=operator, value=expected)
        assert evaluate_condition(cond, {"f": actual}) is result


class TestActionExecution:
    def test_email_stub_succeeds(self):
        step = WorkflowStep(step=3, type="action", action_type="email", meta={"template": "t"})
        assert execute_action(step, {"a": 1})["ok"] is True

    def test_viber_stub_succeeds(self):
        step = WorkflowStep(step=3, type="action", action_type="viber", meta={})
        assert execute_action(step, {})["ok"] is True

    def test_http_request_without_url_fails(self):
        step = WorkflowStep(step=3, type="action", action_type="http_request", meta={})
        result = execute_action(step, {})
        assert result["ok"] is False
        assert "url" in result["detail"]

    def test_http_request_calls_endpoint(self, monkeypatch):
        import backend.core.workflow_engine as engine

        captured = {}

        class FakeResponse:
            is_success = True
            status_code = 200

        def fake_request(method, url, json, timeout):
            captured.update(method=method, url=url, json=json)
            return FakeResponse()

        monkeypatch.setattr(engine.httpx, "request", fake_request)
        step = WorkflowStep(
            step=3,
            type="action",
            action_type="http_request",
            meta={"url": "https://example.com/hook", "method": "post"},
        )
        result = execute_action(step, {"x": 1})
        assert result == {"ok": True, "status_code": 200}
        assert captured == {
            "method": "POST",
            "url": "https://example.com/hook",
            "json": {"x": 1},
        }


class TestWorkflowExecution:
    STEPS = [
        {"step": 1, "type": "trigger", "action_type": "webhook_receive"},
        {"step": 2, "type": "condition", "field": "amount", "operator": "gt", "value": 500},
        {"step": 3, "type": "action", "action_type": "email", "meta": {"template": "t"}},
    ]

    def test_full_run_when_condition_passes(self):
        results = execute_workflow(self.STEPS, {"amount": 900})
        assert [r["type"] for r in results] == ["trigger", "condition", "action"]
        assert results[1]["result"] is True
        assert results[2]["result"]["ok"] is True

    def test_stops_at_false_condition(self):
        results = execute_workflow(self.STEPS, {"amount": 100})
        assert [r["type"] for r in results] == ["trigger", "condition"]
        assert results[1]["result"] is False

    def test_steps_execute_in_step_number_order(self):
        shuffled = [self.STEPS[2], self.STEPS[0], self.STEPS[1]]
        results = execute_workflow(shuffled, {"amount": 900})
        assert [r["step"] for r in results] == [1, 2, 3]


class TestParser:
    def test_rejects_empty_steps(self):
        with pytest.raises(WorkflowParseError):
            parse_steps([])

    def test_rejects_workflow_not_starting_with_trigger(self):
        with pytest.raises(WorkflowParseError):
            parse_steps([{"step": 1, "type": "action", "action_type": "email"}])

    def test_rejects_duplicate_step_numbers(self):
        with pytest.raises(WorkflowParseError):
            parse_steps(
                [
                    {"step": 1, "type": "trigger", "action_type": "webhook_receive"},
                    {"step": 1, "type": "action", "action_type": "email"},
                ]
            )

    def test_rejects_invalid_operator(self):
        with pytest.raises(WorkflowParseError):
            parse_steps(
                [
                    {"step": 1, "type": "trigger", "action_type": "webhook_receive"},
                    {"step": 2, "type": "condition", "field": "x", "operator": "??", "value": 1},
                ]
            )

    def test_parses_valid_steps(self):
        steps = parse_steps(TestWorkflowExecution.STEPS)
        assert len(steps) == 3
        assert all(isinstance(s, WorkflowStep) for s in steps)
