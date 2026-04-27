# Smart Reminder System — Complete Codebase Flow

## Table of Contents
1. [System Architecture Overview](#1-system-architecture-overview)
2. [Directory Structure](#2-directory-structure)
3. [Environment Variables](#3-environment-variables)
4. [Database Schema](#4-database-schema)
5. [Backend API — All Endpoints](#5-backend-api--all-endpoints)
6. [User Flows — End to End](#6-user-flows--end-to-end)
7. [Background Job Pipeline](#7-background-job-pipeline)
8. [Twilio Call & SMS Flow](#8-twilio-call--sms-flow)
9. [Frontend Pages & Components](#9-frontend-pages--components)
10. [Frontend API Calls Map](#10-frontend-api-calls-map)
11. [Database Hit Count — Every Endpoint](#11-database-hit-count--every-endpoint)
12. [Data Flow Diagrams](#12-data-flow-diagrams)

---

## 1. System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                          BROWSER (React)                            │
│  Login/Signup → Dashboard → Create Reminder → Analytics             │
│  Contacts → Groups → Calendar → (all behind ProtectedRoute)         │
└──────────────────────────┬──────────────────────────────────────────┘
                           │ HTTP / axios (JSON + FormData)
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      FASTAPI (Python)                               │
│  /auth  /reminders  /voice  /templates  /contacts                   │
│  /groups  /dashboard  /translate                                    │
│  Static: /audio → backend/uploads/                                  │
└────┬────────────────────────┬──────────────────────────────────────-┘
     │ SQLAlchemy              │ Celery tasks (trigger_call / beat)
     ▼                         ▼
┌──────────────┐       ┌──────────────────────────────────────────────┐
│ PostgreSQL   │       │  Redis (broker + result backend)             │
│  SHR_V1.*   │       │                                              │
└──────────────┘       │  Celery Worker  ←  Celery Beat (10min, recovery-only)  │
                       └──────────────────────┬───────────────────────┘
                                              │ REST API calls
                                              ▼
                                     ┌────────────────┐
                                     │  Twilio API    │
                                     │  Voice + SMS   │
                                     └───────┬────────┘
                                             │ Webhooks back to FastAPI
                                             ▼
                                     /voice/{id}  (TwiML)
                                     /voice/status/{id}  (callback)
```

**Tech stack at a glance:**

| Layer | Technology |
|---|---|
| Frontend | React 18, Vite, TailwindCSS, Axios, Recharts, FullCalendar |
| Backend | FastAPI 0.115, Python 3.x |
| ORM | SQLAlchemy 2.0 + Alembic migrations |
| Database | PostgreSQL (dev: SQLite) |
| Task Queue | Celery 5.4 with Redis broker |
| Voice/SMS | Twilio REST API |
| Translation | deep-translator (Google Translate, free) |
| Auth | JWT (HS256) in HttpOnly cookie + Bearer header |

---

## 2. Directory Structure

```
smart-reminder-system/
├── backend/
│   ├── .env                        ← secrets (never commit)
│   ├── .env.example                ← template
│   ├── requirements.txt
│   ├── uploads/                    ← audio files (UUID filenames)
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/               ← 8 migration files
│   └── app/
│       ├── main.py                 ← FastAPI app, CORS, mounts routers
│       ├── config.py               ← Pydantic Settings (reads .env)
│       ├── database.py             ← SQLAlchemy engine + get_db()
│       ├── models.py               ← ORM models (6 tables)
│       ├── schemas.py              ← Pydantic request/response schemas
│       ├── auth.py                 ← JWT + bcrypt helpers
│       ├── celery_app.py           ← Celery config + beat schedule
│       ├── tasks.py                ← enqueue_reminder_eta, trigger_call, _handle_system_failure, recover_missed_reminders
│       ├── scheduler.py            ← recurrence + retry helpers
│       ├── twilio_service.py       ← make_reminder_call()
│       ├── rate_limit.py           ← in-memory rate limiter
│       ├── routers/
│       │   ├── auth_router.py
│       │   ├── reminder_router.py
│       │   ├── voice_router.py
│       │   ├── template_router.py
│       │   ├── translate_router.py
│       │   ├── dashboard_router.py
│       │   ├── contacts_router.py
│       │   └── groups_router.py
│       └── services/
│           ├── sms_service.py      ← Twilio SMS
│           └── translate_service.py← GoogleTranslator wrapper
└── frontend/
    ├── package.json
    ├── vite.config.js              ← proxy /api → localhost:8000
    └── src/
        ├── main.jsx
        ├── App.jsx                 ← routes + ErrorBoundary
        ├── api/axios.js            ← axios instance + 401 interceptor
        ├── context/AuthContext.jsx ← login/logout/user state
        ├── components/
        │   ├── Navbar.jsx
        │   ├── ProtectedRoute.jsx
        │   ├── AudioRecorder.jsx   ← MediaRecorder API
        │   ├── AudioUploader.jsx
        │   ├── ReminderCard.jsx
        │   └── CalendarView.jsx    ← FullCalendar
        └── pages/
            ├── Login.jsx
            ├── Signup.jsx
            ├── Dashboard.jsx
            ├── CreateReminder.jsx
            ├── DashboardAnalytics.jsx
            ├── Contacts.jsx
            └── Groups.jsx
```

---

## 3. Environment Variables

All consumed by `backend/app/config.py` (Pydantic BaseSettings):

| Variable | Default | Required in Prod |
|---|---|---|
| `APP_NAME` | SmartReminderSystem | No |
| `DEBUG` | False | Set `false` |
| `DATABASE_URL` | postgresql://postgres:postgres@localhost:5432/smart_reminder | **YES** |
| `JWT_SECRET_KEY` | change-this-secret-key-in-production | **YES** — change it |
| `JWT_ALGORITHM` | HS256 | No |
| `JWT_EXPIRY_HOURS` | 24 | No |
| `TWILIO_ACCOUNT_SID` | — | **YES** |
| `TWILIO_AUTH_TOKEN` | — | **YES** |
| `TWILIO_PHONE_NUMBER` | — | **YES** |
| `REDIS_URL` | redis://localhost:6379/0 | **YES** |
| `PUBLIC_BASE_URL` | http://localhost:8000 | **YES** — must be public HTTPS URL |
| `CORS_ORIGINS` | ["http://localhost:5173"] | **YES** — set frontend domain |
| `COOKIE_SECURE` | False | Set `true` on HTTPS |

Frontend `.env` (Vite):

| Variable | Default | Notes |
|---|---|---|
| `VITE_API_URL` | `/api` (proxied) | Set to full backend URL in production |

---

## 4. Database Schema

Schema name: `SHR_V1`

### Table: users
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | auto increment |
| username | VARCHAR(50) UNIQUE | |
| email | VARCHAR(100) UNIQUE | |
| hashed_password | TEXT | bcrypt |
| created_at | DATETIME | |

### Table: reminders
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| user_id | INTEGER FK(users) | |
| title | VARCHAR(200) | |
| phone_number | VARCHAR(20) | E.164 |
| scheduled_time | DATETIME | UTC |
| audio_filename | TEXT | UUID name in uploads/ |
| status | VARCHAR(20) | pending/processing/calling/answered/no-answer/busy/failed_system |
| recurrence | VARCHAR(20) | daily/weekly/monthly/weekdays or NULL |
| recurrence_end_date | DATETIME | optional |
| call_sid | VARCHAR(50) | Twilio call SID |
| retry_count | INTEGER | 0–2 (max retries) |
| retry_gap_minutes | INTEGER | 5–60 |
| attempt_number | INTEGER | 1 for original, 2/3 for retries |
| parent_reminder_id | INTEGER FK(reminders) | self-ref for retry chain |
| system_retry_count | INTEGER | infra retry counter (0–2, independent of user retry_count) |
| feedback_rating | INTEGER | 1–5 |
| feedback_comment | TEXT | |
| original_text | TEXT | English text for SMS |
| fallback_text | TEXT | translated SMS text |
| fallback_sent | BOOLEAN | idempotent SMS guard |
| preferred_language | VARCHAR(10) | ISO 639-1 |
| group_id | INTEGER FK(groups) | if from group |
| created_at | DATETIME | |
| updated_at | DATETIME | |

Indexes: `(user_id)`, `(status, scheduled_time)`, `(status, updated_at)`

### Table: groups
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| user_id | INTEGER FK(users) | |
| name | VARCHAR(100) | |
| created_at | DATETIME | |

### Table: group_members (junction)
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| group_id | INTEGER FK(groups) | |
| contact_id | INTEGER FK(contacts) | |
| UNIQUE | (group_id, contact_id) | no duplicates |

### Table: contacts
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| user_id | INTEGER FK(users) | |
| name | VARCHAR(100) | |
| phone_number | VARCHAR(20) | E.164 |
| created_at | DATETIME | |

### Table: reminder_templates
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| user_id | INTEGER FK(users) | |
| name | VARCHAR(100) | display name |
| title | VARCHAR(200) | |
| phone_number | VARCHAR(20) | |
| audio_filename | TEXT | |
| recurrence | VARCHAR(20) | |
| retry_count | INTEGER | |
| retry_gap_minutes | INTEGER | |
| created_at | DATETIME | |

### Entity Relationships
```
users ──< reminders
users ──< reminder_templates
users ──< contacts
users ──< groups
groups ──< group_members >── contacts
groups ──< reminders (group_id)
reminders ──< reminders (parent_reminder_id = retry chain)
```

---

## 5. Backend API — All Endpoints

Base URL: `http://localhost:8000` (development)

### Auth — `/auth`

| Method | Path | Auth | Request | Response | Notes |
|---|---|---|---|---|---|
| POST | /auth/signup | No | `{username, email, password}` | `{message}` | Rate: 3/60s |
| POST | /auth/login | No | `{email, password}` | `{access_token, token_type}` + HttpOnly cookie | Rate: 5/60s |
| POST | /auth/logout | No | — | `{message}` | Clears cookie |
| GET | /auth/me | JWT | — | `{id, username, email, created_at}` | |

### Reminders — `/reminders`

| Method | Path | Auth | Request | Response | Notes |
|---|---|---|---|---|---|
| POST | /reminders | JWT | FormData (see below) | ReminderResponse | Creates reminder |
| GET | /reminders | JWT | `?status_filter=` | list[ReminderResponse] | Sorted by scheduled_time DESC |
| GET | /reminders/{id} | JWT | — | ReminderResponse | |
| PUT | /reminders/{id} | JWT | FormData (all optional) | ReminderResponse | Updates reminder |
| PUT | /reminders/{id}/feedback | JWT | `{rating, comment}` | ReminderResponse | 1–5 stars |
| DELETE | /reminders/{id} | JWT | — | `{message}` | Deletes file too |
| GET | /reminders/{id}/export-ics | JWT | — | .ics file | Calendar download |

**POST /reminders FormData fields:**
```
title            (string, required)
phone_number     (string, E.164, e.g. +14155552671)
scheduled_time   (ISO 8601 string, must be future)
audio_file       (file, optional if template_id given)
template_id      (integer, optional)
recurrence       (daily|weekly|monthly|weekdays, optional)
recurrence_end_date (ISO 8601, optional)
retry_count      (0|1|2, default 0)
retry_gap_minutes (5–60, default 10)
original_text    (string, English text for SMS fallback)
fallback_text    (string, translated text for SMS)
preferred_language (ISO 639-1 code)
```

### Voice Webhooks — `/voice` (called by Twilio, not frontend)

| Method | Path | Auth | Request | Response | Notes |
|---|---|---|---|---|---|
| POST | /voice/{id} | Twilio sig | Twilio form fields | TwiML XML | Plays audio |
| POST | /voice/status/{id} | Twilio sig | Twilio form fields | 200 OK | Updates status |

**TwiML response for /voice/{id}:**
```xml
<Response>
  <Say>Hello! Here is your scheduled reminder.</Say>
  <Play>https://PUBLIC_BASE_URL/audio/{filename}</Play>
  <Say>Goodbye!</Say>
  <Hangup/>
</Response>
```

### Templates — `/templates`

| Method | Path | Auth | Request | Response | Notes |
|---|---|---|---|---|---|
| GET | /templates | JWT | — | list[TemplateResponse] | |
| POST | /templates | JWT | FormData | TemplateResponse | Upload audio |
| POST | /templates/from-reminder/{id} | JWT | `{name}` | TemplateResponse | Copy from reminder |
| DELETE | /templates/{id} | JWT | — | `{message}` | Deletes file too |

### Contacts — `/contacts`

| Method | Path | Auth | Request | Response | Notes |
|---|---|---|---|---|---|
| GET | /contacts | JWT | — | list[ContactResponse] | Sorted by name |
| POST | /contacts | JWT | `{name, phone_number}` | ContactResponse | E.164 validated |
| PUT | /contacts/{id} | JWT | `{name?, phone_number?}` | ContactResponse | |
| DELETE | /contacts/{id} | JWT | — | `{message}` | |

### Groups — `/groups`

| Method | Path | Auth | Request | Response | Notes |
|---|---|---|---|---|---|
| GET | /groups | JWT | — | list[GroupResponse] | Includes members |
| POST | /groups | JWT | `{name}` | GroupResponse | |
| PUT | /groups/{id} | JWT | `{name}` | GroupResponse | Rename |
| DELETE | /groups/{id} | JWT | — | `{message}` | Cascades |
| POST | /groups/{id}/members | JWT | `{contact_id}` | GroupResponse | |
| DELETE | /groups/{id}/members/{contact_id} | JWT | — | GroupResponse | |
| POST | /groups/{id}/remind | JWT | FormData | GroupReminderCreateResponse | Creates N reminders |

### Dashboard — `/dashboard`

| Method | Path | Auth | Response | Notes |
|---|---|---|---|---|
| GET | /dashboard/analytics | JWT | AnalyticsResponse | Stats + 7-day trend |
| GET | /dashboard/group-analytics | JWT | GroupAnalyticsResponse | Group batch stats |

**AnalyticsResponse:**
```json
{
  "total_reminders": 42,
  "success_rate": 85.7,
  "sms_fallback_count": 3,
  "total_retries": 5,
  "failed_distribution": {"failed": 2, "no_answer": 1, "busy": 0},
  "retry_distribution": {"0": 30, "1": 8, "2": 4},
  "trend_7_days": [{"date": "2026-04-18", "count": 5}, ...],
  "template_count": 7
}
```

### Translate — `/translate`

| Method | Path | Auth | Request | Response | Notes |
|---|---|---|---|---|---|
| GET | /translate/languages | JWT | — | `{code: name, ...}` | 20 languages |
| POST | /translate | JWT | `{text, target_lang}` | TranslateResponse | Preview only |

**Supported languages:** hi, te, ta, kn, ml, mr, bn, gu, pa, ur, fr, es, de, ar, zh-CN, ja, ko, pt, ru, it

### Static Files
```
GET /audio/{filename}    ← Serves from backend/uploads/
```

---

## 6. User Flows — End to End

### Flow 1: Sign Up & Log In
```
1. User opens /signup
2. Fills username, email, password, confirmPassword
3. Frontend: POST /auth/signup  →  {message: "User created"}
4. Frontend: POST /auth/login   →  {access_token} + sets HttpOnly cookie
5. AuthContext stores user state
6. Redirected to /dashboard
```

### Flow 2: Create a Single Reminder
```
1. User navigates to /create
2. Page loads templates: GET /templates
3. User fills form:
   - Title: "Doctor appointment"
   - Phone: +14155552671
   - Date/time: 2026-04-25 09:00
   - Audio: records via browser mic (AudioRecorder component)
     OR uploads audio file (AudioUploader component)
   - Recurrence: weekly
   - Retry count: 1, gap: 10 min
4. (Optional) SMS fallback:
   - User types English text
   - Selects language (e.g. "hi" = Hindi)
   - Clicks "Translate" → POST /translate → preview shown
   - Clicks "Confirm" to save translation to form state
5. Submit: POST /reminders (multipart FormData)
   → Backend saves to DB, audio saved as UUID.wav in uploads/
   → Response: ReminderResponse {id, status:"pending", ...}
6. Redirected to /dashboard
```

### Flow 3: Reminder Fires (Automated — ETA-based)
```
1. POST /reminders saves reminder to DB (status='pending')
2. enqueue_reminder_eta(reminder) called immediately:
   → trigger_call.apply_async(args=[id], eta=scheduled_time)
   → Celery pushes an ETA task into Redis — fires at EXACT scheduled_time

3. At scheduled_time, Celery worker picks up trigger_call(reminder_id):
   a. Atomic DB claim:
      UPDATE reminders SET status='processing'
      WHERE id=? AND status IN ('pending','processing')
      → If 0 rows updated: another worker already claimed it → exit silently
   b. Stale-ETA guard: if scheduled_time > now+60s → release to 'pending', exit
      (handles case where user edited scheduled_time after ETA was enqueued)
   c. make_reminder_call(phone_number, reminder_id) → Twilio REST API
   d. On Twilio API failure (network, credentials, rate-limit):
      → _handle_system_failure(): system retry with 30s/60s backoff
      → If system retries exhausted: status='failed_system'
   e. On success: status='calling', call_sid stored

4. Twilio dials user's phone
   → Fetches TwiML from POST /voice/{reminder_id}
   → TwiML says greeting + plays /audio/{filename}

5. Call ends → Twilio fires POST /voice/status/{reminder_id}:

   CallStatus='completed' (user answered):
     → status='answered'
     → If recurrence: _schedule_next_occurrence() + enqueue_reminder_eta(next)

   CallStatus='no-answer' or 'busy' (USER-SIDE failure — phone rang):
     → If retries remain (attempt_number ≤ retry_count):
        _schedule_retry() creates new reminder row (attempt_number+1)
        enqueue_reminder_eta(retry_reminder)
     → If final attempt:
        If recurrence: schedule next occurrence
        SMS fallback sent (fallback_sent=True, idempotent)

   CallStatus='failed' or 'canceled' (SYSTEM-SIDE failure — Twilio couldn't connect):
     → _handle_system_failure(): system retry with 30s/60s backoff
     → If system retries exhausted (status='failed_system'):
        If recurrence: schedule next occurrence
        SMS fallback sent
```

### Flow 4: Group Reminder
```
1. User goes to /groups, creates a group, adds contacts
2. Clicks "Create Reminder" for the group
3. Navigated to /create with group state
4. Fills reminder form (no phone field — group handles phones)
5. Submit: POST /groups/{id}/remind
   → Creates one reminder per group member
   → Each reminder: own audio file copy, own phone number
   → All fire at same scheduled_time
6. Viewing analytics: GET /dashboard/group-analytics
   → Batches grouped by (title, scheduled_time)
   → Member reliability tracked per contact
```

### Flow 5: View Dashboard
```
1. User opens /dashboard
2. GET /reminders (optionally ?status_filter=pending)
3. ReminderCard renders for each:
   - Play audio via GET /audio/{filename}
   - Edit → navigates to /edit/{id}
   - Delete → DELETE /reminders/{id}
   - Export ICS → GET /reminders/{id}/export-ics
   - Save as template → POST /templates/from-reminder/{id}
4. For terminal status (answered/failed/no-answer/busy):
   - Star rating UI shown
   - Submit: PUT /reminders/{id}/feedback
5. Polling: re-fetches GET /reminders every 30s
```

### Flow 6: Analytics
```
1. User opens /analytics
2. GET /dashboard/analytics → stat cards + charts
3. GET /dashboard/group-analytics → group table + member reliability
4. Recharts renders:
   - AreaChart: 7-day trend
   - PieChart: retry distribution
   - PieChart: failure distribution
```

### Flow 7: Template Management
```
1. GET /templates → list existing templates
2. Create template:
   - Upload audio + fill fields → POST /templates
   - OR from reminder → POST /templates/from-reminder/{id}
3. When creating reminder, select template → audio auto-populated
4. DELETE /templates/{id} → removes template + audio file
```

---

## 7. Background Job Pipeline

### Primary Scheduler — ETA-based (exact-time firing)
```
enqueue_reminder_eta(reminder)
  Called after every db.commit() that creates or reschedules a reminder.
  → trigger_call.apply_async(args=[reminder.id], eta=reminder.scheduled_time)
  → Task sits in Redis until the exact fire time — zero DB polling

trigger_call(reminder_id)  [Celery Worker]
├── Atomic claim: UPDATE WHERE status IN ('pending','processing') → 'processing'
│   → 0 rows updated? Already claimed by another worker — exit silently
├── Stale-ETA guard: scheduled_time > now+60s? Release to 'pending', exit
│   (user edited the reminder after ETA was enqueued — new ETA handles it)
├── make_reminder_call(phone_number, reminder_id)  [Twilio REST API]
│   ├── SUCCESS: status='calling', call_sid stored
│   └── EXCEPTION (network, credentials, rate-limit, etc.):
│       _handle_system_failure(db, reminder, reason)
└── All user-side outcomes (no-answer, busy, completed) handled by
    /voice/status/{id} Twilio webhook callback — NOT here
```

### _handle_system_failure() — infrastructure failure handler
```
Called when: Twilio API throws an exception in trigger_call
             OR Twilio sends CallStatus='failed'/'canceled'

reminder.system_retry_count += 1

If system_retry_count ≤ 2 (MAX_SYSTEM_RETRIES):
  reminder.status = 'pending'
  db.commit()
  Backoff: 30s on first failure, 60s on second
  trigger_call.apply_async(eta=now+backoff_seconds)

If system_retry_count > 2:
  reminder.status = 'failed_system'
  db.commit()
  → Caller (voice_router) then sends SMS fallback + schedules next recurrence
```

### Safety Net 1 — Celery Beat (every 10 minutes, recovery-only)
```
recover_missed_reminders()

PRIMARY PATH — only runs if ETA tasks were lost (Redis restart, crash).
Does NOT run in normal operation.

1. Stuck recovery:
   SELECT WHERE status IN ('calling','processing') AND updated_at <= now-10min
   → Worker crashed mid-call OR Twilio webhook was never received
   → Applies _handle_system_failure logic:
      system_retry_count ≤ 2: status='pending', re-enqueue with backoff
      system_retry_count > 2: status='failed_system'

2. Missed reminder recovery:
   SELECT WHERE status='pending' AND scheduled_time <= now-30s
   (30s grace period lets normal ETA tasks fire first)
   → Batch-marks as 'processing' in one commit (prevents double-enqueue
     if beat fires again before workers process these)
   → trigger_call.delay(r.id) for each
```

### Safety Net 2 — Startup Recovery (FastAPI lifespan)
```
_startup_recovery()  — runs once when the app starts

Handles Azure deployment restarts: if the app was down for a few minutes,
ETA tasks whose fire time passed during the downtime will never fire.

SELECT WHERE status='pending' AND scheduled_time <= now AND scheduled_time >= now-10min
→ Re-enqueues each as trigger_call.delay(r.id) immediately
→ 10-minute window: very recent misses only (older ones likely need manual review)
```

### _schedule_next_occurrence() — for recurring reminders
```
compute_next_time(scheduled_time, recurrence)
├── daily    → + 1 day
├── weekly   → + 7 days
├── monthly  → same day next month
└── weekdays → + 1 day skipping Sat/Sun

If next_time <= recurrence_end_date (or no end date):
  db.add(new reminder, status='pending', scheduled_time=next_time)
  db.flush()           ← assigns ID before caller commits
  return new_reminder  ← caller commits then calls enqueue_reminder_eta(new_reminder)
```

### _schedule_retry() — for user-side failures (no-answer, busy)
```
If reminder.attempt_number <= reminder.retry_count:
  db.add(new reminder,
    status='pending',
    scheduled_time = now + retry_gap_minutes,
    attempt_number = attempt_number + 1,
    parent_reminder_id = original.id
  )
  db.flush()           ← assigns ID before caller commits
  return new_reminder  ← caller commits then calls enqueue_reminder_eta(new_reminder)
```

### Two-Layer Retry System Summary
```
Layer 1 — USER retry (no-answer / busy):
  Controlled by: reminder.retry_count (user's setting, 0–2)
  Tracked by:    reminder.attempt_number
  New row per attempt: parent_reminder_id chains them
  Scheduled by:  _schedule_retry() + enqueue_reminder_eta()

Layer 2 — SYSTEM retry (infra failures):
  Triggered by:  Twilio API exception OR CallStatus='failed'/'canceled'
  Controlled by: MAX_SYSTEM_RETRIES = 2 (always, regardless of user setting)
  Tracked by:    reminder.system_retry_count on the SAME reminder row
  Backoff:       30s → 60s
  Exhausted:     status='failed_system'
  Scheduled by:  _handle_system_failure() directly
```

---

## 8. Twilio Call & SMS Flow

### Outbound Call Flow
```
FastAPI (trigger_call)
  │ REST API: POST /2010-04-01/Accounts/{SID}/Calls
  ▼
Twilio
  │ Initiates phone call to user's phone_number
  │ When connected, fetches TwiML from:
  ▼
FastAPI: POST /voice/{reminder_id}
  │ Validates X-Twilio-Signature header
  │ Returns TwiML XML
  ▼
Twilio
  │ Plays audio, says messages
  │ Hangs up
  │ Fires status callback to:
  ▼
FastAPI: POST /voice/status/{reminder_id}
  │ Parses CallStatus field
  │ Updates reminder.status in DB
  └── If failure + fallback: POST /2010-04-01/Accounts/{SID}/Messages (SMS)
```

### Twilio Webhook Requirements
- `PUBLIC_BASE_URL` must be publicly reachable HTTPS URL
- Twilio validates signature on `/voice/*` routes
- In development: use ngrok tunnel
- In production: use the Azure App Service URL or custom domain

### Twilio CallStatus Classification
```
CallStatus      Classification   Handler
─────────────────────────────────────────────────────────────────
completed       SUCCESS          Mark 'answered', schedule recurrence
no-answer       USER FAILURE     Phone rang, user didn't pick up → _schedule_retry
busy            USER FAILURE     User's line was busy            → _schedule_retry
failed          SYSTEM FAILURE   Twilio couldn't connect call    → _handle_system_failure
canceled        SYSTEM FAILURE   Call canceled before connecting → _handle_system_failure
```

### SMS Fallback
```
Conditions for SMS to send:
  USER-SIDE path:   final attempt failed (no-answer/busy) AND attempt_number > retry_count
  SYSTEM-SIDE path: all system retries exhausted (status='failed_system')
  Guard:            fallback_sent == False (idempotent — safe if Twilio fires callback twice)

Message content priority:
  1. reminder.fallback_text (user's translated text)
  2. "You missed a reminder: {reminder.original_text}"
  3. "You missed a reminder: {reminder.title}"
```

---

## 9. Frontend Pages & Components

### Route Map
```
/               → redirect to /dashboard
/login          → Login.jsx         (public)
/signup         → Signup.jsx        (public)
/dashboard      → Dashboard.jsx     (protected)
/analytics      → DashboardAnalytics.jsx (protected)
/calendar       → CalendarView.jsx  (protected)
/create         → CreateReminder.jsx (protected)
/edit/:id       → CreateReminder.jsx (protected, edit mode)
/contacts       → Contacts.jsx      (protected)
/groups         → Groups.jsx        (protected)
*               → redirect to /dashboard
```

### AuthContext
```
State: { user, loading }

login(email, password)
  → POST /auth/login
  → GET /auth/me
  → sets user state

signup(username, email, password)
  → POST /auth/signup
  → login(email, password)

logout()
  → POST /auth/logout
  → clears user state, redirects /login

On mount: GET /auth/me to restore session from cookie
```

### ProtectedRoute
```
if (loading) → show loading spinner
if (!user)   → redirect to /login
else         → render children
```

### AudioRecorder
```
Uses: navigator.mediaDevices.getUserMedia({ audio: true })
States: idle → recording → recorded
Timer: shows MM:SS during recording
Output: File("recording.webm", blob, {type: "audio/webm"})
Callback: onRecordingComplete(File)
```

### AudioUploader
```
Accepts: .wav, .mp3, .ogg, .webm, .m4a
Drag-and-drop or click to browse
Output: File object
Callback: onFileSelect(File)
```

### ReminderCard
```
Shows: title, phone, scheduled_time, status badge
Icons: recurrence, group, retry chain, language
Audio: plays from /audio/{filename}
Actions:
  - Edit → /edit/{id}
  - Delete → DELETE /reminders/{id}
  - Export ICS → GET /reminders/{id}/export-ics
  - Save template → POST /templates/from-reminder/{id}
  - Download audio → GET /audio/{filename}
Feedback (terminal status):
  - Stars UI → PUT /reminders/{id}/feedback
```

### CalendarView
```
Library: @fullcalendar/react daygrid
Colors: green=answered, red=failed/no-answer, yellow=pending, blue=processing
Click event: shows reminder details
```

---

## 10. Frontend API Calls Map

| Page/Component | Method | Endpoint | Trigger |
|---|---|---|---|
| AuthContext (mount) | GET | /auth/me | App load |
| Login | POST | /auth/login | Form submit |
| Signup | POST | /auth/signup | Form submit |
| Signup | POST | /auth/login | After signup |
| Navbar | POST | /auth/logout | Logout click |
| Dashboard | GET | /reminders | Mount + every 30s |
| Dashboard | DELETE | /reminders/{id} | Delete button |
| CreateReminder | GET | /templates | Mount |
| CreateReminder | GET | /translate/languages | Mount |
| CreateReminder | POST | /translate | Translate button |
| CreateReminder | POST | /reminders | Submit (new) |
| CreateReminder | PUT | /reminders/{id} | Submit (edit) |
| CreateReminder | GET | /reminders/{id} | Mount (edit mode) |
| CreateReminder | POST | /groups/{id}/remind | Submit (group mode) |
| ReminderCard | PUT | /reminders/{id}/feedback | Feedback submit |
| ReminderCard | GET | /reminders/{id}/export-ics | Export click |
| ReminderCard | POST | /templates/from-reminder/{id} | Save template |
| DashboardAnalytics | GET | /dashboard/analytics | Mount |
| DashboardAnalytics | GET | /dashboard/group-analytics | Mount |
| Contacts | GET | /contacts | Mount |
| Contacts | POST | /contacts | Create form submit |
| Contacts | PUT | /contacts/{id} | Inline edit save |
| Contacts | DELETE | /contacts/{id} | Delete button |
| Groups | GET | /groups | Mount |
| Groups | GET | /contacts | Mount (for member dropdown) |
| Groups | POST | /groups | Create form submit |
| Groups | PUT | /groups/{id} | Rename save |
| Groups | DELETE | /groups/{id} | Delete button |
| Groups | POST | /groups/{id}/members | Add member button |
| Groups | DELETE | /groups/{id}/members/{contact_id} | Remove member |
| CalendarView | GET | /reminders | Mount |
| Templates page | GET | /templates | Mount |
| Templates page | POST | /templates | Upload form |
| Templates page | DELETE | /templates/{id} | Delete button |

---

## 11. Database Hit Count — Every Endpoint

> **How to read this table:**
> - Every authenticated endpoint automatically gets **+1 DB hit** from `get_current_user()` in [auth.py](backend/app/auth.py#L93) — it does `db.query(User).filter(User.id == user_id).first()`.
> - A **"write"** counts as 1 hit (`db.commit()`). A **"read"** counts as 1 hit (`db.query(...).all()` or `.first()`).
> - `_schedule_next_occurrence()` and `_schedule_retry()` each do a `db.add()` but NO separate commit — their row is flushed inside the caller's commit, so they add **0 extra round-trips** unless called in a different context.

---

### Auth — `/auth`

| Endpoint | DB Hits | Breakdown |
|---|---|---|
| POST /auth/signup | **3** | 1 check email, 1 check username, 1 INSERT user |
| POST /auth/login | **1** | 1 SELECT user by email |
| POST /auth/logout | **0** | only clears cookie, no DB |
| GET /auth/me | **1** | 1 SELECT user (from `get_current_user`) |

---

### Reminders — `/reminders`

> All endpoints below: **+1** from `get_current_user` already included in totals.

| Endpoint | DB Hits | Breakdown |
|---|---|---|
| POST /reminders (audio upload) | **2** | 1 auth user, 1 INSERT reminder |
| POST /reminders (template_id) | **3** | 1 auth user, 1 SELECT template, 1 INSERT reminder |
| GET /reminders | **2** | 1 auth user, 1 SELECT all user reminders |
| GET /reminders/{id} | **2** | 1 auth user, 1 SELECT reminder by id |
| PUT /reminders/{id} | **3** | 1 auth user, 1 SELECT reminder, 1 UPDATE commit |
| PUT /reminders/{id}/feedback | **3** | 1 auth user, 1 SELECT reminder, 1 UPDATE commit |
| DELETE /reminders/{id} | **3** | 1 auth user, 1 SELECT reminder, 1 DELETE commit |
| GET /reminders/{id}/export-ics | **2** | 1 auth user, 1 SELECT reminder |

---

### Voice Webhooks — `/voice` (called by Twilio, no JWT)

| Endpoint | DB Hits | Breakdown |
|---|---|---|
| POST /voice/{id} | **1** | 1 SELECT reminder (to get audio_filename for TwiML) |
| POST /voice/status/{id} — call answered | **2** | 1 SELECT reminder, 1 UPDATE commit (+ `db.add` next recurrence in same commit = still 1 write) |
| POST /voice/status/{id} — failure + retry available | **2** | 1 SELECT reminder, 1 UPDATE commit (+ `db.add` retry reminder in same commit) |
| POST /voice/status/{id} — final failure + SMS fallback | **2** | 1 SELECT reminder, 1 UPDATE commit (sets `fallback_sent=True`) |
| POST /voice/status/{id} — intermediate status (ringing, etc.) | **0** | discarded early before any DB query |

---

### Templates — `/templates`

| Endpoint | DB Hits | Breakdown |
|---|---|---|
| GET /templates | **2** | 1 auth user, 1 SELECT all user templates |
| POST /templates (upload) | **2** | 1 auth user, 1 INSERT template |
| POST /templates/from-reminder/{id} | **3** | 1 auth user, 1 SELECT reminder, 1 INSERT template |
| DELETE /templates/{id} | **3** | 1 auth user, 1 SELECT template, 1 DELETE commit |

---

### Contacts — `/contacts`

| Endpoint | DB Hits | Breakdown |
|---|---|---|
| GET /contacts | **2** | 1 auth user, 1 SELECT all user contacts |
| POST /contacts | **3** | 1 auth user, 1 SELECT duplicate phone check, 1 INSERT contact |
| PUT /contacts/{id} (name only) | **3** | 1 auth user, 1 SELECT contact, 1 UPDATE commit |
| PUT /contacts/{id} (phone changed) | **4** | 1 auth user, 1 SELECT contact, 1 SELECT duplicate phone check, 1 UPDATE commit |
| DELETE /contacts/{id} | **3** | 1 auth user, 1 SELECT contact, 1 DELETE commit |

---

### Groups — `/groups`

> **Lazy loading note:** `_build_group_response()` accesses `group.members` (lazy relationship).
> Each group triggers 1 extra query to load its members. For a list of N groups, add +N hits.

| Endpoint | DB Hits | Breakdown |
|---|---|---|
| GET /groups (N groups) | **2 + N** | 1 auth user, 1 SELECT groups, +1 per group for members (lazy load) |
| POST /groups | **4** | 1 auth user, 1 SELECT duplicate name, 1 INSERT group, 1 lazy load members |
| PUT /groups/{id} | **4** | 1 auth user, 1 SELECT group, 1 UPDATE commit, 1 lazy load members |
| DELETE /groups/{id} | **3** | 1 auth user, 1 SELECT group, 1 DELETE commit |
| POST /groups/{id}/members | **6** | 1 auth user, 1 SELECT group, 1 SELECT contact, 1 SELECT duplicate member, 1 INSERT member commit, 1 lazy load members |
| DELETE /groups/{id}/members/{contact_id} | **5** | 1 auth user, 1 SELECT group, 1 SELECT group_member, 1 DELETE commit, 1 lazy load members |
| POST /groups/{id}/remind — N members (audio) | **3 + N** | 1 auth user, 1 SELECT group, 1 lazy load members, then 1 lazy load per member's contact for phone number, 1 bulk INSERT (all N reminders in 1 commit) |
| POST /groups/{id}/remind — N members (template) | **4 + N** | same as above + 1 SELECT template |

---

### Dashboard — `/dashboard`

| Endpoint | DB Hits | Breakdown |
|---|---|---|
| GET /dashboard/analytics | **3** | 1 auth user, 1 SELECT all reminders (single query, all stats computed in Python), 1 COUNT templates |
| GET /dashboard/group-analytics (no groups) | **2** | 1 auth user, 1 SELECT groups → empty → return early |
| GET /dashboard/group-analytics (with groups) | **4** | 1 auth user, 1 SELECT groups, 1 SELECT all group reminders, 1 SELECT group_members JOIN contacts |

---

### Celery Background Jobs (no HTTP — internal)

| Task | DB Hits per Run | Breakdown |
|---|---|---|
| `recover_missed_reminders` — nothing stuck, nothing missed | **2** | 1 SELECT stuck (0 results), 1 SELECT missed (0 results) |
| `recover_missed_reminders` — N missed reminders, none stuck | **3** | 1 SELECT stuck, 1 SELECT missed (N results), 1 UPDATE all N→'processing' (batch commit) |
| `recover_missed_reminders` — N missed + M stuck | **4–5** | 1 SELECT stuck, 1 UPDATE stuck+retry commit, 1 SELECT missed, 1 UPDATE missed commit |
| `trigger_call` per reminder (Twilio success) | **2** | 1 UPDATE atomic claim, 1 UPDATE→'calling' commit |
| `trigger_call` per reminder (Twilio API exception) | **2** | 1 UPDATE atomic claim, 1 UPDATE via `_handle_system_failure` commit |
| `_startup_recovery` on app start | **1–2** | 1 SELECT past-due pending, 1 bulk re-enqueue (no DB write — just `delay()`) |

> **Celery beat fires every 10 minutes (recovery-only).** With no Redis crashes = **2 DB hits/10min ≈ 12/hour**.
> Normal operation = **0 beat-triggered DB hits** — ETA tasks fire directly from Redis, no DB scan needed.

---

### Summary: Total DB Hits Per User Action (end-to-end including all layers)

| User Action | Total DB Hits |
|---|---|
| Sign up | 3 |
| Log in | 1 |
| Open dashboard (load reminders) | 2 |
| Create reminder (audio upload) | 2 |
| Create reminder (from template) | 3 |
| Edit reminder | 3 |
| Delete reminder | 3 |
| Submit feedback | 3 |
| Export to .ics | 2 |
| View analytics page | 3 + 4 = **7** (two separate API calls) |
| Create contact | 3 |
| Update contact (phone changed) | 4 |
| Add contact to group | 6 |
| Create group reminder for N members | 3 + N (audio) |
| Twilio call answered → recurrence | 2 |
| Twilio user failure (no-answer/busy) → retry scheduled | 2 |
| Twilio user failure → final attempt → SMS fallback | 2 |
| Twilio system failure (failed/canceled) → system retry | 2 |
| Twilio system failure → retries exhausted → SMS fallback | 3 |
| Celery beat recovery (idle, every 10min) | 2 |
| Celery beat recovery (N missed reminders) | 3 + (1 per trigger_call) |

---

### Key Observations

1. **`get_current_user` is the silent +1** on every authenticated endpoint. It queries the `users` table on every single API call. If you add caching here (e.g. store user in Redis keyed by JWT), you eliminate one DB hit per request.

2. **`GET /groups` uses eager loading** — `_load_groups()` fetches all groups with their members and contacts in a single query via eager loading. No N+1 regardless of how many groups or members.

3. **`GET /dashboard/analytics` is the most efficient** — it pulls all reminder data in 1 SELECT and computes all stats (success rate, retries, trends, distribution) in Python memory. Only 3 total hits regardless of how many reminders.

4. **`POST /groups/{id}/remind`** uses eager loading when fetching the group — all member contacts are loaded in the initial query, so no per-member lazy load queries.

5. **Celery beat is now minimal load** — runs every 10 minutes as a safety net only. Normal operation = 0 beat-triggered DB hits. The beat only matters after a Redis crash, which is rare. Old polling approach = 2 hits/60s = 120/hour always. New approach = 2 hits/10min = 12/hour and only if the safety net is actually needed.

6. **All write paths are single-commit** — `_schedule_next_occurrence` and `_schedule_retry` both use `db.flush()` (to get the new row ID) then return the new reminder to the caller, which commits once and then calls `enqueue_reminder_eta()`. This means recurrence and retry scheduling add 0 extra DB round-trips.

---

## 12. Data Flow Diagrams

### Reminder Lifecycle State Machine
```
     POST /reminders
          │
          ▼
      [pending] ◄──────────────────────────────────────────────────┐
          │                                                         │
          │ enqueue_reminder_eta()                                  │
          │ (ETA task pushed into Redis at creation)               │
          ▼                                                         │
   [Redis ETA task]                                                 │
          │ fires at exact scheduled_time                           │
          ▼                                                         │
   trigger_call()                                                   │
   atomic claim → [processing]                                      │
          │                                                         │
          ├─ stale ETA? → back to [pending] ──────────────────────►─┘
          │                                                         │
          ├─ Twilio API FAILS ──► _handle_system_failure()          │
          │                            │                            │
          │                    system_retry_count ≤ 2?             │
          │                         │         │                     │
          │                        YES        NO                    │
          │                         │         │                     │
          │                    [pending]  [failed_system]           │
          │                    +backoff   +SMS fallback             │
          │                    (30s/60s)  +next recurrence          │
          │                         │                               │
          │                         └────────────────────────────►─┘
          │
          ▼
      [calling] ── Twilio dials user
          │
          │ POST /voice/status/{id}
          │
          ├─ CallStatus='completed'
          │       │
          │   [answered]
          │       │
          │  if recurrence:
          │  _schedule_next_occurrence()
          │  + enqueue_reminder_eta()  ──────────────────────────►─┐
          │                                                         │
          ├─ CallStatus='no-answer' or 'busy'  (USER FAILURE)      │
          │       │                                                 │
          │   [no-answer / busy]                                    │
          │       │                                                 │
          │  retries remain?                                        │
          │     │         │                                         │
          │    YES        NO                                        │
          │     │         │                                         │
          │  _schedule_   SMS fallback                              │
          │  retry()      + next recurrence ──────────────────────►─┤
          │  + enqueue_   (if recurring)                            │
          │  eta() ──────────────────────────────────────────────►─┘
          │
          └─ CallStatus='failed' or 'canceled'  (SYSTEM FAILURE)
                  │
          _handle_system_failure()
                  │
          system_retry_count ≤ 2?
               │         │
              YES         NO
               │          │
          [pending]  [failed_system]
          +backoff   +SMS fallback
          (30s/60s)  +next recurrence
               │
          re-enqueued ─────────────────────────────────────────►─┘
                                              (loops back to pending)


Safety nets running in parallel:
  ┌─────────────────────────────────────────────────────────────┐
  │  Celery Beat (every 10min) — recover_missed_reminders()     │
  │  • Stuck: status IN ('calling','processing') > 10min old   │
  │    → _handle_system_failure() per stuck reminder            │
  │  • Missed: status='pending' past scheduled_time-30s grace  │
  │    → batch mark 'processing' → trigger_call.delay()        │
  │                                                             │
  │  Startup scan — _startup_recovery() on app start           │
  │  • Finds pending past-due reminders (last 10min window)    │
  │    → trigger_call.delay() immediately                       │
  └─────────────────────────────────────────────────────────────┘
```

### Audio File Lifecycle
```
User uploads/records → UUID filename generated → Saved to backend/uploads/
    │
    ▼
Stored in reminder.audio_filename (e.g. "a1b2c3d4.wav")
    │
    ├─→ Served at: GET /audio/a1b2c3d4.wav
    │   (FastAPI static mount)
    │
    ├─→ Twilio fetches: https://PUBLIC_BASE_URL/audio/a1b2c3d4.wav
    │   (in TwiML <Play> tag)
    │
    └─→ Deleted when: reminder deleted OR audio replaced in edit
```

### JWT Authentication Flow
```
Login:
  POST /auth/login → JWT created → returned in body + HttpOnly cookie

Subsequent requests:
  Option A: Authorization: Bearer <token> header
  Option B: Cookie: access_token=<token> (automatic via withCredentials)

FastAPI get_current_user():
  Tries header first, then falls back to cookie
  Decodes JWT, fetches user from DB

Logout:
  POST /auth/logout → cookie cleared
```
