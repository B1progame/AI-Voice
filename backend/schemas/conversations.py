from pydantic import BaseModel, Field


class ConversationCreateIn(BaseModel):
    title: str | None = Field(default=None, max_length=200)


class ConversationRenameIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)


class MessageCreateIn(BaseModel):
    role: str = Field(default="user")
    content: str = Field(min_length=1, max_length=20000)