import sys

sys.path.append("/Users/pllueca/Code/netplay")
import asyncio
import uvicorn
import logging
from threading import Thread

from config import API_HOST, API_PORT, WS_HOST, WS_PORT
from api.http_server import app

# from api.websocket_server import start_websocket_server

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Run FastAPI in a separate thread
def run_fastapi():
    uvicorn.run(app, host=API_HOST, port=API_PORT)


# Main function to start both servers
async def main():
    logger.info("Starting Game Server...")

    # Start FastAPI HTTP server in a separate thread
    fastapi_thread = Thread(target=run_fastapi)
    fastapi_thread.daemon = True
    fastapi_thread.start()
    logger.info(f"HTTP server started on http://{API_HOST}:{API_PORT}")

    # Start WebSocket server in the main thread
    # ws_server = await start_websocket_server(WS_HOST, WS_PORT)
    #
    # Keep the server running
    await asyncio.Future()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down Game Server...")
