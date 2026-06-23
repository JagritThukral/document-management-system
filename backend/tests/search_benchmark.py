import asyncio
import json
import os
import dotenv
from psycopg_pool import AsyncConnectionPool
from services.search import SearchService
from services.embeddings import EmbeddingsService

dotenv.load_dotenv()
def run_benchmark():
    db_pool = AsyncConnectionPool(os.environ.get("POSTGRES_DATABASE_URL"))
    embeddings_service = EmbeddingsService()
    search_service = SearchService(db_pool, embeddings_service)
    