import json
import redis
from datetime import datetime
from config import REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_PASSWORD


# Redis key prefixes
PLAYER_PREFIX = "player:"
ONLINE_PLAYERS_SET = "online_players"
NUM_ONLINE_PLAYERS = "num_online_players"


class RedisClient:
    def __init__(self):
        # Create Redis connection
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
        # redis_client.sadd(ONLINE_PLAYERS_SET, player_id)
        current_players = self.redis_client.get(NUM_ONLINE_PLAYERS) or "0"
        self.redis_client.set(NUM_ONLINE_PLAYERS, int(current_players) + 1)

    def remove_player_from_online(self, player_id: str):
        """Remove player from the set of online players"""
        # redis_client.srem(ONLINE_PLAYERS_SET, player_id)
        self.redis_client.decr(NUM_ONLINE_PLAYERS)

    def get_online_players(self):
        """Get all online players"""
        # return redis_client.smembers(ONLINE_PLAYERS_SET)
        return self.redis_client.get(NUM_ONLINE_PLAYERS)
