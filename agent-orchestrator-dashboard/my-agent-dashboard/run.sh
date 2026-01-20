#!/bin/bash
PROJECT_DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd "$PROJECT_DIR"

npm i --legacy-peer-deps
npm run build
npm run start
