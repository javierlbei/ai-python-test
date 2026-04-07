"""Helper utilities for prompt-provider request payloads."""


from utils import get_logger


_logger = get_logger()


def generate_payload(system_prompt: str, user_input: str) -> dict:
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
