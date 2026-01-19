"""
NRAIZES - Centralized Logging Module
Provides structured logging with file rotation and console output.
"""
import logging
import os
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import Optional


# Project root directory
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(PROJECT_ROOT, 'logs')


def setup_logger(
    name: str,
    level: int = logging.INFO,
    log_to_file: bool = True,
    log_to_console: bool = True,
    max_bytes: int = 5 * 1024 * 1024,  # 5 MB
    backup_count: int = 5
) -> logging.Logger:
    """
    Configure and return a logger instance with file and console handlers.

    Args:
        name: Logger name (typically __name__ of the module)
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_to_file: Whether to log to file
        log_to_console: Whether to log to console
        max_bytes: Maximum size of log file before rotation
        backup_count: Number of backup files to keep

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Avoid adding handlers multiple times
    if logger.handlers:
        return logger

    logger.setLevel(level)

    # Formatter with timestamp, level, module, and message
    formatter = logging.Formatter(
        fmt='%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Console handler
    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # File handler with rotation
    if log_to_file:
        os.makedirs(LOG_DIR, exist_ok=True)

        # Main log file
        log_file = os.path.join(LOG_DIR, 'nraizes.log')
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        # Error-only log file
        error_log_file = os.path.join(LOG_DIR, 'errors.log')
        error_handler = RotatingFileHandler(
            error_log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        logger.addHandler(error_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get or create a logger with default configuration.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Logger instance
    """
    return setup_logger(name)


class APILogger:
    """
    Specialized logger for API requests and responses.
    Provides structured logging for external API interactions.
    """

    def __init__(self, api_name: str):
        """
        Initialize API logger.

        Args:
            api_name: Name of the API (e.g., 'bling', 'gestao', 'woo')
        """
        self.logger = get_logger(f'api.{api_name}')
        self.api_name = api_name

    def log_request(self, method: str, url: str, params: Optional[dict] = None):
        """Log an outgoing API request."""
        self.logger.debug(
            f"REQUEST: {method} {url}" +
            (f" | params={params}" if params else "")
        )

    def log_response(self, status_code: int, url: str, response_time_ms: Optional[float] = None):
        """Log an API response."""
        msg = f"RESPONSE: {status_code} {url}"
        if response_time_ms:
            msg += f" | {response_time_ms:.0f}ms"

        if status_code >= 500:
            self.logger.error(msg)
        elif status_code >= 400:
            self.logger.warning(msg)
        else:
            self.logger.debug(msg)

    def log_error(self, error: Exception, context: str = ""):
        """Log an API error with context."""
        self.logger.error(
            f"API_ERROR: {self.api_name} | {context} | {type(error).__name__}: {error}"
        )

    def log_token_refresh(self, success: bool):
        """Log token refresh attempt."""
        if success:
            self.logger.info(f"TOKEN_REFRESH: {self.api_name} | Success")
        else:
            self.logger.warning(f"TOKEN_REFRESH: {self.api_name} | Failed")


class BusinessLogger:
    """
    Specialized logger for business operations.
    Provides structured logging for pricing, enrichment, and sync operations.
    """

    def __init__(self, operation: str):
        """
        Initialize business logger.

        Args:
            operation: Type of operation (e.g., 'pricing', 'enrichment', 'sync')
        """
        self.logger = get_logger(f'business.{operation}')
        self.operation = operation

    def log_start(self, description: str, **kwargs):
        """Log operation start."""
        extra = " | ".join(f"{k}={v}" for k, v in kwargs.items()) if kwargs else ""
        self.logger.info(f"START: {description}" + (f" | {extra}" if extra else ""))

    def log_success(self, description: str, **kwargs):
        """Log operation success."""
        extra = " | ".join(f"{k}={v}" for k, v in kwargs.items()) if kwargs else ""
        self.logger.info(f"SUCCESS: {description}" + (f" | {extra}" if extra else ""))

    def log_failure(self, description: str, error: Optional[Exception] = None, **kwargs):
        """Log operation failure."""
        extra = " | ".join(f"{k}={v}" for k, v in kwargs.items()) if kwargs else ""
        msg = f"FAILURE: {description}" + (f" | {extra}" if extra else "")
        if error:
            msg += f" | {type(error).__name__}: {error}"
        self.logger.error(msg)

    def log_progress(self, current: int, total: int, description: str = ""):
        """Log operation progress."""
        percent = (current / total * 100) if total > 0 else 0
        self.logger.info(f"PROGRESS: {current}/{total} ({percent:.1f}%) {description}")

    def log_price_change(self, product_id: int, old_price: float, new_price: float, reason: str):
        """Log a price change."""
        change_pct = ((new_price - old_price) / old_price * 100) if old_price > 0 else 0
        self.logger.info(
            f"PRICE_CHANGE: product_id={product_id} | "
            f"R${old_price:.2f} -> R${new_price:.2f} ({change_pct:+.1f}%) | {reason}"
        )


# Pre-configured loggers for common use cases
def get_api_logger(api_name: str) -> APILogger:
    """Get a pre-configured API logger."""
    return APILogger(api_name)


def get_business_logger(operation: str) -> BusinessLogger:
    """Get a pre-configured business logger."""
    return BusinessLogger(operation)


# Module-level logger for this module
_logger = get_logger(__name__)


if __name__ == "__main__":
    # Test logging
    logger = get_logger("test")
    logger.debug("Debug message")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")

    api_log = get_api_logger("bling")
    api_log.log_request("GET", "https://api.bling.com.br/produtos")
    api_log.log_response(200, "https://api.bling.com.br/produtos", 150.5)

    biz_log = get_business_logger("pricing")
    biz_log.log_start("Price analysis", products=100)
    biz_log.log_price_change(12345, 45.90, 42.90, "Market adjustment")
    biz_log.log_success("Price analysis complete", updated=15, skipped=85)

    print(f"\nLogs saved to: {LOG_DIR}")
