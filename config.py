import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Database configuration
SQLITE_DB_URL = os.getenv("SQLITE_DB_URL", "sqlite:///./game_server.db")

# Redis configuration
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)

# API configuration
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", 8000))
API_URL = f"http://{API_HOST}:{API_PORT}"

# WebSocket configuration
WS_HOST = os.getenv("WS_HOST", "0.0.0.0")
WS_PORT = int(os.getenv("WS_PORT", 8001))
WS_URL = f"ws://{WS_HOST}:{WS_PORT}"

# Player configuration
PLAYER_TIMEOUT_SECONDS = int(os.getenv("PLAYER_TIMEOUT_SECONDS", 300))  # 5 minutes
