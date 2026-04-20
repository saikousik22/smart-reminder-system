# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Backend
```bash
cd backend
python -m venv venv
source venv/Scripts/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload  # runs on port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev      # Vite dev server on port 5173
npm run build    # production bundle
npm run lint     # ESLint
npm run preview  # preview production build
```

### External requirements
- **ffmpeg** must be on PATH (used for WebM/Ogg → WAV transcoding)
- **ngrok**: `npx ngrok http 8000` — required so Twilio can reach local webhooks; update `PUBLIC_BASE_URL` in `backend/.env` with the generated URL

### Environment
Copy and fill in `backend/.env`:
```
DATABASE_URL=sqlite:///./reminders.db
JWT_SECRET_KEY=<secret>
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=<token>
TWILIO_PHONE_NUMBER=+1...
PUBLIC_BASE_URL=https://<ngrok-id>.ngrok-free.app
```

No test framework is configured.

## Architecture

### Request flow
1. Frontend (React/Vite, port 5173) proxies `/api` and `/audio` to backend (FastAPI, port 8000) via `vite.config.js`.
2. Auth uses JWT stored in HttpOnly cookies (`access_token`). The `get_current_user` dependency in `auth.py` is injected into all protected routes.
3. APScheduler (`scheduler.py`) polls the DB every 60 seconds for `pending` reminders whose `scheduled_time ≤ now`, marks them `calling`, and calls `twilio_service.make_reminder_call()`.
4. Twilio calls back two FastAPI webhooks: `POST /voice/{id}` (returns TwiML with `<Play>` pointing to the audio file URL) and `POST /voice/status/{id}` (updates reminder status to `answered`/`no-answer`/`busy`/`failed`).
5. Audio files are saved as UUIDs under `backend/uploads/` and served as static files at `/audio/*`. Non-WAV/MP3 formats are transcoded to WAV via ffmpeg in `reminder_router.py`.

### Backend structure (`backend/app/`)
| File | Responsibility |
|------|---------------|
| `main.py` | FastAPI app, CORS, static mount, DB init, scheduler start |
| `config.py` | Pydantic-settings loading from `.env` |
| `database.py` | SQLAlchemy engine, `SessionLocal`, `Base` |
| `models.py` | `User`, `Reminder` ORM models |
| `schemas.py` | Pydantic request/response schemas |
| `auth.py` | JWT create/verify, bcrypt password helpers, `get_current_user` dependency |
| `rate_limit.py` | In-memory per-IP rate limiter (5 login / 3 signup per minute) |
| `scheduler.py` | APScheduler job: polls due reminders, triggers calls, handles recurrence, recovers stuck `calling` reminders after 10 min |
| `twilio_service.py` | Twilio client wrapper, `make_reminder_call()` |
| `routers/auth_router.py` | `/auth/signup`, `/login`, `/logout`, `/me` |
| `routers/reminder_router.py` | CRUD for reminders + audio upload/ffmpeg transcode |
| `routers/voice_router.py` | TwiML webhook + status callback, Twilio signature validation |

### Frontend structure (`frontend/src/`)
| Path | Responsibility |
|------|---------------|
| `context/AuthContext.jsx` | Global auth state; calls `/auth/me` on load; 401 interceptor in `api/axios.js` redirects to `/login` |
| `pages/Dashboard.jsx` | Lists reminders with 30-second polling, status filter, title/phone search |
| `pages/CreateReminder.jsx` | Create/edit form; audio tab switches between `AudioRecorder` (MediaRecorder API) and `AudioUploader` (drag-and-drop) |
| `components/ReminderCard.jsx` | Status badge, inline audio playback, edit/delete actions |

### Reminder status lifecycle
`pending` → `calling` → `answered` / `no-answer` / `busy` / `failed`

Stuck `calling` reminders (>10 min) are auto-reset to `failed` by the scheduler.

### Recurrence logic (in `scheduler.py`)
After a call is triggered, a new `pending` reminder is created at the next occurrence: daily (+1 day), weekly (+7 days), monthly (+1 month with day-overflow handling), weekdays (+1 day skipping Sat/Sun). Stops when `recurrence_end_date` is reached.

### Key constraints
- SQLite is used for local dev; not safe for concurrent writes in production.
- Rate limiting is in-memory — not suitable for multi-process deployments (use Redis).
- All times are UTC; no timezone conversion is implemented.
- `PUBLIC_BASE_URL` must be set and reachable by Twilio (ngrok locally) for audio playback and webhook delivery.
