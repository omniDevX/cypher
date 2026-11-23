"""Neo4j driver lifecycle and graph constraint setup."""

import logging

from neo4j import GraphDatabase

from config.config import NEO4J_PASSWORD, NEO4J_URI, NEO4J_USER
from .schema import UNIQUE_CONSTRAINTS

logger = logging.getLogger(__name__)


class Neo4jClient:
    def __init__(self):
        self.driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    def verify_connection(self) -> None:
        with self.driver.session() as session:
            session.run("RETURN 1").consume()

    def create_constraints(self) -> None:
        with self.driver.session() as session:
            for statement in UNIQUE_CONSTRAINTS:
                session.run(statement).consume()

    def clear_graph(self) -> None:
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n").consume()

    def close(self) -> None:
        self.driver.close()
