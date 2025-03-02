import sys

sys.path.append("/Users/pllueca/Code/netplay")

import asyncio
from src.game_client.client import GameClient


async def main():
    game = GameClient()
    await game.run()


if __name__ == "__main__":
    print("foo")
    asyncio.run(main())
