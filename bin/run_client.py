import sys

sys.path.append("/Users/pllueca/Code/netplay")

import asyncio
import requests
from src.game_client.client import GameClient
import websockets
import json
import datetime
from config import API_REMOTE_URL, WS_REMOTE_URL
import argparse
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("player_name", type=str)
    return parser.parse_args()


def get_player_id(player_name: str) -> int:
    """Get a new or existing player id from the http api"""
    r = requests.post(f"{API_REMOTE_URL}/players", json={"username": player_name})
    r.raise_for_status()
    return int(r.json()["id"])


async def main():
    args = parse_args()

    # get or create a player id
    try:
        player_id = get_player_id(args.player_name)
    except requests.exceptions.HTTPError as e:
        print(f"Could not contact the game server, error: {e}")
        sys.exit(1)

    print(player_id)

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

            # position = {"x": 0, "y": 0, "z": 0}

            # while True:
            #     # Update position (simulating movement)
            #     position["x"] += 1
            #     position["y"] += 0.5

            #     # Send position update
            #     await websocket.send(
            #         json.dumps({"type": "position_update", "data": position})
            #     )

            #     # Send ping
            #     await websocket.send(
            #         json.dumps(
            #             {"type": "ping", "timestamp": datetime.now().isoformat()}
            #         )
            #     )

            #     # Receive messages
            #     try:
            #         message = await asyncio.wait_for(websocket.recv(), timeout=0.1)
            #         logger.info(f"Received: {message}")
            #     except asyncio.TimeoutError:
            #         pass

            #     # Wait before next update
            #     await asyncio.sleep(1)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")


if __name__ == "__main__":
    print("foo")
    asyncio.run(main())
