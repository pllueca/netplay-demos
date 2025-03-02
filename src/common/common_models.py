from typing import Any, LiteralString, TypedDict

from pydantic import BaseModel


class PositionData(BaseModel):
    pos_x: float
    pos_y: float


class PositionUpdateMessage(BaseModel):
    player_id: int
    position_data: PositionData


class NewPlayerConnectedMessage(BaseModel):
    player_id: int
    username: str


class PlayerDisconectedMessage(BaseModel):
    player_id: int


class SocketMessagePlayerToServer(BaseModel):
    type: str
    data: PositionUpdateMessage | NewPlayerConnectedMessage | PlayerDisconectedMessage
