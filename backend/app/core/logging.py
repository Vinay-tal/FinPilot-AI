import logging
import re
import sys
from app.core.config import settings

CARD_PATTERN = re.compile(r'\b(?:\d{4}[ -]?){3}\d{4}\b')
PAN_PATTERN = re.compile(r'\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b')
PASSWORD_PATTERN = re.compile(r'(?i)(["\']?password["\']?\s*[:=]\s*["\']?)[^"\'\s,]+(["\']?)')
AUTH_TOKEN_PATTERN = re.compile(r'(?i)(bearer\s+)[A-Za-z0-9_-]{20,}')

class SensitiveDataFilter(logging.Filter):
    """Filters and scrubs sensitive financial/PII data from all emitted logs."""
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            msg = record.msg
            msg = CARD_PATTERN.sub('[REDACTED_CARD]', msg)
            msg = PAN_PATTERN.sub('[REDACTED_PAN]', msg)
            msg = PASSWORD_PATTERN.sub(r'\1[REDACTED_PASSWORD]\2', msg)
            msg = AUTH_TOKEN_PATTERN.sub(r'\1[REDACTED_TOKEN]', msg)
            record.msg = msg
        return True

def setup_logging():
    """Configure structured logging for FinPilot AI with sensitive data redaction."""
    log_level = logging.DEBUG if settings.DEBUG else logging.INFO
    
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    handler.addFilter(SensitiveDataFilter())

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Avoid duplicate handlers if called multiple times
    if not root_logger.handlers:
        root_logger.addHandler(handler)
    else:
        root_logger.handlers = [handler]

    # Silence overly verbose libraries in dev
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

logger = logging.getLogger("finpilot")
