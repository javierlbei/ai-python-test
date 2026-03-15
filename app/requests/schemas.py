"""Pydantic schemas used by request API endpoints."""

from pydantic import BaseModel

from requests.constants import RequestStatus


class CreateRequestBody(BaseModel):
    """Request body for creating a new user request.

    Attributes:
        user_input (str): User input that should be processed.
    """

    user_input: str

class CreateRequestResponse(BaseModel):
    """Response model for successful request creation.

    Attributes:
        id (str): Unique identifier of the created request.
    """

    id: str

class GetRequestResponse(BaseModel):
    """Response model for request retrieval.

    Attributes:
        id (str): Unique identifier of the request.
        status (RequestStatus): Current processing status.
    """

    id: str
    status: RequestStatus
