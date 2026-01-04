from datetime import datetime
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.database.models import Player
from src.database.redis_db import RedisClient
from src.database.sqlite_db import get_db_session
from src.game_server.game import game_state

from src.common.logging import logger

redis_client = RedisClient()
if not redis_client.is_redis_available():
    raise RuntimeError("Could not connect to redis server")

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
    id: str
    username: str
    created_at: datetime
    last_seen: datetime


class OnlinePlayerResponse(BaseModel):
    id: str
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
    logger.info(f"Created Player {db_player}")
    return db_player


@app.get("/players", response_model=List[PlayerResponse])
def get_players():
    """Get all players"""
    with get_db_session() as db:
        players = db.query(Player).all()
    return players


@app.get("/players/{player_id}", response_model=PlayerResponse)
def get_player(player_id: str):
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


@app.get("/map", response_class=HTMLResponse)
def get_map():
    """Return a simple html view of the map"""
    html_content = "<html><body><table>"
    for row in game_state.map:
        html_content += "<tr>"
        for tile in row:
            color = "white" if tile else "black"
            html_content += (
                f'<td style="width: 20px; height: 20px; background-color: {color};"></td>'
            )
        html_content += "</tr>"
    html_content += "</table></body></html>"
    return HTMLResponse(content=html_content, status_code=200)


# Health check endpoint
@app.get("/health")
@app.get("/")
def health_check():
    """Health check endpoint"""
    redis_status = "UP" if redis_client.is_redis_available() else "DOWN"

    num_online_players = len(redis_client.get_online_players())
    return {
        "status": "UP",
        "redis": redis_status,
        "timestamp": datetime.now().isoformat(),
        "online_players": num_online_players,
    }
