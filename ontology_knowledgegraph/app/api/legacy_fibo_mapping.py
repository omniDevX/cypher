from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator, model_validator
from sqlalchemy import create_engine, text

from ..sql_lineage_parser import load_sql_lineage

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

database_url = os.getenv("PG_URL") or os.getenv("DATABASE_URL")
if not database_url:
    raise RuntimeError("Set PG_URL or DATABASE_URL for legacy-to-FIBO mappings")
if database_url.startswith("postgresql+asyncpg://"):
    database_url = database_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)

engine = create_engine(database_url, pool_pre_ping=True)
legacyFiboRouter = APIRouter(prefix="/legacy-fibo-mapping", tags=["Legacy to FIBO Mapping"])
LOAN_MODEL_PATH = PROJECT_ROOT / "fibo" / "loan" / "neo4j_importer_model.json"


def _fibo_vocabulary() -> dict[str, list[dict[str, str]]]:
    model = json.loads(LOAN_MODEL_PATH.read_text(encoding="utf-8"))
    schema = model["dataModel"]["graphSchemaRepresentation"]["graphSchema"]
    return {
        "classes": [
            {"name": item["token"], "description": item.get("description", "")}
            for item in schema.get("nodeLabels", [])
        ],
        "properties": [
            {
                "name": f"{item['token']}.{prop['token']}",
                "domain": item["token"],
                "description": prop.get("description", ""),
            }
            for item in schema.get("nodeLabels", [])
            for prop in item.get("properties", [])
        ],
        "relationships": [
            {"name": item["token"], "description": item.get("description", "")}
            for item in schema.get("relationshipTypes", [])
        ],
    }


@legacyFiboRouter.get("/targets")
def list_fibo_targets():
    return _fibo_vocabulary()


@legacyFiboRouter.get("/sources")
def list_legacy_sources():
    source_file, _, queries = load_sql_lineage()
    elements = []
    for query in queries:
        query_id = str(query["queryId"])
        elements.append({
            "sourceRef": query["sourceRef"],
            "sourceKind": "entity",
            "sourceTable": query_id,
            "sourceField": None,
            "graphElement": str(query["name"]),
            "description": f"SQL result set from {', '.join(query['tables'])}; {len(query['outputs'])} output columns.",
            "fiboTargetKind": "class",
        })
        for clause in query["clauses"]:
            if clause["clauseKind"] != "join":
                continue
            source_columns = clause["sourceColumns"]
            source_names = [f"{column['table']}.{column['field']}" for column in source_columns]
            elements.append({
                "sourceRef": clause["sourceRef"],
                "sourceKind": "relationship",
                "sourceTable": query_id,
                "sourceField": clause["sourceRef"],
                "graphElement": clause["expression"],
                "description": f"SQL join between {', '.join(source_names)}.",
                "fiboTargetKind": "relationship",
            })
        for output in query["outputs"]:
            source_columns = output["sourceColumns"]
            source_names = [f"{column['table']}.{column['field']}" for column in source_columns]
            elements.append({
                "sourceRef": output["sourceRef"],
                "sourceKind": "field",
                "sourceTable": query_id,
                "sourceField": output["name"],
                "graphElement": output["name"],
                "description": (
                    f"{output['expressionKind'].capitalize()} output: {output['sqlExpression']}. "
                    f"Input columns: {', '.join(source_names) if source_names else 'none identified'}"
                ),
                "fiboTargetKind": "property",
                "semanticExample": f"{query['name']} · {output['expressionKind']} result column",
            })

    return {
        "sourceSystem": "Legacy SQL transformation outputs",
        "sourceFile": f"fibo/sql/{source_file}",
        "elements": elements,
    }


