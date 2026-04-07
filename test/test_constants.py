"""Tests for app/constants.py — shared enumerations."""

from constants import HTTPMethod


class TestHTTPMethod:

    def test_members(self):
        assert set(HTTPMethod) == {
            HTTPMethod.GET,
            HTTPMethod.POST,
            HTTPMethod.PUT,
            HTTPMethod.DELETE,
        }

    def test_is_str(self):
        assert isinstance(HTTPMethod.GET, str)

    def test_get(self):
        assert HTTPMethod.GET == "GET"

    def test_post(self):
        assert HTTPMethod.POST == "POST"

    def test_put(self):
        assert HTTPMethod.PUT == "PUT"

    def test_delete(self):
        assert HTTPMethod.DELETE == "DELETE"
