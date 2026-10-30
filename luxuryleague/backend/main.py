from __future__ import annotations

import random
import secrets
import string
from collections import defaultdict
from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException, Header, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(title="Luxury League API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

# Game-point values are illustrative and configurable, not real-world brand valuations.
BRANDS = [
    {"id": "hm", "name": "H&M", "tier": 1, "points": 10},
    {"id": "uniqlo", "name": "Uniqlo", "tier": 1, "points": 10},
    {"id": "massimo_dutti", "name": "Massimo Dutti", "tier": 1, "points": 20},
    {"id": "mango", "name": "Mango", "tier": 1, "points": 20},
    {"id": "guess", "name": "Guess", "tier": 1, "points": 20},
    {"id": "zara", "name": "Zara", "tier": 1, "points": 30},
    {"id": "cos", "name": "COS", "tier": 1, "points": 30},
    {"id": "stories", "name": "& Other Stories", "tier": 1, "points": 30},
    {"id": "chanel", "name": "Chanel", "tier": 2, "points": 70},
    {"id": "louis_vuitton", "name": "Louis Vuitton", "tier": 2, "points": 70},
    {"id": "jimmy_choo", "name": "Jimmy Choo", "tier": 2, "points": 70},
    {"id": "gucci", "name": "Gucci", "tier": 2, "points": 70},
    {"id": "prada", "name": "Prada", "tier": 2, "points": 70},
    {"id": "dior", "name": "Dior", "tier": 2, "points": 70},
    {"id": "burberry", "name": "Burberry", "tier": 2, "points": 70},
    {"id": "saint_laurent", "name": "Saint Laurent", "tier": 2, "points": 70},
    {"id": "tiffany", "name": "Tiffany & Co.", "tier": 3, "points": 100},
    {"id": "bvlgari", "name": "Bvlgari", "tier": 3, "points": 100},
    {"id": "cartier", "name": "Cartier", "tier": 3, "points": 100},
    {"id": "vca", "name": "Van Cleef & Arpels", "tier": 3, "points": 100},
]
BRAND_BY_ID = {b["id"]: b for b in BRANDS}
MATCH_BONUS = 100
MAX_PLAYERS = 4
TURNS_PER_PLAYER = 15
STARTING_HAND = 5

rooms: Dict[str, dict] = {}
connections: Dict[str, List[WebSocket]] = defaultdict(list)


class CreateRoom(BaseModel):
    player_name: str = Field(min_length=1, max_length=20)


class JoinRoom(BaseModel):
    player_name: str = Field(min_length=1, max_length=20)


def make_code():
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(6))


def player_for(room: dict, token: str):
    for player in room["players"]:
        if secrets.compare_digest(player["token"], token or ""):
            return player
    raise HTTPException(status_code=401, detail="Invalid player token")


def public_state(room: dict):
    return {
        "room_code": room["code"],
        "status": room["status"],
        "players": [
            {
                "id": p["id"], "name": p["name"], "score": p["score"],
                "pairs": p["pairs"], "turns_taken": p["turns_taken"],
                "is_host": p["is_host"],
            } for p in room["players"]
        ],
        "active_player_id": room["active_player_id"],
        "turn_number": room["turn_number"],
        "max_turns": TURNS_PER_PLAYER,
        "deck_remaining": len(room["deck"]),
        "recent_event": room.get("recent_event"),
        "winner_id": room.get("winner_id"),
    }


def private_state(room: dict, player: dict):
    state = public_state(room)
    state["you"] = {"id": player["id"], "name": player["name"], "is_host": player["is_host"]}
    state["hand"] = [
        {**BRAND_BY_ID[c["brand_id"]], "instance_id": c["instance_id"]}
        for c in player["hand"]
    ]
    state["completed_pairs"] = player["completed_pairs"]
    return state


async def broadcast(room_code: str):
    room = rooms.get(room_code)
    if not room:
        return
    payload = {"type": "state_changed", "state": public_state(room)}
    dead = []
    for ws in connections[room_code]:
        try:
            await ws.send_json(payload)
        except Exception:
            dead.append(ws)
    for ws in dead:
        connections[room_code].remove(ws)


