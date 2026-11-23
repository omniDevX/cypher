from __future__ import annotations

import logging
import os
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text

from config.fibo_connector import FiboConnector
from app.config import get_settings_singleton

neo4jRou = APIRouter()
neo4jconn = FiboConnector()
logger = logging.getLogger("app.http")
settings = get_settings_singleton()
pg_url = os.getenv("PG_URL") or os.getenv("DATABASE_URL") or settings.TOO_SB_DB
if pg_url.startswith("postgresql+asyncpg://"):
    pg_url = pg_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)
pg_engine = create_engine(pg_url, pool_pre_ping=True)

class CypherRequest(BaseModel):
    cypher: str
    parameters: dict[str, Any] = Field(default_factory=dict)


class SavedQueryRequest(BaseModel):
    name: str
    cypher: str

@neo4jRou.post("/query")
def run_cypher(request: CypherRequest):
    return neo4jconn.run(request.cypher, request.parameters)


@neo4jRou.get("/saved-queries")
def list_saved_queries():
    with pg_engine.connect() as connection:
        rows = connection.execute(text(
            "SELECT id, name, cypher, created_at FROM saved_cypher_queries ORDER BY created_at DESC, id DESC"
        )).mappings().all()
        return [
            {
                "id": row["id"],
                "name": row["name"],
                "cypher": str(row["cypher"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]


@neo4jRou.post("/saved-queries")
def save_query(request: SavedQueryRequest):
    with pg_engine.begin() as connection:
        row = connection.execute(
            text("INSERT INTO saved_cypher_queries (name, cypher) VALUES (:name, :cypher) "
                 "RETURNING id, name, cypher, created_at"),
            {"name": request.name, "cypher": request.cypher},
        ).mappings().one()
        return dict(row)


@neo4jRou.delete("/saved-queries/{query_id}")
def delete_saved_query(query_id: int):
    with pg_engine.begin() as connection:
        result = connection.execute(
            text("DELETE FROM saved_cypher_queries WHERE id = :query_id"),
            {"query_id": query_id},
        )
        return {"deleted": result.rowcount == 1}
