"""Tests for app/main.py — application bootstrap, middleware, exception handler."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


class TestBuildApp:

    def test_app_title(self):
        from main import app
        assert app.title == 'Notification Service (Technical Test)'

    def test_app_has_routes(self):
        from main import app
        paths = [route.path for route in app.routes]
        assert '/v1/requests' in paths
        assert '/v1/requests/{request_id}/process' in paths
        assert '/v1/requests/{request_id}' in paths


class TestLifespan:

    async def test_lifespan_calls_startup_and_shutdown(self):
        with patch("main.requests_router") as mock_router:
            mock_router.startup = AsyncMock()
            mock_router.shutdown = AsyncMock()

            from main import lifespan

            fake_app = FastAPI()
            async with lifespan(fake_app):
                mock_router.startup.assert_awaited_once()

            mock_router.shutdown.assert_awaited_once()


class TestSecurityHeaders:

    def test_headers_present(self):
        from main import build_app

        with patch("main.Container"):
            with patch("main.requests_router"):
                app = build_app()

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/nonexistent")
        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert response.headers.get("X-Frame-Options") == "DENY"
        assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
        assert "Strict-Transport-Security" in response.headers
        assert response.headers.get("Content-Security-Policy") == "default-src 'none'; frame-ancestors 'none'"


class TestBodySizeLimit:

    def test_oversized_body_returns_413(self):
        from main import build_app

        with patch("main.Container"):
            with patch("main.requests_router"):
                app = build_app()

        client = TestClient(app, raise_server_exceptions=False)
        response = client.post(
            "/v1/requests",
            content="x" * 5000,
            headers={"content-length": "5000", "content-type": "application/json"},
        )
        assert response.status_code == 413

    def test_oversized_body_without_content_length_returns_413(self):
        from main import build_app

        with patch("main.Container"):
            with patch("main.requests_router"):
                app = build_app()

        client = TestClient(app, raise_server_exceptions=False)
        response = client.post(
            "/v1/requests",
            content="x" * 5000,
            headers={"content-type": "application/json"},
        )
        assert response.status_code == 413

    def test_malformed_content_length_returns_400(self):
        from main import build_app

        with patch("main.Container"):
            with patch("main.requests_router"):
                app = build_app()

        client = TestClient(app, raise_server_exceptions=False)
        response = client.post(
            "/v1/requests",
            content="test",
            headers={
                "content-length": "not-a-number",
                "content-type": "application/json",
            },
        )
        assert response.status_code == 400


class TestExceptionHandler:

    def test_exception_handler_registered(self):
        from main import app
        assert Exception in app.exception_handlers

    def test_handler_returns_500_json(self):
        from main import app

        handler = app.exception_handlers[Exception]
        assert handler is not None

    async def test_unhandled_exception_returns_500(self):
        from main import app

        handler = app.exception_handlers[Exception]
        response = await handler(None, Exception("boom"))
        assert response.status_code == 500
        assert b"unexpected error" in response.body
