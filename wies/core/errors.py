from django.conf import settings


class EmailNotAvailableError(Exception):
    """Raised when an email is already in use."""

    def __init__(self, email):
        self.email = email
        super().__init__(f"{email} already in use")


class InvalidEmailDomainError(Exception):
    """Raised when an email has a non-allowed domain."""

    def __init__(self, email):
        self.email = email
        self.allowed_domains = getattr(settings, "ALLOWED_EMAIL_DOMAINS", [])
        domains_str = ", ".join(self.allowed_domains) if self.allowed_domains else "none configured"
        super().__init__(f"{email} has invalid domain. Allowed: {domains_str}")
