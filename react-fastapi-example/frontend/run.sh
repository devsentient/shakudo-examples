#!/usr/bin/env bash
PROJECT_DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

npm install
REACT_APP_BACKEND_URL=$BACKEND_URL npm run start