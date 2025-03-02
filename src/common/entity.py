from pydantic import BaseModel

from common.component import PositionComponent, SerializePlayerJsonComponent


class Entity(BaseModel):
    id: int


class CharacterEntity(Entity, PositionComponent):
    pass


class PlayerEntity(CharacterEntity, SerializePlayerJsonComponent):
    name: str


class NPCEntity(CharacterEntity):
    pass
