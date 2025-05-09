import os

NEO4J_PARAMS = {
    "URL": os.environ.get(
        "NEO4J_URL", "bolt://neo4j.hyperplane-neo4j:7687"
    ),
    "user": os.environ.get("HYPERPLANE_CUSTOM_SECRET_KEY_NEO4J_USER", "neo4j"),
    "password": os.environ.get("HYPERPLANE_CUSTOM_SECRET_KEY_NEO4J_PASSWORD", "Shakudo312!"),
}
