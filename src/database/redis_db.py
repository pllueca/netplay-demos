import json
from datetime import datetime

import redis

from config import REDIS_DB, REDIS_HOST, REDIS_PASSWORD, REDIS_PORT
from src.common.common_models import PositionData

# Redis key prefixes
PLAYER_PREFIX = "player:"
ONLINE_PLAYERS_SET = "online_players"
NUM_ONLINE_PLAYERS = "num_online_players"


class RedisClient:
    def __init__(self):
        self.redis_client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            password=REDIS_PASSWORD,
            decode_responses=True,
        )

        print("connected to redis server")

    def is_redis_available(self):
        """Check if Redis is available"""
        try:
            return self.redis_client.ping()
        except redis.exceptions.ConnectionError:
            return False

    def add_player_to_online(self, player_id: str):
        """Add player to the set of online players"""
        self.redis_client.sadd(ONLINE_PLAYERS_SET, player_id)

    def remove_player_from_online(self, player_id: str):
        """Remove player from the set of online players"""
        self.redis_client.srem(ONLINE_PLAYERS_SET, player_id)

    def get_online_players(self) -> set[str]:
        """Get all online players"""
        return self.redis_client.smembers(ONLINE_PLAYERS_SET)

    def save_player_position(
        self,
        player_id: str,
        position_data: PositionData,
    ) -> None:
        """Save player position to Redis"""
        key = f"{PLAYER_PREFIX}{player_id}:position"
        position_data = {
            "last_update": datetime.now().isoformat(),
            "pos_x": position_data.pos_x,
            "pos_y": position_data.pos_y,
        }
        self.redis_client.set(key, json.dumps(position_data))
