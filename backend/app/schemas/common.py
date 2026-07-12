from pydantic import BaseModel, Field


class Source(BaseModel):
    """A user-facing excerpt from a retrieved knowledge-base document."""

    title: str = Field(default="", description="Source title or section heading")
    content: str = Field(default="", description="Retrieved source excerpt")
    file: str = Field(default="", description="Source file name")
