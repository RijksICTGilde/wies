from django.conf import settings
from django.core.exceptions import ValidationError


class EmailNotAvailableError(Exception):
    """Raised when an email is already in use."""

    def __init__(self, email):
        self.email = email
        super().__init__(f"{email} already in use")


class InvalidEmailDomainError(ValidationError):
    """Raised when an email has a non-allowed domain."""

    def __init__(self, email: str, *, user_facing: bool = False):
        self.email = email
        self.allowed_domains = getattr(settings, "ALLOWED_EMAIL_DOMAINS", [])
        domains_str = ", ".join(self.allowed_domains) if self.allowed_domains else "geen"
        if user_facing:
            message = f"Alleen ODI e-mailadressen zijn toegestaan ({domains_str})"
        else:
            message = f"{email} has invalid domain. Allowed: {domains_str}"
        super().__init__(message)
