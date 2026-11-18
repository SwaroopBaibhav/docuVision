import aiohttp
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential
from src.utils.logger import logger
from src.utils.schemas import ExtractedData

OLLAMA_URL = "http://localhost:11434/api/generate"
# Assuming you have pulled this. You can swap to llava or minicpm-v
MODEL_NAME = "qwen2.5vl:latest" 

# The Semaphore: The true hero of backend AI.
# This ensures we NEVER send more than 2 images to the GPU at the exact same time.
# If 100 pages arrive, 98 wait in line without crashing your machine.
MAX_CONCURRENT_REQUESTS = 2
gpu_semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

PROMPT = """Extract information from this image. 
You MUST return ONLY valid JSON matching this schema:
{
    "document_id": "string",
    "total_amount": 0.0,
    "date": "string",
    "key_entities": ["string"]
}
Do not include markdown blocks or conversational text.
"""

@retry(
    stop=stop_after_attempt(3), 
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True
)
async def process_image_with_vlm(base64_image: str, page_num: int) -> str:
    """
    Sends the image to Ollama. 
    Retries automatically up to 3 times if the AI hallucinates or the API drops.
    """
    async with gpu_semaphore:
        logger.debug(f"Acquired GPU semaphore for page {page_num}. Sending to VLM...")
        
        payload = {
            "model": MODEL_NAME,
            "prompt": PROMPT,
            "stream": False,
            "images": [base64_image],
            "format": "json" # Forces Ollama's engine to output parseable JSON
        }
        
        # We create a new session here for the example, but in a massive production app, 
        # you'd pass a global aiohttp.ClientSession() to reuse TCP connections.
        async with aiohttp.ClientSession() as session:
            async with session.post(OLLAMA_URL, json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Ollama API Error: {error_text}")
                    raise Exception(f"VLM returned status {response.status}")
                
                data = await response.json()
                raw_response = data.get("response", "{}")
                
                # Validation Step
                try:
                    # If the AI missed a field or returned a string instead of a float,
                    # Pydantic fails immediately.
                    parsed_data = ExtractedData.model_validate_json(raw_response)
                    logger.info(f"Page {page_num}: Successfully extracted and validated data.")
                    return parsed_data.model_dump_json()
                
                except Exception as e:
                    logger.warning(f"Page {page_num}: AI returned malformed JSON, triggering retry. Error: {e}")
                    # Raising the error is what tells Tenacity to retry this function
                    raise