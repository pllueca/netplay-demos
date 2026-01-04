from pydantic import BaseModel, Field
import uuid

from src.common.component import (
    PositionComponent,
    SerializePlayerJsonComponent,
    SerializeNPCJsonComponent,
)


class Entity(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))


class CharacterEntity(Entity, PositionComponent):
    pass


class PlayerEntity(CharacterEntity, SerializePlayerJsonComponent):
    player_id: str
    username: str = Field(default="Unknown Player")


class NPCEntity(CharacterEntity, SerializeNPCJsonComponent):
    type: str