def new_player(name: str, is_host: bool = False):
    return {
        "id": secrets.token_hex(8),
        "token": secrets.token_urlsafe(24),
        "name": name.strip(),
        "is_host": is_host,
        "hand": [],
        "completed_pairs": [],
        "score": 0,
        "pairs": 0,
        "turns_taken": 0,
    }


def score_pair(player: dict, first: dict, second: dict):
    brand = BRAND_BY_ID[first["brand_id"]]
    points = brand["points"] * 2 + MATCH_BONUS
    player["score"] += points
    player["pairs"] += 1
    player["completed_pairs"].append({
        "brand_id": brand["id"], "brand_name": brand["name"],
        "card_points": brand["points"] * 2,
        "bonus_points": MATCH_BONUS, "total_points": points,
    })


def auto_match(player: dict):
    grouped = defaultdict(list)
    for card in player["hand"]:
        grouped[card["brand_id"]].append(card)
    removed = set()
    matched = []
    for brand_id, cards in grouped.items():
        while len(cards) >= 2:
            first, second = cards.pop(0), cards.pop(0)
            removed.add(first["instance_id"])
            removed.add(second["instance_id"])
            score_pair(player, first, second)
            matched.append(BRAND_BY_ID[brand_id]["name"])
    if removed:
        player["hand"] = [c for c in player["hand"] if c["instance_id"] not in removed]
    return matched


def finish_if_done(room: dict):
    if all(p["turns_taken"] >= TURNS_PER_PLAYER for p in room["players"]):
        room["status"] = "finished"
        high = max(p["score"] + sum(BRAND_BY_ID[c["brand_id"]]["points"] for c in p["hand"]) for p in room["players"])
        tied = [p for p in room["players"] if p["score"] + sum(BRAND_BY_ID[c["brand_id"]]["points"] for c in p["hand"]) == high]
        tied.sort(key=lambda p: (p["pairs"], max([BRAND_BY_ID[c["brand_id"]]["points"] for c in p["hand"]] + [0])), reverse=True)
        room["winner_id"] = tied[0]["id"]
        room["final_scores"] = {
            p["id"]: p["score"] + sum(BRAND_BY_ID[c["brand_id"]]["points"] for c in p["hand"])
            for p in room["players"]
        }


@app.post("/api/rooms")
async def create_room(body: CreateRoom):
    code = make_code()
    while code in rooms:
        code = make_code()
    host = new_player(body.player_name, True)
    rooms[code] = {
        "code": code, "status": "lobby", "players": [host],
        "deck": [], "active_player_id": None, "turn_number": 0,
        "recent_event": f"{host['name']} created the room.", "winner_id": None,
    }
    return {"room_code": code, "player_id": host["id"], "player_token": host["token"], "state": private_state(rooms[code], host)}


@app.post("/api/rooms/{code}/join")
async def join_room(code: str, body: JoinRoom):
    room = rooms.get(code.upper())
    if not room:
        raise HTTPException(404, "Room not found.")
    if room["status"] != "lobby":
        raise HTTPException(409, "This game has already started.")
    if len(room["players"]) >= MAX_PLAYERS:
        raise HTTPException(409, "This room is full.")
    if any(p["name"].lower() == body.player_name.strip().lower() for p in room["players"]):
        raise HTTPException(409, "That player name is already taken in this room.")
    player = new_player(body.player_name)
    
room["players"].append(player)
room["recent_event"] = f"{player['name']} joined the room."

if len(room["players"]) == MAX_PLAYERS:
    deck = []
    for brand in BRANDS:
        for copy_number in range(4):
            deck.append({
                "instance_id": secrets.token_hex(8),
                "brand_id": brand["id"]
            })

    random.SystemRandom().shuffle(deck)
    room["deck"] = deck

    for p in room["players"]:
        p["hand"] = [
            room["deck"].pop()
            for _ in range(STARTING_HAND)
        ]
        auto_match(p)

    room["status"] = "playing"
    room["active_player_id"] = room["players"][0]["id"]
    room["recent_event"] = "Four players joined. Game started!"

