from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine, text

from .neo4j.api_loan import neo4jconn
from app.sql_lineage_parser import PROJECT_ROOT, load_sql_lineage, parse_sql_lineage

sqlLineageRouter = APIRouter(prefix="/sql-lineage", tags=["SQL Lineage"])
MODEL_PATH = PROJECT_ROOT / "fibo" / "loan" / "neo4j_importer_model.json"

database_url = os.getenv("PG_URL") or os.getenv("DATABASE_URL")
if not database_url:
    from app.config import get_settings_singleton
    database_url = get_settings_singleton().TOO_SB_DB
if database_url.startswith("postgresql+asyncpg://"):
    database_url = database_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)
pg_engine = create_engine(database_url, pool_pre_ping=True)
SOURCE_KEY = "fibo/sql/sql.sql"


class SavedSqlQueryRequest(BaseModel):
    name: str
    sql: str


class SqlLineageRequest(BaseModel):
    sql: str


def _term_catalog() -> tuple[list[dict[str, Any]], list[dict[str, str]], list[dict[str, str]]]:
    model = json.loads(MODEL_PATH.read_text(encoding="utf-8"))
    data_model = model["dataModel"]
    schema = data_model["graphSchemaRepresentation"]["graphSchema"]
    labels = {item["$id"]: item["token"] for item in schema["nodeLabels"]}
    node_types = {item["$id"]: item for item in schema["nodeObjectTypes"]}
    relationship_types = {item["$id"]: item for item in schema["relationshipTypes"]}

    terms: list[dict[str, Any]] = []
    property_links: list[dict[str, str]] = []
    for node_label in schema["nodeLabels"]:
        class_name = node_label["token"]
        terms.append({
            "termKey": f"class:{class_name}",
            "termKind": "class",
            "name": class_name,
            "description": node_label.get("description", ""),
        })
        for prop in node_label.get("properties", []):
            property_name = f"{class_name}.{prop['token']}"
            terms.append({
                "termKey": f"property:{property_name}",
                "termKind": "property",
                "name": property_name,
                "domain": class_name,
                "description": prop.get("description", ""),
            })
            property_links.append({"class": class_name, "property": property_name})

    relationship_links: list[dict[str, str]] = []
    for relationship in schema["relationshipTypes"]:
        name = relationship["token"]
        terms.append({
            "termKey": f"relationship:{name}",
            "termKind": "relationship",
            "name": name,
            "description": relationship.get("description", ""),
        })

    for relationship_object in schema["relationshipObjectTypes"]:
        relationship_id = relationship_object["type"]["$ref"].removeprefix("#")
        relationship_name = relationship_types[relationship_id]["token"]
        from_type = node_types[relationship_object["from"]["$ref"].removeprefix("#")]
        to_type = node_types[relationship_object["to"]["$ref"].removeprefix("#")]
        from_label = labels[from_type["labels"][0]["$ref"].removeprefix("#")]
        to_label = labels[to_type["labels"][0]["$ref"].removeprefix("#")]
        relationship_links.append({
            "fromClass": from_label,
            "relationship": relationship_name,
            "toClass": to_label,
        })
    return terms, property_links, relationship_links


def _source_and_graph_payload(
    sql: str | None = None,
    file_name: str | None = None,
) -> tuple[str, str, str, list[dict[str, Any]], list[dict[str, Any]], list[dict[str, str]]]:
    if sql is None:
        file_name, sql, queries = load_sql_lineage()
    else:
        file_name = file_name or "saved-query.sql"
        queries = parse_sql_lineage(sql)
        if queries:
            queries[0]["name"] = Path(file_name).stem
    source_hash = hashlib.sha256(sql.encode("utf-8")).hexdigest()
    input_fields: dict[str, dict[str, str]] = {}
    tables: set[str] = set()
    for query in queries:
        for column in query["referencedColumns"]:
            input_fields[column["sourceRef"]] = column
            tables.add(column["table"])
    return file_name, sql, source_hash, queries, list(input_fields.values()), [{"name": table} for table in sorted(tables)]


