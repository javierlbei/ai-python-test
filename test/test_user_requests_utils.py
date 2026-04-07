"""Tests for app/user_requests/utils.py — JSON extraction and validation."""

import pytest

from user_requests.constants import CreateNotificationBodyAttribute, RequestType
from user_requests.exceptions import InvalidJSONContentError
from user_requests.utils import (
    _attribute_type,
    _is_valid_json,
    _matches_user_input,
    _sanitize_json,
    json_extractor,
)


class TestMatchesUserInput:

    async def test_identical_text(self):
        assert await _matches_user_input("hello world", "hello world") is True

    async def test_similar_text(self):
        assert await _matches_user_input(
            "send an email to John", "send email to John",
        ) is True

    async def test_dissimilar_text(self):
        assert await _matches_user_input(
            "completely different", "send email to John",
        ) is False

    async def test_empty_strings(self):
        assert await _matches_user_input("", "") is False


class TestAttributeType:

    async def test_email_detected(self):
        result = await _attribute_type("user@example.com", "test")
        assert result == CreateNotificationBodyAttribute.TO

    async def test_phone_detected(self):
        result = await _attribute_type("+34722677446", "test")
        assert result == CreateNotificationBodyAttribute.TO

    async def test_type_email(self):
        result = await _attribute_type("email", "test")
        assert result == CreateNotificationBodyAttribute.TYPE

    async def test_type_sms(self):
        result = await _attribute_type("sms", "test")
        assert result == CreateNotificationBodyAttribute.TYPE

    async def test_type_push(self):
        result = await _attribute_type("push", "test")
        assert result == CreateNotificationBodyAttribute.TYPE

    async def test_message_detected(self):
        result = await _attribute_type(
            "please send this email",
            "please send this email to John",
        )
        assert result == CreateNotificationBodyAttribute.MESSAGE

    async def test_unknown_value(self):
        result = await _attribute_type("xyz", "abc")
        assert result is None

    async def test_non_string_value(self):
        result = await _attribute_type(123, "test")
        assert result is None


class TestSanitizeJson:

    async def test_already_correct_keys(self):
        payload = {"to": "a@b.com", "type": "email", "message": "hi"}
        result = await _sanitize_json(payload, "send email to a@b.com")
        assert result is not None
        assert result["to"] == "a@b.com"
        assert result["type"] == "email"
        assert result["message"] == "hi"

    async def test_detects_attributes_from_values(self):
        payload = {
            "recipient": "a@b.com",
            "channel": "email",
            "body": "send email to a@b.com saying hi",
        }
        result = await _sanitize_json(
            payload, "send email to a@b.com saying hi",
        )
        assert result is not None
        assert result[CreateNotificationBodyAttribute.TO] == "a@b.com"
        assert result[CreateNotificationBodyAttribute.TYPE] == "email"

    async def test_missing_required_keys_returns_none(self):
        payload = {"to": "a@b.com"}
        result = await _sanitize_json(payload, "test")
        assert result is None

    async def test_empty_payload(self):
        result = await _sanitize_json({}, "test")
        assert result is None


class TestIsValidJson:

    async def test_valid_email(self):
        payload = {"to": "a@b.com", "type": "email", "message": "hi"}
        assert await _is_valid_json(payload) is True

    async def test_valid_sms(self):
        payload = {"to": "+34722677446", "type": "sms", "message": "hi"}
        assert await _is_valid_json(payload) is True

    async def test_valid_push_with_email(self):
        payload = {"to": "a@b.com", "type": "push", "message": "hi"}
        assert await _is_valid_json(payload) is True

    async def test_invalid_email_for_email_type(self):
        payload = {"to": "not-an-email", "type": "email", "message": "hi"}
        assert await _is_valid_json(payload) is False

    async def test_invalid_phone_for_sms_type(self):
        payload = {"to": "not-a-phone", "type": "sms", "message": "hi"}
        assert await _is_valid_json(payload) is False

    async def test_unknown_type_returns_false(self):
        payload = {"to": "a@b.com", "type": "fax", "message": "hi"}
        assert await _is_valid_json(payload) is False


class TestJsonExtractor:

    async def test_valid_json_email(self):
        llm_response = {
            "user_input": "send email to a@b.com saying hi",
            "llm_response": '{"to": "a@b.com", "type": "email", "message": "hi"}',
        }
        result = await json_extractor(llm_response)
        assert result["to"] == "a@b.com"
        assert result["type"] == "email"
        assert result["message"] == "hi"

    async def test_valid_json_sms(self):
        llm_response = {
            "user_input": "send sms to +34722677446",
            "llm_response": '{"to": "+34722677446", "type": "sms", "message": "hello"}',
        }
        result = await json_extractor(llm_response)
        assert result["to"] == "+34722677446"
        assert result["type"] == "sms"

    async def test_non_dict_raises(self):
        llm_response = {
            "user_input": "test",
            "llm_response": '["not", "a", "dict"]',
        }
        with pytest.raises(InvalidJSONContentError):
            await json_extractor(llm_response)

    async def test_invalid_json_content_raises(self):
        llm_response = {
            "user_input": "test",
            "llm_response": '{"random": "data"}',
        }
        with pytest.raises(InvalidJSONContentError):
            await json_extractor(llm_response)

    async def test_sanitize_then_invalid_validation(self):
        llm_response = {
            "user_input": "send email to bad-address",
            "llm_response": '{"to": "not-valid", "type": "email", "message": "send email to bad-address"}',
        }
        with pytest.raises(InvalidJSONContentError):
            await json_extractor(llm_response)

    async def test_valid_keys_invalid_values(self):
        llm_response = {
            "user_input": "test",
            "llm_response": '{"to": "invalid", "type": "sms", "message": "test"}',
        }
        with pytest.raises(InvalidJSONContentError):
            await json_extractor(llm_response)
