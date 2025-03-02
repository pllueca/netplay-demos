from pydantic import BaseModel

from common.component import PositionComponent, SerializePlayerJsonComponent


class Entity(BaseModel):
    id: int


class CharacterEntity(Entity, PositionComponent, SerializePlayerJsonComponent):
    pass


class PlayerEntity(CharacterEntity):
    pass


class NPCEntity(CharacterEntity):
    pass
