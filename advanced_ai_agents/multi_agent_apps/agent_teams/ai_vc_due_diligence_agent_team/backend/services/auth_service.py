"""Auth Service - Clerk JWT verification for FastAPI

Provides JWT token verification using Clerk's JWKS endpoint.
All protected routes should use the get_current_user dependency.
"""

import os
from typing import Optional
from fastapi import HTTPException, Security, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import httpx
from jose import jwt, JWTError, jwk
from jose.utils import base64url_decode
from loguru import logger


# HTTP Bearer token security scheme
security = HTTPBearer(auto_error=False)

# Clerk configuration from environment
CLERK_ISSUER = os.getenv("CLERK_ISSUER")  # e.g., https://your-app.clerk.accounts.dev
CLERK_SECRET_KEY = os.getenv("CLERK_SECRET_KEY")  # sk_test_xxxxx

# Cache for JWKS
_jwks_cache: Optional[dict] = None
_jwks_client: Optional[httpx.AsyncClient] = None


async def get_jwks() -> dict:
    """
    Fetch and cache Clerk's JWKS (JSON Web Key Set).

    The JWKS contains the public keys used to verify JWT signatures.
    We cache it to avoid fetching on every request.
    """
    global _jwks_cache, _jwks_client

    if _jwks_cache is not None:
        return _jwks_cache

    if not CLERK_ISSUER:
        raise HTTPException(
            status_code=500,
            detail="CLERK_ISSUER environment variable not configured"
        )

    jwks_url = f"{CLERK_ISSUER}/.well-known/jwks.json"

    try:
        if _jwks_client is None:
            _jwks_client = httpx.AsyncClient()

        response = await _jwks_client.get(jwks_url, timeout=10.0)
        response.raise_for_status()

        _jwks_cache = response.json()
        logger.info(f"Fetched JWKS from {jwks_url}")
        return _jwks_cache

    except httpx.HTTPError as e:
        logger.error(f"Failed to fetch JWKS from {jwks_url}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch authentication keys: {e}"
        )


def get_signing_key(jwks: dict, token: str) -> dict:
    """
    Find the correct signing key from JWKS based on the token's kid (key ID).

    Args:
        jwks: The JSON Web Key Set
        token: The JWT token to find the key for

    Returns:
        The matching key from the JWKS

    Raises:
        HTTPException: If no matching key is found
    """
    try:
        # Decode header without verification to get kid
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")

        if not kid:
            raise HTTPException(
                status_code=401,
                detail="Token missing key ID (kid)"
            )

        # Find matching key in JWKS
        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                return key

        raise HTTPException(
            status_code=401,
            detail="No matching key found for token"
        )

    except JWTError as e:
        raise HTTPException(
            status_code=401,
            detail=f"Invalid token header: {e}"
        )


async def verify_clerk_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security)
) -> dict:
    """
    Verify a Clerk JWT token and return the decoded payload.

    This is the core authentication function. It:
    1. Extracts the Bearer token from the Authorization header
    2. Fetches the JWKS from Clerk
    3. Finds the correct signing key
    4. Verifies the token signature and claims

    Args:
        credentials: The HTTP Authorization credentials (Bearer token)

    Returns:
        The decoded JWT payload containing user claims

    Raises:
        HTTPException: If token is missing, invalid, or verification fails
    """
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Authorization header missing",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    try:
        # Fetch JWKS
        jwks = await get_jwks()

        # Find the signing key
        signing_key = get_signing_key(jwks, token)

        # Convert JWK to PEM format for jose library
        # The jose library can work with JWK directly
        payload = jwt.decode(
            token,
            signing_key,
            algorithms=["RS256"],
            issuer=CLERK_ISSUER,
            options={
                "verify_aud": False,  # Clerk doesn't always set audience
                "verify_iss": True,
                "verify_exp": True,
            }
        )

        logger.debug(f"Token verified for user: {payload.get('sub')}")
        return payload

    except JWTError as e:
        logger.warning(f"JWT verification failed: {e}")
        raise HTTPException(
            status_code=401,
            detail=f"Invalid or expired token: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Authentication error: {e}", exc_info=True)
        raise HTTPException(
            status_code=401,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    user: dict = Depends(verify_clerk_token)
) -> dict:
    """
    Dependency to get the current authenticated user.

    Use this in route functions to require authentication:

    ```python
    @router.get("/protected")
    async def protected_route(current_user: dict = Depends(get_current_user)):
        return {"user_id": current_user["sub"]}
    ```

    Args:
        user: The decoded JWT payload from verify_clerk_token

    Returns:
        The user claims dict with fields like:
        - sub: User ID
        - email: User's email (if available)
        - name: User's name (if available)
    """
    return user


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security)
) -> Optional[dict]:
    """
    Dependency to optionally get the current user.

    Unlike get_current_user, this doesn't raise an error if no token is provided.
    Useful for routes that have different behavior for authenticated vs anonymous users.

    Args:
        credentials: Optional HTTP Authorization credentials

    Returns:
        The user claims dict if authenticated, None otherwise
    """
    if credentials is None:
        return None

    try:
        return await verify_clerk_token(credentials)
    except HTTPException:
        return None


def is_auth_enabled() -> bool:
    """
    Check if authentication is properly configured.

    Returns:
        True if CLERK_ISSUER is configured, False otherwise
    """
    return bool(CLERK_ISSUER)


async def clear_jwks_cache() -> None:
    """
    Clear the JWKS cache.

    Call this if keys need to be refreshed (e.g., after key rotation).
    """
    global _jwks_cache
    _jwks_cache = None
    logger.info("JWKS cache cleared")
