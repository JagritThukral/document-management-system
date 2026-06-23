import os
import re
import aiofiles
import xxhash
import asyncio
from time import perf_counter
from pathlib import Path
from functools import partial
from concurrent.futures import ProcessPoolExecutor
from uuid_extensions import uuid7
from html.parser import HTMLParser
from fastapi import HTTPException, UploadFile
from psycopg import AsyncConnection
from psycopg.rows import dict_row
from unstructured.partition.auto import partition
from unstructured.chunking.title import chunk_by_title
from unstructured.documents.elements import Table, TableChunk
from services.embeddings import EmbeddingsService

_SKIP_CATEGORIES = {"Header", "Footer", "PageBreak"}
cpu_pool = ProcessPoolExecutor()


class _TableHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self._rows: list[list[str]] = []
        self._row: list[str] = []
        self._cell_buf: list[str] = []
        self._in_cell = False

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self._row = []
        elif tag in ("td", "th"):
            self._cell_buf = []
            self._in_cell = True

    def handle_endtag(self, tag):
        if tag in ("td", "th"):
            self._row.append(" ".join(self._cell_buf).strip())
            self._in_cell = False
        elif tag == "tr" and self._row:
            self._rows.append(self._row)

    def handle_data(self, data):
        if self._in_cell:
            self._cell_buf.append(data)

    def to_markdown(self) -> str:
        if not self._rows:
            return ""
        lines = [" | ".join(self._rows[0])]
        lines.append(" | ".join(["---"] * len(self._rows[0])))
        lines.extend(" | ".join(row) for row in self._rows[1:])
        return "\n".join(lines)


def _table_to_text(element) -> str:
    html = getattr(element.metadata, "text_as_html", None)
    if html:
        parser = _TableHTMLParser()
        parser.feed(html)
        md = parser.to_markdown()
        if md:
            return md
    return str(element).strip()


def _chunk_page(chunk) -> int | None:
    orig = getattr(chunk.metadata, "orig_elements", None) or []
    pages = [
        getattr(el.metadata, "page_number", None)
        for el in orig
        if getattr(el.metadata, "page_number", None) is not None
    ]
    if pages:
        return min(pages)
    return getattr(chunk.metadata, "page_number", None)


