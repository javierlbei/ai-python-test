"""Utilities for extracting and validating JSON from model responses."""

import logging
import re

import json_repair

from requests.constants import CreateNotificationBodyAttribute, RequestType
from requests.exceptions import InvalidJSONContentException


_logger = logging.getLogger('uvicorn.error')

EMAIL_PATTERN = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
PHONE_PATTERN = r'^\+[1-9]\d{1,3}[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9}$'

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

    return intersection / union >= 0.5

async def _attribute_type(value: str, user_input: str) -> str | None:
    """Checks if the provided value is an email or a phone number.

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
        return 'to'

    if isinstance(value, str) and value in RequestType:
        return 'type'

    if isinstance(value, str) and await _matches_user_input(value, user_input):
        return 'message'

    return None

async def _sanitize_json(json: dict, user_input: str) -> dict:
    """Normalizes model output keys to the expected payload schema.

    Args:
        json (dict): Parsed model output dictionary.
        user_input (str): Original user input for message detection.

    Returns:
        dict | None: Sanitized payload when required keys are present,
        otherwise ``None``.
    """
    keys_to_add = {}
    keys_to_remove = []

    for key, value in json.items():
        if key in CreateNotificationBodyAttribute:
            continue
        else:
            attribute_name = await _attribute_type(value, user_input)

            if attribute_name is not None:
                keys_to_add[attribute_name] = value
                keys_to_remove.append(key)
            else:
                keys_to_remove.append(key)

    for key, value in keys_to_add.items():
        json[key] = value

    for key in keys_to_remove:
        del json[key]

    if all(key in json for key in CreateNotificationBodyAttribute): return json

    return None

async def _is_valid_json(json: dict) -> bool:
    """Validates whether a sanitized payload is semantically valid.

    Args:
        json (dict): Candidate payload with `to`, `type`, and `message`.

    Returns:
        bool: ``True`` when channel and target values are valid.
    """

    match json['type']:
        case 'email' | 'push':
            return re.match(EMAIL_PATTERN, json['to']) is not None
        case 'sms':
            return re.match(PHONE_PATTERN, json['to']) is not None
        case _:
            return False

async def json_extractor(llm_response: dict[str, str]) -> dict[str, str]:
    """Extracts and validates notification JSON from model output.

    Args:
        llm_response (dict): Dictionary containing `user_input` and raw
            `llm_response` text.

    Returns:
        dict: Validated notification payload.

    Raises:
        InvalidJSONContentException: If output cannot be parsed, sanitized, or
            validated.
    """

    _logger.debug('Extracting JSON from LLM response')
    formatted_json = json_repair.loads(llm_response['llm_response'], strict=True)

    if not formatted_json:
        _logger.warning('LLM response did not contain parseable JSON')
        raise InvalidJSONContentException()

    sanitized_json = await _sanitize_json(formatted_json, llm_response['user_input'])

    if sanitized_json and await _is_valid_json(sanitized_json):
        _logger.debug('LLM JSON payload extracted and validated successfully')
        return sanitized_json

    _logger.warning('LLM JSON payload failed sanitization or validation')
    raise InvalidJSONContentException()
