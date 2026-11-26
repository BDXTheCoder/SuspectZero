from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import json
import os
import uuid

app = FastAPI()

# Track all connected players and their latest game states
players = {}
connections = {}

# Serve your HTML frontend directly from the root URL
@app.get("/")
async def get_game():
    if os.path.exists("index.html"):
        with open("index.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>index.html not found! Make sure it's in the same folder as server.py.</h1>", status_code=404)

# WebSocket endpoint for real-time multiplayer communication
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    player_id = str(uuid.uuid4())[:6]  # Generate a short random ID for the player
    connections[player_id] = websocket

    try:
        while True:
            # Receive movement/position data from a client
            data = await websocket.receive_text()
            players[player_id] = json.loads(data)
            
            # Broadcast the updated state of all players to everyone connected
            state = json.dumps({"players": players})
            for conn in list(connections.values()):
                await conn.send_text(state)
                
    except WebSocketDisconnect:
        # Clean up when a player disconnects or closes the browser tab
        connections.pop(player_id, None)
        players.pop(player_id, None)
        
        # Broadcast the updated player list after someone leaves
        state = json.dumps({"players": players})
        for conn in list(connections.values()):
            try:
                await conn.send_text(state)
            except:
                pass

# Local development fallback (safe to keep, Render uses start command instead)
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=True)
