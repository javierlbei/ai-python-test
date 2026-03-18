"""Shared constants and enumerations for the application."""

from enum import Enum


class HTTPMethod(str, Enum):
    """Supported HTTP methods for provider requests."""

    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
