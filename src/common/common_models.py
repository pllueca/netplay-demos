from pydantic import BaseModel
from typing import List


class MapData(BaseModel):
    width: int
    height: int
    tiles: List[List[bool]]


class NpcData(BaseModel):
    id: str
    type: str
    pos_x: float
    pos_y: float


class PositionData(BaseModel):
    pos_x: float
    pos_y: float


class PositionUpdateMessage(BaseModel):
    player_id: str  # uuid
    position_data: PositionData


class NpcPositionUpdateMessage(BaseModel):
    npc_id: str  # uuid
    position_data: PositionData


class NewPlayerConnectedMessage(BaseModel):
    player_id: str  # uuid
    username: str


class PlayerDisconectedMessage(BaseModel):
    player_id: str  # uuid


class SocketMessagePlayerToServer(BaseModel):
    type: str
    data: (
        PositionUpdateMessage
        | NewPlayerConnectedMessage
        | PlayerDisconectedMessage
        | List[NpcPositionUpdateMessage]
        | MapData
    )
