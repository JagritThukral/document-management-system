import os
from contextlib import asynccontextmanager
from psycopg_pool import AsyncConnectionPool
from pgvector.psycopg import register_vector_async
from fastapi import FastAPI, Request


@asynccontextmanager
async def db_lifespan(app: FastAPI):
    async with AsyncConnectionPool(
        conninfo=os.getenv("POSTGRES_DATABASE_URL"),
        min_size=1,
        max_size=10,
    ) as pool:
        print("[Database] Connection pool created")
        app.state.db_pool = pool
        print("[Database] Initializing database")
        async with pool.connection() as conn:
            print("[Database] Connected to database")
            async with conn.cursor() as cur:
                print("[Database] Registering vector extension if it does not exist")
                await cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
                await register_vector_async(conn)
                print(
                    "[Database] Creating documents, chunks tables if they do not exist")
                await cur.execute("""
                    CREATE TABLE IF NOT EXISTS documents (
                        id UUID PRIMARY KEY,
                        filename TEXT NOT NULL,
                        file_size BIGINT NOT NULL,
                        header_hash VARCHAR(64) NOT NULL,
                        status VARCHAR(20) DEFAULT 'pending',
                        message TEXT DEFAULT 'Waiting in queue...',
                        category TEXT,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    );
                    CREATE TABLE IF NOT EXISTS document_chunks (
                        id UUID PRIMARY KEY,
                        document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
                        chunk_text TEXT NOT NULL,
                        embedding VECTOR(1536),
                        page_number INTEGER,      
                        chunk_type TEXT           
                    );
                """)
                print(
                    "[Database] Creating users, roles, permissions and user_documents tables if they do not exist")
                await cur.execute("""
                    -- Stores the titles of your user groups
                    CREATE TABLE IF NOT EXISTS roles (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(50) UNIQUE NOT NULL,
                        description TEXT
                    );

                    -- Stores explicit actions or page views
                    CREATE TABLE IF NOT EXISTS permissions (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(50) UNIQUE NOT NULL,
                        description TEXT
                    );

                    -- The junction linking Roles to Permissions
                    CREATE TABLE IF NOT EXISTS role_permissions (
                        role_id INTEGER REFERENCES roles(id) ON DELETE CASCADE,
                        permission_id INTEGER REFERENCES permissions(id) ON DELETE CASCADE,
                        PRIMARY KEY (role_id, permission_id)
                    );

                    -- We add a foreign key pointing to the roles table
                    CREATE TABLE IF NOT EXISTS users (
                        id UUID PRIMARY KEY,
                        username VARCHAR(100) UNIQUE NOT NULL,
                        hashed_password VARCHAR(255) NOT NULL,
                        role_id INTEGER REFERENCES roles(id) ON DELETE SET NULL,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    );
                    CREATE TABLE IF NOT EXISTS user_documents (
                        user_id UUID REFERENCES users(id) ON DELETE CASCADE,
                        document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
                        PRIMARY KEY (user_id, document_id)
                    );
                """)
                print("[Database] Seeding permissions...")
                await cur.execute("""
                    INSERT INTO permissions (id, name, description) VALUES
                        (1, 'search', 'Access to the search page and API'),
                        (2, 'upload', 'Access to the file upload page and API'),
                        (3, 'view_documents', 'Access to the documents list page'),
                        (4, 'view_ai_chat', 'Access to the AI chat page'),
                        (5, 'admin', 'Access to the admin control panel, including user and role management'),
                        (6, 'view_all_documents', 'Can see documents uploaded by anyone')
                        ON CONFLICT (id) DO UPDATE SET 
                        name = EXCLUDED.name, description = EXCLUDED.description;
                """)

                print("[Database] Seeding roles...")
                await cur.execute("""
                    INSERT INTO roles (id, name, description) VALUES
                        (1, 'Admin', 'Full system access'),
                        (2, 'Standard', 'Regular user with restricted access'),
                        (3, 'Viewer', 'Can only view documents and search')
                    ON CONFLICT (id) DO UPDATE SET 
                        name = EXCLUDED.name, description = EXCLUDED.description;
                """)

                print("[Database] Linking roles and permissions...")
                await cur.execute("""
                    INSERT INTO role_permissions (role_id, permission_id) VALUES
                        (1, 1), (1, 2), (1, 3), (1, 4), (1, 5), (1, 6), 
                        (2, 1), (2, 2), (2, 3), (2, 4), (2, 6),
                        (3, 1), (3, 3)
                    ON CONFLICT (role_id, permission_id) DO UPDATE SET 
                        role_id = EXCLUDED.role_id, permission_id = EXCLUDED.permission_id
                    ;
                """)

                print("[Database] Creating indexes if they do not exist")
                await cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_documents_size_hash ON documents(file_size, header_hash);
                """)
                await cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_doc_chunks_fts 
                    ON document_chunks USING gin(to_tsvector('english', chunk_text));
                """)
                await cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_doc_chunks_embedding
                    ON document_chunks USING hnsw (embedding vector_cosine_ops);
                """)
                print("[Database] Committing changes")
                await conn.commit()
                print("[Database] Changes committed")
        yield
    print("[Database] Connection pool closed")


async def get_db_connection(request: Request):
    pool: AsyncConnectionPool = request.app.state.db_pool
    async with pool.connection() as conn:
        yield conn


async def get_db_pool(request: Request):
    yield request.app.state.db_pool
