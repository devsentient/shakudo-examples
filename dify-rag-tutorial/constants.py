import os

ROOT_PATH = os.environ.get('ROOT_PATH', '')

OPENAI_API_KEY = os.environ.get('HYPERPLANE_CUSTOM_SECRET_KEY_OPENAI_API_KEY', '')

QDRANT_URL = os.environ.get('QDRANT_URL', 'http://qdrant.hyperplane-qdrant.svc.cluster.local:6333')

TEMPERATURE = 0.3
SEED = 1234