def _mapping_target_key(mapping: dict[str, Any]) -> str:
    kind = mapping["fibo_target_kind"]
    label = mapping["fibo_label"]
    return f"{kind}:{label}"


def _mapping_rows() -> list[dict[str, Any]]:
    with pg_engine.connect() as connection:
        rows = connection.execute(text(
            "SELECT id, source_ref, source_kind, fibo_target_kind, fibo_label, rationale, "
            "is_cde, cde_definition, review_status FROM legacy_fibo_mappings"
        )).mappings().all()
    return [dict(row) for row in rows]


def _interactive_mapping_rows(sql: str) -> list[dict[str, Any]]:
    source_queries = load_sql_lineage()[2]
    interactive_queries = parse_sql_lineage(sql)
    source_queries_by_statement = {query["statement"]: query for query in source_queries}
    interactive_source_refs: dict[str, str] = {}

    for interactive_query in interactive_queries:
        source_query = source_queries_by_statement.get(interactive_query["statement"])
        if source_query is None:
            continue

        interactive_source_refs[source_query["sourceRef"]] = interactive_query["sourceRef"]
        source_outputs = {output["name"]: output for output in source_query["outputs"]}
        interactive_outputs = {output["name"]: output for output in interactive_query["outputs"]}
        for name in source_outputs.keys() & interactive_outputs.keys():
            interactive_source_refs[source_outputs[name]["sourceRef"]] = interactive_outputs[name]["sourceRef"]

        source_joins = [clause for clause in source_query["clauses"] if clause["clauseKind"] == "join"]
        interactive_joins = [clause for clause in interactive_query["clauses"] if clause["clauseKind"] == "join"]
        for source_join, interactive_join in zip(source_joins, interactive_joins):
            interactive_source_refs[source_join["sourceRef"]] = interactive_join["sourceRef"]

    return [
        {**mapping, "source_ref": interactive_source_refs[mapping["source_ref"]]}
        for mapping in _mapping_rows()
        if mapping["source_ref"] in interactive_source_refs
    ]


def _ensure_graph_constraints() -> None:
    neo4jconn.run(
        "CREATE CONSTRAINT legacy_sql_source_key IF NOT EXISTS "
        "FOR (source:LegacySqlSource) REQUIRE source.sourceKey IS UNIQUE"
    )
    neo4jconn.run(
        "CREATE CONSTRAINT legacy_sql_element_key IF NOT EXISTS "
        "FOR (element:LegacySqlElement) REQUIRE (element.sourceKey, element.sourceRef) IS UNIQUE"
    )
    neo4jconn.run(
        "CREATE CONSTRAINT ontology_term_key IF NOT EXISTS "
        "FOR (term:OntologyTerm) REQUIRE term.termKey IS UNIQUE"
    )


