import sys
from loguru import logger

def setup_logger():
    # Remove the default logger
    logger.remove()
    
    # Add a beautiful, colored console logger
    logger.add(
        sys.stderr, 
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
        level="INFO",
        enqueue=True  # THIS IS THE MAGIC WORD
    )
    
    # Add a rotating file logger for debugging
    logger.add(
        "logs/docuvision.log", 
        rotation="10 MB", 
        retention="1 week", 
        level="DEBUG",
        enqueue=True 
    )

setup_logger()