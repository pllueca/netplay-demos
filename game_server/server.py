import asyncio
import logging
import json
from dataclasses import dataclass

from picows import (
    ws_create_server,
    WSFrame,
    WSTransport,
    WSListener,
    WSMsgType,
    WSUpgradeRequest,
)

logger = logging.getLogger("game_server_main")
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger.setLevel(logging.DEBUG)
logger.info("init")


@dataclass
class Player:
    id: int
    pos_x: float
    pos_y: float

    def __repr__(self) -> str:
        return f"<Player id={self.id}, pos=({self.pos_x, self.pos_y})>"

    def to_json(self):
        return {"id": self.id, "pos_x": self.pos_x, "pos_y": self.pos_y}


class GameState:

    def __init__(self):
        self.last_id = 0
        self.players: dict[int, Player] = {}

    def create_new_player(self) -> int:
        self.last_id += 1
        player = Player(
            self.last_id,
            0.0,
            0.0,
        )
        self.players[player.id] = player
        print(f"created player with id {player.id}")
        return player.id

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

    def on_ws_frame(self, transport: WSTransport, frame: WSFrame):
        if frame.msg_type == WSMsgType.CLOSE:
            transport.send_close(frame.get_close_code(), frame.get_close_message())
            transport.disconnect()
        else:
            msg = frame.get_payload_as_ascii_text()
            game_state = self.handle_player_update(msg)
            transport.send(frame.msg_type, json.dumps(game_state).encode("utf-8"))


async def log_game_state(game_state: GameState):

    logger_2 = logging.getLogger("game_server")
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    logger_2.setLevel(logging.DEBUG)
    logger_2.info("init server logging")
    while True:
        log_msg = game_state.log_state()
        logger_2.info(log_msg)
        await asyncio.sleep(5)


SOCKET_IP = "127.0.0.1"
SOCKET_PORT = 9001


async def main():
    # global game_state
    game_state = GameState()

    def listener_factory(r: WSUpgradeRequest):
        # Routing can be implemented here by analyzing request content
        return ServerClientListener(game_state)

    server: asyncio.Server = await ws_create_server(
        listener_factory,
        SOCKET_IP,
        SOCKET_PORT,
    )
    for s in server.sockets:
        print(f"Server started on {s.getsockname()}")

    print_task = asyncio.create_task(log_game_state(game_state))
    await server.serve_forever()
    print_task.cancel()


if __name__ == "__main__":
    asyncio.run(main())
