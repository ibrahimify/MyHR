"""FastAPI application entry point.

Phase 1 is engineering scaffolding only. No business endpoints are
implemented yet; the only route is ``/health``. The app imports the existing
desktop packages to confirm the backend reuses ``src.database`` and
``src.services`` rather than duplicating them.
"""

# Import side effect: puts the repository root on sys.path so `src` resolves.
import app._paths  # noqa: F401

from fastapi import FastAPI

from app.config import get_settings

# Reuse the existing desktop packages. Imported here to confirm the backend
# can reference them; the model and policy modules are not re-declared.
from src.database import models as _models  # noqa: F401
from src.services import promotion_policy as _promotion_policy  # noqa: F401


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(title=settings.app_name, version="0.1.0")

    @application.get("/health", tags=["system"])
    def health() -> dict:
        return {"status": "ok"}

    return application


app = create_app()