class MappingInput(BaseModel):
    source_ref: str
    source_kind: Literal["entity", "field", "relationship"]
    source_table: str
    source_field: str | None = None
    graph_element: str
    fibo_target_kind: Literal["class", "property", "relationship"]
    fibo_iri: str | None = None
    fibo_label: str
    rationale: str = ""
    is_cde: bool = False
    cde_definition: str | None = None
    review_status: Literal["draft", "reviewed"] = "draft"

    @field_validator("fibo_iri")
    @classmethod
    def require_absolute_iri_when_provided(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        value = value.strip()
        if not value.startswith(("https://", "http://")):
            raise ValueError("FIBO IRI must be an absolute HTTP or HTTPS URI")
        return value

    @model_validator(mode="after")
    def validate_source_target_and_cde(self) -> MappingInput:
        expected_target = {
            "entity": "class",
            "field": "property",
            "relationship": "relationship",
        }[self.source_kind]
        if self.fibo_target_kind != expected_target:
            raise ValueError(f"{self.source_kind} sources must map to a FIBO {expected_target}")
        vocabulary_key = {
            "class": "classes",
            "property": "properties",
            "relationship": "relationships",
        }[self.fibo_target_kind]
        valid_names = {item["name"] for item in _fibo_vocabulary()[vocabulary_key]}
        if self.fibo_label not in valid_names:
            raise ValueError(f"Choose a {self.fibo_target_kind} label from the current loan graph vocabulary")
        _, _, queries = load_sql_lineage()
        valid_sources = {
            query["sourceRef"]: ("entity", query["queryId"], None)
            for query in queries
        }
        valid_sources.update({
            output["sourceRef"]: ("field", query["queryId"], output["name"])
            for query in queries
            for output in query["outputs"]
        })
        valid_sources.update({
            clause["sourceRef"]: ("relationship", query["queryId"], clause["sourceRef"])
            for query in queries
            for clause in query["clauses"]
            if clause["clauseKind"] == "join"
        })
        expected_source = valid_sources.get(self.source_ref)
        actual_source = (self.source_kind, self.source_table, self.source_field)
        if expected_source is None or actual_source != expected_source:
            raise ValueError("Choose a query or output column from the current fibo/sql/sql.sql source")
        if self.is_cde and self.source_kind != "field":
            raise ValueError("CDE designation applies to legacy fields")
        if self.is_cde and not (self.cde_definition or "").strip():
            raise ValueError("Enter a CDE definition when marking a field as a CDE")
        if not self.is_cde:
            self.cde_definition = None
        return self


def _mapping_values(mapping: MappingInput) -> dict[str, object]:
    return mapping.model_dump()


@legacyFiboRouter.get("/mappings")
def list_mappings():
    with engine.connect() as connection:
        rows = connection.execute(text(
            "SELECT id, source_ref, source_kind, source_table, source_field, graph_element, "
            "fibo_target_kind, fibo_iri, fibo_label, rationale, is_cde, cde_definition, "
            "review_status, created_at, updated_at "
            "FROM legacy_fibo_mappings ORDER BY source_table, source_field NULLS FIRST, id"
        )).mappings().all()
        return [dict(row) for row in rows]


@legacyFiboRouter.post("/mappings")
def create_mapping(mapping: MappingInput):
    values = _mapping_values(mapping)
    with engine.begin() as connection:
        row = connection.execute(
            text(
                "INSERT INTO legacy_fibo_mappings "
                "(source_ref, source_kind, source_table, source_field, graph_element, "
                "fibo_target_kind, fibo_iri, fibo_label, rationale, is_cde, cde_definition, review_status) "
                "VALUES (:source_ref, :source_kind, :source_table, :source_field, :graph_element, "
                ":fibo_target_kind, :fibo_iri, :fibo_label, :rationale, :is_cde, :cde_definition, :review_status) "
                "RETURNING *"
            ),
            values,
        ).mappings().one()
        return dict(row)


@legacyFiboRouter.put("/mappings/{mapping_id}")
def update_mapping(mapping_id: int, mapping: MappingInput):
    values = _mapping_values(mapping)
    values["mapping_id"] = mapping_id
    with engine.begin() as connection:
        row = connection.execute(
            text(
                "UPDATE legacy_fibo_mappings SET source_ref=:source_ref, source_kind=:source_kind, "
                "source_table=:source_table, source_field=:source_field, graph_element=:graph_element, "
                "fibo_target_kind=:fibo_target_kind, fibo_iri=:fibo_iri, fibo_label=:fibo_label, "
                "rationale=:rationale, is_cde=:is_cde, cde_definition=:cde_definition, "
                "review_status=:review_status, updated_at=now() WHERE id=:mapping_id RETURNING *"
            ),
            values,
        ).mappings().first()
        if row is None:
            raise HTTPException(status_code=404, detail="Mapping not found")
        return dict(row)


@legacyFiboRouter.delete("/mappings/{mapping_id}")
def delete_mapping(mapping_id: int):
    with engine.begin() as connection:
        result = connection.execute(
            text("DELETE FROM legacy_fibo_mappings WHERE id=:mapping_id"),
            {"mapping_id": mapping_id},
        )
        if result.rowcount != 1:
            raise HTTPException(status_code=404, detail="Mapping not found")
        return {"deleted": True}