def _sync_to_graph(
    source_key: str = SOURCE_KEY,
    sql: str | None = None,
    file_name: str | None = None,
    mappings: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    file_name, sql, source_hash, queries, input_fields, source_tables = _source_and_graph_payload(sql, file_name)
    if mappings is None:
        mappings = _mapping_rows() if source_key == SOURCE_KEY else []
    terms, property_links, relationship_links = _term_catalog()
    term_keys = {term["termKey"] for term in terms}

    query_refs = {query["sourceRef"] for query in queries}
    output_refs = {
        output["sourceRef"] for query in queries for output in query["outputs"]
    }
    clause_refs = {
        clause["sourceRef"] for query in queries for clause in query["clauses"]
        if clause["clauseKind"] == "join"
    }
    source_refs = query_refs | output_refs | clause_refs | {field["sourceRef"] for field in input_fields}
    valid_mappings: list[dict[str, Any]] = []
    unresolved: list[dict[str, str]] = []
    for mapping in mappings:
        target_key = _mapping_target_key(mapping)
        if mapping["source_ref"] not in source_refs:
            reason = "Source is not present in sql.sql" if source_key == SOURCE_KEY else f"Source is not present in {file_name}"
            unresolved.append({"sourceRef": mapping["source_ref"], "reason": reason})
        elif target_key not in term_keys:
            unresolved.append({"sourceRef": mapping["source_ref"], "reason": f"Unknown graph target {target_key}"})
        else:
            valid_mappings.append(mapping)

    mapping_by_ref = {mapping["source_ref"]: mapping for mapping in valid_mappings}
    rows: list[dict[str, Any]] = []
    edges: dict[str, list[dict[str, str]]] = {
        "HAS_QUERY": [], "RETURNS": [], "BELONGS_TO": [], "DERIVES_FROM": [], "READS_FROM": [],
        "HAS_CLAUSE": [], "REFERENCES_COLUMN": [],
    }

    for table in source_tables:
        table_name = table["name"]
        rows.append({
            "sourceRef": f"table|{table_name}", "elementKind": "input_table", "name": table_name,
            "tableName": table_name, "active": True,
        })
    for field in input_fields:
        rows.append({
            "sourceRef": field["sourceRef"], "elementKind": "input_column",
            "name": f"{field['table']}.{field['field']}", "tableName": field["table"],
            "columnName": field["field"], "active": True,
        })
        edges["BELONGS_TO"].append({"fromRef": field["sourceRef"], "toRef": f"table|{field['table']}"})

    for query in queries:
        query_id = query["queryId"]
        query_mapping = mapping_by_ref.get(query["sourceRef"])
        rows.append({
            "sourceRef": query["sourceRef"], "elementKind": "query", "name": query["name"],
            "queryId": query_id, "queryNumber": query["queryNumber"], "lineStart": query["lineStart"],
            "sqlStatement": query["statement"], "tables": query["tables"], "sourceHash": source_hash,
            "clauseCount": len(query["clauses"]),
            "active": True, "fiboLabel": query_mapping["fibo_label"] if query_mapping else None,
            "fiboTargetKind": query_mapping["fibo_target_kind"] if query_mapping else None,
            "reviewStatus": query_mapping["review_status"] if query_mapping else None,
        })
        edges["HAS_QUERY"].append({"fromRef": "source|sql", "toRef": query["sourceRef"]})
        for clause in query["clauses"]:
            clause_mapping = mapping_by_ref.get(clause["sourceRef"])
            rows.append({
                "sourceRef": clause["sourceRef"], "elementKind": "sql_clause",
                "name": clause["clauseKind"].capitalize(), "queryId": query_id,
                "clauseKind": clause["clauseKind"], "sqlExpression": clause["expression"],
                "fiboLabel": clause_mapping["fibo_label"] if clause_mapping else None,
                "fiboTargetKind": clause_mapping["fibo_target_kind"] if clause_mapping else None,
                "reviewStatus": clause_mapping["review_status"] if clause_mapping else None,
                "mappingRationale": clause_mapping["rationale"] if clause_mapping else None,
                "active": True,
            })
            edges["HAS_CLAUSE"].append({"fromRef": query["sourceRef"], "toRef": clause["sourceRef"]})
            for source in clause["sourceColumns"]:
                edges["REFERENCES_COLUMN"].append({"fromRef": clause["sourceRef"], "toRef": source["sourceRef"]})
        for output in query["outputs"]:
            output_mapping = mapping_by_ref.get(output["sourceRef"])
            rows.append({
                "sourceRef": output["sourceRef"], "elementKind": "output_column",
                "name": output["name"], "queryId": query_id, "position": output["position"],
                "sqlExpression": output["sqlExpression"], "expressionKind": output["expressionKind"],
                "sourceHash": source_hash, "active": True,
                "fiboLabel": output_mapping["fibo_label"] if output_mapping else None,
                "fiboTargetKind": output_mapping["fibo_target_kind"] if output_mapping else None,
                "reviewStatus": output_mapping["review_status"] if output_mapping else None,
                "isCde": bool(output_mapping["is_cde"]) if output_mapping else False,
                "cdeDefinition": output_mapping["cde_definition"] if output_mapping else None,
                "mappingRationale": output_mapping["rationale"] if output_mapping else None,
            })
            edges["RETURNS"].append({"fromRef": query["sourceRef"], "toRef": output["sourceRef"]})
            for source in output["sourceColumns"]:
                edges["DERIVES_FROM"].append({"fromRef": output["sourceRef"], "toRef": source["sourceRef"]})
            for source in query["referencedColumns"]:
                edges["READS_FROM"].append({"fromRef": query["sourceRef"], "toRef": source["sourceRef"]})

    ontology_terms, property_links, relationship_links = _term_catalog()
    statements: list[tuple[str, dict[str, Any]]] = [
        (
            "MATCH (n:LegacySqlElement {sourceKey:$sourceKey}) SET n.active=false",
            {"sourceKey": source_key},
        ),
        (
            "MERGE (source:LegacySqlSource {sourceKey:$sourceKey}) "
            "SET source.fileName=$fileName, source.sha256=$sourceHash, source.sqlText=$sqlText, "
            "source.syncedAt=$syncedAt, source.active=true",
            {
                "sourceKey": source_key, "fileName": file_name, "sourceHash": source_hash,
                "sqlText": sql,
                "syncedAt": datetime.now(timezone.utc).isoformat(),
            },
        ),
        (
            "UNWIND $rows AS row MERGE (n:LegacySqlElement {sourceKey:$sourceKey, sourceRef:row.sourceRef}) "
            "SET n += row",
            {"sourceKey": source_key, "rows": rows},
        ),
        (
            "UNWIND $terms AS row MERGE (term:OntologyTerm {termKey:row.termKey}) SET term += row",
            {"terms": ontology_terms},
        ),
    ]
    for relationship_type in (
        "HAS_QUERY", "RETURNS", "BELONGS_TO", "DERIVES_FROM", "READS_FROM",
        "HAS_CLAUSE", "REFERENCES_COLUMN", "MAPS_TO", "PROPOSES_MAPPING_TO",
    ):
        statements.append((
            f"MATCH ()-[r:{relationship_type} {{sourceKey:$sourceKey}}]->() DELETE r",
            {"sourceKey": source_key},
        ))

    edge_queries = {
        "HAS_QUERY": "MATCH (source:LegacySqlSource {sourceKey:$sourceKey}) MATCH (a:LegacySqlElement {sourceKey:$sourceKey,sourceRef:edge.fromRef}) MATCH (b:LegacySqlElement {sourceKey:$sourceKey,sourceRef:edge.toRef}) MERGE (source)-[r:HAS_QUERY {sourceKey:$sourceKey}]->(b)",
        "RETURNS": "MATCH (a:LegacySqlElement {sourceKey:$sourceKey,sourceRef:edge.fromRef}) MATCH (b:LegacySqlElement {sourceKey:$sourceKey,sourceRef:edge.toRef}) MERGE (a)-[r:RETURNS {sourceKey:$sourceKey}]->(b)",
        "BELONGS_TO": "MATCH (a:LegacySqlElement {sourceKey:$sourceKey,sourceRef:edge.fromRef}) MATCH (b:LegacySqlElement {sourceKey:$sourceKey,sourceRef:edge.toRef}) MERGE (a)-[r:BELONGS_TO {sourceKey:$sourceKey}]->(b)",
        "DERIVES_FROM": "MATCH (a:LegacySqlElement {sourceKey:$sourceKey,sourceRef:edge.fromRef}) MATCH (b:LegacySqlElement {sourceKey:$sourceKey,sourceRef:edge.toRef}) MERGE (a)-[r:DERIVES_FROM {sourceKey:$sourceKey}]->(b)",
        "READS_FROM": "MATCH (a:LegacySqlElement {sourceKey:$sourceKey,sourceRef:edge.fromRef}) MATCH (b:LegacySqlElement {sourceKey:$sourceKey,sourceRef:edge.toRef}) MERGE (a)-[r:READS_FROM {sourceKey:$sourceKey}]->(b)",
        "HAS_CLAUSE": "MATCH (a:LegacySqlElement {sourceKey:$sourceKey,sourceRef:edge.fromRef}) MATCH (b:LegacySqlElement {sourceKey:$sourceKey,sourceRef:edge.toRef}) MERGE (a)-[r:HAS_CLAUSE {sourceKey:$sourceKey}]->(b)",
        "REFERENCES_COLUMN": "MATCH (a:LegacySqlElement {sourceKey:$sourceKey,sourceRef:edge.fromRef}) MATCH (b:LegacySqlElement {sourceKey:$sourceKey,sourceRef:edge.toRef}) MERGE (a)-[r:REFERENCES_COLUMN {sourceKey:$sourceKey}]->(b)",
    }
    for edge_type, edge_rows in edges.items():
        if edge_type == "HAS_QUERY":
            statement = (
                "UNWIND $edges AS edge MATCH (source:LegacySqlSource {sourceKey:$sourceKey}) "
                "MATCH (query:LegacySqlElement {sourceKey:$sourceKey,sourceRef:edge.toRef}) "
                "MERGE (source)-[r:HAS_QUERY {sourceKey:$sourceKey}]->(query)"
            )
        else:
            statement = f"UNWIND $edges AS edge {edge_queries[edge_type]}"
        statements.append((statement, {"sourceKey": source_key, "edges": edge_rows}))

    reviewed_mappings = []
    proposed_mappings = []
    for mapping in valid_mappings:
        graph_mapping = {
            "sourceRef": mapping["source_ref"],
            "termKey": _mapping_target_key(mapping),
            "reviewStatus": mapping["review_status"],
            "rationale": mapping["rationale"],
            "mappingId": mapping["id"],
        }
        (reviewed_mappings if mapping["review_status"] == "reviewed" else proposed_mappings).append(graph_mapping)
    for relationship_type, mapping_rows in (("MAPS_TO", reviewed_mappings), ("PROPOSES_MAPPING_TO", proposed_mappings)):
        statements.append((
            "UNWIND $mappings AS mapping "
            "MATCH (source:LegacySqlElement {sourceKey:$sourceKey,sourceRef:mapping.sourceRef}) "
            "MATCH (term:OntologyTerm {termKey:mapping.termKey}) "
            f"MERGE (source)-[r:{relationship_type} {{sourceKey:$sourceKey}}]->(term) "
            "SET r += mapping",
            {"sourceKey": source_key, "mappings": mapping_rows},
        ))

    statements.append((
        "UNWIND $links AS link "
        "MATCH (class:OntologyTerm {termKey:link.classKey}) "
        "MATCH (prop:OntologyTerm {termKey:link.propertyKey}) "
        "MERGE (class)-[:HAS_PROPERTY {schemaKey:'loan-graph-v1'}]->(prop)",
        {"links": [
            {"classKey": f"class:{link['class']}", "propertyKey": f"property:{link['property']}"}
            for link in property_links
        ]},
    ))
    statements.append((
        "UNWIND $links AS link "
        "MATCH (from:OntologyTerm {termKey:link.fromKey}) "
        "MATCH (relationship:OntologyTerm {termKey:link.relationshipKey}) "
        "MATCH (to:OntologyTerm {termKey:link.toKey}) "
        "MERGE (from)-[:SOURCE_OF {schemaKey:'loan-graph-v1'}]->(relationship) "
        "MERGE (relationship)-[:TARGETS {schemaKey:'loan-graph-v1'}]->(to)",
        {"links": [
            {
                "fromKey": f"class:{link['fromClass']}",
                "relationshipKey": f"relationship:{link['relationship']}",
                "toKey": f"class:{link['toClass']}",
            }
            for link in relationship_links
        ]},
    ))
    class_terms = [
        {"name": term["name"], "termKey": term["termKey"]}
        for term in ontology_terms if term["termKind"] == "class"
    ]
    property_terms = [
        {
            "domain": term["domain"], "propertyName": term["name"].split(".", 1)[1],
            "termKey": term["termKey"],
        }
        for term in ontology_terms if term["termKind"] == "property"
    ]
    statements.append((
        "UNWIND $classes AS classRow MATCH (instance:$(classRow.name)) "
        "MATCH (term:OntologyTerm {termKey:classRow.termKey}) "
        "MERGE (instance)-[:INSTANCE_OF {schemaKey:'loan-graph-v1'}]->(term)",
        {"classes": class_terms},
    ))
    statements.append((
        "UNWIND $properties AS propertyRow MATCH (instance:$(propertyRow.domain)) "
        "WHERE instance[propertyRow.propertyName] IS NOT NULL "
        "MATCH (term:OntologyTerm {termKey:propertyRow.termKey}) "
        "MERGE (instance)-[:HAS_PROPERTY_VALUE {schemaKey:'loan-graph-v1'}]->(term)",
        {"properties": property_terms},
    ))

    _ensure_graph_constraints()
    neo4jconn.run_transaction(statements)
    return {
        "sourceFile": f"fibo/sql/{file_name}", "sourceHash": source_hash,
        "queries": len(queries), "outputColumns": sum(len(query["outputs"]) for query in queries),
        "inputColumns": len(input_fields), "mappedElements": len(valid_mappings),
        "unresolvedMappings": unresolved,
    }


@sqlLineageRouter.post("/sync")
def sync_sql_lineage_to_graph():
    try:
        return {"synced": True, **_sync_to_graph()}
    except Exception as error:
        raise HTTPException(status_code=503, detail=f"Could not synchronize SQL lineage to Neo4j: {error}") from error


@sqlLineageRouter.post("/analyze")
def analyze_sql_lineage(request: SqlLineageRequest):
    if not request.sql.strip():
        raise HTTPException(status_code=422, detail="SQL is required")
    queries = parse_sql_lineage(request.sql)
    if not queries:
        raise HTTPException(status_code=422, detail="No supported SELECT statement with a FROM clause was found")
    if len(queries) != 1:
        raise HTTPException(status_code=422, detail="Analyze one SELECT statement at a time")

    source_hash = hashlib.sha256(request.sql.encode("utf-8")).hexdigest()
    source_key = f"interactive-sql/{source_hash}"
    try:
        mappings = _interactive_mapping_rows(request.sql)
        _sync_to_graph(source_key, request.sql, "SQL Input.sql", mappings)
        return _get_sql_lineage(source_key)
    except Exception as error:
        raise HTTPException(status_code=503, detail=f"Could not build lineage for SQL input: {error}") from error


@sqlLineageRouter.get("/saved-queries")
def list_saved_sql_queries():
    with pg_engine.connect() as connection:
        rows = connection.execute(text(
            "SELECT id, name, sql_text, created_at FROM saved_sql_queries ORDER BY created_at DESC, id DESC"
        )).mappings().all()
    return [
        {"id": row["id"], "name": row["name"], "sql": str(row["sql_text"]), "created_at": row["created_at"]}
        for row in rows
    ]


@sqlLineageRouter.post("/saved-queries")
def save_sql_query(request: SavedSqlQueryRequest):
    if not request.name.strip() or not request.sql.strip():
        raise HTTPException(status_code=422, detail="Query name and SQL are required")
    with pg_engine.begin() as connection:
        row = connection.execute(
            text("INSERT INTO saved_sql_queries (name, sql_text) VALUES (:name, :sql) "
                 "RETURNING id, name, sql_text, created_at"),
            {"name": request.name.strip(), "sql": request.sql},
        ).mappings().one()
    return {
        "id": row["id"],
        "name": row["name"],
        "sql": str(row["sql_text"]),
        "created_at": row["created_at"],
    }


@sqlLineageRouter.post("/saved-queries/{query_id}/lineage")
def build_saved_sql_lineage(query_id: int):
    with pg_engine.connect() as connection:
        saved = connection.execute(
            text("SELECT id, name, sql_text FROM saved_sql_queries WHERE id = :query_id"),
            {"query_id": query_id},
        ).mappings().first()
    if saved is None:
        raise HTTPException(status_code=404, detail="Saved SQL query not found")

    source_key = f"saved-sql/{query_id}"
    try:
        _sync_to_graph(source_key, str(saved["sql_text"]), f"{saved['name']}.sql")
        return _get_sql_lineage(source_key)
    except Exception as error:
        raise HTTPException(status_code=503, detail=f"Could not build lineage for saved SQL: {error}") from error


def _get_sql_lineage(source_key: str) -> dict[str, Any]:
    source_rows = neo4jconn.run(
        "MATCH (source:LegacySqlSource {sourceKey:$sourceKey,active:true}) "
        "RETURN properties(source) AS source",
        {"sourceKey": source_key},
    )
    if not source_rows:
        return {"synced": False, "sourceFile": "fibo/sql/sql.sql", "queries": []}
    source = source_rows[0]["source"]
    query_rows = neo4jconn.run(
        "MATCH (source:LegacySqlSource {sourceKey:$sourceKey})-[:HAS_QUERY]->(query:LegacySqlElement {active:true}) "
        "OPTIONAL MATCH (query)-[mapping:MAPS_TO|PROPOSES_MAPPING_TO]->(term:OntologyTerm) "
        "RETURN properties(query) AS query, "
        "collect(DISTINCT CASE WHEN term IS NULL THEN null ELSE "
        "{term:properties(term),status:mapping.reviewStatus,relationshipType:type(mapping)} END) AS mappings "
        "ORDER BY query.queryNumber",
        {"sourceKey": source_key},
    )
    queries: list[dict[str, Any]] = []
    for query_row in query_rows:
        query = query_row["query"]
        query["mappings"] = [item for item in query_row["mappings"] if item]
        output_rows = neo4jconn.run(
            "MATCH (query:LegacySqlElement {sourceKey:$sourceKey,queryId:$queryId,active:true})-[:RETURNS]->"
            "(output:LegacySqlElement {active:true}) "
            "OPTIONAL MATCH (output)-[:DERIVES_FROM]->(input:LegacySqlElement {active:true}) "
            "WITH output, collect(DISTINCT properties(input)) AS inputs "
            "OPTIONAL MATCH (output)-[mapping:MAPS_TO|PROPOSES_MAPPING_TO]->(term:OntologyTerm) "
            "RETURN properties(output) AS output, inputs, "
            "collect(DISTINCT CASE WHEN term IS NULL THEN null ELSE "
            "{term:properties(term),status:mapping.reviewStatus,relationshipType:type(mapping)} END) AS mappings "
            "ORDER BY output.position",
            {"sourceKey": source_key, "queryId": query["queryId"]},
        )
        query["outputs"] = []
        clause_rows = neo4jconn.run(
            "MATCH (query:LegacySqlElement {sourceKey:$sourceKey,queryId:$queryId,active:true})-[:HAS_CLAUSE]->"
            "(clause:LegacySqlElement {active:true}) "
            "OPTIONAL MATCH (clause)-[:REFERENCES_COLUMN]->(input:LegacySqlElement {active:true}) "
            "WITH clause, collect(DISTINCT properties(input)) AS sourceColumns "
            "OPTIONAL MATCH (clause)-[mapping:MAPS_TO|PROPOSES_MAPPING_TO]->(term:OntologyTerm) "
            "RETURN properties(clause) AS clause, sourceColumns, "
            "collect(DISTINCT CASE WHEN term IS NULL THEN null ELSE "
            "{term:properties(term),status:mapping.reviewStatus,relationshipType:type(mapping)} END) AS mappings "
            "ORDER BY clause.clauseKind",
            {"sourceKey": source_key, "queryId": query["queryId"]},
        )
        query["clauses"] = []
        for clause_row in clause_rows:
            clause = clause_row["clause"]
            clause["sourceColumns"] = [item for item in clause_row["sourceColumns"] if item]
            clause["mappings"] = [item for item in clause_row["mappings"] if item]
            query["clauses"].append(clause)
        for output_row in output_rows:
            output = output_row["output"]
            output["sourceColumns"] = [item for item in output_row["inputs"] if item]
            output["mappings"] = [item for item in output_row["mappings"] if item]
            query["outputs"].append(output)
        queries.append(query)

    return {
        "synced": True,
        "sourceFile": source.get("fileName"),
        "sourceHash": source.get("sha256"),
        "syncedAt": source.get("syncedAt"),
        "summary": {
            "queries": len(queries),
            "outputColumns": sum(len(query["outputs"]) for query in queries),
            "mappedOutputs": sum(bool(output.get("mappings")) for query in queries for output in query["outputs"]),
            "cdes": sum(bool(output.get("isCde")) for query in queries for output in query["outputs"]),
        },
        "queries": queries,
    }


@sqlLineageRouter.get("")
def get_sql_lineage():
    return _get_sql_lineage(SOURCE_KEY)
