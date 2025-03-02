from typing import cast
import asyncio
import json
import logging
import websockets
from websockets import WebSocketServerProtocol
from datetime import datetime

from src.database.redis_db import RedisClient
from src.database.sqlite_db import get_db_session
from src.database.models import Player
from src.common.common_models import (
    SocketMessagePlayerToServer,
    PositionUpdateMessage,
    NewPlayerConnectedMessage,
    PlayerDisconectedMessage,
)


redis_client = RedisClient()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Connected clients
connected_clients: dict[int, WebSocketServerProtocol] = {}


# Message handler
async def handle_message(websocket: WebSocketServerProtocol, player_id: int):
    """Handle a message from a client.

    types:
    position_update: A client sends the new position of its player.
    Update its new position in redis and broadcast its new position to the rest of connected players.
    """
    try:
        async for message_str in websocket:
            try:
                message = SocketMessagePlayerToServer.model_validate_json(message_str)
                message_type = message.type
                match message_type:
                    case "position_update":
                        position_update_message = cast(
                            PositionUpdateMessage, message.data
                        )
                        redis_client.save_player_position(
                            player_id,
                            position_update_message.position_data,
                        )
                        # Position of player `player_id` updated
                        # respond with the positions of all the other players
                        await broadcast_position_update(
                            player_id,
                            position_update_message,
                        )
                    case _:
                        logger.warning(f"Unknown message type: {message_type}")

            except json.JSONDecodeError:
                logger.error(f"Invalid JSON message: {message}")

    except websockets.exceptions.ConnectionClosed:
        logger.info(f"Connection closed for player {player_id}")
    finally:
        # Clean up when connection is closed
        if player_id in connected_clients:
            del connected_clients[player_id]
        redis_client.remove_player_from_online(player_id)

        # Notify other players that this player has disconnected
        await broadcast_player_disconnect(player_id)


# Authentication handler
async def authenticate(websocket: WebSocketServerProtocol):
    try:
        # Expect authentication message with player ID
        auth_message = await websocket.recv()
        auth_data = json.loads(auth_message)

        player_id = auth_data.get("player_id")
        if not player_id:
            await websocket.send(json.dumps({"error": "Missing player_id"}))
            return None

        # Verify player exists in database
        with get_db_session() as db:
            player = db.query(Player).filter(Player.id == player_id).first()
            if not player:
                await websocket.send(json.dumps({"error": "Player not found"}))
                return None

            # Update last_seen
            player.last_seen = datetime.now()
            db.commit()
            username = player.username

        # Add to connected clients
        connected_clients[player_id] = websocket
        redis_client.add_player_to_online(player_id)

        # Send welcome message
        await websocket.send(
            json.dumps(
                {
                    "type": "welcome",
                    "message": f"Welcome, {username}!",
                    "player_id": player_id,
                }
            )
        )

        # Notify other players about this player connecting
        await broadcast_player_connect(player_id)

        return player_id

    except (json.JSONDecodeError, websockets.exceptions.ConnectionClosed):
        return None


# Broadcast position update to all other connected players
async def broadcast_position_update(
    player_id: int, position_data_message: PositionUpdateMessage
):
    message = SocketMessagePlayerToServer(
        type="player_position",
        data=position_data_message,
    )
    await broadcast_to_others(player_id, message.model_dump_json())


# Broadcast player connection to all other connected players
async def broadcast_player_connect(player_id: int):
    with get_db_session() as db:
        player = db.query(Player).filter(Player.id == player_id).first()
        if not player:
            return

        username = player.username

    message = SocketMessagePlayerToServer(
        type="player_connected",
        data=NewPlayerConnectedMessage(
            player_id=player_id,
            username=username,
        ),
    )

    await broadcast_to_others(player_id, message.model_dump_json())


# Broadcast player disconnection to all other connected players
async def broadcast_player_disconnect(player_id: int):
    message = SocketMessagePlayerToServer(
        type="player_disconnected",
        data=PlayerDisconectedMessage(player_id=player_id),
    )
    await broadcast_to_others(player_id, message.model_dump_json())


# Helper to broadcast to all connected clients except the sender
async def broadcast_to_others(sender_id: int, message: str):
    for player_id, websocket in connected_clients.items():
        if player_id != sender_id:
            try:
                await websocket.send(message)
            except websockets.exceptions.ConnectionClosed:
                # This will be cleaned up in the handler
                pass


# WebSocket connection handler
async def websocket_handler(websocket: WebSocketServerProtocol):
    player_id = await authenticate(websocket)

    if player_id:
        await handle_message(websocket, player_id)


# Create WebSocket server
async def start_websocket_server(host: str, port: int):
    server = await websockets.serve(websocket_handler, host, port)
    logger.info(f"WebSocket server started on ws://{host}:{port}")
    return server
