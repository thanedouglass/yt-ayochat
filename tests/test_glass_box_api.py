"""Unit and Integration Tests for the Glass Box Telemetry & Study Server."""

from __future__ import annotations

import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from src.server import app


@pytest.fixture
def client() -> TestClient:
    """FastAPI TestClient fixture."""
    return TestClient(app)


def test_glass_box_health_endpoint(client: TestClient):
    """Verify /api/health returns healthy status and system metadata."""
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert "version" in data


def test_panel_1_governance_ledger_endpoint(client: TestClient):
    """Verify /api/ledger/council returns regional open-source model registries and debate logs."""
    res = client.get("/api/ledger/council")
    assert res.status_code == 200
    data = res.json()
    assert "council_registries" in data
    assert "es" in data["council_registries"]
    assert "ar" in data["council_registries"]
    assert "pt" in data["council_registries"]
    assert len(data["sample_debates"]) > 0


def test_panel_2_triad_metrics_matrix_endpoint(client: TestClient):
    """Verify /api/metrics/triad returns mathematical formulations and evaluation report."""
    res = client.get("/api/metrics/triad")
    assert res.status_code == 200
    data = res.json()
    assert "math_spec" in data
    assert "context_relevance" in data["math_spec"]
    assert "faithfulness" in data["math_spec"]
    assert "answer_relevance" in data["math_spec"]
    assert "evaluation_report" in data


def test_panel_3_model_armor_interventions_endpoint(client: TestClient):
    """Verify /api/governance/armor returns active rules and SDP/Model Armor intervention logs."""
    res = client.get("/api/governance/armor")
    assert res.status_code == 200
    data = res.json()
    assert "active_rules" in data
    assert "intervention_log" in data
    assert len(data["intervention_log"]) >= 5

    # Verify PII email redaction test was logged
    email_test = next((i for i in data["intervention_log"] if i["test_name"] == "PII Email Redaction"), None)
    assert email_test is not None
    assert "[REDACTED_EMAIL]" in email_test["processed_text"]

    # Verify Prompt Injection test was blocked
    injection_test = next((i for i in data["intervention_log"] if i["test_name"] == "Prompt Injection / Jailbreak"), None)
    assert injection_test is not None
    assert injection_test["is_blocked"] is True


def test_panel_4_synthetic_memory_inspector_endpoint(client: TestClient):
    """Verify /api/memory/synthetic returns historical and calibrated records."""
    res = client.get("/api/memory/synthetic")
    assert res.status_code == 200
    data = res.json()
    assert "synthetic_memory_records" in data
    assert "hitl_alignment_records" in data
    assert isinstance(data["total_synthetic_logged"], int)
    assert isinstance(data["total_hitl_calibrated"], int)


def test_live_swarm_simulation_endpoint(client: TestClient):
    """Verify POST /api/simulate/swarm runs full multi-agent trace with node telemetry."""
    payload = {
        "comment": "that footwork transition at 0:15 was literally impossible how did you hit that?!",
        "author_id": "test_user_dance",
        "video_id": "M1G92FWmdJw",
        "video_title": "KATSEYE Dance Cover",
    }
    res = client.post("/api/simulate/swarm", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "trace_id" in data
    assert "room_temperature" in data
    assert "perception" in data
    assert "hive_response" in data
    assert "governance" in data
    assert len(data["final_dispatched_reply"]) > 0


def test_glass_box_dashboard_html_routes(client: TestClient):
    """Verify root / and /glassbox serve valid HTML dashboard."""
    res = client.get("/")
    assert res.status_code == 200
    assert "<!DOCTYPE html>" in res.text
    assert "Glass Box" in res.text

    res_gb = client.get("/glassbox")
    assert res_gb.status_code == 200
    assert "Governance Ledger" in res_gb.text
