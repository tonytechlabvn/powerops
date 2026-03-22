"""Integration tests for AI Studio API routes.

Tests all /api/ai/studio/* endpoints with mocked auth and Claude API.
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _mock_claude_response(text: str):
    """Create a mock Claude response."""
    mock_resp = MagicMock()
    mock_resp.content = [MagicMock(text=text)]
    mock_resp.usage = MagicMock(input_tokens=50, output_tokens=100)
    return mock_resp


SAMPLE_RESPONSE = (
    '<file name="main.tf.j2">resource "aws_instance" "web" { instance_type = "{{ instance_type }}" }</file>\n'
    '<file name="variables.json">{"variables": [{"name": "instance_type", "type": "string", "default": "t3.micro"}]}</file>\n'
    '<file name="metadata.json">{"name": "aws/test", "provider": "aws", "display_name": "Test"}</file>'
)


@pytest.fixture
def mock_auth():
    """Patch auth middleware to always set a valid user."""
    async def fake_dispatch(request, call_next):
        request.state.user = {"sub": "test-user", "email": "test@example.com"}
        return await call_next(request)

    return fake_dispatch


@pytest.fixture
async def client(mock_auth, tmp_path):
    """Create test client with mocked auth and Claude API."""
    with patch.dict("os.environ", {
        "TERRABOT_ANTHROPIC_API_KEY": "test-key",
        "TERRABOT_TEMPLATE_DIR": str(tmp_path / "templates"),
        "TERRABOT_DB_URL": "sqlite+aiosqlite:///",
    }):
        # Clear cached settings
        from backend.core.config import get_settings
        get_settings.cache_clear()

        from backend.api.main import create_app
        app = create_app()

        # Replace auth middleware with mock
        from starlette.middleware.base import BaseHTTPMiddleware
        app.middleware_stack = None  # Reset middleware
        app.add_middleware(BaseHTTPMiddleware, dispatch=mock_auth)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac

        get_settings.cache_clear()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestAIStudioRoutes:
    """Integration tests for /api/ai/studio endpoints."""

    @pytest.mark.asyncio
    async def test_generate_returns_200(self, client):
        with patch("anthropic.AsyncAnthropic") as MockClient:
            instance = MockClient.return_value
            instance.messages.create = AsyncMock(return_value=_mock_claude_response(SAMPLE_RESPONSE))

            resp = await client.post("/api/ai/studio/generate", json={
                "description": "Simple EC2 instance with nginx",
                "providers": ["aws"],
                "complexity": "simple",
            })
            assert resp.status_code == 200
            data = resp.json()
            assert "files" in data
            assert "name" in data

    @pytest.mark.asyncio
    async def test_generate_validates_request_body(self, client):
        resp = await client.post("/api/ai/studio/generate", json={
            "description": "short",  # Less than min_length=10
        })
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_extract_returns_200(self, client):
        with patch("anthropic.AsyncAnthropic") as MockClient:
            instance = MockClient.return_value
            instance.messages.create = AsyncMock(return_value=_mock_claude_response(SAMPLE_RESPONSE))

            resp = await client.post("/api/ai/studio/extract", json={
                "hcl_code": 'resource "aws_instance" "web" { instance_type = "t3.micro" }',
            })
            assert resp.status_code == 200
            data = resp.json()
            assert "files" in data

    @pytest.mark.asyncio
    async def test_validate_returns_validation_result(self, client):
        resp = await client.post("/api/ai/studio/validate", json={
            "template_files": {"main.tf.j2": "{{ valid_variable }}"},
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "valid" in data
        assert "jinja2_errors" in data

    @pytest.mark.asyncio
    async def test_validate_catches_jinja2_errors(self, client):
        resp = await client.post("/api/ai/studio/validate", json={
            "template_files": {"main.tf.j2": "{{ broken"},
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["valid"] is False
        assert len(data["jinja2_errors"]) > 0

    @pytest.mark.asyncio
    async def test_save_and_load_roundtrip(self, client, tmp_path):
        # Save
        resp = await client.post("/api/ai/studio/save", json={
            "template_name": "aws/roundtrip-test",
            "files": {
                "main.tf.j2": "resource {}",
                "variables.json": "{}",
                "metadata.json": '{"name": "aws/roundtrip-test", "provider": "aws"}',
            },
            "providers": ["aws"],
        })
        assert resp.status_code == 200
        save_data = resp.json()
        assert "saved_path" in save_data

        # Load
        resp = await client.get("/api/ai/studio/load/aws/roundtrip-test")
        assert resp.status_code == 200
        load_data = resp.json()
        assert load_data["name"] == "aws/roundtrip-test"
        assert "main.tf.j2" in load_data["files"]

    @pytest.mark.asyncio
    async def test_save_rejects_path_traversal(self, client):
        resp = await client.post("/api/ai/studio/save", json={
            "template_name": "../../../hack",
            "files": {"main.tf.j2": "test"},
        })
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_load_nonexistent_returns_404(self, client):
        resp = await client.get("/api/ai/studio/load/nonexistent/template")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_wizard_steps_returns_200(self, client):
        wizard_response = json.dumps({
            "steps": ["provider", "compute", "networking", "review"],
            "defaults": {"provider": {"providers": ["aws"]}, "compute": {"instance_type": "t3.micro"}},
            "reasoning": "EC2 instance needs compute and networking",
        })
        with patch("anthropic.AsyncAnthropic") as MockClient:
            instance = MockClient.return_value
            instance.messages.create = AsyncMock(return_value=_mock_claude_response(wizard_response))

            resp = await client.post("/api/ai/studio/wizard-steps", json={
                "description": "Simple EC2 instance with VPC",
            })
            assert resp.status_code == 200
            data = resp.json()
            assert "steps" in data
            assert "provider" in data["steps"]
            assert "review" in data["steps"]
