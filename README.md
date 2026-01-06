# AI Assistant MVP (Stage 1) – Text Chat (FastAPI + SQLite + Vanilla JS + SSE + Ollama)

## Features (Stage 1)
- Registrierung/Login:
  - Register erstellt User mit `status=pending`
  - Login nur wenn `status=approved`
  - Rollen: `admin` / `user`
  - Admin-Panel: pending Users approve/deny
- Chat SPA:
  - Konversationsliste + Chatfenster
  - Konversationen: erstellen/umbenennen/löschen
  - Messages persistent in SQLite
- Ollama Integration:
  - Backend ruft Ollama HTTP API auf (`OLLAMA_URL`)
  - `OLLAMA_MODEL` via `.env`
  - Live-Streaming per SSE (`/api/conversations/{id}/stream`)
- Basis-Sicherheit:
  - Passwörter: Argon2 (passlib[argon2])
  - Auth: JWT im httpOnly Cookie
  - CSRF Schutz: double submit cookie (`csrf_token` Cookie + `X-CSRF-Token` Header)
- Logging:
  - logs/app.log

## Endpoints (required)
- POST /api/auth/register
- POST /api/auth/login
- POST /api/auth/logout
- GET  /api/me
- GET  /api/admin/users?status=pending
- POST /api/admin/users/{id}/approve
- POST /api/admin/users/{id}/deny
- GET  /api/conversations
- POST /api/conversations
- PATCH /api/conversations/{id}
- DELETE /api/conversations/{id}
- GET  /api/conversations/{id}/messages
- POST /api/conversations/{id}/messages
- GET  /api/conversations/{id}/stream

## Data
- SQLite DB: `backend/data/app.db`
- Logs: `logs/app.log`

## Stage 1.5 (implemented): Tools + Admin Settings + Internet Abfragen

### Admin Settings
Admin-Panel (`/admin`) enthält eine Sektion **Settings**. Diese Settings sind global (Heimnetz/Familie) und werden in SQLite gespeichert.

Neue Endpoints:
- GET  /api/admin/settings (admin only)
- PUT  /api/admin/settings (admin only)
- GET  /api/settings (read-only, eingeloggte User)

Defaults werden beim Start automatisch angelegt (singleton row).

### Tool-System
Tools sind strikt allowlisted und werden nur serverseitig ausgeführt.

Pflicht-Tools:
- `get_datetime()` (kein Internet)
- `get_weather(location_optional)` (Open-Meteo)
- `web_search(query,max_results)` (nur mit SEARXNG_URL)
- `recipe_search(query)` (nutzt web_search; LLM muss Quellen enthalten)

### Web Search (SearXNG)
Für Web-Suche wird **kein Scraping-Fallback** verwendet. Setze dafür in `.env`:

- `SEARXNG_URL=http://<host>:<port>`

Ohne diese Variable geben `web_search` und `recipe_search` eine klare Fehlermeldung zurück.

### LLM Tool-Orchestration (Planner → Tool → Final Answer)
Der Backend-Flow für `/api/conversations/{id}/stream`:
1) Planner Phase: Modell darf nur strikt JSON entscheiden (`respond` oder `tool_call`)
2) Optional Tool ausführen
3) Final Answer Phase: Modell erhält TOOL_RESULT_JSON und streamt wie Stage 1 per SSE

Tool-Results werden nicht als eigene Chatmessages gespeichert (UI bleibt unverändert).

## Stage 2 readiness (not implemented)
- Clear separation in:
  - `backend/services/` (LLM clients)
  - `backend/routers/` (API)
  - `frontend/` (SPA)
  - Easy to add websockets/audio later without rewriting auth/db foundations.