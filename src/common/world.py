from src.common.entity import PlayerEntity, NPCEntity, Entity


class GameState:
    entities: dict[int, Entity]
    player_ids: set[int]
    npc_ids: set[int]

    def __init__(self):
        self.entities = {}
        self.player_ids = set()
        self.npc_ids = set()

    def add_player(self, player: PlayerEntity):
        self.entities[player.id] = player
        self.player_ids.add(player.id)
