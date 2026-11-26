from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import json
import os
import uuid

app = FastAPI()

# Stores active rooms: { room_code: { "is_public": bool, "players": {}, "connections": {} } }
game_rooms = {}

@app.get("/")
async def get_game():
    if os.path.exists("index.html"):
        with open("index.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>index.html not found</h1>", status_code=404)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    player_id = str(uuid.uuid4())[:6]
    current_room = None

    try:
        while True:
            raw_data = await websocket.receive_text()
            msg = json.loads(raw_data)
            action = msg.get("action")

            # 1. Fetch list of public rooms for the menu tab
            if action == "get_rooms":
                public_rooms = [
                    {"code": code, "players": len(room["players"])}
                    for code, room in game_rooms.items()
                    if room["is_public"]
                ]
                await websocket.send_text(json.dumps({"type": "room_list", "rooms": public_rooms}))

            # 2. Create a new room (Public or Private)
            elif action == "create_room":
                room_code = str(uuid.uuid4())[:4].upper()
                is_public = msg.get("is_public", True)

                game_rooms[room_code] = {
                    "is_public": is_public,
                    "players": {},
                    "connections": {}
                }
                current_room = room_code
                game_rooms[room_code]["connections"][player_id] = websocket
                
                await websocket.send_text(json.dumps({"type": "room_joined", "code": room_code}))

            # 3. Join an existing room via code or list click
            elif action == "join_room":
                room_code = msg.get("code", "").upper().strip()
                if room_code in game_rooms:
                    current_room = room_code
                    game_rooms[room_code]["connections"][player_id] = websocket
                    await websocket.send_text(json.dumps({"type": "room_joined", "code": room_code}))
                else:
                    await websocket.send_text(json.dumps({"type": "error", "message": "Room not found!"}))

            # 4. Handle ingame movement & updates within the room
            elif action == "player_update":
                if current_room and current_room in game_rooms:
                    game_rooms[current_room]["players"][player_id] = msg.get("state")
                    
                    state_data = json.dumps({
                        "type": "game_state",
                        "players": game_rooms[current_room]["players"]
                    })
                    for conn in game_rooms[current_room]["connections"].values():
                        await conn.send_text(state_data)

    except WebSocketDisconnect:
        if current_room and current_room in game_rooms:
            room = game_rooms[current_room]
            room["players"].pop(player_id, None)
            room["connections"].pop(player_id, None)
            
            # Delete room if empty, otherwise update remaining players
            if not room["players"]:
                del game_rooms[current_room]
            else:
                state_data = json.dumps({
                    "type": "game_state",
                    "players": room["players"]
                })
                for conn in room["connections"].values():
                    try:
                        await conn.send_text(state_data)
                    except:
                        pass
