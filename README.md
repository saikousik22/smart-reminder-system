# 🔔 Smart Reminder System

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009485?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-61DAFB?style=flat-square&logo=react)](https://react.dev/)
[![Python](https://img.shields.io/badge/Python-3.8%2B-3776AB?style=flat-square&logo=python)](https://www.python.org/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind%20CSS-3-38B2AC?style=flat-square&logo=tailwindcss)](https://tailwindcss.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Latest-316192?style=flat-square&logo=postgresql)](https://www.postgresql.org/)
[![Twilio](https://img.shields.io/badge/Twilio-Voice%20API-F22F46?style=flat-square&logo=twilio)](https://www.twilio.com/)

> **A full-stack application that lets users create reminders with custom voice messages. At the scheduled time, the system automatically calls the user and plays their recorded voice message via Twilio.**

---

## ✨ Key Features

| Feature | Description |
|---------|-------------|
| 🎤 **Voice Recording** | Record reminders directly from your browser microphone |
| 📤 **Audio Upload** | Upload existing `.mp3` or `.wav` files as reminders |
| 🗓️ **Smart Scheduling** | Set reminders for any date and time in the future |
| 📞 **Automated Calls** | Twilio automatically calls you and plays your message at the scheduled time |
| 👥 **Contact Management** | Save and organize phone numbers for quick access |
| 👨‍👩‍👧 **Contact Groups** | Organize contacts into groups for better management |
| 📊 **Analytics Dashboard** | Track reminder statistics and call history |
| 🔐 **Secure Authentication** | JWT-based auth with password hashing (bcrypt) |
| 🗣️ **Multi-Language Support** | Translate reminders using Google Translate |
| 📱 **Responsive Design** | Works seamlessly on desktop, tablet, and mobile devices |

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      React Frontend (Vite)                      │
│  Login → Dashboard → Create Reminder → Analytics → Contacts     │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTP / Axios (JSON + FormData)
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                     FastAPI Backend (Python)                    │
│  /auth  /reminders  /voice  /contacts  /groups  /dashboard      │
│                      Static: /audio                             │
└────┬────────────────────────┬──────────────────────────────────-┘
     │ SQLAlchemy ORM          │ Celery Tasks (Beat Scheduler)
     ▼                         ▼
┌──────────────┐       ┌──────────────────────────────────────────┐
│ PostgreSQL   │       │  Redis (Message Broker)                  │
│  Database    │       │  Celery Worker + Beat Scheduler          │
└──────────────┘       └──────────────────────┬───────────────────┘
                                              │
                                              ▼
                                     ┌────────────────────┐
                                     │   Twilio API       │
                                     │ Voice Calls + SMS  │
                                     └────────────────────┘
```

---

## 🛠️ Tech Stack

### Frontend
- **React 18** — Modern UI framework
- **Vite** — Lightning-fast build tool with HMR
- **Tailwind CSS 3** — Utility-first styling
- **Axios** — HTTP client for API calls
- **FullCalendar** — Calendar view for reminders
- **Recharts** — Analytics charts

### Backend
- **FastAPI 0.115** — High-performance async REST API
- **SQLAlchemy 2.0** — ORM for database operations
- **Pydantic** — Data validation
- **Alembic** — Database migrations
- **JWT (python-jose)** — Stateless authentication
- **bcrypt** — Secure password hashing

### Infrastructure
- **PostgreSQL** — Relational database (SQLite for development)
- **Redis** — Message broker for Celery
- **Celery** — Distributed task queue with Beat scheduler
- **Twilio** — Voice API for automated calls
- **Docker & Docker Compose** — Containerization
- **Azure** — Cloud deployment platform

---

## 📦 Project Structure

```
smart-reminder-system/
├── README.md                          # This file
├── PROJECT_PLAN.md                    # Architecture & planning
├── CODEBASE_COMPLETE_FLOW.md          # Detailed flow documentation
├── RUN.md                             # Local development setup
├── AZURE_DEPLOYMENT.md                # Production deployment guide
├── docker-compose.yml                 # Local Docker setup
│
├── backend/
│   ├── requirements.txt               # Python dependencies
│   ├── .env.example                   # Environment template
│   ├── Dockerfile                     # Docker image for backend
│   ├── entrypoint.sh                  # Container startup script
│   ├── uploads/                       # Audio files storage
│   ├── alembic/                       # Database migrations
│   │   ├── env.py
│   │   └── versions/                  # Migration files
│   └── app/
│       ├── main.py                    # FastAPI app entry point
│       ├── config.py                  # Configuration & settings
│       ├── database.py                # SQLAlchemy setup
│       ├── models.py                  # ORM models
│       ├── schemas.py                 # Pydantic schemas
│       ├── auth.py                    # JWT & password utilities
│       ├── celery_app.py              # Celery configuration
│       ├── tasks.py                   # Background tasks
│       ├── scheduler.py               # Scheduling utilities
│       ├── twilio_service.py          # Twilio API wrapper
│       ├── rate_limit.py              # Rate limiting
│       ├── routers/                   # API endpoints
│       │   ├── auth_router.py         # /auth endpoints
│       │   ├── reminder_router.py     # /reminders CRUD
│       │   ├── voice_router.py        # /voice webhooks
│       │   ├── contacts_router.py     # /contacts management
│       │   ├── groups_router.py       # /groups management
│       │   ├── template_router.py     # /templates
│       │   ├── dashboard_router.py    # /dashboard analytics
│       │   └── translate_router.py    # /translate
│       └── services/                  # Business logic
│           ├── sms_service.py         # SMS operations
│           ├── blob_storage.py        # Cloud storage
│           └── translate_service.py   # Translation logic
│
└── frontend/
    ├── package.json                   # Node dependencies
    ├── vite.config.js                 # Vite configuration
    ├── tailwind.config.cjs            # Tailwind setup
    ├── nginx.conf                     # Nginx configuration
    ├── Dockerfile                     # Frontend image
    ├── index.html                     # Entry HTML
    └── src/
        ├── App.jsx                    # Root component
        ├── main.jsx                   # Entry point
        ├── index.css                  # Global styles
        ├── api/                       # API utilities
        │   └── axios.js               # Axios config
        ├── context/                   # React context
        │   └── AuthContext.jsx        # Auth state management
        ├── components/                # Reusable components
        │   ├── Navbar.jsx
        │   ├── ProtectedRoute.jsx
        │   ├── ReminderCard.jsx
        │   ├── AudioRecorder.jsx
        │   ├── AudioUploader.jsx
        │   └── CalendarView.jsx
        └── pages/                     # Page components
            ├── Login.jsx
            ├── Signup.jsx
            ├── Dashboard.jsx
            ├── DashboardAnalytics.jsx
            ├── CreateReminder.jsx
            ├── Contacts.jsx
            ├── Groups.jsx
```

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.8+**
- **Node.js 16+**
- **Docker & Docker Compose** (optional, for containerized setup)
- **ngrok** (for local Twilio webhook testing)
- **FFmpeg** (for audio transcoding)
- **Twilio Account** with a Voice-enabled phone number

### Local Development Setup

#### 1. Clone and Navigate to Project
```bash
git clone <repository-url>
cd smart-reminder-system
```

#### 2. Backend Setup
```bash
cd backend

# Create virtual environment
python -m venv venv
.\venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Create .env file (copy from .env.example)
cp .env.example .env
```

#### 3. Configure Environment Variables
Create `.env` in the `backend/` directory:
```env
# Security
SECRET_KEY=your-random-secret-key-here

# Twilio Configuration
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=your-token
TWILIO_PHONE_NUMBER=+1234567890

# Public URL (from ngrok)
PUBLIC_BASE_URL=https://your-ngrok-url.ngrok-free.app

# Database (optional for local SQLite)
DATABASE_URL=sqlite:///./reminder.db

# Redis (if using Celery)
REDIS_URL=redis://localhost:6379/0
```

#### 4. Start Backend
```bash
uvicorn app.main:app --reload
```
Backend runs at `http://localhost:8000`

#### 5. Setup ngrok (for Twilio Webhooks)
```bash
ngrok http 8000
```
Copy the forwarding URL and update `PUBLIC_BASE_URL` in `.env`

#### 6. Frontend Setup
In a new terminal:
```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```
Frontend runs at `http://localhost:5173`

#### 7. Using the Application
1. **Sign up** with an account
2. **Create a reminder**:
   - Enter title and description
   - Select phone number (must start with `+` and country code)
   - Pick a future date and time
   - Record audio or upload a file
3. **Sit back** — system will call you at the scheduled time!

> **⚠️ Twilio Trial Note:** Trial accounts can only call verified phone numbers. Verify your number in the Twilio console first.

---

## 🐳 Docker Setup

Run the entire stack with Docker Compose:

```bash
docker-compose up -d
```

This starts:
- **Backend** (FastAPI) on `http://localhost:8000`
- **Frontend** (React) on `http://localhost:3000`
- **PostgreSQL** database
- **Redis** cache
- **Celery Worker** for background tasks

View logs:
```bash
docker-compose logs -f
```

Stop services:
```bash
docker-compose down
```

---

## 📚 API Endpoints

### Authentication
- `POST /auth/signup` — Register new user
- `POST /auth/login` — Login and receive JWT token

### Reminders
- `GET /reminders` — List all user reminders
- `POST /reminders` — Create a new reminder
- `GET /reminders/{id}` — Get reminder details
- `PUT /reminders/{id}` — Update reminder
- `DELETE /reminders/{id}` — Delete reminder

### Contacts
- `GET /contacts` — List all contacts
- `POST /contacts` — Add a contact
- `PUT /contacts/{id}` — Update contact
- `DELETE /contacts/{id}` — Delete contact

### Groups
- `GET /groups` — List contact groups
- `POST /groups` — Create a group
- `PUT /groups/{id}` — Update group
- `DELETE /groups/{id}` — Delete group

### Voice & Webhooks
- `GET /voice/{reminder_id}` — Twilio voice webhook (TwiML)
- `POST /voice/status/{reminder_id}` — Call status callback

### Dashboard
- `GET /dashboard/stats` — Get analytics and statistics
- `GET /dashboard/recent` — Get recent reminders

### Translations
- `POST /translate` — Translate reminder text

See [CODEBASE_COMPLETE_FLOW.md](CODEBASE_COMPLETE_FLOW.md) for detailed endpoint documentation.

---

## 🔄 How It Works

### User Creates Reminder
```
1. User records/uploads audio → Frontend stores in browser
2. Frontend sends to /reminders → Backend validates and saves
3. Audio stored in backend/uploads/ or Azure Blob Storage
4. Reminder scheduled in database
```

### Scheduled Time Arrives
```
1. Celery Beat checks every minute for due reminders
2. Due reminder found → Celery task triggered
3. Task calls Twilio API with reminder details
4. Twilio makes outbound call to phone number
```

### User Receives Call
```
1. User picks up phone
2. Twilio connects to backend /voice/{reminder_id}
3. Backend returns TwiML with audio URL
4. Twilio plays audio file to user
5. Call ends, status callback sent to backend
```

---

## 🔧 Environment Variables Reference

| Variable | Description | Example |
|----------|-------------|---------|
| `SECRET_KEY` | JWT signing secret | `your-secret-key` |
| `TWILIO_ACCOUNT_SID` | Twilio account identifier | `AC...` |
| `TWILIO_AUTH_TOKEN` | Twilio authentication token | `token...` |
| `TWILIO_PHONE_NUMBER` | Your Twilio phone number | `+1234567890` |
| `PUBLIC_BASE_URL` | Public URL for webhooks | `https://xyz.ngrok-free.app` |
| `DATABASE_URL` | Database connection string | `postgresql://...` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379/0` |
| `ALLOWED_ORIGINS` | CORS allowed domains | `http://localhost:5173` |

See `.env.example` for a complete template.

---

## 📊 Database Schema

The system uses 6 core tables:

1. **users** — User accounts and authentication
2. **reminders** — Reminder records with scheduling info
3. **contacts** — Saved phone numbers
4. **contact_groups** — Contact organization
5. **reminder_templates** — Reusable reminder templates
6. **call_logs** — Call history and status tracking

See [PROJECT_PLAN.md](PROJECT_PLAN.md) for detailed schema documentation.

---

## ☁️ Production Deployment

### Azure Deployment
The system is designed for Azure deployment including:
- **Azure Static Web Apps** — Frontend hosting
- **Azure App Service** — FastAPI backend
- **Azure Database for PostgreSQL** — Production database
- **Azure Cache for Redis** — Message broker
- **Azure Storage Blobs** — Audio file storage
- **Azure App Service** — Celery worker

Follow the [AZURE_DEPLOYMENT.md](AZURE_DEPLOYMENT.md) guide for step-by-step deployment instructions.

### Cost Estimate
- Frontend (Static Web App): ~$0-12/month
- Backend App Service: ~$15-30/month
- PostgreSQL Flexible: ~$15-40/month
- Redis Cache: ~$15-30/month
- Blob Storage: ~$0.50-5/month
- **Total**: ~$60-120/month (varies by usage)

---

## 🧪 Testing

### Manual Testing Checklist
- [ ] User signup and login workflow
- [ ] Record audio message
- [ ] Upload audio file
- [ ] Create and schedule reminder
- [ ] Receive automated call at scheduled time
- [ ] Manage contacts and groups
- [ ] View analytics dashboard
- [ ] Test with different time zones
- [ ] Verify responsive design on mobile

### API Testing
Use Postman, curl, or the included API documentation to test endpoints:
```bash
# Example: Login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password"}'
```

---

## 🐛 Troubleshooting

### Issue: "FFmpeg not found"
**Solution:** Install FFmpeg on your system
- Windows: `choco install ffmpeg`
- Mac: `brew install ffmpeg`
- Linux: `sudo apt-get install ffmpeg`

### Issue: Twilio calls not being made
**Solution:**
1. Verify `PUBLIC_BASE_URL` is set correctly (ngrok forwarding URL)
2. Check Twilio webhook URL in Twilio console
3. Verify phone number is verified in Twilio trial account
4. Check Celery worker is running: `celery -A app.celery_app worker`

### Issue: Audio upload fails
**Solution:**
1. Check file size (max 25MB)
2. Verify ffmpeg is installed
3. Check backend logs for encoding errors

### Issue: Database connection error
**Solution:**
1. Verify DATABASE_URL in .env
2. Ensure PostgreSQL is running
3. Run migrations: `alembic upgrade head`

---

## 📖 Documentation

- [PROJECT_PLAN.md](PROJECT_PLAN.md) — Complete architecture and design
- [CODEBASE_COMPLETE_FLOW.md](CODEBASE_COMPLETE_FLOW.md) — Detailed code flow and endpoints
- [RUN.md](RUN.md) — Local development setup
- [AZURE_DEPLOYMENT.md](AZURE_DEPLOYMENT.md) — Production deployment
- [BUG_REPORT.md](BUG_REPORT.md) — Known issues and bug tracking

---

## 🤝 Contributing

We welcome contributions! Here's how to get started:

1. **Fork the repository**
2. **Create a feature branch** (`git checkout -b feature/amazing-feature`)
3. **Commit your changes** (`git commit -m 'Add amazing feature'`)
4. **Push to the branch** (`git push origin feature/amazing-feature`)
5. **Open a Pull Request**

### Code Guidelines
- Follow PEP 8 for Python code
- Use meaningful commit messages
- Add tests for new features
- Update documentation as needed
- Test locally before submitting PR

---

## 📝 License

This project is licensed under the MIT License — see the LICENSE file for details.

---

## 🎯 Roadmap

Planned features for future releases:

- [ ] SMS reminders in addition to voice calls
- [ ] Recurring reminders (daily, weekly, monthly)
- [ ] Reminder snooze functionality
- [ ] Advanced analytics and insights
- [ ] Mobile app (iOS/Android)
- [ ] WhatsApp integration
- [ ] Email notifications
- [ ] Machine learning for optimal reminder times
- [ ] Voice command support

---

## 💬 Support & Questions

- **Documentation**: See the docs folder for detailed guides
- **Issues**: Report bugs on GitHub Issues
- **Discussions**: Join our community discussions
- **Email**: Contact the development team

---

## 🙏 Acknowledgments

- **Twilio** for the Voice API
- **FastAPI** for the amazing framework
- **React** community for tools and libraries
- All contributors and users

---

<div align="center">

**Made with ❤️ by the Smart Reminder System Team**

⭐ If you find this project useful, please consider giving it a star!

</div>
