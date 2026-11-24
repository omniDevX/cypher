"""Orchestrate PostgreSQL demo data and Neo4j graph construction."""

import logging

from ds.software_engineering_data import SoftwareEngineeringDemo
from graph.builder import KnowledgeGraphBuilder
from graph.neo4j_client import Neo4jClient
from graph.verification import print_graph_summary

logger = logging.getLogger(__name__)


class BuildPipeline:
    def __init__(self):
        self.demo = SoftwareEngineeringDemo()
        self.neo4j = Neo4jClient()

    def run(self) -> None:
        self.neo4j.verify_connection()
        if not self.demo.create_database():
            raise RuntimeError("Could not apply PostgreSQL migrations or load demo data")
        KnowledgeGraphBuilder(self.neo4j).rebuild_from_postgres(self.demo.db_url)
        print_graph_summary(self.neo4j.driver)

    def close(self) -> None:
        self.neo4j.close()
