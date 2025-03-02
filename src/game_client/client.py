from dataclasses import dataclass, field
import websockets
import pygame
import json

from src.common.entity import PlayerEntity
from config import WS_URL

# Game constants
WIDTH, HEIGHT = 800, 600
WHITE = (255, 255, 255)
RED = (255, 0, 0)
PLAYER_SIZE = 50


class LocalGameState:
    player: PlayerEntity
    player_changed: bool
    others: dict[int, PlayerEntity]

    def update_state(self, state_dict):
        # {
        #     "self": {"id": 7, "pos_x": 390, "pos_y": 190},
        #     "others": [
        #         {"id": 1, "pos_x": 0.0, "pos_y": 0.0},
        #         ...
        #     ],
        # }
        self.others = {}
        for other in state_dict.get("others", []):
            self.others[other["id"]] = PlayerEntity(
                id=other["id"],
                player_id=other.get("player_id", "unknown"),
                pos_x=other["pos_x"],
                pos_y=other["pos_y"],
            )

    def __init__(self, player_id):
        self.player_id = player_id
        self.player_changed = False
        self.player = PlayerEntity(
            id=0,
            player_id=self.player_id,
            pos_x=0,
            pos_y=0,
        )

        self.others = {}


class GameClient:
    def __init__(self, player_id: int):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Multiplayer Game")
        self.clock = pygame.time.Clock()
        self.approx_fps: float = -1.0
        self.game_state = LocalGameState(player_id)
        self.websocket = None

    async def connect(self):
        try:
            self.websocket = await websockets.connect(WS_URL)
            print("Connected to server")
            await self.receive_initial_message()
        except Exception as e:
            print(f"Error connecting to server: {e}")
            raise

    async def receive_initial_message(self):
        try:
            message = await self.websocket.recv()
            player_id = int(message)
        except websockets.exceptions.ConnectionClosedOK:
            print("Connection closed by server")
        except Exception as e:
            print(f"Error receiving messages: {e}")

        print(f"created player with id {player_id}")
        self.game_state.player.id = player_id

    async def send_state(self):
        if self.websocket:
            try:
                state = {
                    "id": self.game_state.player.id,
                    "player_id": self.game_state.player_id,
                    "pos_x": self.game_state.player.pos_x,
                    "pos_y": self.game_state.player.pos_y,
                }
                await self.websocket.send(json.dumps(state))
            except Exception as e:
                raise

            # receive updated state
            state = await self.websocket.recv()
            self.game_state.update_state(json.loads(state))

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
        font = pygame.font.Font("freesansbold.ttf", 32)
        text_surface = font.render(
            f"fps: {int(self.approx_fps)}",
            True,
            RED,
            WHITE,
        )
        text_rect = text_surface.get_rect()
        # set the text to the top right of the screen
        text_rect.topright = (WIDTH, 0)
        self.screen.blit(text_surface, text_rect)

    async def run(self):
        await self.connect()
        running = True
        while running:
            running = self.handle_events()
            self.draw()
            await self.send_state()
            self.clock.tick(60)

            # update fps count
            # ns between last 2 clock.tick
            elapsed_ms = self.clock.get_time()
            self.approx_fps = 1 / (elapsed_ms / 1e3)

        if self.websocket:
            await self.websocket.close()
        pygame.quit()
