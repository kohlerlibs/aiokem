"""Exceptions for the aiokem package."""


class AioKemError(Exception):
    """Base exception for the aiokem package."""

    pass


class AuthenticationError(AioKemError):
    """Exception raised for authentication-related errors."""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message)


class AuthenticationCredentialsError(AuthenticationError):
    """Exception raised for authentication-related errors."""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message)


class CommunicationError(AioKemError):
    """Exception raised for communication-related errors."""

    def __init__(self, message: str = "Communication error"):
        super().__init__(message)
