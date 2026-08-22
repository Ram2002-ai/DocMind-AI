"""Structured logging configuration"""
import logging
import json
from datetime import datetime
import uuid

def setup_logging():
    """Configure structured logging for the application"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        handlers=[
            logging.StreamHandler(),
        ]
    )


class StructuredLogger:
    """Structured logger for consistent log formatting"""

    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.request_id = None

    def set_request_id(self, request_id: str = None):
        """Set the request ID for correlation"""
        self.request_id = request_id or str(uuid.uuid4())

    def _format_log(self, level: str, message: str, **extra) -> str:
        """Format log message with metadata"""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level,
            "message": message,
            "request_id": self.request_id,
            **extra
        }
        return json.dumps(log_data, default=str)

    @staticmethod
    def _render(message: str, args: tuple) -> str:
        """Support stdlib-style positional %-formatting, e.g.
        logger.error("failed: %s", exc), in addition to plain strings.
        Falls back to appending the args if %-formatting doesn't apply
        (e.g. wrong number/type of placeholders) so a logging call can
        never itself raise and mask the real error being logged.
        """
        if not args:
            return message
        try:
            return message % args
        except Exception:
            return f"{message} {args}"

    def info(self, message: str, *args, **extra):
        """Log info message"""
        self.logger.info(self._format_log("INFO", self._render(message, args), **extra))

    def warning(self, message: str, *args, **extra):
        """Log warning message"""
        self.logger.warning(self._format_log("WARNING", self._render(message, args), **extra))

    def error(self, message: str, *args, **extra):
        """Log error message"""
        self.logger.error(self._format_log("ERROR", self._render(message, args), **extra))

    def debug(self, message: str, *args, **extra):
        """Log debug message"""
        self.logger.debug(self._format_log("DEBUG", self._render(message, args), **extra))


def get_logger(name: str) -> StructuredLogger:
    """Get a structured logger instance"""
    return StructuredLogger(name)
