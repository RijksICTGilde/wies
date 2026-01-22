class EmailNotAvailableError(Exception):
    """Raised when an email is already in use."""

    def __init__(self, email, field="email"):
        self.email = email
        self.field = field
        super().__init__(f"{email} already in use")
