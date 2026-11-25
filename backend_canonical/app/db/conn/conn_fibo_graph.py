from neo4j import GraphDatabase
from typing import Any

from app.config import get_settings_singleton


class FiboGraphConnector:
    def __init__(self):
        settings = get_settings_singleton()
        self.driver = GraphDatabase.driver(settings.NEO4J_URI, auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD))

    def run(self, cypher: str, parameters: dict|None=None)->list[dict]:
        with self.driver.session() as session:
            result = session.run(cypher, parameters or {}) # type: ignore
            return [record.data() for record in result]

    def run_transaction(self, statements: list[tuple[str, dict[str, Any]]]) -> None:
        with self.driver.session() as session:
            def write_all(transaction: Any) -> None:
                for cypher, parameters in statements:
                    transaction.run(cypher, parameters).consume() # type: ignore
            session.execute_write(write_all)

    def close(self) -> None: self.driver.close()
