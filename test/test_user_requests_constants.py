"""Tests for app/user_requests/constants.py — domain enums."""

from user_requests.constants import (
    CreateNotificationBodyAttribute,
    RequestStatus,
    RequestType,
)


class TestCreateNotificationBodyAttribute:

    def test_members(self):
        assert set(CreateNotificationBodyAttribute) == {
            CreateNotificationBodyAttribute.TO,
            CreateNotificationBodyAttribute.TYPE,
            CreateNotificationBodyAttribute.MESSAGE,
        }

    def test_to(self):
        assert CreateNotificationBodyAttribute.TO == "to"

    def test_type(self):
        assert CreateNotificationBodyAttribute.TYPE == "type"

    def test_message(self):
        assert CreateNotificationBodyAttribute.MESSAGE == "message"


class TestRequestType:

    def test_members(self):
        assert set(RequestType) == {
            RequestType.EMAIL,
            RequestType.SMS,
            RequestType.PUSH,
        }

    def test_email(self):
        assert RequestType.EMAIL == "email"

    def test_sms(self):
        assert RequestType.SMS == "sms"

    def test_push(self):
        assert RequestType.PUSH == "push"


class TestRequestStatus:

    def test_members(self):
        assert set(RequestStatus) == {
            RequestStatus.QUEUED,
            RequestStatus.PROCESSING,
            RequestStatus.SENT,
            RequestStatus.FAILED,
        }

    def test_queued(self):
        assert RequestStatus.QUEUED == "queued"

    def test_processing(self):
        assert RequestStatus.PROCESSING == "processing"

    def test_sent(self):
        assert RequestStatus.SENT == "sent"

    def test_failed(self):
        assert RequestStatus.FAILED == "failed"
