"""Application bootstrap and dependency wiring for the API service."""

from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI

from concurrency.service import ConcurrencyService
from notifications.client import NotificationClient
from notifications.config import NotificationClientConfig
from prompts.client import PromptClient
from prompts.config import PromptClientConfig
from requests import router as requests_router
from requests.service import RequestService


_logger = logging.getLogger('uvicorn.error')


PROVIDER_BASE_URL = "http://localhost:3001"
PROVIDER_AUTH_HEADER = {"X-API-Key": "test-dev-2026"}
MAX_RETRIES = 3
NUM_WORKERS = 10
SYSTEM_PROMPT = """
You are a data extractor for a notification service. Extract and return a JSON object based strictly on the user's request. Do not introduce external information, add explanations, or clarify ambiguous terms—only extract what is explicitly provided.

Users may write in any language. Translate their input to English internally for processing, but respond to the user in their original language.

Return a JSON object with this exact structure:
{
    "to": "email address or phone number",
    "message": "message text",
    "type": "sms" or "email"
}

Field requirements:
- "to": Extract exactly one email address or phone number. Validate formats as follows:
  - Email: Must contain an @ symbol and a valid domain structure (e.g., user@example.com).
  - Phone: Must contain at least 6-15 consecutive digits, preceded by a + symbol for international format (e.g., +34722677446). If a phone number appears incomplete, ambiguous, or lacks sufficient digits, ask the user to provide a complete number with country code if international.
  If multiple recipients are provided, none is clear, or the format is invalid, ask the user to specify a single, complete contact.
- "message": Extract the message text. You may correct grammar or rewrite for clarity, but preserve the core intent. If the message is missing or empty, ask the user to provide it.
- "type": Infer whether the user wants 'sms' or 'email'. If a phone number is provided without explicit instruction, assume 'sms'. If an email is provided without explicit instruction, assume 'email'. If the contact type and desired channel conflict, ask the user to clarify.

If any mandatory field cannot be extracted or validated, ask the user to provide the missing information before returning JSON.
"""

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    _logger.info('Starting application services')
    await request_service.start()

    app.state.concurrency_service = concurrency_service
    app.state.request_service = request_service

    yield

    # Shutdown
    _logger.info('Stopping application services')
    await request_service.stop()
    await notification_client.close()
    await prompt_client.close()


concurrency_service = ConcurrencyService()
notification_client_config = NotificationClientConfig(
    base_url=PROVIDER_BASE_URL,
    auth_header=PROVIDER_AUTH_HEADER,
    max_retries=MAX_RETRIES,
)
notification_client = NotificationClient(notification_client_config)
prompt_client_config = PromptClientConfig(
    base_url=PROVIDER_BASE_URL,
    auth_header=PROVIDER_AUTH_HEADER,
    system_prompt=SYSTEM_PROMPT,
    max_retries=MAX_RETRIES,
)
prompt_client = PromptClient(prompt_client_config)
request_service = RequestService(
    concurrency_service,
    notification_client,
    prompt_client,
    NUM_WORKERS,
)

app = FastAPI(
    title="Notification Service (Technical Test)",
    lifespan=lifespan,
)
app.include_router(requests_router.router)
