from typing import Optional, Literal

from pydantic import BaseModel, Field

# Author: Jin Ting Zhou
class CreateIssueRequest(BaseModel):
    title: str = Field(min_length=1)
    body: Optional[str] = None
    labels: Optional[list[str]] = None


class UpdateIssueRequest(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1)
    body: Optional[str] = None
    state: Optional[Literal["open", "closed"]] = None


class CreateCommentRequest(BaseModel):
    body: str = Field(min_length=1)