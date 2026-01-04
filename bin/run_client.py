import sys
import os
from pathlib import Path

src_path = (Path(os.path.dirname(__file__)) / "..").resolve()
sys.path.append(str(src_path))


import asyncio
import requests
from src.game_client.client import GameClient
import websockets
import json
import datetime
from config import API_REMOTE_URL, WS_REMOTE_URL
import argparse
from src.common.logging import logger


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("player_name", type=str)
    return parser.parse_args()


def get_player_id(player_name: str) -> str:
    """Get a new or existing player id from the http api"""
    r = requests.post(f"{API_REMOTE_URL}/players", json={"username": player_name})
    r.raise_for_status()
    return r.json()["id"]


async def main():
    args = parse_args()

    logger.info(
        f"""urls:
- api: {API_REMOTE_URL}
- ws: {WS_REMOTE_URL}"""
    )

    # get or create a player id
    try:
        player_id = get_player_id(args.player_name)
    except requests.exceptions.HTTPError as e:
        logger.info(f"Could not contact the game server, error: {e}")
        sys.exit(1)

    try:
        async with websockets.connect(WS_REMOTE_URL) as websocket:
            # Send authentication
            await websocket.send(json.dumps({"player_id": player_id}))

            # Receive welcome message
            welcome = await websocket.recv()
            logger.info(f"Received: {welcome}")

            # socket and http server reachable, initialize pygame
            game_client = GameClient(player_id, args.player_name, websocket)
            await game_client.run()

    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
