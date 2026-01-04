import random
from typing import List
import uuid
from src.common.entity import PlayerEntity, NPCEntity, Entity

from src.common.common_models import (
    MapData,
    PositionData,
)


class GameState:
    entities: dict[str, Entity]
    player_ids: set[str]
    npc_ids: set[str]
    map: List[List[bool]]

    # World dimensions
    WORLD_WIDTH: int = 100
    WORLD_HEIGHT: int = 100

    # game constants
    NPC_UPDATES_PER_SECOND = 30

    def __init__(self):
        self.entities = {}
        self.player_ids = set()
        self.npc_ids = set()
        self.map = []

    def generate_map(self, width: int, height: int, blocked_probability: float = 0.2):
        self.map = [
            [random.random() > blocked_probability for _ in range(width)]
            for _ in range(height)
        ]

    def get_map_data(self) -> MapData:
        return MapData(
            width=len(self.map[0]), height=len(self.map), tiles=self.map
        )

    def add_player(self, player: PlayerEntity):
        self.entities[player.id] = player
        self.player_ids.add(player.id)

    def add_npc(self, npc: NPCEntity) -> None:
        self.entities[npc.id] = npc
        self.npc_ids.add(npc.id)

    def delete_player(self, player_id: str) -> None:
        if player_id not in self.entities or player_id not in self.player_ids:
            raise KeyError()
        del self.entities[player_id]
        self.player_ids.remove(player_id)

    def update_entity_position(
        self, entity_id: str, new_position: PositionData
    ) -> None:
        if entity_id not in self.entities:
            raise KeyError()

        if not (
            0 <= new_position.pos_x <= self.WORLD_WIDTH
            and 0 <= new_position.pos_x <= self.WORLD_HEIGHT
        ):
            raise ValueError("invalid position")
        self.entities[entity_id].update_position(new_position)

    def game_tick(self) -> None:
        """execute 1 world update.

        * Npcs move"""
        for npc_id in self.npc_ids:
            npc_entity = self.entities[npc_id]
            npc_entity.pos_x += random.randint(-1, 1)
            npc_entity.pos_y += random.randint(-1, 1)
