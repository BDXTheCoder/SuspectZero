from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import json
import os
import uuid

app = FastAPI()

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
    is_host = False

    try:
        while True:
            raw_data = await websocket.receive_text()
            msg = json.loads(raw_data)
            action = msg.get("action")

            if action == "get_rooms":
                public_rooms = [
                    {"code": code, "players": len(room["players"]), "started": room["game_started"]}
                    for code, room in game_rooms.items()
                    if room["is_public"] and not room["game_started"]
                ]
                await websocket.send_text(json.dumps({"type": "room_list", "rooms": public_rooms}))

            elif action == "create_room":
                room_code = str(uuid.uuid4())[:4].upper()
                is_public = msg.get("is_public", True)

                game_rooms[room_code] = {
                    "is_public": is_public,
                    "game_started": False,
                    "players": {},
                    "connections": {}
                }
                current_room = room_code
                is_host = True
                game_rooms[room_code]["connections"][player_id] = websocket
                
                await websocket.send_text(json.dumps({"type": "room_joined", "code": room_code, "is_host": True}))

            elif action == "join_room":
                room_code = msg.get("code", "").upper().strip()
                if room_code in game_rooms:
                    if game_rooms[room_code]["game_started"]:
                        await websocket.send_text(json.dumps({"type": "error", "message": "Game already started!"}))
                        continue
                    current_room = room_code
                    is_host = False
                    game_rooms[room_code]["connections"][player_id] = websocket
                    await websocket.send_text(json.dumps({"type": "room_joined", "code": room_code, "is_host": False}))
                else:
                    await websocket.send_text(json.dumps({"type": "error", "message": "Room not found!"}))

            # Host triggers the game start!
            elif action == "start_game":
                if current_room and current_room in game_rooms and is_host:
                    game_rooms[current_room]["game_started"] = True
                    start_msg = json.dumps({"type": "match_started"})
                    for conn in game_rooms[current_room]["connections"].values():
                        await conn.send_text(start_msg)

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
                    try:
                        await conn.send_text(state_data)
                    except:
                        pass
