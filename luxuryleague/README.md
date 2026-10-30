# Luxury League

This project contains a compact multiplayer card game implementation for the `luxuryleague` folder.

## Project layout

- `luxuryleague/backend/` — FastAPI server and game logic
- `luxuryleague/frontend/` — browser client for lobby, room, game, and results

## Run the backend

```bash
cd luxuryleague/backend
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

Open `luxuryleague/frontend/index.html` in a browser, or serve it locally:

```bash
cd luxuryleague/frontend
python -m http.server 5500
```

Then open `http://127.0.0.1:5500`.

If the backend is on another machine, update `API` in `frontend/app.js` to the correct host.

## Notes

- Four players are required per room.
- The host starts the round once everyone joins.
- Each player has five starting cards and 15 turns.
- Matching pairs are automatically scored.
