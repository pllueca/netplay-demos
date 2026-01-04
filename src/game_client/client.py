import uuid
import asyncio
import logging
from typing import cast

import pygame

from src.common.common_models import (
    NpcPositionUpdateMessage,
    PositionData,
    PositionUpdateMessage,
    SocketMessagePlayerToServer,
    NewPlayerConnectedMessage,
)
from src.common.entity import PlayerEntity, NPCEntity, Entity
from src.common.world import GameState
from src.common.logging import logger

# Game constants

WIDTH, HEIGHT = 800, 600

NPC_SIZE = 20

WHITE = (255, 255, 255)

RED = (255, 0, 0)

PLAYER_SIZE = 50


class LocalGameState:

    player_id: str

    other_player_ids: set[str]

    npc_ids: set[str]

    def __init__(self, player_id: str, username: str):

        self._state = GameState()

        self.player_id = player_id

        self._state.add_player(
            PlayerEntity(
                id=player_id,
                player_id=player_id,
                username=username,
                pos_x=0,
                pos_y=0,
            )
        )

        self.other_player_ids = set()

        self.npc_ids = set()

    def update_state_other_player(self, position_update: PositionUpdateMessage):
        """Update a position of another player.



        This player may or may have not been seen before."""

        if (position_update.player_id not in self.entities) or (
            position_update.player_id not in self.other_player_ids
        ):

            # havent seen this guy

            logger.info(f"New player with id {position_update.player_id} joined")

            self.entities[position_update.player_id] = PlayerEntity(
                player_id=position_update.player_id,
                id=position_update.player_id,
                pos_x=0,
                pos_y=0.0,
            )

            self.other_player_ids.add(position_update.player_id)

        self.entities[position_update.player_id].pos_x = (
            position_update.position_data.pos_x
        )

        self.entities[position_update.player_id].pos_y = (
            position_update.position_data.pos_y
        )

    def update_state_npc(self, npc_update: NpcPositionUpdateMessage):
        """Update a position of an NPC.



        This NPC may or may have not been seen before."""

        if (npc_update.npc_id not in self.entities) or (
            npc_update.npc_id not in self.npc_ids
        ):

            # havent seen this npc

            logger.info(f"New npc with id {npc_update.npc_id} joined")

            self.entities[npc_update.npc_id] = NPCEntity(
                id=npc_update.npc_id,
                type="enemy",  # TODO: get npc type from server
                pos_x=0,
                pos_y=0.0,
            )

            self.npc_ids.add(npc_update.npc_id)

        self.entities[npc_update.npc_id].pos_x = npc_update.position_data.pos_x

        self.entities[npc_update.npc_id].pos_y = npc_update.position_data.pos_y

    def add_other_player(self, player_id: str, username: str):

        logger.info(f"New player with id {player_id} joined")

        self.entities[player_id] = PlayerEntity(
            player_id=player_id,
            id=player_id,
            username=username,
            pos_x=0,
            pos_y=0.0,
        )

        self.other_player_ids.add(player_id)

    def delete_player(self, player_id: str):

        del self.entities[player_id]

        self.other_player_ids.remove(player_id)

    @property
    def entities(self) -> dict[str, Entity]:

        return self._state.entities

    @property
    def player(self) -> PlayerEntity:

        return self.entities[self.player_id]

    @property
    def player_position_data(self) -> PositionData:

        return PositionData(pos_x=self.player.pos_x, pos_y=self.player.pos_y)


