from typing import Any

from pydantic import BaseModel, Field


class CypherRequest(BaseModel):
    cypher: str
    parameters: dict[str, Any] = Field(default_factory=dict)


class SavedCypherRequest(BaseModel):
    name: str
    cypher: str
