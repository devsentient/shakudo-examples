from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import documents, drafts, embeddings, export, templates
from app.services.database import init_db
from app.services.seed import seed_demo_data

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info('Initializing Executive Document Studio backend...')
    await init_db()
    await seed_demo_data()
    logger.info('Backend initialization complete')
    yield
    logger.info('Shutting down Executive Document Studio backend...')


app = FastAPI(
    title='Executive Document Studio',
    description='Secure AI-powered document drafting for executives',
    version='0.1.0',
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(documents.router, prefix='/api/documents', tags=['documents'])
app.include_router(embeddings.router, prefix='/api/embeddings', tags=['embeddings'])
app.include_router(drafts.router, prefix='/api/drafts', tags=['drafts'])
app.include_router(templates.router, prefix='/api/templates', tags=['templates'])
app.include_router(export.router, prefix='/api/export', tags=['export'])


@app.get('/health')
async def health_check():
    return {'status': 'ok', 'service': 'executive-document-studio'}


@app.get('/ready')
async def readiness_check():
    return {'status': 'ready'}
