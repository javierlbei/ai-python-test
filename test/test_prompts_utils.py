"""Tests for app/prompts/utils.py — prompt payload generation."""

from prompts.utils import generate_payload


class TestGeneratePayload:

    def test_payload_structure(self):
        payload = generate_payload("system prompt", "user input")
        assert "messages" in payload
        assert len(payload["messages"]) == 2

    def test_system_message(self):
        payload = generate_payload("Extract JSON", "send email")
        system_msg = payload["messages"][0]
        assert system_msg["content"] == "Extract JSON"
        assert system_msg["role"] == "system"

    def test_user_message(self):
        payload = generate_payload("Extract JSON", "send email")
        user_msg = payload["messages"][1]
        assert user_msg["content"] == "send email"
        assert user_msg["role"] == "user"
