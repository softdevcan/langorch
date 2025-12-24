"""
Custom exceptions for the application
"""
from typing import Optional
from fastapi import HTTPException, status


class LangOrchException(Exception):
    """Base exception for LangOrch application"""
    def __init__(self, message: str, detail: Optional[str] = None):
        self.message = message
        self.detail = detail
        super().__init__(self.message)


class AuthenticationException(LangOrchException):
    """Raised when authentication fails"""
    pass


class AuthorizationException(LangOrchException):
    """Raised when user is not authorized"""
    pass


class NotFoundException(LangOrchException):
    """Raised when resource is not found"""
    pass


class ConflictException(LangOrchException):
    """Raised when there's a conflict (e.g., duplicate email)"""
    pass


class ValidationException(LangOrchException):
    """Raised when validation fails"""
    pass


class TenantIsolationException(LangOrchException):
    """Raised when tenant isolation is violated"""
    pass


# HTTP Exception helpers
def http_401_unauthorized(detail: str = "Could not validate credentials") -> HTTPException:
    """Return 401 Unauthorized exception"""
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def http_403_forbidden(detail: str = "Forbidden") -> HTTPException:
    """Return 403 Forbidden exception"""
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=detail,
    )


def http_404_not_found(detail: str = "Resource not found") -> HTTPException:
    """Return 404 Not Found exception"""
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=detail,
    )


def http_409_conflict(detail: str = "Resource already exists") -> HTTPException:
    """Return 409 Conflict exception"""
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=detail,
    )


def http_422_validation_error(detail: str = "Validation error") -> HTTPException:
    """Return 422 Unprocessable Entity exception"""
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=detail,
    )
