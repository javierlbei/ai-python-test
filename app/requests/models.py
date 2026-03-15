"""Domain models for request processing."""

from dataclasses import dataclass

from requests.constants import RequestStatus

@dataclass
class UserRequest:
    """Represents a user request to be processed.

    Attributes:
        user_input (str): Raw user input sent to the model.
        id (str | None): Request identifier. Assigned during persistence.
        status (RequestStatus): Current processing status.
    """

    user_input: str
    id: str | None = None
    status: RequestStatus = RequestStatus.QUEUED
