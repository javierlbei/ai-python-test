"""Tests for app/user_requests/schemas.py — Pydantic API schemas."""

import pytest
from pydantic import ValidationError

from user_requests.constants import RequestStatus
from user_requests.schemas import (
    CreateRequestBody,
    CreateRequestResponse,
    GetRequestResponse,
)


class TestCreateRequestBody:

    def test_valid_input(self):
        body = CreateRequestBody(user_input="Send email to test@example.com")
        assert body.user_input == "Send email to test@example.com"

    def test_min_length_accepted(self):
        body = CreateRequestBody(user_input="x")
        assert body.user_input == "x"

    def test_max_length_accepted(self):
        body = CreateRequestBody(user_input="a" * 4096)
        assert len(body.user_input) == 4096

    def test_empty_input_rejected(self):
        with pytest.raises(ValidationError):
            CreateRequestBody(user_input="")

    def test_too_long_input_rejected(self):
        with pytest.raises(ValidationError):
            CreateRequestBody(user_input="a" * 4097)


class TestCreateRequestResponse:

    def test_valid(self):
        resp = CreateRequestResponse(id="abc123")
        assert resp.id == "abc123"


class TestGetRequestResponse:

    def test_valid(self):
        resp = GetRequestResponse(id="abc123", status=RequestStatus.QUEUED)
        assert resp.id == "abc123"
        assert resp.status == RequestStatus.QUEUED

    def test_all_statuses(self):
        for status in RequestStatus:
            resp = GetRequestResponse(id="test", status=status)
            assert resp.status == status
