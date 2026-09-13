from typing import Literal

from pydantic import BaseModel, Field


# Author: Jin Ting Zhou
class CreateIssueRequest(BaseModel):
    title: str = Field(min_length=1)
    body: str | None = None
    labels: list[str] | None = None


class UpdateIssueRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1)
    body: str | None = None
    state: Literal["open", "closed"] | None = None


class CreateCommentRequest(BaseModel):
    body: str = Field(min_length=1)