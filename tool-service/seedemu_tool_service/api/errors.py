"""Exception handlers translating internal errors into structured HTTP responses."""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError

from seedemu_tool_service.backends import RuntimeBackendError, RuntimeTargetNotFoundError
from seedemu_tool_service.registry.registry import ToolNotFoundError


class ErrorInfo(BaseModel):
    """Machine-readable error payload."""

    code: str
    message: str
    detail: Any | None = None


class ErrorResponse(BaseModel):
    """Envelope returned for every error response."""

    error: ErrorInfo


def _error_response(status_code: int, code: str, message: str, detail: Any = None) -> JSONResponse:
    payload = ErrorResponse(error=ErrorInfo(code=code, message=message, detail=detail))
    return JSONResponse(status_code=status_code, content=payload.model_dump())


def register_exception_handlers(application: FastAPI) -> None:
    """Map internal exceptions to structured error responses."""

    @application.exception_handler(ToolNotFoundError)
    async def tool_not_found(request: Request, exc: ToolNotFoundError) -> JSONResponse:
        return _error_response(404, "tool_not_found", str(exc))

    @application.exception_handler(ValidationError)
    async def invalid_arguments(request: Request, exc: ValidationError) -> JSONResponse:
        return _error_response(
            422,
            "invalid_arguments",
            "Tool arguments failed validation.",
            detail=exc.errors(include_url=False),
        )

    @application.exception_handler(RuntimeTargetNotFoundError)
    async def target_not_found(
        request: Request, exc: RuntimeTargetNotFoundError
    ) -> JSONResponse:
        return _error_response(404, "target_not_found", str(exc))

    @application.exception_handler(RuntimeBackendError)
    async def backend_error(request: Request, exc: RuntimeBackendError) -> JSONResponse:
        return _error_response(502, "backend_error", str(exc))

    @application.exception_handler(Exception)
    async def internal_error(request: Request, exc: Exception) -> JSONResponse:
        return _error_response(500, "internal_error", "Internal server error.")
