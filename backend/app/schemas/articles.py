from pydantic import BaseModel, ConfigDict, Field


class ArticleCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1)


class ArticleUpdate(ArticleCreate):
    pass


class ArticleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    content: str
