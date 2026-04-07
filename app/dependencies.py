"""Dependency injection container wiring for the application."""

import os

from circuitbreaker import CircuitBreaker
from dependency_injector import containers, providers
from httpx import AsyncClient

from notifications.client import NotificationClient
from prompts.client import PromptClient
from user_requests.concurrency import UserRequestConcurrencyService
from user_requests.processor import RequestProcessor
from user_requests.repository import RequestRepository
from user_requests.service import RequestService
from utils import get_logger

_logger = get_logger()

_DEFAULT_API_KEY = 'test-dev-2026'


def _build_auth_header(env_var: str, default: str = _DEFAULT_API_KEY) -> dict:
    """Builds an auth header dict from an environment variable."""
    api_key = os.environ.get(env_var)
    if api_key is None:
        _logger.warning(
            'Environment variable %s is not set, using insecure default',
            env_var,
        )
        api_key = default
    return {'X-API-Key': api_key}


class Container(containers.DeclarativeContainer):
    """Dependency injection container for application services."""

    wiring_config = containers.WiringConfiguration(
        modules=['user_requests.router'],
    )

    config = providers.Configuration(yaml_files=['config.yml'])

    http_client_factory = providers.Factory(providers.Factory, AsyncClient)
    circuit_breaker_factory = providers.Factory(
        providers.Factory,
        CircuitBreaker,
    )

    prompt_auth_header = providers.Factory(
        _build_auth_header,
        env_var='PROMPT_PROVIDER_API_KEY',
        default='test-dev-2026',
    )

    prompt_client = providers.Singleton(
        PromptClient,
        http_client=http_client_factory(
            base_url=config.prompt_provider.base_url,
            headers=prompt_auth_header,
            timeout=config.prompt_provider.timeout_seconds,
        ),
        circuit_breaker=circuit_breaker_factory(
            failure_threshold=(
                config.prompt_provider
                .circuit_breaker_fail_threshold
            ),
            recovery_timeout=(
                config.prompt_provider
                .circuit_breaker_reset_timeout
            ),
        ),
        system_prompt=config.prompt_provider.system_prompt,
        max_retries=config.prompt_provider.max_retries,
    )

    notification_auth_header = providers.Factory(
        _build_auth_header,
        env_var='NOTIFICATION_PROVIDER_API_KEY',
        default='test-dev-2026',
    )

    notification_client = providers.Singleton(
        NotificationClient,
        http_client=http_client_factory(
            base_url=config.notification_provider.base_url,
            headers=notification_auth_header,
            timeout=config.notification_provider.timeout_seconds,
        ),
        circuit_breaker=circuit_breaker_factory(
            failure_threshold=(
                config.notification_provider
                .circuit_breaker_fail_threshold
            ),
            recovery_timeout=(
                config.notification_provider
                .circuit_breaker_reset_timeout
            ),
        ),
        max_retries=config.notification_provider.max_retries,
    )

    requests_repository = providers.Singleton(
        RequestRepository,
    )

    concurrency_service = providers.Singleton(
        UserRequestConcurrencyService,
        queue_size=config.concurrency.queue_size,
        max_retries=config.concurrency.max_retries,
    )

    request_service = providers.Singleton(
        RequestService,
        requests_repository=requests_repository,
    )

    request_processor = providers.Singleton(
        RequestProcessor,
        concurrency_service=concurrency_service,
        notification_client=notification_client,
        requests_repository=requests_repository,
        prompt_client=prompt_client,
        num_workers=config.concurrency.num_workers,
    )
