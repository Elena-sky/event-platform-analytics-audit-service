"""Application settings from environment / ``.env`` only (no in-code defaults)."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration. Every field must be set via environment or ``.env``."""

    app_name: str
    app_env: str
    app_port: int
    log_level: str

    rabbitmq_host: str
    rabbitmq_port: int
    rabbitmq_user: str
    rabbitmq_password: str

    rabbitmq_events_exchange: str
    rabbitmq_queue: str
    rabbitmq_binding_keys: str
    rabbitmq_prefetch: int

    audit_log_path: str

    redis_host: str
    redis_port: int
    idempotency_ttl_seconds: int

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def rabbitmq_url(self) -> str:
        """AMQP connection URL built from host, port, user, and password."""
        return (
            f"amqp://{self.rabbitmq_user}:{self.rabbitmq_password}"
            f"@{self.rabbitmq_host}:{self.rabbitmq_port}/"
        )

    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/0"

    @property
    def binding_keys(self) -> list[str]:
        """Parsed list of AMQP binding keys from the comma-separated env variable."""
        raw = self.rabbitmq_binding_keys.split(",")
        return [item.strip() for item in raw if item.strip()]


settings = Settings()
