"""Smoke tests for Prometheus metrics exposition."""

from prometheus_client import CONTENT_TYPE_LATEST


async def test_metrics_endpoint_exposes_bigweld_metrics(client):
    response = await client.get("/metrics")

    assert response.status_code == 200
    assert response.headers["content-type"] == CONTENT_TYPE_LATEST
    body = response.text
    assert "bigweld_portal_turn_total" in body
    assert "bigweld_portal_turn_duration_seconds" in body
    assert "bigweld_portal_subprocess_startup_seconds" in body
    assert "bigweld_portal_resume_failure_total" in body
    assert "bigweld_portal_summarizer_total" in body
