# AI Assistant Server – STUFE 1 (MVP, Text-Chat)

**Stack (fix):**
- Backend: FastAPI + Uvicorn
- DB: SQLite + SQLAlchemy
- Frontend: Vanilla JS SPA (served by backend)
- Streaming: SSE (Server-Sent Events)
- Auth: JWT in **httpOnly cookie** + CSRF double-submit cookie
- Reverse Proxy + HTTPS: Caddy (tls internal)

## Features (STUFE 1)
- Registrierung erzeugt User mit Status **pending**
- Login nur wenn Status **approved**
- Admin Panel: pending Users **approve/deny**
- Rollen: **admin / user**
- Pro User eigene Conversations + Messages in DB
- Conversations: erstellen, umbenennen, löschen
- SSE Streaming: Assistant Antwort erscheint live
- Ollama Anbindung per HTTP API: `OLLAMA_URL` + `OLLAMA_MODEL`

## 1) Setup (Windows)

### 1.1 Voraussetzungen
- Python 3.11+ (empfohlen)
- Git (optional)
- Ollama läuft in WSL2 und ist von Windows über `http://localhost:11434` erreichbar (wie von dir beschrieben)

### 1.2 Projekt holen / Ordner
Lege den Ordner `ai-assistant-mvp` an und kopiere alle Dateien exakt so hinein.

### 1.3 Virtualenv + Dependencies
Öffne PowerShell im Projektordner:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt"# AI-Voice" 
