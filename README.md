# Setup

install uv `curl -LsSf https://astral.sh/uv/install.sh | sh`

# Game Server
Start redis server `redis-server`
Start game server `uv run bin/run_server.py`

# Game Client

run with `uv run bin/run_client.py $PLAYER_NAME`


# dev

recompile protos with `protoc -I=src/common --python_out=src/common/game_pb2 src/common/game.proto`