from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


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


def error_response(
    request: Request,
    status_code: int,
    code: str,
    message: str,
    hint: str,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "hint": hint,
                "trace_id": getattr(request.state, "trace_id", "unavailable"),
            }
        },
    )


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def api_error(request: Request, error: ApiError) -> JSONResponse:
        return error_response(
            request,
            error.status_code,
            error.code,
            error.message,
            error.hint,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(
        request: Request,
        _error: RequestValidationError,
    ) -> JSONResponse:
        return error_response(
            request,
            422,
            "invalid_request",
            "The request could not be validated",
            "Check the documented fields and try again",
        )

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, _error: Exception) -> JSONResponse:
        return error_response(
            request,
            500,
            "internal_error",
            "The vault could not complete the request",
            "Try again and share the trace id if the problem continues",
        )
