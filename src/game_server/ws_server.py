import asyncio
import json

from picows import (
    WSFrame,
    WSListener,
    WSMsgType,
    WSTransport,
    WSUpgradeRequest,
    ws_create_server,
)

from config import WS_HOST, WS_PORT
from src.common.entity import PlayerEntity
from src.database.redis_db import RedisClient

redis_client = RedisClient()


class GameState:
    def __init__(self):
        self.last_id = 0
        self.players: dict[int, PlayerEntity] = {}

    def create_new_player(self) -> int:
        self.last_id += 1
        new_id = self.last_id

        self.players[new_id] = PlayerEntity(
            id=new_id,
            player_id="",
            pos_x=0.0,
            pos_y=0.0,
        )
        print(f"created player with id {new_id}")
        return new_id

    def update_player(self, id: int, pos_x: float, pos_y: float) -> None:
        if not self.player_exists(id):
            raise ValueError(f"no player with id {id}")
        self.players[id].pos_x = pos_x
        self.players[id].pos_y = pos_y

    def player_exists(self, id: int) -> bool:
        return id in self.players

    def get_game_state_from_player(self, id) -> dict:
        state = {"self": self.players[id].to_json(), "others": []}
        for other_player_id, other_player in self.players.items():
            if other_player_id != id:
                state["others"].append(other_player.to_json())
        return state

    def log_state(self) -> str:
        s = f"Server State:\n# players: {len(self.players)}"
        for pid, player in self.players.items():
            s += f"\nid {pid} -> ({player.pos_x}, {player.pos_y})"
        return s


class ServerClientListener(WSListener):
    def __init__(self, game_state: GameState):
        super().__init__()
        self.game_state = game_state

    def handle_player_update(self, player_payload) -> dict:
        """Update the game state, return the current game state"""
        data = json.loads(player_payload)
        if {"id", "pos_x", "pos_y"} > data.keys():
            raise Exception(f"missing keys: {data}")

        self.game_state.update_player(data["id"], data["pos_x"], data["pos_y"])

        return self.game_state.get_game_state_from_player(data["id"])

    def on_ws_connected(self, transport: WSTransport):
        new_player_id = self.game_state.create_new_player()
        transport.send(WSMsgType.BINARY, str(new_player_id).encode("utf-8"))

        print(f"new connection, created player with id: {new_player_id}")
        redis_client.add_player_to_online("..")

    def on_ws_disconnected(self, _transport: WSTransport):
        print("client disconnected")
        redis_client.remove_player_from_online("..")

    def on_ws_frame(self, transport: WSTransport, frame: WSFrame):
        if frame.msg_type == WSMsgType.CLOSE:
            transport.send_close(frame.get_close_code(), frame.get_close_message())
            transport.disconnect()
        else:
            msg = frame.get_payload_as_ascii_text()
            game_state = self.handle_player_update(msg)

            transport.send(frame.msg_type, json.dumps(game_state).encode("utf-8"))


async def main():
    # global game_state
    game_state = GameState()

    def listener_factory(r: WSUpgradeRequest):
        # Routing can be implemented here by analyzing request content
        return ServerClientListener(game_state)

    server: asyncio.Server = await ws_create_server(
        listener_factory,
        WS_HOST,
        WS_PORT,
    )
    for s in server.sockets:
        print(f"Server started on {s.getsockname()}, url: ws://{WS_HOST}:{WS_PORT}")

    await server.serve_forever()
