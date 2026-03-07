"""
Error handling middleware and utilities
"""
import traceback
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from loguru import logger


def setup_error_handlers(app: FastAPI):
    """Setup global error handlers for FastAPI app."""

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """Handle uncaught exceptions."""
        # Log the full traceback
        logger.error(f"Unhandled exception: {exc}")
        logger.debug(traceback.format_exc())

        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "message": str(exc),
                "path": str(request.url),
            }
        )

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        """Handle ValueError exceptions."""
        logger.warning(f"ValueError: {exc}")
        return JSONResponse(
            status_code=400,
            content={
                "error": "Bad request",
                "message": str(exc),
            }
        )


class ErrorTracker:
    """Track and aggregate errors for monitoring."""

    def __init__(self, max_history: int = 100):
        self.max_history = max_history
        self.errors: list[dict] = []

    def record_error(
        self,
        error: Exception,
        context: Optional[dict] = None
    ):
        """Record an error with context."""
        import datetime

        error_record = {
            "timestamp": datetime.datetime.now().isoformat(),
            "type": type(error).__name__,
            "message": str(error),
            "context": context or {},
        }

        self.errors.append(error_record)

        # Keep only recent errors
        if len(self.errors) > self.max_history:
            self.errors = self.errors[-self.max_history:]

    def get_recent_errors(self, count: int = 10) -> list[dict]:
        """Get recent errors."""
        return self.errors[-count:]

    def get_error_summary(self) -> dict:
        """Get error summary statistics."""
        if not self.errors:
            return {"total": 0, "by_type": {}}

        by_type = {}
        for error in self.errors:
            error_type = error["type"]
            by_type[error_type] = by_type.get(error_type, 0) + 1

        return {
            "total": len(self.errors),
            "by_type": by_type,
        }


# Global error tracker instance
error_tracker = ErrorTracker()


def track_error(error: Exception, context: Optional[dict] = None):
    """Helper function to track errors globally."""
    error_tracker.record_error(error, context)
