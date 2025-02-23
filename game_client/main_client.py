from dataclasses import dataclass, field
import pygame
import asyncio
import websockets
import json

# Game constants
WIDTH, HEIGHT = 800, 600
WHITE = (255, 255, 255)
RED = (255, 0, 0)
PLAYER_SIZE = 50


@dataclass
class PlayerState:
    id: int
    pos_x: float
    pos_y: float
    changed: bool = True


@dataclass
class LocalGameState:
    player: PlayerState
    others: dict[int, PlayerState] = field(default_factory=dict)

    def update_state(self, state_dict):
        # {'self': {'id': 7, 'pos_x': 390, 'pos_y': 190}, 'others': [{'id': 1, 'pos_x': 0.0, 'pos_y': 0.0}, {'id': 2, 'pos_x': 405, 'pos_y': 100}, {'id': 3, 'pos_x': 465, 'pos_y': 285}, {'id': 4, 'pos_x': 375, 'pos_y': 215}, {'id': 5, 'pos_x': 440, 'pos_y': 240}, {'id': 6, 'pos_x': 455, 'pos_y': 160}]}
        self.others = {}
        for other in state_dict.get("others", []):
            self.others[other["id"]] = PlayerState(
                other["id"],
                other["pos_x"],
                other["pos_y"],
            )


class GameClient:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Multiplayer Game")
        self.clock = pygame.time.Clock()

        self.game_state = LocalGameState(
            PlayerState(
                None, WIDTH // 2 - PLAYER_SIZE // 2, HEIGHT // 2 - PLAYER_SIZE // 2
            )
        )
        self.websocket = None

    async def connect(self):
        try:
            self.websocket = await websockets.connect("ws://127.0.0.1:9001")
            print("Connected to server")
            await self.receive_initial_message()
        except Exception as e:
            print(f"Error connecting to server: {e}")

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
        self.game_state.player.changed = False
        if keys[pygame.K_LEFT]:
            self.game_state.player.pos_x -= 5
            self.game_state.player.changed = True
        if keys[pygame.K_RIGHT]:
            self.game_state.player.pos_x += 5
            self.game_state.player.changed = True
        if keys[pygame.K_UP]:
            self.game_state.player.pos_y -= 5
            self.game_state.player.changed = True
        if keys[pygame.K_DOWN]:
            self.game_state.player.pos_y += 5
            self.game_state.player.changed = True
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

        pygame.display.flip()

    async def run(self):
        await self.connect()
        running = True
        while running:
            running = self.handle_events()
            self.draw()
            await self.send_state()
            # await self.receive_messages()
            self.clock.tick(60)

        if self.websocket:
            await self.websocket.close()
        pygame.quit()


async def main():
    game = GameClient()
    await game.run()


if __name__ == "__main__":
    asyncio.run(main())
