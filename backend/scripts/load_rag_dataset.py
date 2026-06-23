import sys
import os
import glob
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from dotenv import load_dotenv
from psycopg_pool import AsyncConnectionPool
from fastapi import UploadFile
from openai import AsyncOpenAI
from collections import Counter

# --- Rich UI Imports ---
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich.console import Group

from services.storage import StorageService
from services.embeddings import EmbeddingsService

load_dotenv()

class load_rag_dataset:
    limit = 10000  # Limit to 10k files for testing

    def __init__(self):
        self.db_pool: AsyncConnectionPool = None
        self.openai_client: AsyncOpenAI = None
        self.embeddings: EmbeddingsService = None
        self.dataset_path = None
        self.file_paths = []

    @asynccontextmanager
    async def initialize(self):
        print("[Dataset Loader] Initializing dataset loader")
        self.dataset_path = Path(os.getenv("DATASET_PATH", "C:\\Users\\maddy\\Documents\\hawkins\\document-management-system\\EnterpriseRAG-dataset-all_documents"))
        print(f"[Dataset Loader] Dataset path set to: {self.dataset_path}")
        print(f"[Dataset Loader] Searching for .txt files in {self.dataset_path}")
        
        self.file_paths = glob.glob(str(self.dataset_path / "**/*.txt"), recursive=True)[:self.limit]
        
        print(f"[Dataset Loader] Found {len(self.file_paths)} .txt files within limit")
        print("[Dataset Loader] Initializing database connection pool")
        
        async with AsyncConnectionPool(conninfo=os.getenv("POSTGRES_DATABASE_URL"), min_size=1, max_size=200) as pool:
            self.db_pool = pool
            self.openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            self.embeddings = EmbeddingsService(self.openai_client)
            yield

    async def upload_file(self, file_path_str: str, worker_id: int, ui_queue: asyncio.Queue):
        if file_path_str.endswith("questions.jsonl"):
            return
            
        file_path = Path(file_path_str)
        user_id = "278d2e89-3c33-47fa-be95-3f5f9f6b94da"
        relative_path = file_path.parent.relative_to(self.dataset_path)
        category = relative_path.as_posix() if relative_path != Path(".") else None

        await ui_queue.put({"worker_id": worker_id, "file": file_path.name, "status": "Reading file from disk...", "type": "progress"})

        with open(file_path_str, "rb") as f:
            file = UploadFile(filename=os.path.basename(file_path), file=f)
            async with self.db_pool.connection() as conn:
                # Pass the ui_queue and worker_id into the storage service!
                storage = StorageService("./storage", conn, self.embeddings, ui_queue, worker_id)
                
                await ui_queue.put({"worker_id": worker_id, "file": file.filename, "status": "Checking database for duplicates...", "type": "progress"})
                doc_id, is_new_file = await storage.save(file, user_id, category)
                
                if is_new_file:
                    await storage.process_document(doc_id, file.filename, category)
                else:
                    await ui_queue.put({"worker_id": worker_id, "file": file.filename, "status": "Skipped (Duplicate)", "type": "progress"})
                    await asyncio.sleep(0.1) # Brief pause so you can visually see the skip


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    loader = load_rag_dataset()

    # --- Shared State for the UI ---
    total_files = 0
    completed_files = 0
    active_tasks = {i: {"file": "Idle", "status": ""} for i in range(1, 21)} 
    error_counts = Counter() 
    
    # Event queues
    ui_queue = asyncio.Queue()
    worker_queue = asyncio.Queue()
    for i in range(1, 21):
        worker_queue.put_nowait(i)

    def generate_ui() -> Group:
        """Generates the layout to be drawn to the terminal."""
        progress_pct = (completed_files / total_files * 100) if total_files > 0 else 0
        progress_text = f"[bold cyan]Overall Progress:[/bold cyan] [{completed_files}/{total_files}] files ({progress_pct:.1f}%)"
        
        table = Table(show_header=True, header_style="bold magenta", expand=True)
        table.add_column("Worker Slot", style="dim", width=15)
        table.add_column("File")
        table.add_column("Current Status")
        
        for worker_id, info in active_tasks.items():
            file_name = info["file"]
            status = info["status"]
            if file_name == "Idle":
                table.add_row(f"Worker {worker_id}", "[dim]Idle[/dim]", "")
            else:
                table.add_row(f"Worker {worker_id}", f"[green]{file_name}[/green]", f"[yellow]{status}[/yellow]")
        
        if not error_counts:
            err_text = "[green]No errors encountered yet.[/green]"
        else:
            err_lines = [f"[bold red]{count}x[/bold red] - {msg}" for msg, count in error_counts.items()]
            err_text = "\n".join(err_lines)
            
        return Group(
            Panel(progress_text, border_style="cyan"),
            Panel(table, title="Active Processing Pipelines (Concurrency: 20)", border_style="magenta"),
            Panel(err_text, title=f"Accumulated Errors ({sum(error_counts.values())})", border_style="red")
        )

    async def process_with_semaphore(sem: asyncio.Semaphore, file_path: str):
        global completed_files
        worker_id = await worker_queue.get()
        
        async with sem:
            try:
                # Pass UI coordinates down the chain
                await loader.upload_file(file_path, worker_id, ui_queue)
            except Exception as e:
                err_signature = f"{type(e).__name__}: {str(e)}"
                await ui_queue.put({"type": "error", "error_msg": err_signature})
            finally:
                completed_files += 1
                # Reset slot to idle
                await ui_queue.put({"worker_id": worker_id, "file": "Idle", "status": "", "type": "progress"})
                worker_queue.put_nowait(worker_id) 

    async def ui_updater(live: Live):
        """Background task that instantly applies events to the UI grid."""
        while completed_files < total_files:
            while not ui_queue.empty():
                event = ui_queue.get_nowait()
                if event["type"] == "progress":
                    active_tasks[event["worker_id"]] = {"file": event["file"], "status": event["status"]}
                elif event["type"] == "error":
                    error_counts[event["error_msg"]] += 1
                    
            live.update(generate_ui())
            await asyncio.sleep(0.1) # 10 FPS refresh
            
        live.update(generate_ui()) # Final render on completion

    async def main():
        global total_files
        async with loader.initialize():
            total_files = len(loader.file_paths)
            sem = asyncio.Semaphore(20) 
            
            with Live(generate_ui(), refresh_per_second=10, transient=False) as live:
                ui_task = asyncio.create_task(ui_updater(live))
                
                tasks = [
                    asyncio.create_task(process_with_semaphore(sem, file_path))
                    for file_path in loader.file_paths
                ]
                
                await asyncio.gather(*tasks, return_exceptions=True)
                await ui_task 

    asyncio.run(main())