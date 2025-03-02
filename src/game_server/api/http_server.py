from datetime import datetime
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database.models import Player
from database.redis_db import RedisClient
from database.sqlite_db import get_db_session

redis_client = RedisClient()

app = FastAPI(title="Game Server API")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models for API
class PlayerCreate(BaseModel):
    username: str


class PlayerResponse(BaseModel):
    id: int
    username: str
    created_at: datetime
    last_seen: datetime


class OnlinePlayerResponse(BaseModel):
    id: int
    username: str
    position: Optional[dict] = None
    last_ping: Optional[str] = None


# HTTP endpoints
@app.post("/players", response_model=PlayerResponse)
def create_player(player: PlayerCreate):
    """Create a new player given a username.

    If already exists one return it.
    """
    with get_db_session() as db:
        db_player = db.query(Player).filter(Player.username == player.username).first()
        if not db_player:
            # Create new player
            db_player = Player(username=player.username)
            db.add(db_player)
            db.commit()
            db.refresh(db_player)

    return db_player


@app.get("/players", response_model=List[PlayerResponse])
def get_players():
    """Get all players"""
    with get_db_session() as db:
        players = db.query(Player).all()
    return players


@app.get("/players/{player_id}", response_model=PlayerResponse)
def get_player(player_id: int):
    """Get player by ID"""
    with get_db_session() as db:
        player = db.query(Player).filter(Player.id == player_id).first()
    if player is None:
        raise HTTPException(status_code=404, detail="Player not found")
    return player


@app.get("/players/get_by_name/{player_name}", response_model=PlayerResponse)
def get_player_by_name(player_name: str):
    """Get player by player_name"""
    with get_db_session() as db:
        player = db.query(Player).filter(Player.username == player_name).first()
    if player is None:
        raise HTTPException(
            status_code=404, detail=f"Player with name {player_name} not found"
        )
    return player


@app.get("/online-players", response_model=List[OnlinePlayerResponse])
def get_online_players():
    """Get all online players with their position data"""
    # Check Redis for online players
    online_player_ids = redis_client.get_online_players()

    # If no online players, return empty list
    if not online_player_ids:
        return []

    # Get player details from SQLite
    with get_db_session() as db:
        players = db.query(Player).filter(Player.id.in_(online_player_ids)).all()

    # Combine with Redis data
    result = []
    for player in players:
        # # position_data = redis_client.get_player_position(player.id)

        # # Get last ping time
        # last_ping_key = f"{redis_client.PLAYER_PREFIX}{player.id}:last_ping"
        # last_ping = redis_client.redis_client.get(last_ping_key)

        result.append(
            OnlinePlayerResponse(
                id=player.id,
                username=player.username,
                # position=position_data,
                # last_ping=last_ping,
            )
        )

    return result


# Health check endpoint
@app.get("/health")
@app.get("/")
def health_check():
    """Health check endpoint"""
    redis_status = "UP" if redis_client.is_redis_available() else "DOWN"

    return {
        "status": "UP",
        "redis": redis_status,
        "timestamp": datetime.now().isoformat(),
    }
