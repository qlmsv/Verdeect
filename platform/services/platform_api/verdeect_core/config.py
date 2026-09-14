from dataclasses import dataclass
import os
from pathlib import Path
from urllib.parse import urlsplit

@dataclass(frozen=True)
class Settings:
    database_url: str
    installation_org_id: str
    public_origin: str
    metering_url: str
    delegation_private_key: str
    environment: str = "development"
    secure_cookies: bool = False
    oidc_issuer: str = ""
    oidc_client_id: str = ""
    oidc_client_secret: str = ""
    oauth_cookie_secret: str = ""
    allow_dev_login: bool = False

    def __post_init__(self):
        if self.environment not in {"development", "test"}:
            raise ValueError("M0.1 is development-only. Production is blocked until SSO, upstream access and restore acceptance tests pass.")
        origin = urlsplit(self.public_origin)
        if origin.scheme not in {"http", "https"} or not origin.netloc or origin.path not in {"", "/"} or origin.query or origin.fragment or origin.username:
            raise ValueError("public_origin must be an exact origin")
        if self.public_origin.endswith("/"):
            raise ValueError("public_origin must not end with slash")
        if not self.installation_org_id or not self.delegation_private_key:
            raise ValueError("Installation and signing key are required")
        if self.oidc_issuer and (not self.oidc_client_id or not self.oidc_client_secret or len(self.oauth_cookie_secret) < 32):
            raise ValueError("OIDC requires client credentials and an independent random cookie secret")

    @classmethod
    def from_env(cls):
        return cls(
            database_url=os.environ["DATABASE_URL"],
            installation_org_id=os.environ["INSTALLATION_ORG_ID"],
            public_origin=os.environ["PUBLIC_ORIGIN"],
            metering_url=os.environ["METERING_URL"],
            delegation_private_key=Path(os.environ["DELEGATION_PRIVATE_KEY_FILE"]).read_text(),
            environment=os.getenv("APP_ENV", "development"),
            secure_cookies=os.getenv("COOKIE_SECURE", "false").lower() == "true",
            allow_dev_login=os.getenv("ALLOW_DEV_LOGIN", "false").lower() == "true",
            oidc_issuer=os.getenv("OIDC_ISSUER", ""),
            oidc_client_id=os.getenv("OIDC_CLIENT_ID", ""),
            oidc_client_secret=os.getenv("OIDC_CLIENT_SECRET", ""),
            oauth_cookie_secret=os.getenv("OAUTH_COOKIE_SECRET", ""),
        )
