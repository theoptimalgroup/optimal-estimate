import logging
import sys

from app.core.config import settings


def configure_logging() -> None:
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        stream=sys.stdout,
        force=True,
    )
    logging.getLogger("uvicorn.access").setLevel(level)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def configure_application_insights() -> None:
    if not settings.should_enable_application_insights:
        return

    try:
        from azure.monitor.opentelemetry import configure_azure_monitor
    except ImportError:
        logging.getLogger(__name__).warning(
            "Application Insights enabled but azure-monitor-opentelemetry is not installed"
        )
        return

    configure_azure_monitor(
        connection_string=settings.applicationinsights_connection_string,
        logger_name="estimate_tool",
    )
    logging.getLogger(__name__).info("Application Insights telemetry enabled")
