from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import ApiError, require_permission
from app.core.database import get_db
from app.core.permissions import ARTICLES_READ, ARTICLES_WRITE
from app.models import Article
from app.schemas.articles import ArticleCreate, ArticleResponse, ArticleUpdate

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


@router.put("/{article_id}", dependencies=[require_permission(ARTICLES_WRITE)])
def update_article(
    article_id: int, body: ArticleUpdate, db: Annotated[Session, Depends(get_db)]
) -> ArticleResponse:
    article = db.get(Article, article_id)
    if article is None:
        raise ApiError(status.HTTP_404_NOT_FOUND, "Nie znaleziono artykułu", "article_not_found")
    article.title = body.title
    article.content = body.content
    db.commit()
    return ArticleResponse.model_validate(article)
