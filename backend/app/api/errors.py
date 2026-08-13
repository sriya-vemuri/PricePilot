"""HTTP error mapping for the PricePilot API.

Validation errors (invalid body, UUID, query params) are normalized to
ErrorResponse with HTTP 422 and error code `validation_error`.
Pydantic/FastAPI 422 loc/msg/type details are included; input values are not.
"""

from uuid import UUID

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.clients.tavily import TavilyNotConfiguredError
from app.models.errors import ErrorResponse
from app.repositories.errors import DatabaseError
from app.services.errors import PricingCalculationError


class AnalysisNotFoundError(Exception):
    def __init__(self, analysis_id: UUID) -> None:
        self.analysis_id = analysis_id
        super().__init__("Analysis not found")


def _error_response(status_code: int, error: str, message: str, details: dict | None = None) -> JSONResponse:
    payload = ErrorResponse(error=error, message=message, details=details)
    return JSONResponse(status_code=status_code, content=payload.model_dump(exclude_none=True))


async def tavily_not_configured_handler(request: Request, exc: TavilyNotConfiguredError) -> JSONResponse:
    return _error_response(
        503,
        "tavily_not_configured",
        "Tavily is not configured",
    )


async def pricing_calculation_handler(request: Request, exc: PricingCalculationError) -> JSONResponse:
    return _error_response(
        500,
        "pricing_calculation_error",
        "Pricing calculation failed",
    )


async def database_error_handler(request: Request, exc: DatabaseError) -> JSONResponse:
    return _error_response(
        500,
        "database_error",
        "A database error occurred",
    )


async def analysis_not_found_handler(request: Request, exc: AnalysisNotFoundError) -> JSONResponse:
    return _error_response(
        404,
        "analysis_not_found",
        "Analysis not found",
        details={"analysis_id": str(exc.analysis_id)},
    )


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = [
        {
            "loc": [str(part) for part in err.get("loc", ())],
            "msg": err.get("msg"),
            "type": err.get("type"),
        }
        for err in exc.errors()
    ]
    return _error_response(
        422,
        "validation_error",
        "Request validation failed",
        details={"errors": errors},
    )


def register_exception_handlers(application: FastAPI) -> None:
    application.add_exception_handler(TavilyNotConfiguredError, tavily_not_configured_handler)
    application.add_exception_handler(PricingCalculationError, pricing_calculation_handler)
    application.add_exception_handler(DatabaseError, database_error_handler)
    application.add_exception_handler(AnalysisNotFoundError, analysis_not_found_handler)
    application.add_exception_handler(RequestValidationError, validation_error_handler)
