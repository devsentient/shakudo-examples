import os

NEO4J_PARAMS = {
    "URL": os.environ.get(
        "NEO4J_URL", "neo4j://neo4j.hyperplane-neo4j.svc.cluster.local:7687"
    ),
    "user": os.environ.get("NEO4J_USER", "neo4j"),
    "password": os.environ.get("NEO4J_PASSWORD", "Shakudo312!"),
}
