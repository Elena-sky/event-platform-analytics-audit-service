"""ASGI + AMQP entrypoint: runs the HTTP API and the analytics consumer concurrently."""

import asyncio

import uvicorn

from app.api import app
from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.messaging.rabbitmq_consumer import AnalyticsConsumer

configure_logging()
logger = get_logger(__name__)


async def _run_consumer() -> None:
    consumer = AnalyticsConsumer()
    await consumer.start()


async def _run_api() -> None:
    config = uvicorn.Config(
        app,
        host="0.0.0.0",  # noqa: S104
        port=settings.app_port,
        log_level=settings.log_level.lower(),
    )
    server = uvicorn.Server(config)
    await server.serve()


async def main() -> None:
    logger.info(
        "Starting analytics-audit-service",
        extra={"service": settings.app_name, "env": settings.app_env},
    )
    await asyncio.gather(_run_consumer(), _run_api())


if __name__ == "__main__":
    asyncio.run(main())
