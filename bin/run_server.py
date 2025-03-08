import sys
import os
from pathlib import Path

src_path = (Path(os.path.dirname(__file__)) / "..").resolve()
sys.path.append(str(src_path))

import asyncio
import logging
from threading import Thread

import uvicorn

from config import API_HOST, API_PORT, WS_HOST, WS_PORT
from src.game_server.api.http_server import app
from src.game_server.api.websocket_server import start_websocket_server
from src.common.logging import logger


def run_fastapi():
    uvicorn.run(app, host=API_HOST, port=API_PORT)


async def main():
    logger.info("Starting Game Server...")

    fastapi_thread = Thread(target=run_fastapi)
    fastapi_thread.daemon = True
    fastapi_thread.start()
    logger.info(f"HTTP server started on http://{API_HOST}:{API_PORT}")

    _ws_server = await start_websocket_server(WS_HOST, WS_PORT)
    await asyncio.Future()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down Game Server...")
