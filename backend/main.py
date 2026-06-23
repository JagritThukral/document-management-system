import os
import mimetypes
import asyncio
import jwt
from datetime import datetime, timedelta, timezone
from typing import Annotated, AsyncIterable
from uuid import UUID
from fastapi import Depends, FastAPI, File, Form, Query, Request, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi import BackgroundTasks
from fastapi.sse import EventSourceResponse, ServerSentEvent
from openai import AsyncOpenAI
from dotenv import load_dotenv
from pydantic import BaseModel
from psycopg import AsyncConnection
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool
from cachetools import TTLCache
from passlib.context import CryptContext

from services.embeddings import EmbeddingsService
from services.storage import StorageService
from services.search import SearchService
from utils.database import db_lifespan, get_db_connection, get_db_pool

load_dotenv()
app = FastAPI(lifespan=db_lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://127.0.0.1:44320",
        "http://localhost:62957",
        "https://localhost:44320"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
embeddings = EmbeddingsService(openai_client)


search_cache = TTLCache(maxsize=100, ttl=600)

hash_context = CryptContext(schemes=["argon2"], deprecated="auto")

#  Pydantic Schemas


class UploadResponse(BaseModel):
    status: str
    message: str
    document_id: str


class VaultItemOut(BaseModel):
    id: UUID | None
    name: str
    item_type: str
    created_at: datetime | None
    file_size: int | None


class DocumentListResponse(BaseModel):
    status: str
    count: int
    current_path: str
    data: list[VaultItemOut]


class HybridMatch(BaseModel):
    document_id: UUID
    filename: str
    chunk_text: str
    snippet: str | None
    score: float


class HybridSearchResponse(BaseModel):
    status: str
    results: list[HybridMatch]


def get_storage_service(db: AsyncConnection = Depends(get_db_connection)):
    return StorageService(os.getenv("STORAGE_DIR", "./storage"), db, embeddings)


def get_search_service(db: AsyncConnectionPool = Depends(get_db_pool)):
    return SearchService(db, embeddings)


def create_access_token(user_id: str, permissions: list[str]):
    # expiration (1 day from now)
    expire = datetime.now(timezone.utc) + timedelta(days=1)

    # payload
    to_encode = {
        "sub": str(user_id),
        "permissions": permissions,
        "exp": expire
    }

    # Encode the token
    encoded_jwt = jwt.encode(to_encode, os.getenv(
        "JWT_SECRET"), algorithm="HS256")
    return encoded_jwt


def require_permission(required_permission: str):
    def get_token_from_cookie(request: Request):
        if len(request.cookies) == 0:
            print("[Auth] No cookies found in request")
        return request.cookies.get("access_token")

    def permission_dependency(token: str = Depends(get_token_from_cookie)) -> dict:
        if not token:
            raise HTTPException(status_code=401, detail="Missing token")

        try:
            payload = jwt.decode(token, os.getenv(
                "JWT_SECRET"), algorithms=["HS256"])
            user_permissions = payload.get("permissions", [])

            if required_permission not in user_permissions:
                raise HTTPException(
                    status_code=403, detail=f"Permission '{required_permission}' required")
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")

    return permission_dependency


@app.post("/auth/register")
async def register(username: str, password: str, role_id: int, db: AsyncConnection = Depends(get_db_connection), ):
    hashed_password = hash_context.hash(password)
    async with db.cursor() as cursor:
        try:
            await cursor.execute("SELECT id FROM roles WHERE id = %s", (role_id,))
            role = await cursor.fetchone()
            if not role:
                raise HTTPException(status_code=400, detail="Invalid role_id")

            await cursor.execute(
                "INSERT INTO users (id, username, role_id, hashed_password) VALUES (gen_random_uuid(), %s, %s, %s)",
                (username, role_id, hashed_password)
            )

            await db.commit()
            return {"status": "success", "message": "User registered successfully"}
        except Exception as e:
            await db.rollback()
            if "unique constraint" in str(e).lower():
                raise HTTPException(
                    status_code=400, detail="Username already exists")
            else:
                print(f"[main] Error registering user: {e}")
                raise HTTPException(
                    status_code=500, detail="Internal server error")


@app.post("/auth/login")
async def login(username: Annotated[str, Form()], password: Annotated[str, Form()], db: AsyncConnection = Depends(get_db_connection)):
    async with db.cursor(row_factory=dict_row) as cursor:
        await cursor.execute("SELECT id, hashed_password FROM users WHERE username = %s", (username,))
        user = await cursor.fetchone()

        if not user or not hash_context.verify(password, user["hashed_password"]):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        await cursor.execute("""
                             SELECT p.name
                             FROM users u
                             JOIN roles r ON u.role_id = r.id
                             JOIN role_permissions rp ON r.id = rp.role_id
                             JOIN permissions p ON rp.permission_id = p.id
                             WHERE u.username = %s;
                             """, (username,))
        permissions = [row["name"] for row in await cursor.fetchall()]
    token = create_access_token(user["id"], permissions)
    return {"status": "success", "message": "Login successful", "user_id": str(user["id"]), "token": token}


@app.get("/documents/{document_id}/events", response_class=EventSourceResponse)
async def document_events(document_id: UUID, request: Request) -> AsyncIterable[ServerSentEvent]:
    pool = request.app.state.db_pool

    while True:
        if await request.is_disconnected():
            break

        async with pool.connection() as db:
            async with db.cursor(row_factory=dict_row) as cursor:
                await cursor.execute(
                    "SELECT status, message FROM documents WHERE id = %s",
                    (str(document_id),)
                )
                doc = await cursor.fetchone()

        if not doc:
            yield ServerSentEvent(data={"status": "error", "message": "Document not found"})
            break

        status = doc["status"]
        msg = doc["message"]

        yield ServerSentEvent(data={"status": status, "message": msg})

        if status in ["completed", "error"]:
            break

        await asyncio.sleep(1)


@app.post("/documents", response_model=UploadResponse, status_code=202)
async def upload_document(background_tasks: BackgroundTasks, file: UploadFile = File(...), category: Annotated[str | None, Query(min_length=3)] = None, storage: StorageService = Depends(get_storage_service), jwt_payload: dict = Depends(require_permission("upload"))):
    user_id = jwt_payload.get("sub")
    doc_id, is_new_file = await storage.save(file, user_id, category)
    # ONLY process embeddings if this is a brand new physical file
    if is_new_file:
        background_tasks.add_task(
            storage.process_document, doc_id, file.filename, category)
        msg = "File accepted for processing"
    else:
        msg = "Document already exists in vault. Access granted instantly."
    return {
        "status": "pending",
        "message": msg,
        "document_id": str(doc_id)
    }


@app.get("/documents", response_model=DocumentListResponse)
async def get_documents(
    path: str = "",
    limit: Annotated[int, Query(gt=0, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    db: AsyncConnection = Depends(get_db_connection),
    jwt_payload: dict = Depends(require_permission("view_documents"))
):
    user_id = jwt_payload.get("sub")
    permissions = jwt_payload.get("permissions", [])

    can_view_all = "view_all_documents" in permissions

    owner_condition = "id IN (SELECT document_id FROM user_documents WHERE user_id = %s)" if not can_view_all else "TRUE"
    owner_params = [user_id] if not can_view_all else []

    safe_path = path.strip("/")

    if safe_path == "":
        regex_pattern = '^([^/]+)'
        dir_condition = "category IS NOT NULL AND category != ''"
        dir_params = []

        file_condition = "(category IS NULL OR category = '')"
        file_params = []
    else:
        regex_pattern = f"^{safe_path}/([^/]+)"
        dir_condition = "category LIKE %s"
        dir_params = [f"{safe_path}/%"]

        file_condition = "category = %s"
        file_params = [safe_path]

    query = f"""
        WITH dirs AS (
            SELECT DISTINCT substring(category FROM %s) AS name
            FROM documents
            WHERE {owner_condition} AND {dir_condition}
        ),
        folder_items AS (
            SELECT
                NULL::uuid AS id,
                name,
                'folder' AS item_type,
                NULL::timestamp with time zone AS created_at,
                NULL::bigint AS file_size    -- <-- Added for folders
            FROM dirs
            WHERE name IS NOT NULL
        ),
        file_items AS (
            SELECT
                id,
                filename AS name,
                'file' AS item_type,
                created_at,
                file_size                    -- <-- Added for files
            FROM documents
            WHERE {file_condition}
        )
        SELECT * FROM folder_items
        UNION ALL
        SELECT * FROM file_items
        ORDER BY item_type DESC, name ASC
        LIMIT %s OFFSET %s;
    """

    params = [regex_pattern] + owner_params + \
        dir_params + file_params + [limit, offset]

    async with db.cursor(row_factory=dict_row) as cursor:
        await cursor.execute(query, params)
        items = await cursor.fetchall()

    return {
        "status": "success",
        "count": len(items),
        "current_path": safe_path,
        "data": items
    }


@app.get("/documents/{document_id}")
async def view_document(document_id: UUID, download: Annotated[bool, Query()] = False, storage: StorageService = Depends(get_storage_service), jwt_payload: dict = Depends(require_permission("view_documents"))):
    async with storage.db.cursor(row_factory=dict_row) as cursor:
        await cursor.execute(
            "SELECT filename, category FROM documents WHERE id = %s",
            (str(document_id),)
        )
        document = await cursor.fetchone()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    file_path = storage.get_secure_document_path(
        document_id,
        document["filename"],
        document["category"]
    )

    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="Document file is missing")

    media_type, _ = mimetypes.guess_type(document["filename"])

    return FileResponse(
        path=file_path,
        media_type=media_type or "application/octet-stream",
        filename=document["filename"],
        content_disposition_type="attachment" if download else "inline",
    )


@app.get("/ai-response", )
async def ai_response(query: str, db: AsyncConnection = Depends(get_db_connection), jwt_payload: dict = Depends(require_permission("view_ai_chat"))):
    try:
        cache_key = query.strip().lower()
        cached_data = search_cache.get(cache_key, {})

        context_chunks = {}

        if "embeddings" in cached_data or "keywords" in cached_data:
            print(f"[AI Search] Cache HIT for query: '{query}'")

            if "embeddings" in cached_data:
                for r in cached_data["embeddings"]:
                    context_chunks[r["chunk_text"]] = r["filename"]

            if "keywords" in cached_data:
                for r in cached_data["keywords"]:
                    context_chunks[r["chunk_text"]] = r["filename"]
        else:
            print(
                f"[AI Search] Cache MISS for query: '{query}'. Running fallback embedding search.")
            query_vector = await embeddings.create_embedding(query)
            vector_str = f"[{','.join(map(str, query_vector))}]"

            async with db.cursor(row_factory=dict_row) as cursor:
                await cursor.execute("""
                    SELECT c.chunk_text, d.filename 
                    FROM document_chunks c
                    JOIN documents d ON c.document_id = d.id
                    ORDER BY c.embedding <=> %s::vector
                    LIMIT 10;
                """, (vector_str,))
                embedding_results = await cursor.fetchall()

            async with db.cursor(row_factory=dict_row) as cursor:
                await cursor.execute("""
                    SELECT c.chunk_text, d.filename 
                    FROM document_chunks c
                    JOIN documents d ON c.document_id = d.id
                    WHERE to_tsvector('english', c.chunk_text) @@ plainto_tsquery('english', %s)
                    ORDER BY ts_rank_cd(to_tsvector('english', c.chunk_text), plainto_tsquery('english', %s), 33) DESC
                    LIMIT 10;
                """, (query, query))
                keyword_results = await cursor.fetchall()

            for r in embedding_results:
                context_chunks[r["chunk_text"]] = r["filename"]

            for r in keyword_results:
                context_chunks[r["chunk_text"]] = r["filename"]

        if not context_chunks:
            return {"answer": "I cannot find this information in the current documentation.", "sources": []}

        context = "\n---\n".join(
            [f"Source ({filename}): {text}" for text,
             filename in context_chunks.items()]
        )
        unique_sources = list(set(context_chunks.values()))

        system_prompt = """You are the Hawkins Enterprise AI Vault Assistant. 
        Answer the user's question based ONLY on the provided context.
        If the user inputs a single keyword (like "coach" or "tax"), assume they are searching for related concepts (like "mentor" or "percentage") and summarize what the context says about those concepts. 
        If the answer is not in the context, say 'I cannot find this information in the current documentation.'"""

        completion = await openai_client.chat.completions.create(
            model="gpt-5.4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query}"}
            ]
        )

        return {
            "answer": completion.choices[0].message.content,
            "sources": unique_sources
        }
    except Exception as e:
        print(f"[AI Search Error]: {e}")
        return {"answer": f"System Error: {str(e)}", "sources": []}


@app.get("/search", response_model=HybridSearchResponse)
async def hybrid_search(
    query: str,
    limit: int = 15,
    jwt_payload: dict = Depends(require_permission("search")),
    search_service: SearchService = Depends(get_search_service)
):
    try:
        user_id = jwt_payload.get("sub")
        permissions = jwt_payload.get("permissions", [])

        sorted_results = await search_service.hybrid_search(query, user_id, permissions, limit)

        # 5. Update Cache (Unified)
        cache_key = query.strip().lower()
        if cache_key not in search_cache:
            search_cache[cache_key] = {}
        search_cache[cache_key]["hybrid"] = sorted_results

        return {"status": "success", "results": sorted_results}

    except Exception as e:
        print(f"[Hybrid Search Error]: {e}")
        return {"status": "error", "results": []}
