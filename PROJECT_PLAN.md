# 🔔 Smart Reminder System — Project Plan & Architecture

> **A full-stack application that lets users create reminders with custom voice messages. At the scheduled time, the system automatically calls the user and plays their recorded voice message via Twilio.**

---

## 📋 Table of Contents

1. [Project Overview](#1-project-overview)
2. [Tech Stack](#2-tech-stack)
3. [Directory Structure](#3-directory-structure)
4. [Database Schema](#4-database-schema)
5. [Authentication Flow](#5-authentication-flow)
6. [REST API Design](#6-rest-api-design)
7. [Audio Handling](#7-audio-handling)
8. [Twilio Voice Integration](#8-twilio-voice-integration)
9. [Background Scheduler](#9-background-scheduler)
10. [Frontend Pages & Components](#10-frontend-pages--components)
11. [Environment Variables](#11-environment-variables)
12. [Deployment & Public Access](#12-deployment--public-access)
13. [Known Limitations & Future Enhancements](#13-known-limitations--future-enhancements)

---

## 1. Project Overview

### Core Workflow

```
User records/uploads audio → Sets phone + date/time → Saves reminder
                                    ↓
            APScheduler checks every 60 seconds
                                    ↓
              Time matches? → Twilio makes voice call
                                    ↓
              Twilio hits /voice webhook → Returns TwiML with audio URL
                                    ↓
              User receives call and hears their recorded message
```

### Key Features

| Feature                  | Description                                              |
| ------------------------ | -------------------------------------------------------- |
| User Authentication      | JWT-based signup/login                                   |
| Voice Recording          | Record via browser microphone (MediaRecorder API)        |
| Audio Upload             | Upload .mp3 / .wav files                                 |
| Reminder Scheduling      | Pick date and time, attach audio, set phone number       |
| Automated Calls          | Twilio Voice API triggers call at scheduled time         |
| Reminder Management      | View, edit, delete reminders with status tracking        |
| Background Scheduling    | APScheduler polls every minute for due reminders         |

---

## 2. Tech Stack

| Layer          | Technology           | Purpose                                  |
| -------------- | -------------------- | ---------------------------------------- |
| **Frontend**   | React 18 + Vite      | SPA with fast HMR                        |
| **Styling**    | Tailwind CSS v3      | Utility-first responsive styling         |
| **Backend**    | FastAPI (Python)     | Async REST API server                    |
| **Database**   | SQLite + SQLAlchemy  | Lightweight relational storage           |
| **Auth**       | JWT (python-jose)    | Stateless token-based authentication     |
| **Scheduler**  | APScheduler          | Background job for checking due reminders|
| **Calls**      | Twilio Voice API     | Automated outbound phone calls           |
| **Tunneling**  | ngrok                | Expose local server for Twilio webhooks  |

---

## 3. Directory Structure

```
smart-reminder-system/
├── PROJECT_PLAN.md
│
├── backend/
│   ├── main.py                  # FastAPI app entry point + scheduler startup
│   ├── config.py                # Environment variables & settings
│   ├── database.py              # SQLAlchemy engine, session, Base
│   ├── models.py                # SQLAlchemy ORM models (User, Reminder)
│   ├── schemas.py               # Pydantic request/response schemas
│   ├── auth.py                  # JWT creation, verification, password hashing
│   ├── requirements.txt         # Python dependencies
│   │
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── users.py             # POST /signup, POST /login
│   │   ├── reminders.py         # CRUD /reminders
│   │   └── voice.py             # GET /voice/{reminder_id} (TwiML webhook)
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── scheduler.py         # APScheduler setup & reminder check logic
│   │   └── twilio_service.py    # Twilio client, make_call()
│   │
│   ├── uploads/                 # Stored audio files (gitignored)
│   │   └── ...
│   │
│   └── reminder.db              # SQLite database file (gitignored)
│
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   │
│   ├── public/
│   │   └── favicon.ico
│   │
│   └── src/
│       ├── main.jsx             # React entry point
│       ├── App.jsx              # Router + layout
│       ├── index.css            # Tailwind directives + custom styles
│       │
│       ├── api/
│       │   └── axios.js         # Axios instance with JWT interceptor
│       │
│       ├── context/
│       │   └── AuthContext.jsx  # Auth state provider
│       │
│       ├── pages/
│       │   ├── Login.jsx        # Login page
│       │   ├── Signup.jsx       # Signup page
│       │   ├── Dashboard.jsx    # Reminder list + status
│       │   └── CreateReminder.jsx  # Form: phone, datetime, audio
│       │
│       └── components/
│           ├── Navbar.jsx       # Top navigation bar
│           ├── ReminderCard.jsx # Single reminder display card
│           ├── AudioRecorder.jsx# Mic recording component
│           ├── AudioUploader.jsx# File upload component
│           └── ProtectedRoute.jsx # Auth route guard
│
└── .gitignore
```

---

## 4. Database Schema

### Users Table

| Column             | Type         | Constraints                     |
| ------------------ | ------------ | ------------------------------- |
| `id`               | INTEGER      | PRIMARY KEY, AUTOINCREMENT      |
| `username`         | VARCHAR(100) | UNIQUE, NOT NULL                |
| `email`            | VARCHAR(255) | UNIQUE, NOT NULL                |
| `hashed_password`  | TEXT         | NOT NULL                        |
| `created_at`       | DATETIME     | DEFAULT CURRENT_TIMESTAMP       |

### Reminders Table

| Column             | Type         | Constraints                     |
| ------------------ | ------------ | ------------------------------- |
| `id`               | INTEGER      | PRIMARY KEY, AUTOINCREMENT      |
| `user_id`          | INTEGER      | FOREIGN KEY → users.id, NOT NULL|
| `phone_number`     | VARCHAR(15)  | NOT NULL                        |
| `scheduled_time`   | DATETIME     | NOT NULL                        |
| `audio_filename`   | TEXT         | NOT NULL (stored filename)      |
| `audio_url`        | TEXT         | NOT NULL (public playback URL)  |
| `status`           | VARCHAR(20)  | DEFAULT 'pending'               |
| `created_at`       | DATETIME     | DEFAULT CURRENT_TIMESTAMP       |
| `updated_at`       | DATETIME     | ON UPDATE CURRENT_TIMESTAMP     |

**Status Values:** `pending` → `calling` → `sent` / `failed`

### SQLAlchemy Models

```python
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    hashed_password = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    reminders = relationship("Reminder", back_populates="owner")

class Reminder(Base):
    __tablename__ = "reminders"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    phone_number = Column(String(15), nullable=False)
    scheduled_time = Column(DateTime, nullable=False)
    audio_filename = Column(Text, nullable=False)
    audio_url = Column(Text, nullable=False)
    status = Column(String(20), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    owner = relationship("User", back_populates="reminders")
```

---

## 5. Authentication Flow

```
┌──────────┐     POST /signup      ┌──────────┐
│  Client   │ ──────────────────── │  Server   │
│ (React)   │     { username,      │ (FastAPI) │
│           │       email,         │           │
│           │       password }     │           │
└──────────┘                      └──────────┘
      │                                 │
      │     POST /login                 │
      │ ──────────────────────────────► │
      │     { email, password }         │
      │                                 │
      │     ◄────────────────────────── │
      │     { access_token, token_type }│
      │                                 │
      │     GET /reminders              │
      │     Authorization: Bearer jwt   │
      │ ──────────────────────────────► │
```

### JWT Details

- **Algorithm:** HS256
- **Expiration:** 24 hours
- **Payload:** `{ sub: user_id, exp: expiry_timestamp }`
- **Storage (client):** localStorage
- **Library:** python-jose[cryptography]
- **Password Hashing:** passlib[bcrypt]

---

## 6. REST API Design

### Auth Endpoints

| Method | Endpoint        | Body                                 | Response                        | Auth |
| ------ | --------------- | ------------------------------------ | ------------------------------- | ---- |
| POST   | `/api/signup`   | `{ username, email, password }`      | `{ id, username, email }`       | No   |
| POST   | `/api/login`    | `{ email, password }`                | `{ access_token, token_type }`  | No   |
| GET    | `/api/me`       | —                                    | `{ id, username, email }`       | Yes  |

### Reminder Endpoints

| Method | Endpoint               | Body / Params                                    | Response                    | Auth |
| ------ | ---------------------- | ------------------------------------------------ | --------------------------- | ---- |
| GET    | `/api/reminders`       | —                                                | `[ { reminder }, ... ]`     | Yes  |
| POST   | `/api/reminders`       | FormData: phone, scheduled_time, audio_file      | `{ reminder }`              | Yes  |
| GET    | `/api/reminders/{id}`  | —                                                | `{ reminder }`              | Yes  |
| PUT    | `/api/reminders/{id}`  | FormData: phone?, scheduled_time?, audio_file?   | `{ reminder }`              | Yes  |
| DELETE | `/api/reminders/{id}`  | —                                                | `{ message: "deleted" }`    | Yes  |

### Twilio Webhook

| Method | Endpoint                 | Purpose                                    | Auth |
| ------ | -----------------------  | ------------------------------------------ | ---- |
| GET    | `/voice/{reminder_id}`   | Returns TwiML XML with Play tag            | No   |

### Audio Serving

| Method | Endpoint                      | Purpose                           | Auth |
| ------ | ----------------------------- | --------------------------------- | ---- |
| GET    | `/uploads/{filename}`         | Serve stored audio files          | No   |

---

## 7. Audio Handling

### Recording (Browser)

```
Browser Microphone → MediaRecorder API → Blob (audio/webm)
                                            ↓
                              Convert to File → POST /api/reminders (FormData)
                                            ↓
                              Server saves to /uploads/ directory
                                            ↓
                              audio_url = https://ngrok-url/uploads/filename
```

### Upload (File)

```
User selects .mp3/.wav → Attach to FormData → POST /api/reminders
                                            ↓
                              Server saves to /uploads/ directory
                                            ↓
                              audio_url = https://ngrok-url/uploads/filename
```

### File Storage Rules

- **Location:** backend/uploads/
- **Naming:** {user_id}_{uuid}_{original_name}
- **Accepted Formats:** .mp3, .wav, .ogg, .webm
- **Max Size:** 10 MB
- **Public Access:** Served via FastAPI StaticFiles mount at /uploads

**IMPORTANT:** Audio files must be publicly accessible via a URL that Twilio can reach. When running locally, ngrok provides this public URL.

---

## 8. Twilio Voice Integration

### How It Works

1. Scheduler detects a due reminder → Calls twilio_service.make_call()
2. Twilio API receives request → Initiates outbound call to user's phone
3. When user picks up → Twilio hits the webhook URL /voice/{reminder_id}
4. Webhook returns TwiML XML:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say>You have a reminder. Please listen carefully.</Say>
    <Play>https://ngrok-url/uploads/audio_file.mp3</Play>
    <Say>This was your scheduled reminder. Goodbye!</Say>
</Response>
```

5. Twilio plays the audio to the user over the phone call

### Twilio Service Code (Pseudo)

```python
from twilio.rest import Client

def make_call(reminder):
    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    
    call = client.calls.create(
        to=reminder.phone_number,
        from_=TWILIO_PHONE_NUMBER,
        url=f"{PUBLIC_BASE_URL}/voice/{reminder.id}",
        method="GET"
    )
    
    return call.sid
```

### Webhook Endpoint (Pseudo)

```python
from fastapi import APIRouter
from twilio.twiml.voice_response import VoiceResponse

@router.get("/voice/{reminder_id}")
def voice_webhook(reminder_id: int):
    reminder = get_reminder(reminder_id)
    
    response = VoiceResponse()
    response.say("You have a reminder. Please listen carefully.")
    response.play(reminder.audio_url)
    response.say("This was your scheduled reminder. Goodbye!")
    
    return Response(content=str(response), media_type="application/xml")
```

### Twilio Setup Checklist

- [ ] Create Twilio account at twilio.com
- [ ] Get Account SID and Auth Token from console
- [ ] Purchase or use trial phone number
- [ ] Verify your personal phone number (required for trial accounts)
- [ ] Set environment variables (see Section 11)
- [ ] If using trial: only verified numbers can receive calls

**WARNING: Twilio Trial Limitations:**
- Can only call verified phone numbers
- Calls are prefixed with a trial message
- Limited balance (~$15.50 free credit)
- Must upgrade for production use

---

## 9. Background Scheduler

### APScheduler Configuration

```python
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta

scheduler = BackgroundScheduler()

def check_due_reminders():
    """Runs every 60 seconds to find and trigger due reminders."""
    now = datetime.utcnow()
    window = now + timedelta(seconds=60)
    
    # Find reminders where scheduled_time is between now and now+60s
    due_reminders = db.query(Reminder).filter(
        Reminder.status == "pending",
        Reminder.scheduled_time <= window,
        Reminder.scheduled_time >= now - timedelta(seconds=60)
    ).all()
    
    for reminder in due_reminders:
        try:
            reminder.status = "calling"
            db.commit()
            
            call_sid = make_call(reminder)
            
            reminder.status = "sent"
            db.commit()
        except Exception as e:
            reminder.status = "failed"
            db.commit()
            logger.error(f"Failed to call for reminder {reminder.id}: {e}")

# Register job
scheduler.add_job(check_due_reminders, "interval", seconds=60)
scheduler.start()
```

### Lifecycle

```
FastAPI startup event → scheduler.start()
FastAPI shutdown event → scheduler.shutdown()
```

---

## 10. Frontend Pages & Components

### Page: Login (/login)

- Email + password input fields
- "Login" button → POST /api/login
- Link to signup page
- Store JWT in localStorage on success
- Redirect to Dashboard

### Page: Signup (/signup)

- Username + email + password fields
- "Create Account" button → POST /api/signup
- Auto-login after successful signup
- Link to login page

### Page: Dashboard (/dashboard)

- List of all user's reminders as cards
- Each card shows:
  - Phone number
  - Scheduled date/time
  - Audio playback button
  - Status badge (pending=yellow, sent=green, failed=red)
  - Edit button → navigate to edit form
  - Delete button → confirm and delete
- "Create New Reminder" floating action button
- Empty state illustration when no reminders

### Page: Create Reminder (/create)

- Phone number input (with country code selector)
- Date and Time picker
- Audio section:
  - **Tab 1:** Record with microphone (start/stop/preview)
  - **Tab 2:** Upload audio file (drag and drop or file picker)
- Preview recorded/uploaded audio
- "Save Reminder" button → POST /api/reminders
- Loading state during upload

### Shared Components

| Component          | Purpose                                    |
| ------------------ | ------------------------------------------ |
| Navbar             | App title, user info, logout button        |
| ReminderCard       | Displays single reminder with actions      |
| AudioRecorder      | Mic recording with waveform visualization  |
| AudioUploader      | Drag-and-drop file upload                  |
| ProtectedRoute     | Redirects unauthenticated users to login   |

### UI Design Principles

- **Color Scheme:** Dark mode with vibrant accent colors (purple/indigo gradients)
- **Typography:** Inter font from Google Fonts
- **Animations:** Framer Motion for page transitions and micro-interactions
- **Cards:** Glassmorphism effect with backdrop blur
- **Responsive:** Mobile-first, works on all screen sizes

---

## 11. Environment Variables

### Backend (.env)

```env
# Application
SECRET_KEY=your-super-secret-jwt-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Database
DATABASE_URL=sqlite:///./reminder.db

# Twilio
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your-twilio-auth-token
TWILIO_PHONE_NUMBER=+1234567890

# Public URL (ngrok or deployed URL)
PUBLIC_BASE_URL=https://your-ngrok-url.ngrok-free.app

# Audio
UPLOAD_DIR=./uploads
MAX_UPLOAD_SIZE_MB=10
```

### Frontend (.env)

```env
VITE_API_URL=http://localhost:8000/api
```

---

## 12. Deployment & Public Access

### Local Development with ngrok

```bash
# Terminal 1: Start backend
cd backend
uvicorn main:app --reload --port 8000

# Terminal 2: Start frontend
cd frontend
npm run dev

# Terminal 3: Expose backend publicly
ngrok http 8000
```

**NOTE:** Copy the ngrok public URL (e.g., https://abc123.ngrok-free.app) and set it as PUBLIC_BASE_URL in your backend .env file. This URL is needed for Twilio to reach your /voice webhook and /uploads audio files.

### Production Deployment Options

| Component  | Options                                    |
| ---------- | ------------------------------------------ |
| Backend    | Railway, Render, AWS EC2, DigitalOcean     |
| Frontend   | Vercel, Netlify, Cloudflare Pages          |
| Database   | Upgrade to PostgreSQL for production       |
| Audio      | AWS S3, Cloudflare R2 for file storage     |

---

## 13. Known Limitations & Future Enhancements

### Current Limitations

- SQLite is not ideal for concurrent access (fine for dev/demo)
- Audio stored locally (lost on server restart if containerized)
- Twilio trial account restrictions
- No email notifications (call-only)
- No recurring reminders
- No timezone handling (UTC only in v1)

### Future Enhancements

| Enhancement               | Description                                    |
| ------------------------- | ---------------------------------------------- |
| Recurring Reminders       | Daily, weekly, monthly schedules               |
| Timezone Support          | Per-user timezone settings                     |
| Email/SMS Fallback        | Send SMS or email if call fails                |
| Cloud Audio Storage       | AWS S3 or Cloudflare R2 for audio files        |
| Call Analytics             | Track call duration, pickup status            |
| Push Notifications        | Browser push notifications as backup           |
| Text-to-Speech            | Type a message instead of recording audio      |
| Shared Reminders          | Send reminders to other people                 |
| Mobile App                | React Native companion app                     |
| Docker Compose            | One-command deployment setup                   |

---

## Dependencies

### Backend (requirements.txt)

```
fastapi==0.111.0
uvicorn[standard]==0.30.1
sqlalchemy==2.0.31
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.9
python-dotenv==1.0.1
apscheduler==3.10.4
twilio==9.2.3
pydantic==2.8.2
aiofiles==24.1.0
```

### Frontend (package.json key deps)

```json
{
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "^6.24.0",
    "axios": "^1.7.2",
    "framer-motion": "^11.2.12",
    "react-hot-toast": "^2.4.1",
    "lucide-react": "^0.400.0"
  },
  "devDependencies": {
    "tailwindcss": "^3.4.4",
    "autoprefixer": "^10.4.19",
    "postcss": "^8.4.38",
    "@vitejs/plugin-react": "^4.3.1",
    "vite": "^5.3.3"
  }
}
```

---

**Getting Started:** Once this plan is approved, implementation will proceed in this order:
1. Backend setup (database, auth, CRUD APIs)
2. Twilio integration + scheduler
3. Frontend scaffolding with Vite + React + Tailwind
4. Frontend pages (Login, Signup, Dashboard, Create Reminder)
5. Audio recording/upload integration
6. End-to-end testing with ngrok

---

*Last updated: April 17, 2026*
