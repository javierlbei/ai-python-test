"""Tests for app/user_requests/models.py — domain model."""

from user_requests.constants import RequestStatus
from user_requests.models import UserRequest


class TestUserRequest:

    def test_default_values(self):
        request = UserRequest(user_input="test")
        assert request.user_input == "test"
        assert request.id is None
        assert request.status == RequestStatus.QUEUED

    def test_custom_values(self):
        request = UserRequest(
            user_input="hello",
            id="abc123",
            status=RequestStatus.SENT,
        )
        assert request.user_input == "hello"
        assert request.id == "abc123"
        assert request.status == RequestStatus.SENT

    def test_status_can_be_updated(self):
        request = UserRequest(user_input="test")
        request.status = RequestStatus.PROCESSING
        assert request.status == RequestStatus.PROCESSING
