import aiosqlite
from src.utils.logger import logger

DB_PATH = "docuvision.db"

async def init_db():
    """Initializes the database with optimizations for concurrent workloads."""
    logger.info("Initializing SQLite database connection...")
    
    async with aiosqlite.connect(DB_PATH) as db:
        # 1. Enable Write-Ahead Logging (CRITICAL for concurrency)
        await db.execute("PRAGMA journal_mode=WAL;")
        
        # 2. Faster synchronization (safe enough for WAL)
        await db.execute("PRAGMA synchronous=NORMAL;")
        
        # 3. Increase cache size for better read performance
        await db.execute("PRAGMA cache_size=-64000;") # 64MB cache
        
        # Create our core table for the extracted JSON data
        await db.execute("""
            CREATE TABLE IF NOT EXISTS extracted_pages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_name TEXT NOT NULL,
                page_number INTEGER NOT NULL,
                extracted_json TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()
    
    logger.info("Database initialized successfully with WAL mode.")

async def get_db_connection() -> aiosqlite.Connection:
    """Returns a fresh, async database connection."""
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row # Returns dict-like rows instead of tuples
    return db