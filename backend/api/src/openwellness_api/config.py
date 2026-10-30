"""Application configuration.

Datastore and Redis settings (and ``AppConfig``) live once in
``openwellness_core.infrastructure.config.settings`` and are re-exported here
so existing imports keep working. This module adds the API-only settings; all
of them read the one repo-root ``.env`` through ``OpenWellnessSettings``.
"""

from pydantic import Field
from pydantic_settings import SettingsConfigDict

from openwellness_core.infrastructure.config.settings import (
    AppConfig,
    OpenWellnessSettings,
    RedisSettings,
)

__all__ = [
    "APISettings",
    "AppConfig",
    "AuthSettings",
    "RedisSettings",
    "SmtpSettings",
]


class APISettings(OpenWellnessSettings):
    """API-only knobs (not part of the core config interface)."""

    model_config = SettingsConfigDict(env_prefix="API_")

    title: str = "OpenWellness API"
    default_page_size: int = Field(default=50, ge=1, le=1000)
    max_page_size: int = Field(default=1000, ge=1, le=10000)
    time_range_max_span_days: int = 7
    # CORS — comma-separated allowed browser origins for the dashboard SPA.
    # Kept as a plain ``str`` (not ``list[str]``): pydantic-settings parses a
    # bare ``list[str]`` env value as JSON, which breaks a comma-separated
    # ``API_CORS_ALLOWED_ORIGINS``.
    cors_allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_allowed_origins.split(",") if o.strip()]


class SmtpSettings(OpenWellnessSettings):
    """Outbound SMTP settings for email delivery."""

    model_config = SettingsConfigDict(env_prefix="SMTP_")

    host: str = ""
    port: int = Field(default=587, ge=1, le=65535)
    username: str = ""
    password: str = ""
    use_tls: bool = True
    from_address: str = ""


class AuthSettings(OpenWellnessSettings):
    """Authentication knobs: JWT, OTP, rate limits, and misc behaviour flags."""

    model_config = SettingsConfigDict(env_prefix="API_AUTH_")

    # JWT
    jwt_secret: str = ""
    jwt_alg: str = "HS256"
    jwt_issuer: str = "openwellness-api"
    jwt_audience: str = "openwellness-api"
    access_ttl_seconds: int = 900
    refresh_ttl_seconds: int = 2592000
    jwt_leeway_seconds: int = 30
    # OTP
    otp_ttl_seconds: int = 600
    otp_length: int = 6
    otp_max_attempts: int = Field(default=5, ge=1)
    # Rate limits
    send_window_seconds: int = 3600
    send_max_per_window: int = 5
    resend_cooldown_seconds: int = 60
    ip_window_seconds: int = 3600
    ip_max_per_window: int = 20
    # Behaviour
    enforce_principal: bool = False
    refresh_collection: str = "auth_refresh_sessions"
    code_pepper: str = ""
    legacy_verified_id_salt: str | None = None
