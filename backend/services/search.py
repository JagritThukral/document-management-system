import asyncio
from psycopg_pool import AsyncConnectionPool
from psycopg.rows import dict_row

from services.embeddings import EmbeddingsService


class SearchService:
    def __init__(self, db_pool, embeddings):
        self.db_pool: AsyncConnectionPool = db_pool
        self.embeddings: EmbeddingsService = embeddings

    async def keyword_search(self, query: str, user_id: str, permissions: list):
        owned_docs_condition = "c.document_id IN (SELECT document_id FROM user_documents WHERE user_id = %s)" if "view_all_documents" not in permissions else "TRUE"
        key_params = [query, query, query]

        if "view_all_documents" not in permissions:
            key_params.append(user_id)
        key_query = f"""
            SELECT d.id as document_id, d.filename, c.chunk_text,
                ts_headline('english', c.chunk_text, plainto_tsquery('english', %s), 
                            'StartSel=<b>, StopSel=</b>, MaxWords=35, MinWords=15') as snippet,
                ts_rank_cd(to_tsvector('english', c.chunk_text), plainto_tsquery('english', %s), 33) as rank
            FROM document_chunks c
            JOIN documents d ON c.document_id = d.id
            WHERE to_tsvector('english', c.chunk_text) @@ plainto_tsquery('english', %s) AND {owned_docs_condition}
            ORDER BY rank DESC
            LIMIT 20;
        """
        async with self.db_pool.connection() as db:
            async with db.cursor(row_factory=dict_row) as cursor:
                await cursor.execute(key_query, key_params)
                return await cursor.fetchall()

    async def semantic_search(self, query: str, user_id: str, permissions: list):
        owned_docs_condition = "c.document_id IN (SELECT document_id FROM user_documents WHERE user_id = %s)" if "view_all_documents" not in permissions else "TRUE"

        query_vector = await self.embeddings.create_embedding(query)
        vector_str = f"[{','.join(map(str, query_vector))}]"

        sem_params = [vector_str, vector_str]

        if "view_all_documents" not in permissions:
            sem_params.insert(0, user_id)

        sem_query = f"""
            SELECT c.document_id, d.filename, c.chunk_text, (c.embedding <=> %s::vector) as distance
            FROM document_chunks c
            JOIN documents d ON c.document_id = d.id
            WHERE {owned_docs_condition}
            ORDER BY c.embedding <=> %s::vector
            LIMIT 20;
        """
        async with self.db_pool.connection() as db:
            async with db.cursor(row_factory=dict_row) as cursor:
                await cursor.execute(sem_query, sem_params)
                return await cursor.fetchall()

    async def hybrid_search(self, query: str, user_id: str, permissions: list, limit: int = 15):
        keyword_results_task = asyncio.create_task(
            self.keyword_search(query, user_id, permissions))
        semantic_results_task = asyncio.create_task(
            self.semantic_search(query, user_id, permissions))

        keyword_results = await keyword_results_task
        semantic_results = await semantic_results_task

        rrf_k = 60
        fused_results = {}

        for rank, row in enumerate(semantic_results):
            doc_id = row['document_id']
            if doc_id not in fused_results:
                fused_results[doc_id] = {
                    'document_id': doc_id, 'filename': row['filename'],
                    'chunk_text': row['chunk_text'], 'snippet': None, 'score': 0.0
                }
            fused_results[doc_id]['score'] += 1.0 / (rrf_k + rank + 1)

        for rank, row in enumerate(keyword_results):
            doc_id = row['document_id']
            if doc_id not in fused_results:
                fused_results[doc_id] = {
                    'document_id': doc_id, 'filename': row['filename'],
                    'chunk_text': row['chunk_text'], 'snippet': row['snippet'], 'score': 0.0
                }
            else:
                # If exact keyword match exists, prefer its highlighted snippet over plain chunk
                fused_results[doc_id]['snippet'] = row['snippet']
            fused_results[doc_id]['score'] += 1.0 / (rrf_k + rank + 1)

        # Sort by combined RRF score and apply final limit
        sorted_results = sorted(fused_results.values(),
                                key=lambda x: x['score'], reverse=True)[:limit]
        return sorted_results
