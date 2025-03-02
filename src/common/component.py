import json


class PositionComponent:
    pos_x: float
    pos_y: float


class SerializePlayerJsonComponent:

    def to_json_dict(self) -> dict:
        """subclasses should implement"""
        return {
            "id": self.id,
            "player_id": self.player_id,
            "pos_x": self.pos_x,
            "pos_y": self.pos_y,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_json_dict())
