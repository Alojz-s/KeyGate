import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health")
def health(response: Response, db: Annotated[Session, Depends(get_db)]) -> dict[str, str]:
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        logger.exception("Health check: baza danych niedostępna")
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "ok", "database": "error"}
    return {"status": "ok", "database": "ok"}
