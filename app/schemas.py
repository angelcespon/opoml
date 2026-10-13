from pydantic import BaseModel, ConfigDict, Field

class TopicCreate(BaseModel):
    model_config = ConfigDict(
        extra="forbid", str_strip_whitespace=True
    )
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
