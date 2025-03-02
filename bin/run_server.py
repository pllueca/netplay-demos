import sys

sys.path.append("/Users/pllueca/Code/netplay")

from src.game_server.server import main
import asyncio

if __name__ == "__main__":
    asyncio.run(main())
