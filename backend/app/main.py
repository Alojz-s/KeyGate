from fastapi import FastAPI

from app.api.deps import ApiError, api_error_handler
from app.api.router import api_router
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)
app.add_exception_handler(ApiError, api_error_handler)
app.include_router(api_router)
