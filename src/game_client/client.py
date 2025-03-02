import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import cast

import pygame
import websockets

from config import WS_URL
from src.common.common_models import (
    PositionData,
    PositionUpdateMessage,
    SocketMessagePlayerToServer,
)
from src.common.entity import PlayerEntity

# Game constants
WIDTH, HEIGHT = 800, 600
WHITE = (255, 255, 255)
RED = (255, 0, 0)
PLAYER_SIZE = 50


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LocalGameState:
    player: PlayerEntity
    player_changed: bool
    others: dict[int, PlayerEntity]

    def __init__(self, player_id: int, username: str):
        self.player_id = player_id
        self.player_changed = False
        self.player = PlayerEntity(
            id=player_id,
            username=username,
            pos_x=0,
            pos_y=0,
        )

        self.others = {}

    def update_state_other_player(self, position_update: PositionUpdateMessage):
        if position_update.player_id not in self.others:
            self.others[position_update.player_id] = PlayerEntity(
                id=position_update.player_id, pos_x=0, pos_y=0.0
            )
        self.others[
            position_update.player_id
        ].pos_x = position_update.position_data.pos_x
        self.others[
            position_update.player_id
        ].pos_y = position_update.position_data.pos_y

    def delete_player(self, player_id: int):
        if player_id in self.others:
            del self.others[player_id]

    @property
    def player_position_data(self) -> PositionData:
        return PositionData(pos_x=self.player.pos_x, pos_y=self.player.pos_y)


class GameClient:
    def __init__(self, player_id: int, player_username: str, websocket):
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
        while self.new_socket_messages:
            other_player_update = self.new_socket_messages.pop(0)
            match other_player_update.type:
                case "player_position":
                    self.game_state.update_state_other_player(
                        cast(PositionUpdateMessage, other_player_update.data),
                    )
                case "player_disconnected":
                    self.game_state.delete_player(other_player_update.data.player_id)
                case _:
                    pass

    async def send_state(self):
        """Broadcast updated player position to the server."""
        if self.websocket:
            try:
                state = SocketMessagePlayerToServer(
                    type="position_update",
                    data=PositionUpdateMessage(
                        player_id=self.player_id,
                        position_data=self.game_state.player_position_data,
                    ),
                )
                # print("sending", state.model_dump_json())
                await self.websocket.send(state.model_dump_json())
            except Exception as e:
                raise

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
        pygame.draw.rect(
            self.screen,
            RED,
            (
                self.game_state.player.pos_x,
                self.game_state.player.pos_y,
                PLAYER_SIZE,
                PLAYER_SIZE,
            ),
        )

        # # Draw other players
        for other in self.game_state.others.values():
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

        self.draw_fps()

        pygame.display.flip()

    def draw_fps(self):
        font = pygame.font.Font("freesansbold.ttf", 25)
        text_surface = font.render(
            f"fps: {int(self.clock.get_fps())}\nothers: {len(self.game_state.others)}",
            True,
            RED,
            WHITE,
        )
        text_rect = text_surface.get_rect()
        # set the text to the top right of the screen
        text_rect.topright = (WIDTH, 0)
        self.screen.blit(text_surface, text_rect)
