"""Main Entry Point - VC Due Diligence API Server"""

import os
import sys
from pathlib import Path

# Add backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

# Load environment variables
from dotenv import load_dotenv

env_path = backend_dir.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    # Try backend/.env
    backend_env = backend_dir / ".env"
    if backend_env.exists():
        load_dotenv(backend_env)

# Configure logging
from loguru import logger
import sys

logger.remove()  # Remove default handler
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level=os.getenv("LOG_LEVEL", "INFO"),
)

# Import app
from api.app import app

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "0.0.0.0")

    logger.info(f"Starting server on {host}:{port}")

    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=os.getenv("ENVIRONMENT", "production") == "development",
        log_level=os.getenv("LOG_LEVEL", "info").lower(),
    )
