# Luxury League — playable multiplayer MVP

A four-player private-room card game prototype with:
- 6-character invitation codes
- Exactly four players per room
- Private player hands
- 80-card shuffled deck (20 brands × 4 copies)
- Five-card starting hands
- 15 turns per player (60 draws total)
- Automatic matching by `brand_id`
- Two matching cards score both card values plus 100 bonus points
- No discarding, trading, or stealing
- Live public scoreboard and WebSocket updates

## Requirements
- Python 3.10+
- A modern browser
- Network access between the four devices on the same network, or a deployed server

## Run the backend

From the project root:

```bash
cd backend
python -m venv .venv
# macOS/Linux:
source .venv/bin/activate
# Windows PowerShell:
# .venv\Scripts\Activate.ps1

pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The API is available at `http://127.0.0.1:8000` and Swagger docs at `/docs`.

## Run the frontend

For local testing, open `frontend/index.html` in a browser. If your browser blocks local file requests, serve it:

```bash
cd frontend
python -m http.server 5500
```

Then open `http://127.0.0.1:5500`.

### Connecting multiple devices
The frontend currently points to `http://127.0.0.1:8000`. For other devices, change the `API` constant at the top of `frontend/app.js` to the host computer's LAN IP, for example:

```js
const API = "http://192.168.1.20:8000";
```

All four devices must be able to reach that host and port. For internet play, deploy the backend and frontend to reachable HTTPS hosting and update `API` to the deployed backend URL.

## How to play
1. One player creates a private room and shares the six-character code.
2. Three others join with their display names and the code.
3. The host starts once all four players are in the lobby.
4. Each player starts with five cards. Starting-hand pairs are automatically matched.
5. Players take turns clockwise. The active player draws one card.
6. Any pair in the active player's hand with the same brand is automatically completed.
7. Completed pair score = card 1 value + card 2 value + 100 bonus.
8. No discarding. Unmatched cards remain in hand.
9. Each player takes 15 turns. Unmatched cards count at face value at the end.
10. Highest total wins.

## Important MVP limitations
- Game rooms are held in server memory. Restarting the backend clears active rooms.
- This prototype has no login/account system, database persistence, anti-cheat audit log, or production-grade rate limiting.
- WebSocket events expose public game state only. Each player's hand is fetched through an authenticated private API request.
- The first player to create a room is host. Only the host can start.
- The brand list and points are sample game content and can be edited in `backend/main.py`.
- If a player disconnects, their room session remains; reconnect by reopening the same browser session. Full reconnect/recovery and host migration should be added before production.
