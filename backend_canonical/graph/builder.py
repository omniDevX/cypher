"""Load PostgreSQL rows into Neo4j as property-graph entities and relations."""

import logging

from sqlalchemy import create_engine, text

from .neo4j_client import Neo4jClient
from .schema import ENTITY_CLASSES, RELATIONSHIPS

logger = logging.getLogger(__name__)
TABLES = ("projects", "teams", "developers", "requirements", "tasks")
LABELS = {
    "projects": "Project",
    "teams": "Team",
    "developers": "Developer",
    "requirements": "Requirement",
    "tasks": "Task",
}


class KnowledgeGraphBuilder:
    def __init__(self, neo4j: Neo4jClient):
        self.neo4j = neo4j

    def rebuild_from_postgres(self, database_url) -> None:
        """Replace graph contents with current PostgreSQL demo rows."""
        engine = create_engine(database_url)
        try:
            with engine.connect() as connection:
                rows = {
                    table: [dict(row) for row in connection.execute(text(f'SELECT * FROM "{table}"')).mappings()]
                    for table in TABLES
                }
        finally:
            engine.dispose()

        self.neo4j.create_constraints()
        self.neo4j.clear_graph()
        with self.neo4j.driver.session() as session:
            for table, records in rows.items():
                label = LABELS[table]
                for record in records:
                    session.run(f"CREATE (n:{label} $properties)", properties=record).consume()

            for name, definition in ENTITY_CLASSES.items():
                session.run(
                    "CREATE (n:EntityClass $properties)",
                    properties={
                        "name": name,
                        "label": definition["label"],
                        "definition": definition["definition"],
                        "namespace": "software_engineering",
                        "concept_type": "Class",
                        "properties": definition["properties"],
                    },
                ).consume()

            for source_label, source_key, target_label, relation in RELATIONSHIPS:
                session.run(
                    f"""MATCH (source:{source_label}), (target:{target_label})
                        WHERE source.{source_key} = target.id
                        CREATE (source)-[:{relation}]->(target)"""
                ).consume()

            for label in LABELS.values():
                session.run(
                    f"""MATCH (instance:{label}), (class:EntityClass {{name: $name}})
                        CREATE (instance)-[:INSTANCE_OF]->(class)""",
                    name=label,
                ).consume()
        logger.info("Rebuilt Neo4j graph from PostgreSQL")
