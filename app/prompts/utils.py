"""Helper utilities for prompt-provider request payloads."""

import logging


_logger = logging.getLogger('uvicorn.error')


def generate_payload(system_prompt: str, user_input: str):
    """Builds the request payload for prompt extraction.

    Args:
        system_prompt (str): System instruction for the model.
        user_input (str): End-user input that should be processed.

    Returns:
        dict: JSON payload sent to the prompt provider.
    """

    _logger.debug('Generating prompt payload')

    return {
        "messages": [
            {"content": system_prompt, "role": "system"},
            {"content": user_input, "role": "user"},
        ]
    }