class StorageService:
    csv_lock = asyncio.Lock()  # Protects against line-mashing race conditions

    def __init__(self, dir, db: AsyncConnection, embeddings: EmbeddingsService,
                 ui_queue: asyncio.Queue = None, worker_id: int = None):
        self.storage_dir = dir
        self.db = db
        self.embeddings = embeddings
        self.ui_queue = ui_queue
        self.worker_id = worker_id

    async def _emit_ui(self, file_name: str, status: str, event_type: str = "progress", error_msg: str = None):
        """
        Smart Emitter: Sends structured events to an asyncio.Queue if provided (for UIs),
        otherwise falls back to standard print() statements for standard script execution.
        """
        if self.ui_queue and self.worker_id:
            await self.ui_queue.put({
                "worker_id": self.worker_id,
                "file": file_name,
                "status": status,
                "type": event_type,
                "error_msg": error_msg
            })
        else:
            # Fallback to standard console logging
            prefix = f"[Worker {self.worker_id}]" if self.worker_id else "[StorageService]"
            if event_type == "error":
                print(f"{prefix} Error processing {file_name}: {error_msg}")
            else:
                print(f"{prefix} [{file_name}] {status}")

    async def log_benchmark(self, doc_id: str, file_name: str, file_size: int,
                            partition_time: float, chunking_time: float,
                            embedding_time: float, total_time: float, num_chunks: int):
        csv_file = "ingestion_benchmarks.csv"
        file_exists = os.path.isfile(csv_file)

        async with self.csv_lock:
            async with aiofiles.open(csv_file, mode='a', newline='') as f:
                if not file_exists:
                    await f.write("doc_id,file_name,file_size_bytes,num_chunks,partition_time_s,chunking_time_s,embedding_time_s,total_time_s\n")
                row = f"{doc_id},{file_name},{file_size},{num_chunks},{partition_time:.4f},{chunking_time:.4f},{embedding_time:.4f},{total_time:.4f}\n"
                await f.write(row)

    def get_secure_document_path(self, doc_id, filename: str, category: str | None = None) -> Path:
        base_path = Path(self.storage_dir).resolve()
        file_ext = os.path.splitext(filename or "")[1]
        file_name = f"{doc_id}{file_ext}"
        safe_category = (category or "").lstrip("/")
        intended_path = (base_path / safe_category / file_name).resolve()

        if not intended_path.is_relative_to(base_path):
            raise HTTPException(
                status_code=400, detail="Invalid category path detected.")
        return intended_path

    async def check_duplicate(self, db: AsyncConnection, file_size: int, fast_hash: str, user_id: str):
        async with db.cursor() as cursor:
            await cursor.execute("SELECT id, filename FROM documents WHERE file_size = %s", (file_size,))
            size_matches = await cursor.fetchall()

        if not size_matches:
            return

        async with self.db.cursor(row_factory=dict_row) as cursor:
            await cursor.execute("SELECT id, status FROM documents WHERE file_size = %s AND header_hash = %s", (file_size, fast_hash))
            existing_doc = await cursor.fetchone()

        if existing_doc:
            if existing_doc["status"] == "error":
                await self.db.execute("DELETE FROM documents WHERE id = %s", (existing_doc["id"],))
                await self.db.commit()
            else:
                existing_id = existing_doc["id"]
                try:
                    await self.db.execute("INSERT INTO user_documents (user_id, document_id) VALUES (%s, %s)", (user_id, str(existing_id)))
                    await self.db.commit()
                except Exception:
                    pass
                return str(existing_id), False
        return

    async def save(self, file: UploadFile, user_id: str, category: str = None) -> tuple[str, bool]:
        try:
            doc_id = uuid7()
            file_ext = os.path.splitext(file.filename)[1]
            file_name = f"{doc_id}{file_ext}"

            file.file.seek(0, 2)
            file_size = file.file.tell()
            file.file.seek(0)

            header_chunk = file.file.read(4096)
            file.file.seek(0)
            fast_hash = xxhash.xxh64(header_chunk).hexdigest()

            duplicate_result = await self.check_duplicate(self.db, file_size, fast_hash, user_id)
            if duplicate_result:
                return duplicate_result

            file_path = self.get_secure_document_path(
                doc_id, file_name, category)
            file_path.parent.mkdir(parents=True, exist_ok=True)

            async with aiofiles.open(file_path, "wb") as dest_file:
                await dest_file.write(await file.read())

            await self.db.execute(
                "INSERT into documents (id, filename, file_size, header_hash, category) VALUES (%s,%s, %s, %s, %s)",
                (str(doc_id), file.filename, file_size, fast_hash, category),
            )
            await self.db.execute(
                "INSERT INTO user_documents (user_id, document_id) VALUES (%s, %s)",
                (user_id, str(doc_id))
            )
            await self.db.commit()
            return str(doc_id), True

        except Exception as e:
            await self._emit_ui(file.filename, "Error saving to disk", "error", f"Storage Exception: {e}")
            await self.db.rollback()
            raise

    async def process_document(self, doc_id: str, file_name: str, category: str | None):
        total_time_start = perf_counter()
        file_path = None
        try:
            await self.db.execute(
                "UPDATE documents SET status = 'processing', message = 'Extracting text and tables...' WHERE id = %s",
                (str(doc_id),)
            )
            await self.db.commit()

            async with self.db.cursor(row_factory=dict_row) as cursor:
                await cursor.execute("SELECT file_size FROM documents WHERE id = %s", (str(doc_id),))
                doc_record = await cursor.fetchone()
                file_size = doc_record["file_size"] if doc_record else 0

            file_ext = os.path.splitext(file_name)[1]
            stored_file_name = f"{doc_id}{file_ext}"
            file_path = self.get_secure_document_path(
                doc_id, stored_file_name, category)

            # --- 1. Partitioning ---
            await self._emit_ui(file_name, "Partitioning NLP models...")
            partition_time_start = perf_counter()
            loop = asyncio.get_running_loop()
            strategy = "fast" if file_ext.lower(
            ) in [".txt", ".csv"] else "hi_res"

            packaged_func = partial(
                partition, filename=str(file_path), strategy=strategy)
            elements = await loop.run_in_executor(cpu_pool, packaged_func)

            partition_time_end = perf_counter()
            partition_duration = partition_time_end - partition_time_start
            await self._emit_ui(file_name, f"Partitioned in {partition_duration:.2f}s")

            filtered = [
                el for el in elements if el.category not in _SKIP_CATEGORIES]

            await self.db.execute(
                "UPDATE documents SET message = 'Chunking document...' WHERE id = %s",
                (str(doc_id),)
            )
            await self.db.commit()

            # --- 2. Chunking ---
            await self._emit_ui(file_name, "Chunking document text...")
            chunking_time_start = perf_counter()
            raw_chunks = chunk_by_title(
                filtered,
                combine_text_under_n_chars=400,
                max_characters=1500,
                multipage_sections=True,
                overlap=200,
            )
            chunking_time_end = perf_counter()
            chunking_duration = chunking_time_end - chunking_time_start
            await self._emit_ui(file_name, f"Chunked in {chunking_duration:.2f}s")

            chunks: list[dict] = []
            for c in raw_chunks:
                is_table = isinstance(c, (Table, TableChunk))
                if is_table:
                    text = _table_to_text(c)
                else:
                    text = re.sub(r"\s+", " ", str(c).strip())

                if len(text) < 50:
                    continue
                chunks.append({"text": text, "page": _chunk_page(
                    c), "type": "table" if is_table else "text"})

            if chunks:
                await self.db.execute(
                    "UPDATE documents SET message = 'Generating AI embeddings...' WHERE id = %s",
                    (str(doc_id),)
                )
                await self.db.commit()

                # --- 3. Embedding ---
                await self._emit_ui(file_name, f"Embedding {len(chunks)} chunks...")
                texts = [c["text"] for c in chunks]

                embedding_time_start = perf_counter()
                vectors = await self.embeddings.create_embeddings(texts)
                embedding_time_end = perf_counter()
                embedding_duration = embedding_time_end - embedding_time_start
                await self._emit_ui(file_name, f"Embedded in {embedding_duration:.2f}s")

                await self._emit_ui(file_name, "Saving vectors to PostgreSQL...")
                for chunk, vector in zip(chunks, vectors):
                    chunk_id = uuid7()
                    vector_str = f"[{','.join(map(str, vector))}]"
                    await self.db.execute(
                        """
                            INSERT INTO document_chunks
                                (id, document_id, chunk_text, embedding, page_number, chunk_type)
                            VALUES (%s, %s, %s, %s, %s, %s)
                            """,
                        (str(chunk_id), str(doc_id),
                         chunk["text"], vector_str, chunk["page"], chunk["type"]),
                    )

            await self.db.execute(
                "UPDATE documents SET status = 'completed', message = 'Vaulted successfully' WHERE id = %s",
                (str(doc_id),)
            )
            await self.db.commit()

            total_time_end = perf_counter()
            total_duration = total_time_end - total_time_start

            await self.log_benchmark(
                doc_id=str(doc_id),
                file_name=file_name,
                file_size=file_size,
                partition_time=partition_duration,
                chunking_time=chunking_duration,
                embedding_time=embedding_duration,
                total_time=total_duration,
                num_chunks=len(chunks)
            )

            await self._emit_ui(file_name, f"Vaulted successfully | Total: {total_duration:.2f}s")

        except Exception as e:
            await self.db.rollback()
            await self._emit_ui(file_name, "Failed!", "error", f"Processing Error: {str(e)}")

            try:
                if file_path and file_path.exists():
                    file_path.unlink()
                    await self._emit_ui(file_name, f"Cleaned up corrupted file: {file_path.name}")
            except Exception as cleanup_error:
                await self._emit_ui(file_name, "Cleanup Failed", "error", f"Failed to delete file {file_path}: {cleanup_error}")

            error_msg = f"Failed: {str(e)}"[:100]
            await self.db.execute(
                "UPDATE documents SET status = 'error', message = %s WHERE id = %s",
                (error_msg, str(doc_id))
            )
            await self.db.commit()
