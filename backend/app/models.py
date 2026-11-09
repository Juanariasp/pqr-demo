from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Credentials(BaseModel):
    email: str = Field(min_length=5, max_length=254, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    password: str = Field(min_length=8, max_length=128)


class PqrInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=5, max_length=120)
    text: str = Field(min_length=20, max_length=20000)
    upload_id: str | None = Field(default=None, pattern=r"^[a-f0-9]{32}$")

    @field_validator("title", "text", mode="before")
    @classmethod
    def trim(cls, value):
        return value.strip() if isinstance(value, str) else value


class Classification(BaseModel):
    category: Literal["peticion", "queja", "reclamo", "otra"]
    reason: str = Field(min_length=5, max_length=1000)


class Analysis(BaseModel):
    priority: Literal["alta", "media", "baja"]
    topic: str = Field(min_length=3, max_length=200)
    summary: str = Field(min_length=10, max_length=1500)
    relevant_data: list[str] = Field(max_length=12)


class SuggestedResponse(BaseModel):
    response: str = Field(min_length=20, max_length=4000)


class Result(Classification, Analysis, SuggestedResponse):
    engine: Literal["rules", "google-adk"]
    model: str | None = None
