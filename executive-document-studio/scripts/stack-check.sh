#!/usr/bin/env bash
set -euo pipefail

PORT="${PORT:-3000}"

printf '\n[studio] health\n'
curl -fsS "http://127.0.0.1:${PORT}/health"

printf '\n\n[studio] frontend shell\n'
curl -fsS "http://127.0.0.1:${PORT}" | sed -n '1,20p'

printf '\n\n[studio] documents endpoint\n'
curl -fsS "http://127.0.0.1:${PORT}/api/documents" | python3 -c "import json,sys; payload=json.load(sys.stdin); print({'document_count': len(payload), 'first_titles': [item['title'] for item in payload[:3]]})"

printf '\n\n[studio] embeddings stats\n'
curl -fsS "http://127.0.0.1:${PORT}/api/embeddings/stats"
