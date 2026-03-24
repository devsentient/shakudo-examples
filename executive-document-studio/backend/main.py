from pathlib import Path

from fastapi import HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.main import app

DIST = Path(__file__).resolve().parent.parent / 'frontend' / 'out'
NEXT_DIR = DIST / '_next'
RESERVED_PREFIXES = ('api', 'health', 'ready', 'docs', 'redoc', 'openapi.json')

if NEXT_DIR.exists():
    app.mount('/_next', StaticFiles(directory=str(NEXT_DIR)), name='next-static')


@app.get('/{full_path:path}', include_in_schema=False)
async def serve_frontend(full_path: str):
    normalized = full_path.strip('/')
    if normalized.startswith(RESERVED_PREFIXES):
        raise HTTPException(status_code=404)

    if not DIST.exists():
        return JSONResponse(
            {
                'message': 'Frontend not built yet. Run: cd frontend && npm install && NEXT_PUBLIC_API_BASE_URL=/api npm run build',
            },
            status_code=503,
        )

    candidate_paths = []
    if not normalized:
        candidate_paths.append(DIST / 'index.html')
    else:
        candidate_paths.extend(
            [
                DIST / normalized,
                DIST / normalized / 'index.html',
                DIST / f'{normalized}.html',
            ]
        )

    for candidate in candidate_paths:
        if candidate.exists() and candidate.is_file():
            return FileResponse(str(candidate))

    fallback = DIST / 'index.html'
    if fallback.exists():
        return FileResponse(str(fallback))

    return JSONResponse(
        {
            'message': 'Frontend export missing. Run: cd frontend && npm install && NEXT_PUBLIC_API_BASE_URL=/api npm run build',
        },
        status_code=503,
    )