await broadcast(room["code"])

return {
    "room_code": room["code"],
    "player_id": player["id"],
    "player_token": player["token"],
    "state": private_state(room, player)
}

@app.get("/api/rooms/{code}")
async def get_room(code: str, x_player_token: str = Header(default="")):
    room = rooms.get(code.upper())
    if not room:
        raise HTTPException(404, "Room not found.")
    player = player_for(room, x_player_token)
    state = private_state(room, player)
    if room["status"] == "finished":
        state["final_scores"] = room.get("final_scores", {})
    return state


@app.post("/api/rooms/{code}/start")
async def start_game(code: str, x_player_token: str = Header(default="")):
    room = rooms.get(code.upper())
    if not room:
        raise HTTPException(404, "Room not found.")
    player = player_for(room, x_player_token)
    if not player["is_host"]:
        raise HTTPException(403, "Only the host can start the game.")
    if room["status"] != "lobby":
        raise HTTPException(409, "Game has already started.")
    if len(room["players"]) != MAX_PLAYERS:
        raise HTTPException(409, "Exactly four players are required to start.")
    deck = []
    for brand in BRANDS:
        for copy_number in range(4):
            deck.append({"instance_id": secrets.token_hex(8), "brand_id": brand["id"]})
    random.SystemRandom().shuffle(deck)
    room["deck"] = deck
    for p in room["players"]:
        p["hand"] = [room["deck"].pop() for _ in range(STARTING_HAND)]
        auto_match(p)
    room["status"] = "playing"
    room["active_player_id"] = room["players"][0]["id"]
    room["recent_event"] = "Game started. " + room["players"][0]["name"] + " goes first."
    await broadcast(room["code"])
    return private_state(room, player)


@app.post("/api/rooms/{code}/draw")
async def draw_card(code: str, x_player_token: str = Header(default="")):
    room = rooms.get(code.upper())
    if not room:
        raise HTTPException(404, "Room not found.")
    player = player_for(room, x_player_token)
    if room["status"] != "playing":
        raise HTTPException(409, "The game is not currently running.")
    if room["active_player_id"] != player["id"]:
        raise HTTPException(403, "It is not your turn.")
    if player["turns_taken"] >= TURNS_PER_PLAYER:
        raise HTTPException(409, "You have completed all 15 turns.")
    if not room["deck"]:
        raise HTTPException(409, "The deck is empty.")
    card = room["deck"].pop()
    player["hand"].append(card)
    player["turns_taken"] += 1
    brand = BRAND_BY_ID[card["brand_id"]]
    matches = auto_match(player)
    room["turn_number"] += 1
    room["recent_event"] = f"{player['name']} drew a {brand['name']} card."
    if matches:
        room["recent_event"] += " Automatic match: " + ", ".join(matches) + "."
    finish_if_done(room)
    if room["status"] != "finished":
        current_index = next(i for i, p in enumerate(room["players"]) if p["id"] == player["id"])
        for offset in range(1, len(room["players"]) + 1):
            candidate = room["players"][(current_index + offset) % len(room["players"])]
            if candidate["turns_taken"] < TURNS_PER_PLAYER:
                room["active_player_id"] = candidate["id"]
                break
    await broadcast(room["code"])
    state = private_state(room, player)
    if room["status"] == "finished":
        state["final_scores"] = room["final_scores"]
    return state


@app.websocket("/ws/rooms/{code}")
async def room_socket(websocket: WebSocket, code: str):
    code = code.upper()
    if code not in rooms:
        await websocket.close(code=4404)
        return
    await websocket.accept()
    connections[code].append(websocket)
    try:
        await websocket.send_json({"type": "state_changed", "state": public_state(rooms[code])})
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        if websocket in connections[code]:
            connections[code].remove(websocket)


@app.get("/api/brands")
async def get_brands():
    return BRANDS


@app.get("/health")
async def health():
    return {"status": "ok"}
