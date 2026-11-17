import fitz  # PyMuPDF
import base64
import asyncio
from typing import List, Dict
from src.utils.logger import logger

def _process_pdf_sync(pdf_path: str, max_pages: int = None) -> List[Dict[str, str]]:
    """
    Synchronous function to process the PDF. 
    We run this in a background thread because PyMuPDF is CPU-bound.
    """
    logger.info(f"Starting PDF image extraction for: {pdf_path}")
    encoded_pages = []
    
    try:
        # Open the PDF file
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        pages_to_process = min(total_pages, max_pages) if max_pages else total_pages
        
        for page_num in range(pages_to_process):
            page = doc.load_page(page_num)
            
            # Matrix scales the image up for better VLM reading
            # 2.0 (200%) is the sweet spot between OCR quality and RAM usage
            zoom_matrix = fitz.Matrix(2.0, 2.0)
            pix = page.get_pixmap(matrix=zoom_matrix)
            
            # Convert raw image bytes to a base64 string
            img_base64 = base64.b64encode(pix.tobytes("png")).decode("utf-8")
            
            encoded_pages.append({
                "page_number": page_num + 1,
                "image_base64": img_base64
            })
            
        logger.info(f"Successfully processed {len(encoded_pages)} pages from {pdf_path}")
        return encoded_pages
        
    except Exception as e:
        logger.error(f"Failed to process PDF {pdf_path}: {e}")
        raise
    finally:
        # Always ensure the document is closed to prevent memory leaks
        if 'doc' in locals():
            doc.close()

async def extract_pdf_pages(pdf_path: str, max_pages: int = None) -> List[Dict[str, str]]:
    """
    Async wrapper that offloads the CPU-heavy PDF rendering to a background thread pool.
    """
    # asyncio.to_thread automatically dispatches to the default ThreadPoolExecutor
    logger.debug(f"Offloading {pdf_path} to thread pool...")
    return await asyncio.to_thread(_process_pdf_sync, pdf_path, max_pages)