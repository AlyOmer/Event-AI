"""
Pydantic Schemas for JWT Authentication API.
These schemas define request/response contracts for all auth endpoints.

OpenAPI spec generation: FastAPI will auto-generate from these models.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from uuid import UUID


# ============================================
# User Registration & Profile
# ============================================

class UserRegister(BaseModel):
    """Request body for user registration."""
    email: EmailStr = Field(..., description="User's email address (must be unique)")
    password: str = Field(
        ...,
        min_length=12,
        description="Password: min 12 chars, includes uppercase, lowercase, digit, special char"
    )
    first_name: Optional[str] = Field(None, max_length=100, description="User's first name")
    last_name: Optional[str] = Field(None, max_length=100, description="User's last name")
    role: Optional[str] = Field("user", max_length=50, description="Role: user, admin, or vendor")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "email": "user@example.com",
            "password": "Str0ng!Pass#123",
            "first_name": "Ali",
            "last_name": "Khan",
            "role": "user"
        }
    })


class UserLogin(BaseModel):
    """OAuth2 password grant form fields."""
    username: EmailStr = Field(..., description="Email address (OAuth2 'username' field)")
    password: str = Field(..., description="User password")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "username": "user@example.com",
            "password": "Str0ng!Pass#123"
        }
    })


class UserRead(BaseModel):
    """Public user profile (no sensitive fields)."""
    id: UUID
    email: EmailStr
    first_name: Optional[str]
    last_name: Optional[str]
    role: str
    is_active: bool
    email_verified: bool
    last_login_at: Optional[datetime]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, json_schema_extra={
        "example": {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "email": "user@example.com",
            "first_name": "Ali",
            "last_name": "Khan",
            "role": "user",
            "is_active": True,
            "email_verified": False,
            "last_login_at": "2026-04-09T10:30:00Z",
            "created_at": "2026-04-08T14:22:00Z"
        }
    })


# ============================================
# Tokens (Access + Refresh)
# ============================================

class Token(BaseModel):
    """OAuth2 token response."""
    access_token: str = Field(..., description="JWT access token (short-lived)")
    token_type: str = Field("bearer", description="Token type; always 'bearer'")
    expires_in: int = Field(..., description="Access token expiry in seconds")
    refresh_token: str = Field(..., description="Refresh token (long-lived)")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "token_type": "bearer",
            "expires_in": 900,
            "refresh_token": "dGhpcyBpcyBhIHJlZnJlc2ggdG9rZW4..."
        }
    })


class TokenData(BaseModel):
    """Payload decoded from JWT access token."""
    sub: UUID = Field(..., description="User ID (subject claim)")
    email: EmailStr = Field(..., description="User email")
    role: str = Field(..., description="User role")
    iat: datetime = Field(..., description="Issued at timestamp")
    exp: datetime = Field(..., description="Expiry timestamp")
    iss: str = Field("event-ai", description="Token issuer")

    model_config = ConfigDict(from_attributes=True)


class RefreshTokenRequest(BaseModel):
    """Request to refresh an access token."""
    refresh_token: str = Field(..., description="Valid, non-revoked refresh token")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "refresh_token": "dGhpcyBpcyBhIHJlZnJlc2ggdG9rZW4..."
        }
    })


# ============================================
# Password Reset
# ============================================

class PasswordResetRequest(BaseModel):
    """Request to initiate password reset."""
    email: EmailStr = Field(..., description="Registered user's email")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "email": "user@example.com"
        }
    })


class PasswordResetConfirm(BaseModel):
    """Confirm password reset with token and new password."""
    token: str = Field(..., description="One-time password reset token")
    new_password: str = Field(
        ...,
        min_length=12,
        description="New password: min 12 chars with complexity requirements"
    )

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "token": "cmVzdXNfY2hhbmdlX3Rva2VuX3Rva2VuX3Rva2Vu...",
            "new_password": "N3wStr0ng!Pass#456"
        }
    })


class PasswordResetTokenResponse(BaseModel):
    """Response containing reset token (for testing/development)."""
    token: str = Field(..., description="Raw password reset token")
    expires_at: datetime = Field(..., description="Token expiry timestamp")
    user_email: EmailStr = Field(..., description="Email of the user")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "token": "cmVzdXNfY2hhbmdlX3Rva2VuX3Rva2VuX3Rva2Vu...",
            "expires_at": "2026-04-09T11:00:00Z",
            "user_email": "user@example.com"
        }
    })


# ============================================
# Error Response (Standardized API Envelope)
# ============================================

class ErrorDetail(BaseModel):
    code: str = Field(..., description="Machine-readable error code from taxonomy")
    message: str = Field(..., description="Human-readable error description")
    field: Optional[str] = Field(None, description="Field name if validation error")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "code": "VALIDATION_EMAIL_EXISTS",
            "message": "Email already registered",
            "field": "email"
        }
    })


class ErrorResponse(BaseModel):
    """Standardized error envelope."""
    success: bool = Field(False, description="Always false for errors")
    error: ErrorDetail

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "success": False,
            "error": {
                "code": "AUTH_INVALID_CREDENTIALS",
                "message": "Incorrect email or password",
                "field": None
            }
        }
    })


# ============================================
# Success Response (Standardized API Envelope)
# ============================================

class SuccessResponse(BaseModel):
    """Generic success response for operations with no data."""
    success: bool = Field(True, description="Always true for success")
    message: str = Field(..., description="Human-readable success message")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "success": True,
            "message": "Password reset email sent"
        }
    })


class UserCreatedResponse(BaseModel):
    """Response after successful user registration."""
    success: bool = Field(True)
    message: str = Field("User registered successfully")
    user: UserRead
    tokens: Token

    model_config = ConfigDict(from_attributes=True)


# ============================================
# Rate Limit Error
# ============================================

class RateLimitError(BaseModel):
    """429 Too Many Requests response."""
    success: bool = Field(False)
    error: ErrorDetail = Field(default_factory=lambda: ErrorDetail(
        code="RATE_LIMIT_EXCEEDED",
        message="Too many requests. Please try again later."
    ))
