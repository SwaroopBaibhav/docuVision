import asyncio
import os
from pathlib import Path
from typing import Optional

from src.utils.logger import logger
from src.db.database import init_db, get_db_connection
from src.utils.pdf_processor import extract_pdf_pages
from src.utils.vlm_client import process_image_with_vlm

# --- WORKERS ---

async def vlm_worker(worker_id: int, image_queue: asyncio.Queue, db_queue: asyncio.Queue):
    """Pulls images from the queue, hits the VLM, and passes validated data to the DB queue."""
    logger.debug(f"VLM Worker-{worker_id} started.")
    while True:
        try:
            # Get the next page from the queue
            task = await image_queue.get()
            
            file_name = task["file_name"]
            page_num = task["page_number"]
            image_base64 = task["image_base64"]
            
            logger.info(f"Worker-{worker_id} processing {file_name} - Page {page_num}")
            
            # Hit the AI (retries and concurrency limits are handled inside this function!)
            extracted_json = await process_image_with_vlm(image_base64, page_num)
            
            # Send the successful result to the database writer
            await db_queue.put({
                "file_name": file_name,
                "page_number": page_num,
                "extracted_json": extracted_json,
                "status": "SUCCESS"
            })
            
        except Exception as e:
            logger.error(f"Worker-{worker_id} failed on page {page_num}: {e}")
            await db_queue.put({
                "file_name": file_name,
                "page_number": page_num,
                "extracted_json": "{}",
                "status": f"FAILED: {str(e)}"
            })
        finally:
            # Tell the queue this specific task is complete
            image_queue.task_done()


async def db_writer_worker(db_queue: asyncio.Queue):
    """A dedicated worker that ensures writes to SQLite happen smoothly."""
    logger.debug("Database Writer Worker started.")
    db = await get_db_connection()
    
    try:
        while True:
            record = await db_queue.get()
            
            # Poison pill / Sentinel value to gracefully shut down the worker
            if record is None:
                db_queue.task_done()
                break
                
            await db.execute(
                """
                INSERT INTO extracted_pages (file_name, page_number, extracted_json, status)
                VALUES (?, ?, ?, ?)
                """,
                (record["file_name"], record["page_number"], record["extracted_json"], record["status"])
            )
            await db.commit()
            logger.debug(f"Saved {record['file_name']} page {record['page_number']} to database.")
            
            db_queue.task_done()
    finally:
        await db.close()
        logger.debug("Database Writer Worker safely shut down.")


# --- MAIN ORCHESTRATOR ---

async def process_document(pdf_path: str, num_workers: int = 4):
    """The main pipeline orchestrator."""
    await init_db()
    
    file_name = Path(pdf_path).name
    if not os.path.exists(pdf_path):
        logger.error(f"File not found: {pdf_path}")
        return

    # 1. Initialize our async queues
    image_queue = asyncio.Queue()
    db_queue = asyncio.Queue()
    
    # 2. Fire up the background workers
    # Start the DB writer
    db_task = asyncio.create_task(db_writer_worker(db_queue))
    
    # Start the VLM workers
    worker_tasks = []
    for i in range(num_workers):
        task = asyncio.create_task(vlm_worker(i, image_queue, db_queue))
        worker_tasks.append(task)
        
    # 3. The Producer: Extract pages and fill the image queue
    logger.info(f"Extracting pages from {file_name}...")
    pages = await extract_pdf_pages(pdf_path) # Remember, this runs in a thread pool!
    
    for page in pages:
        # Add metadata before pushing to queue
        page["file_name"] = file_name
        await image_queue.put(page)
        
    logger.info(f"Pushed {len(pages)} pages to the processing queue.")
    
    # 4. Wait for all images to be processed
    await image_queue.join()
    logger.info("All images processed by VLM workers.")
    
    # 5. Shut down workers gracefully
    # Cancel VLM workers (they are waiting for new items via while True)
    for w in worker_tasks:
        w.cancel()
        
    # Send the poison pill to the DB worker so it writes the last item and exits
    await db_queue.put(None)
    
    # Wait for the DB to finish its final writes
    await db_queue.join()
    await db_task
    
    logger.success(f"Pipeline complete for {file_name}. Data saved to SQLite.")

import typer
from rich.console import Console

app = typer.Typer(help="DocuVision: Async VLM Document Extraction Pipeline")
console = Console()

@app.command()
def ingest(
    pdf_path: str = typer.Argument(..., help="Path to the PDF document"),
    workers: int = typer.Option(4, "--workers", "-w", help="Number of concurrent VLM workers")
):
    """
    Extracts pages from a PDF and processes them concurrently using a local Vision-Language Model.
    """
    console.print(f"[bold cyan]Starting DocuVision Pipeline[/bold cyan] for {pdf_path}")
    console.print(f"[yellow]Concurrency Level:[/yellow] {workers} Workers")
    
    # Run our async orchestrator
    asyncio.run(process_document(pdf_path, num_workers=workers))
    
    console.print("[bold green]Pipeline execution completed![/bold green]")

if __name__ == "__main__":
    app()