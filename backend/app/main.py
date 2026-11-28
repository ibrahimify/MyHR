"""FastAPI application entry point.

The app imports the existing desktop packages and exposes web routes through
shared service modules instead of duplicating business logic.
"""

# Import side effect: puts the repository root on sys.path so `src` resolves.
import app._paths  # noqa: F401

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers.employees import router as employee_router

# Reuse the existing desktop packages. Imported here to confirm the backend
# can reference them; the model and policy modules are not re-declared.
from src.database import models as _models  # noqa: F401
from src.services import promotion_policy as _promotion_policy  # noqa: F401


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="MyHR web API. Business endpoints use the /api prefix.",
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )
    application.include_router(employee_router)

    @application.get("/health", tags=["system"])
    def health() -> dict:
        return {"status": "ok"}

    return application


app = create_app()
