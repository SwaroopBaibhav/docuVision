# docuVision 🔍

An open-source, asynchronous multimodal ETL pipeline that transforms PDFs into structured data using Qwen Vision-Language Models.

### Key Highlights
- **Parallel PDF Processing:** PyMuPDF with `ThreadPoolExecutor` for non-blocking document rendering.
- **Async AI Inference:** `aiohttp` for asynchronous communication with Qwen VLM.
- **GPU Resource Management:** `asyncio.Semaphore` to control inference concurrency and prevent GPU memory exhaustion.
- **Efficient Data Pipeline:** Async Producer-Consumer architecture for decoupled processing.
- **Optimized Storage:** SQLite with WAL mode for efficient data persistence.

**Built with Python, asyncio, PyMuPDF, Qwen VLM, and SQLite.**