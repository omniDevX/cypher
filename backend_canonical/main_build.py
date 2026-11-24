"""Build the demo knowledge graph from PostgreSQL into Neo4j."""

import logging

from pipeline.build_knowledge_graph import BuildPipeline


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    pipeline = BuildPipeline()
    try:
        pipeline.run()
        print("Knowledge graph build completed.")
    except Exception:
        logging.getLogger(__name__).exception("Knowledge graph build failed")
        raise
    finally:
        pipeline.close()


if __name__ == "__main__":
    main()
