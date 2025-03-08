from src.common.entity import PlayerEntity, NPCEntity, Entity

from src.common.common_models import (
    PositionData,
)


class GameState:
    entities: dict[int, Entity]
    player_ids: set[int]
    npc_ids: set[int]

    # World dimensions
    WORLD_WIDTH: int = 100
    WORLD_HEIGHT: int = 100

    def __init__(self):
        self.entities = {}
        self.player_ids = set()
        self.npc_ids = set()

    def add_player(self, player: PlayerEntity):
        self.entities[player.id] = player
        self.player_ids.add(player.id)

    def delete_player(self, player_id: int) -> None:
        if player_id not in self.entities or player_id not in self.player_ids:
            raise KeyError()
        del self.entities[player_id]
        self.player_ids.remove(player_id)

    def update_entity_position(
        self, entity_id: int, new_position: PositionData
    ) -> None:
        if entity_id not in self.entities:
            raise KeyError()

        if not (
            0 <= new_position.pos_x <= self.WORLD_WIDTH
            and 0 <= new_position.pos_x <= self.WORLD_HEIGHT
        ):
            raise ValueError("invalid position")
        self.entities[entity_id].update_position(new_position)
