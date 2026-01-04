from datetime import datetime
from typing import List
import uuid

import redis

from config import REDIS_DB, REDIS_HOST, REDIS_PASSWORD, REDIS_PORT
from src.common.common_models import NpcData, PositionData

# Redis key prefixes
PLAYER_PREFIX = "player:"
ONLINE_PLAYERS_SET = "online_players"
NUM_ONLINE_PLAYERS = "num_online_players"
NPC_PREFIX = "npc:"
NPCS_SET = "npcs"


class RedisClient:
    def __init__(self):
        self.redis_client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            password=REDIS_PASSWORD,
            decode_responses=False,
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
        self.redis_client.set(key, str(position_data))

    def create_npc(self, npc_type: str, pos_x: float, pos_y: float) -> NpcData:
        """Create a new NPC and save it to Redis"""
        npc_id = str(uuid.uuid4())
        key = f"{NPC_PREFIX}{npc_id}"
        npc_data = NpcData(id=npc_id, type=npc_type, pos_x=pos_x, pos_y=pos_y)
        self.redis_client.set(key, npc_data.SerializeToString())
        self.redis_client.sadd(NPCS_SET, npc_id)
        return npc_data

    def save_npc_position(self, npc_id: str, pos_x: float, pos_y: float):
        """Save NPC position to Redis"""
        key = f"{NPC_PREFIX}{npc_id}"
        npc_data = self.get_npc(npc_id)
        if npc_data:
            npc_data.pos_x = pos_x
            npc_data.pos_y = pos_y
            self.redis_client.set(key, npc_data.SerializeToString())

    def get_npc(self, npc_id: str) -> NpcData | None:
        """Get NPC data from Redis"""
        key = f"{NPC_PREFIX}{npc_id}"
        npc_data_str = self.redis_client.get(key)
        if npc_data_str:
            npc_data = NpcData()
            npc_data.ParseFromString(npc_data_str)
            return npc_data
        return None

    def get_npcs(self) -> List[NpcData]:
        """Get all NPCs from Redis"""
        npc_ids = self.redis_client.smembers(NPCS_SET)
        npcs = []
        for npc_id in npc_ids:
            npc_data = self.get_npc(npc_id)
            if npc_data:
                npcs.append(npc_data)
        return npcs
