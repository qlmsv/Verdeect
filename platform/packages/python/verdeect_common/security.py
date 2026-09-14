"""Short-lived, audience-specific delegation. Never an administrative API key."""
import hashlib
import time
import uuid
from urllib.parse import unquote, urlsplit
import jwt

TOKEN_ISSUER = "verdeect-platform-delegation-v1"
DELEGATION_TTL = 30


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def safe_return_path(value: str) -> str:
    # Reject encoded separators, controls and cross-origin / protocol-relative URLs.
    if not value or len(value) > 2048 or not value.startswith("/"):
        raise ValueError("Expected an absolute same-origin path")
    decoded = value
    for _ in range(3):
        decoded = unquote(decoded)
    if decoded.startswith("//") or "\\" in decoded or any(ord(c) < 32 for c in decoded):
        raise ValueError("Unsafe redirect")
    parsed = urlsplit(decoded)
    if parsed.scheme or parsed.netloc or any(part in {".", ".."} for part in parsed.path.split("/")):
        raise ValueError("Unsafe redirect")
    return value


def mint_delegation(private_key: str, org_id: str, user_id: str, scopes: list[str]) -> str:
    now = int(time.time())
    return jwt.encode({
        "iss": TOKEN_ISSUER, "aud": f"metering:{org_id}",
        "sub": user_id, "org": org_id, "scope": sorted(set(scopes)),
        "iat": now, "nbf": now, "exp": now + DELEGATION_TTL, "jti": str(uuid.uuid4()),
    }, private_key, algorithm="EdDSA")


def verify_delegation(token: str, public_key: str, org_id: str) -> dict:
    claims = jwt.decode(token, public_key, algorithms=["EdDSA"],
        audience=f"metering:{org_id}", issuer=TOKEN_ISSUER,
        options={"require": ["iss", "aud", "sub", "org", "scope", "iat", "nbf", "exp", "jti"]})
    if claims["org"] != org_id or not isinstance(claims["sub"], str) or not claims["sub"]:
        raise jwt.InvalidTokenError("Identity does not match installation")
    if not isinstance(claims["scope"], list) or not all(isinstance(s, str) for s in claims["scope"]):
        raise jwt.InvalidTokenError("Malformed scope")
    if not all(isinstance(claims[k], int) for k in ("exp", "iat", "nbf")):
        raise jwt.InvalidTokenError("Malformed token lifetime")
    if not 0 < claims["exp"] - claims["iat"] <= DELEGATION_TTL:
        raise jwt.InvalidTokenError("Delegation lifetime exceeds policy")
    return claims
