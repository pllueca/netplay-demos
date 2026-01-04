import json
from src.common.common_models import (
    PositionData,
)
from pydantic import BaseModel


class PositionComponent(BaseModel):
    pos_x: float
    pos_y: float

    def update_position(self, position: PositionData) -> None:
        self.pos_x = position.pos_x
        self.pos_y = position.pos_y


class SerializePlayerJsonComponent:
    def to_json_dict(self) -> dict:
        """subclasses should implement"""
        return {
            "id": self.id,
            "pos_x": self.pos_x,
            "pos_y": self.pos_y,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_json_dict())


class SerializeNPCJsonComponent:
    def to_json_dict(self) -> dict:
        """subclasses should implement"""
        return {
            "id": self.id,
            "type": self.type,
            "pos_x": self.pos_x,
            "pos_y": self.pos_y,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_json_dict())

