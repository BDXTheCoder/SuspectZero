from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import json
import uuid

app = FastAPI()
players = {}
connections = {}

# Serve the HTML game when someone visits your Render URL
@app.get("/")
async def get_game():
    with open("index.html", "r") as f:
        return HTMLResponse(content=f.read())

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    player_id = str(uuid.uuid4())[:6]
    connections[player_id] = websocket

    try:
        while True:
            data = await websocket.receive_text()
            players[player_id] = json.loads(data)
            
            state = json.dumps({"players": players})
            for conn in list(connections.values()):
                await conn.send_text(state)
    except WebSocketDisconnect:
        del connections[player_id]
        players.pop(player_id, None)
