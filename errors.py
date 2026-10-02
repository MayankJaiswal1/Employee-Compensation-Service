"""Dependency-free error type so validation can be unit-tested in isolation."""


class ApiError(Exception):
    def __init__(self, status: int, message: str, details=None):
        super().__init__(message)
        self.status = status
        self.message = message
        self.details = details
