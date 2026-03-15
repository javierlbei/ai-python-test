"""Configuration objects for notification provider clients."""


class NotificationClientConfig:
    """Holds configuration values for ``NotificationClient``.

    Attributes:
        BASE_URL (str): Base URL of the notification provider service.
        AUTH_HEADER (dict): Authentication headers used for requests.
        MAX_RETRIES (int): Maximum number of request retries.

    """

    def __init__(self, base_url: str, auth_header: dict, max_retries: int):
        """Creates notification client configuration.

        Args:
            base_url (str): Base URL of the provider.
            auth_header (dict): Authentication headers sent on requests.
            max_retries (int): Maximum number of retries per send operation.
        """

        self.BASE_URL = base_url
        self.AUTH_HEADER = auth_header
        self.MAX_RETRIES = max_retries