class GameClient:

    def __init__(self, player_id: str, player_username: str, websocket):

        self.pygame_init()

        self.player_id = player_id

        self.game_state = LocalGameState(player_id, player_username)

        self.websocket = websocket

        # message queue

        self.new_socket_messages = []

    async def run(self):

        running = True

        logging.info("init game")

        while running:

            running = self.handle_events()

            await self.get_socket_messages()

            self.update_state()

            self.draw()

            await self.send_state()

            self.clock.tick(60)

        pygame.quit()

    def pygame_init(self):

        pygame.init()

        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))

        pygame.display.set_caption("Multiplayer Game")

        self.clock = pygame.time.Clock()

        self.approx_fps: float = -1.0

    async def get_socket_messages(self) -> None:
        """Get the updates sent from the server."""

        while True:

            # read messages until TO (no new messages)

            try:

                message = await asyncio.wait_for(
                    self.websocket.recv(), timeout=1 / 180.0
                )

                try:

                    self.new_socket_messages.append(
                        SocketMessagePlayerToServer.model_validate_json(message)
                    )

                except Exception as e:

                    logger.warning(f"could not load {message}: {e}")

            except asyncio.TimeoutError:

                break

    def update_state(self) -> None:
        """Update the game state, after processing keyboard events and socket messages"""

        # update others

        while self.new_socket_messages:

            socket_message = self.new_socket_messages.pop(0)

            match socket_message.type:

                case "player_position":

                    self.game_state.update_state_other_player(
                        cast(PositionUpdateMessage, socket_message.data),
                    )

                case "player_connected":

                    new_player_message = cast(
                        NewPlayerConnectedMessage, socket_message.data
                    )

                    self.game_state.add_other_player(
                        new_player_message.player_id, new_player_message.username
                    )

                case "player_disconnected":

                    self.game_state.delete_player(socket_message.data.player_id)

                case "npc_position_updates":

                    for npc_update in cast(
                        list[NpcPositionUpdateMessage], socket_message.data
                    ):

                        self.game_state.update_state_npc(npc_update)

                case _:

                    logger.warning(f"Unknown message type: {socket_message.type}")

    async def send_state(self):
        """Broadcast updated player position to the server."""

        state = SocketMessagePlayerToServer(
            type="position_update",
            data=PositionUpdateMessage(
                player_id=self.player_id,
                position_data=self.game_state.player_position_data,
            ),
        )

        await self.websocket.send(state.model_dump_json())

        # TODO: implement server sending confirmation that the update is ok

    def handle_events(self):

        for event in pygame.event.get():

            if event.type == pygame.QUIT:

                return False

        keys = pygame.key.get_pressed()

        self.game_state.player_changed = False

        if keys[pygame.K_LEFT]:

            self.game_state.player.pos_x -= 5

            self.game_state.player_changed = True

        if keys[pygame.K_RIGHT]:

            self.game_state.player.pos_x += 5

            self.game_state.player_changed = True

        if keys[pygame.K_UP]:

            self.game_state.player.pos_y -= 5

            self.game_state.player_changed = True

        if keys[pygame.K_DOWN]:

            self.game_state.player.pos_y += 5

            self.game_state.player_changed = True

        return True

    def draw(self):

        self.screen.fill(WHITE)

        player = self.game_state.entities[self.game_state.player_id]

        pygame.draw.rect(
            self.screen,
            RED,
            (
                player.pos_x,
                player.pos_y,
                PLAYER_SIZE,
                PLAYER_SIZE,
            ),
        )

        # # Draw other players

        for other_player_id in self.game_state.other_player_ids:

            other = self.game_state.entities[other_player_id]

            pygame.draw.rect(
                self.screen,
                (0, 0, 255),
                (
                    other.pos_x,
                    other.pos_y,
                    PLAYER_SIZE,
                    PLAYER_SIZE,
                ),
            )

        # draw npcs

        for npc_id in self.game_state.npc_ids:

            npc = self.game_state.entities[npc_id]

            pygame.draw.rect(
                self.screen,
                (128, 128, 0),
                (
                    npc.pos_x,
                    npc.pos_y,
                    NPC_SIZE,
                    NPC_SIZE,
                ),
            )

        self.draw_fps()

        pygame.display.flip()

    def draw_fps(self):

        font = pygame.font.Font("freesansbold.ttf", 25)

        text_surface = font.render(
            f"fps: {int(self.clock.get_fps())}\nothers: {len(self.game_state.other_player_ids)}",
            True,
            RED,
            WHITE,
        )

        text_rect = text_surface.get_rect()

        # set the text to the top right of the screen

        text_rect.topright = (WIDTH, 0)

        self.screen.blit(text_surface, text_rect)
