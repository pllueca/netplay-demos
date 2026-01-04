import asyncio
from typing import cast, List
import json
import websockets
from websockets import WebSocketServerProtocol
from datetime import datetime
import time


from src.database.redis_db import RedisClient
from src.database.sqlite_db import get_db_session
from src.database.models import Player
from src.common.entity import NPCEntity, PlayerEntity
from src.common.common_models import (
    NpcPositionUpdateMessage,
    PositionData,
    SocketMessagePlayerToServer,
    PositionUpdateMessage,
    NewPlayerConnectedMessage,
    PlayerDisconectedMessage,
)
from src.game_server.game import game_state
from src.common.logging import logger

redis_client = RedisClient()

# Connected clients
connected_clients: dict[str, WebSocketServerProtocol] = {}


# Message handler
async def handle_message(websocket: WebSocketServerProtocol, player_id: str):
    """Handle a message from a client.

    types:
    position_update: A client sends the new position of its player.
    Update its new position in redis and broadcast its new position to the rest of connected players.
    """
    try:
        async for message_str in websocket:
            try:
                message = SocketMessagePlayerToServer.model_validate_json(message_str)
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON message: {message}")
                continue
            message_type = message.type
            match message_type:
                case "position_update":
                    position_update_message = cast(PositionUpdateMessage, message.data)
                    redis_client.save_player_position(
                        player_id,
                        position_update_message.position_data,
                    )
                    await broadcast_position_update(
                        player_id,
                        position_update_message,
                    )
                case _:
                    logger.warning(f"Unknown message type: {message_type}")

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
async def authenticate(
    websocket: WebSocketServerProtocol,
) -> str | None:
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

        # Send map data
        map_message = SocketMessagePlayerToServer(
            type="map_data",
            data=game_state.get_map_data(),
        )
        await websocket.send(map_message.model_dump_json())

        # Notify other players about this player connecting
        await broadcast_player_connect(player_id)

        return player_id

    except (json.JSONDecodeError, websockets.exceptions.ConnectionClosed):
        return None


# Broadcast position update to all other connected players
async def broadcast_position_update(
    player_id: str,
    position_data_message: PositionUpdateMessage,
):
    message = SocketMessagePlayerToServer(
        type="player_position",
        data=position_data_message,
    )
    await broadcast_to_others(player_id, message.model_dump_json())


async def broadcast_npc_position_updates():
    """Message every connected player with the updates to npc around them"""
    npc_position_updates: List[NpcPositionUpdateMessage] = []
    for npc_id in game_state.npc_ids:
        npc_entity = game_state.entities[npc_id]
        npc_position_updates.append(
            NpcPositionUpdateMessage(
                npc_id=npc_entity.id,
                position_data=PositionData(
                    pos_x=npc_entity.pos_x, pos_y=npc_entity.pos_y
                ),
            )
        )

    message = SocketMessagePlayerToServer(
        type="npc_position_updates",
        data=npc_position_updates,
    )
    await broadcast_to_others(None, message.model_dump_json())


# Broadcast player connection to all other connected players
async def broadcast_player_connect(player_id: str):
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
async def broadcast_player_disconnect(player_id: str):
    message = SocketMessagePlayerToServer(
        type="player_disconnected",
        data=PlayerDisconectedMessage(player_id=player_id),
    )
    await broadcast_to_others(player_id, message.model_dump_json())


# Helper to broadcast to all connected clients except the sender
async def broadcast_to_others(sender_id: str | None, message: str):
    for player_id, websocket in connected_clients.items():
        if sender_id is None or player_id != sender_id:
            try:
                await websocket.send(message)
            except websockets.exceptions.ConnectionClosed:
                # This will be cleaned up in the handler
                pass


# WebSocket connection handler
async def websocket_handler(websocket: WebSocketServerProtocol):
    player_id = await authenticate(websocket)

    if player_id is not None:
        # create player in the game state
        game_state.add_player(
            PlayerEntity(id=player_id, player_id=player_id, pos_x=0, pos_y=0)
        )
        await handle_message(websocket, player_id)


async def periodic_logger():
    while True:
        logger.info("Server healthy; Connected players: %s", len(game_state.player_ids))
        await asyncio.sleep(10)  # Log every 10 seconds


async def update_npcs():
    """Update the game state every second"""
    while True:
        game_state.game_tick()
        for npc_id in game_state.npc_ids:
            npc = game_state.entities[npc_id]
            redis_client.save_npc_position(npc.id, npc.pos_x, npc.pos_y)
        await broadcast_npc_position_updates()
        await asyncio.sleep(1)


# Entrypoint of the websocket server.
async def start_websocket_server(host: str, port: int):

    if not redis_client.is_redis_available():
        raise RuntimeError("Could not connect to redis server, aborting")

    # Generate the map
    game_state.generate_map(20, 20)

    # Create some npcs
    for _ in range(5):
        npc = redis_client.create_npc("enemy", 10, 10)
        game_state.add_npc(
            NPCEntity(id=npc.id, type=npc.type, pos_x=npc.pos_x, pos_y=npc.pos_y)
        )

    logger_task = asyncio.create_task(periodic_logger())
    npc_task = asyncio.create_task(update_npcs())
    server = await websockets.serve(websocket_handler, host, port)
    logger.info(f"WebSocket server started on ws://{host}:{port}")
    return server
