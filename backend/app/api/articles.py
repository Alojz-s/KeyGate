from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.database import get_db
from app.core.permissions import ARTICLES_READ, ARTICLES_WRITE
from app.models import Article
from app.schemas.articles import ArticleCreate, ArticleResponse

router = APIRouter(prefix="/articles", tags=["articles"])


@router.get("", dependencies=[require_permission(ARTICLES_READ)])
def list_articles(db: Annotated[Session, Depends(get_db)]) -> list[ArticleResponse]:
    articles = db.scalars(select(Article).order_by(Article.id))
    return [ArticleResponse.model_validate(article) for article in articles]


@router.post("", dependencies=[require_permission(ARTICLES_WRITE)])
def create_article(body: ArticleCreate, db: Annotated[Session, Depends(get_db)]) -> ArticleResponse:
    article = Article(title=body.title, content=body.content)
    db.add(article)
    db.commit()
    return ArticleResponse.model_validate(article)
