"""Human-readable checks for the built Neo4j graph."""


def print_graph_summary(driver) -> None:
    with driver.session() as session:
        print("\nNeo4j graph summary")
        print("Node counts:")
        for row in session.run("MATCH (n) UNWIND labels(n) AS label RETURN label, count(*) AS count ORDER BY label"):
            print(f"  {row['label']}: {row['count']}")
        print("Relationship counts:")
        for row in session.run("MATCH ()-[r]->() RETURN type(r) AS type, count(*) AS count ORDER BY type"):
            print(f"  {row['type']}: {row['count']}")
        print("INSTANCE_OF examples:")
        for row in session.run(
            "MATCH (i)-[:INSTANCE_OF]->(c:EntityClass) "
            "RETURN i.name AS instance, labels(i)[0] AS label, c.name AS class LIMIT 8"
        ):
            print(f"  {row['instance']} ({row['label']}) -> {row['class']}")
