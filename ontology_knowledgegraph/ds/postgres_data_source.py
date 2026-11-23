"""SQLAlchemy-backed PostgreSQL data source for ontology extraction."""
from __future__ import annotations

from typing import Any

from sqlalchemy import create_engine, inspect, text
from ontology.ontology_models import DataSource, DataSourceType


class PostgreSQLDataSource(DataSource):
    source_type: DataSourceType = DataSourceType.POSTGRESQL_TABLE
    table_name: str

    def connect(self) -> bool:
        try:
            with create_engine(self.connection_string).connect():
                return True
        except Exception:
            return False

    def get_records(self, query: str | None = None) -> list[dict[str, Any]]:
        statement = text(query) if query else text(f'SELECT * FROM "{self.table_name}"')
        with create_engine(self.connection_string).connect() as conn:
            return [dict(row) for row in conn.execute(statement).mappings().all()]

    def get_schema(self) -> dict[str, Any]:
        inspector = inspect(create_engine(self.connection_string))
        columns = inspector.get_columns(self.table_name)
        return {
            "table_name": self.table_name,
            "columns": [
                {
                    "name": column["name"],
                    "type": str(column["type"]),
                    "not_null": not column["nullable"],
                    "default_value": column.get("default"),
                    "primary_key": column.get("primary_key", False),
                }
                for column in columns
            ],
            "foreign_keys": inspector.get_foreign_keys(self.table_name),
        }

