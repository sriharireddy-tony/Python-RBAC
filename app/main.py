from fastapi import FastAPI

from app.api.v1 import api_router
from app.core.config import settings
from app.core.error_handlers import register_exception_handlers
from app.core.middleware import register_middleware

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
)

register_middleware(app)
register_exception_handlers(app)

app.include_router(api_router, prefix="/api/v1")


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}
