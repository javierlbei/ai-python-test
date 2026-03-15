"""Configuration objects for prompt provider clients."""


class PromptClientConfig:
    """Holds configuration values for ``PromptClient``.

    Attributes:
        BASE_URL (str): Base URL of the prompt provider service.
        AUTH_HEADER (dict): Authentication headers sent on each request.
        SYSTEM_PROMPT (str): System prompt passed to the model.
        MAX_RETRIES (int): Maximum number of request retries.

    """

    def __init__(
        self,
        base_url: str,
        auth_header: dict,
        system_prompt: str,
        max_retries: int
    ):
        """Creates a prompt client configuration.

        Args:
            base_url (str): Base URL of the prompt provider.
            auth_header (dict): Authentication headers for provider requests.
            system_prompt (str): Instruction text used as system context.
            max_retries (int): Maximum number of retries per request.
        """

        self.BASE_URL = base_url
        self.AUTH_HEADER = auth_header
        self.SYSTEM_PROMPT = system_prompt
        self.MAX_RETRIES = max_retries
