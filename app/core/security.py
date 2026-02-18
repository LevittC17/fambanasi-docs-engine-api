"""
Security utilities for authentication and authorization.

Provides JWT token generation, password hashing, and permission
checking for role-based access control.
"""

from datetime import datetime, timedelta
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings
from app.core.exceptions import AuthenticationError, AuthorizationError
from app.core.logging import get_logger
from app.db.models.user import UserRole

logger = get_logger(__name__)

# Password hashing context using bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against its hash.

    Args:
        plain_password: Plain text password to verify
        hashed_password: Hashed password from database

    Returns:
        True if password matches, False otherwise
    """
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False


def get_password_hash(password: str) -> str:
    """
    Hash a plain password using bcrypt.

    Args:
        password: Plain text password

    Returns:
        Hashed password suitable for database storage
    """
    return pwd_context.hash(password)


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """
    Create a JWT access token.

    Args:
        data: Dictionary of claims to encode in the token
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT token string

    Example:
        token = create_access_token(
            data={"sub": str(user.id), "role": user.role},
            expires_delta=timedelta(days=7)
        )
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "iat": datetime.utcnow(), "type": "access"})

    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    return encoded_jwt


def create_refresh_token(data: dict[str, Any]) -> str:
    """
    Create a JWT refresh token with extended expiration.

    Args:
        data: Dictionary of claims to encode in the token

    Returns:
        Encoded JWT refresh token string
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "iat": datetime.utcnow(), "type": "refresh"})

    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    return encoded_jwt


def decode_token(token: str) -> dict[str, Any]:
    """
    Decode and validate a JWT token.

    Args:
        token: JWT token string to decode

    Returns:
        Dictionary of decoded token claims

    Raises:
        AuthenticationError: If token is invalid or expired
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError as e:
        logger.warning(f"Token decode error: {e}")
        raise AuthenticationError(
            message="Invalid or expired token", details={"error": str(e)}
        ) from e


def verify_supabase_token(token: str) -> dict[str, Any]:
    """
    Verify and decode a Supabase JWT token.

    Args:
        token: Supabase JWT token

    Returns:
        Dictionary of decoded token claims

    Raises:
        AuthenticationError: If token is invalid
    """
    try:
        payload = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated",
        )
        return payload
    except JWTError as e:
        logger.warning(f"Supabase token verification error: {e}")
        raise AuthenticationError(
            message="Invalid Supabase token", details={"error": str(e)}
        ) from e


def check_permission(user_role: UserRole, required_role: UserRole) -> None:
    """
    Check if user has required permission level.

    Args:
        user_role: User's current role
        required_role: Minimum required role

    Raises:
        AuthorizationError: If user lacks required permissions

    Example:
        check_permission(current_user.role, UserRole.EDITOR)
    """
    role_hierarchy = {
        UserRole.VIEWER: 1,
        UserRole.EDITOR: 2,
        UserRole.ADMIN: 3,
    }

    if role_hierarchy[user_role] < role_hierarchy[required_role]:
        raise AuthorizationError(
            message=f"Requires {required_role.value} role or higher",
            details={
                "user_role": user_role.value,
                "required_role": required_role.value,
            },
        )


def generate_api_key() -> str:
    """
    Generate a secure API key for service-to-service authentication.

    Returns:
        Cryptographically secure random API key
    """
    import secrets

    return secrets.token_urlsafe(32)


def validate_password_strength(password: str) -> tuple[bool, list[str]]:
    """
    Validate password meets security requirements.

    Args:
        password: Password to validate

    Returns:
        Tuple of (is_valid, list of error messages)
    """
    errors = []

    if len(password) < 8:
        errors.append("Password must be at least 8 characters long")

    if not any(c.isupper() for c in password):
        errors.append("Password must contain at least one uppercase letter")

    if not any(c.islower() for c in password):
        errors.append("Password must contain at least one lowercase letter")

    if not any(c.isdigit() for c in password):
        errors.append("Password must contain at least one digit")

    # Optional: Check for special characters
    if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        errors.append("Password should contain at least one special character")

    return len(errors) == 0, errors
