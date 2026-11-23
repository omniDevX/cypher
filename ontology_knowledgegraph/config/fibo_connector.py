from neo4j import GraphDatabase
from config.config import NEO4J_PASSWORD, NEO4J_URI, NEO4J_USER
from typing import Any

class FiboConnector:
    def __init__(self):
        self.driver = GraphDatabase.driver(NEO4J_URI,auth=(NEO4J_USER, NEO4J_PASSWORD))

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
