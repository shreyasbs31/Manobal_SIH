from __future__ import annotations

from typing import NoReturn

import structlog
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = structlog.get_logger()


class ApiError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        hint: str,
        status_code: int,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.hint = hint
        self.status_code = status_code


def _response(
    request: Request,
    *,
    status_code: int,
    code: str,
    message: str,
    hint: str,
) -> JSONResponse:
    trace_id = getattr(request.state, "trace_id", "unavailable")
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "hint": hint,
                "trace_id": trace_id,
            }
        },
        headers={"x-trace-id": trace_id},
    )


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def api_error_handler(request: Request, error: ApiError) -> JSONResponse:
        return _response(
            request,
            status_code=error.status_code,
            code=error.code,
            message=error.message,
            hint=error.hint,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request,
        _error: RequestValidationError,
    ) -> JSONResponse:
        return _response(
            request,
            status_code=422,
            code="invalid_request",
            message="The request could not be validated",
            hint="Check the documented fields and try again",
        )

    @app.exception_handler(HTTPException)
    async def http_error_handler(request: Request, error: HTTPException) -> JSONResponse:
        message = error.detail if isinstance(error.detail, str) else "Request failed"
        return _response(
            request,
            status_code=error.status_code,
            code="http_error",
            message=message,
            hint="Check the request and try again",
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, error: Exception) -> JSONResponse:
        trace_id = getattr(request.state, "trace_id", "unavailable")
        await logger.aexception(
            "request_failed",
            trace_id=trace_id,
            error_type=type(error).__name__,
        )
        return _response(
            request,
            status_code=500,
            code="internal_error",
            message="The service could not complete the request",
            hint="Try again and share the trace id if the problem continues",
        )


def raise_not_found(resource: str) -> NoReturn:
    raise ApiError(
        "not_found",
        f"{resource} was not found",
        hint="Check the identifier and your access scope",
        status_code=404,
    )
