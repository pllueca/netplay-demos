import sys

sys.path.append("/Users/pllueca/Code/netplay")

import asyncio
import requests
from src.game_client.client import GameClient
from config import API_URL
import argparse


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("player_name", nargs=1, type=str, required=True)
    return parser.parse_args()


def get_player_id(player_name: str) -> int:
    """Get a new or existing player id from the http api"""
    r = requests.post(f"{API_URL}/players", json={"username": player_name})
    r.raise_for_status()
    return int(r.json()["id"])


async def main():
    args = parse_args()
    player_id = get_player_id(args.player_name)
    game = GameClient(player_id)
    await game.run()


if __name__ == "__main__":
    print("foo")
    asyncio.run(main())
