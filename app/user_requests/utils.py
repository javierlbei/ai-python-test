"""Utilities for extracting and validating JSON from model responses."""

import re

import json_repair

from user_requests.constants import CreateNotificationBodyAttribute, RequestType
from user_requests.exceptions import InvalidJSONContentError
from utils import get_logger


_logger = get_logger()

EMAIL_PATTERN = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
PHONE_PATTERN = r'^\+[1-9]\d{1,3}[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9}$'

_SIMILARITY_THRESHOLD = 0.5


async def _matches_user_input(text: str, user_input: str) -> bool:
    """Checks whether two texts are sufficiently similar.

    Similarity is computed using Jaccard overlap over lowercase token sets.

    Args:
        text (str): Candidate message text.
        user_input (str): Original user input.

    Returns:
        bool: ``True`` when similarity is at least 0.5, else ``False``.
    """

    text_set = set(text.lower().split())
    user_input_set = set(user_input.lower().split())

    intersection = len(text_set.intersection(user_input_set))
    union = len(text_set.union(user_input_set))

    if union == 0:
        return False

    return intersection / union >= _SIMILARITY_THRESHOLD


async def _attribute_type(value: str, user_input: str) -> str | None:
    """Classifies a model output value as a notification payload attribute.

    Detects whether the value is an email/phone (``'to'``), a known
    notification channel (``'type'``), or text similar to the original
    user input (``'message'``).

    Args:
        value (str): Candidate value from model output.
        user_input (str): Original user input used for message matching.

    Returns:
        str | None: ``'to'``, ``'type'``, or ``'message'`` when detected;
        otherwise ``None``.
    """

    if isinstance(value, str) and (
        re.match(EMAIL_PATTERN, value) or re.match(PHONE_PATTERN, value)
    ):
        return CreateNotificationBodyAttribute.TO

    if isinstance(value, str) and value in RequestType:
        return CreateNotificationBodyAttribute.TYPE

    if isinstance(value, str) and await _matches_user_input(value, user_input):
        return CreateNotificationBodyAttribute.MESSAGE

    return None


async def _sanitize_json(payload: dict, user_input: str) -> dict:
    """Normalizes model output keys to the expected payload schema.

    Args:
        payload (dict): Parsed model output dictionary.
        user_input (str): Original user input for message detection.

    Returns:
        dict | None: Sanitized payload when required keys are present,
        otherwise ``None``.
    """
    sanitized_json = {}

    for key, value in payload.items():
        if key in CreateNotificationBodyAttribute:
            sanitized_json[key] = value
            continue

        attribute_name = await _attribute_type(value, user_input)

        if attribute_name is not None:
            sanitized_json[attribute_name] = value

    if all(key in sanitized_json for key in CreateNotificationBodyAttribute):
        return sanitized_json

    return None


async def _is_valid_json(payload: dict) -> bool:
    """Validates whether a sanitized payload is semantically valid.

    Args:
        payload (dict): Candidate payload with `to`, `type`, and `message`.

    Returns:
        bool: ``True`` when channel and target values are valid.
    """

    match payload[CreateNotificationBodyAttribute.TYPE]:
        case RequestType.EMAIL | RequestType.PUSH:
            email = payload[CreateNotificationBodyAttribute.TO]
            return re.match(EMAIL_PATTERN, email) is not None
        case RequestType.SMS:
            phone = payload[CreateNotificationBodyAttribute.TO]
            return re.match(PHONE_PATTERN, phone) is not None
        case _:
            return False


async def json_extractor(
    llm_response: dict[str, str],
) -> dict[str, str]:
    """Extracts and validates notification JSON from model output.

    Args:
        llm_response (dict): Dictionary containing `user_input` and raw
            `llm_response` text.

    Returns:
        dict: Validated notification payload.

    Raises:
        InvalidJSONContentError: If output cannot be parsed, sanitized,
            or validated.
    """

    _logger.debug('Extracting JSON from LLM response')
    formatted_json = json_repair.loads(
        llm_response['llm_response'], strict=True,
    )

    if not isinstance(formatted_json, dict):
        _logger.warning('LLM response did not contain parseable JSON')
        raise InvalidJSONContentError()

    sanitized_json = await _sanitize_json(
        formatted_json, llm_response['user_input'],
    )

    if sanitized_json and await _is_valid_json(sanitized_json):
        _logger.debug('LLM JSON payload extracted and validated successfully')
        return sanitized_json

    _logger.warning('LLM JSON payload failed sanitization or validation')
    raise InvalidJSONContentError()
