
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.datasets import router as datasets_router

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title='BiasGuard API',
    version='1.0.0',
    description='AI fairness platform backend',
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(datasets_router, prefix='/api', tags=['BiasGuard'])


@app.get('/')
def root():
    return {'message': 'BiasGuard API is running', 'status': 'healthy'}


@app.get('/health')
def health():
    return {'status': 'healthy'}
