"""Exceptions for the aiokem package."""

from __future__ import annotations


class AioKemError(Exception):
    """Base exception for the aiokem package."""

    pass


class ServerError(AioKemError):
    """Exception raised for server-related errors."""

    def __init__(self, message: str = "Server error"):
        super().__init__(message)


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
