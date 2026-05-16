# Graph Report - .  (2026-05-10)

## Corpus Check
- 65 files · ~42,207 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 401 nodes · 503 edges · 59 communities (27 shown, 32 thin omitted)
- Extraction: 85% EXTRACTED · 15% INFERRED · 0% AMBIGUOUS · INFERRED: 76 edges (avg confidence: 0.67)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_React UI Components|React UI Components]]
- [[_COMMUNITY_Reminder Routing & Scheduling|Reminder Routing & Scheduling]]
- [[_COMMUNITY_Bug Reports & Audio Pipeline|Bug Reports & Audio Pipeline]]
- [[_COMMUNITY_App Configuration|App Configuration]]
- [[_COMMUNITY_Pydantic Schemas|Pydantic Schemas]]
- [[_COMMUNITY_Recurrence Logic|Recurrence Logic]]
- [[_COMMUNITY_ORM Data Models|ORM Data Models]]
- [[_COMMUNITY_Auth & JWT|Auth & JWT]]
- [[_COMMUNITY_Celery Worker Tasks|Celery Worker Tasks]]
- [[_COMMUNITY_Groups API|Groups API]]
- [[_COMMUNITY_Azure Deployment|Azure Deployment]]
- [[_COMMUNITY_App Middleware & Startup|App Middleware & Startup]]
- [[_COMMUNITY_Reminder Templates|Reminder Templates]]
- [[_COMMUNITY_Translation Service|Translation Service]]
- [[_COMMUNITY_Audio Recording UI|Audio Recording UI]]
- [[_COMMUNITY_Contacts API|Contacts API]]
- [[_COMMUNITY_DB Migration Env|DB Migration Env]]
- [[_COMMUNITY_Database Schema|Database Schema]]
- [[_COMMUNITY_Health Server|Health Server]]
- [[_COMMUNITY_Initial Migration|Initial Migration]]
- [[_COMMUNITY_Soft-Delete Migration|Soft-Delete Migration]]
- [[_COMMUNITY_Email Fallback Migration|Email Fallback Migration]]
- [[_COMMUNITY_DB Session|DB Session]]
- [[_COMMUNITY_Azure App Service Setup|Azure App Service Setup]]
- [[_COMMUNITY_Celery App Config|Celery App Config]]
- [[_COMMUNITY_Auth Bug & Login Flow|Auth Bug & Login Flow]]
- [[_COMMUNITY_Timezone Bug & Create Page|Timezone Bug & Create Page]]
- [[_COMMUNITY_ETA Scheduling Design|ETA Scheduling Design]]
- [[_COMMUNITY_Community 28|Community 28]]
- [[_COMMUNITY_Community 37|Community 37]]
- [[_COMMUNITY_Community 38|Community 38]]
- [[_COMMUNITY_Community 39|Community 39]]
- [[_COMMUNITY_Community 40|Community 40]]
- [[_COMMUNITY_Community 41|Community 41]]
- [[_COMMUNITY_Community 42|Community 42]]
- [[_COMMUNITY_Community 43|Community 43]]
- [[_COMMUNITY_Community 44|Community 44]]
- [[_COMMUNITY_Community 45|Community 45]]
- [[_COMMUNITY_Community 46|Community 46]]
- [[_COMMUNITY_Community 47|Community 47]]
- [[_COMMUNITY_Community 48|Community 48]]
- [[_COMMUNITY_Community 49|Community 49]]
- [[_COMMUNITY_Community 50|Community 50]]
- [[_COMMUNITY_Community 51|Community 51]]
- [[_COMMUNITY_Community 52|Community 52]]
- [[_COMMUNITY_Community 53|Community 53]]
- [[_COMMUNITY_Community 54|Community 54]]
- [[_COMMUNITY_Community 55|Community 55]]
- [[_COMMUNITY_Community 56|Community 56]]
- [[_COMMUNITY_Community 57|Community 57]]
- [[_COMMUNITY_Community 58|Community 58]]

## God Nodes (most connected - your core abstractions)
1. `Smart Reminder System` - 13 edges
2. `Reminder` - 12 edges
3. `ReminderTemplate` - 10 edges
4. `Group` - 9 edges
5. `GroupMember` - 9 edges
6. `Contact` - 9 edges
7. `_active_reminders()` - 9 edges
8. `useAuth()` - 9 edges
9. `save_audio_file()` - 8 edges
10. `voice_status_callback()` - 8 edges

## Surprising Connections (you probably didn't know these)
- `ETA-Based Task Scheduling Redis` --semantically_similar_to--> `APScheduler original plan`  [INFERRED] [semantically similar]
  CODEBASE_COMPLETE_FLOW.md → PROJECT_PLAN.md
- `Azure Deployment Guide` --semantically_similar_to--> `Azure App Services 3-Service Deploy Guide`  [INFERRED] [semantically similar]
  AZURE_DEPLOYMENT.md → AZURE_APP_SERVICES_DEPLOY.md
- `Contact` --calls--> `create_contact()`  [INFERRED]
  backend/app/models.py → backend/app/routers/contacts_router.py
- `Celery Task Queue` --conceptually_related_to--> `celery redis dependency`  [INFERRED]
  README.md → backend/requirements.txt
- `Twilio Voice API` --calls--> `trigger_call Celery Task`  [EXTRACTED]
  README.md → CODEBASE_COMPLETE_FLOW.md

## Hyperedges (group relationships)
- **Celery Beat Recovery Pipeline** — codebase_flow_recover_missed_reminders, readme_celery, readme_redis, codebase_flow_trigger_call, codebase_flow_reminders_table [EXTRACTED 0.95]
- **Azure 3-Service Deployment Architecture** — azure_app_services_api, azure_app_services_worker, azure_app_services_beat, azure_deployment_postgres, azure_deployment_redis [EXTRACTED 1.00]
- **End-to-End Reminder Call Flow** — codebase_flow_enqueue_reminder_eta, codebase_flow_trigger_call, readme_twilio, codebase_flow_twiml_webhook, codebase_flow_sms_fallback [EXTRACTED 0.95]

## Communities (59 total, 32 thin omitted)

### Community 0 - "React UI Components"
Cohesion: 0.05
Nodes (21): api, EventModal(), parseUtcDate(), RECURRENCE_LABELS, STATUS_COLORS, Navbar(), ProtectedRoute(), LANGUAGE_NAMES (+13 more)

### Community 1 - "Reminder Routing & Scheduling"
Cohesion: 0.1
Nodes (31): enqueue_reminder_eta(), Schedule trigger_call at reminder.scheduled_time (or immediately if past)., create_group_reminder(), Create one reminder per group member, all firing at the same time., _active_reminders(), bulk_delete_reminders(), create_reminder(), delete_audio_file() (+23 more)

### Community 2 - "Bug Reports & Audio Pipeline"
Cohesion: 0.1
Nodes (22): Config, get_settings(), Application configuration loaded from environment variables., Settings, _check(), _get_client_ip(), login_rate_limit(), _memory_check() (+14 more)

### Community 3 - "App Configuration"
Cohesion: 0.13
Nodes (25): BulkDeleteRequest, Config, ContactCreate, ContactInGroup, ContactResponse, ContactUpdate, FeedbackSubmit, GroupCreate (+17 more)

### Community 4 - "Pydantic Schemas"
Cohesion: 0.09
Nodes (22): compute_next_time(), Pure DB helper functions shared by tasks.py and voice_router.py.  Both functions, Return the next fire time for a recurring reminder, or None for unknown recurren, Create the next pending occurrence for a recurring reminder.      Returns the ne, Create a retry pending reminder if retries are configured and attempts remain., _schedule_next_occurrence(), _schedule_retry(), Twilio Voice webhook router. Returns TwiML XML that instructs Twilio to play the (+14 more)

### Community 5 - "Recurrence Logic"
Cohesion: 0.1
Nodes (21): create_access_token(), decode_access_token(), get_current_user(), hash_password(), JWT authentication utilities: token creation, verification, and password hashing, Hash a plain-text password using bcrypt., Verify a plain-text password against a bcrypt hash., Create a JWT access token with an expiry. (+13 more)

### Community 6 - "ORM Data Models"
Cohesion: 0.28
Nodes (19): Contact, Group, GroupMember, SQLAlchemy ORM models for Users and Reminders., Reminder, ReminderTemplate, AnalyticsResponse, BatchMember (+11 more)

### Community 7 - "Auth & JWT"
Cohesion: 0.11
Nodes (20): Bug Audio File Not Cleaned on Transcode Error, Audio File Lifecycle, Alembic Migrations, Azure Cloud Platform, Azure Blob Storage Audio, Celery Task Queue, Docker and Docker Compose, FastAPI Backend (+12 more)

### Community 8 - "Celery Worker Tasks"
Cohesion: 0.16
Nodes (12): _handle_system_failure(), Celery tasks.  trigger_call            — worker task; atomically claims and exec, Worker task: initiate the Twilio call for one reminder.      Handles two entry p, Handle an infrastructure failure in trigger_call.      System retries are always, Beat task (every 120s) — safety net only, not the primary scheduler.      1. Stu, recover_missed_reminders(), trigger_call(), get_twilio_client() (+4 more)

### Community 9 - "Groups API"
Cohesion: 0.28
Nodes (11): add_member(), _build_group_response(), create_group(), list_groups(), _load_group(), _load_groups(), Groups router — manage contact groups and create multi-recipient reminders., Fetch a single group with members+contacts eagerly loaded in one query. (+3 more)

### Community 10 - "Azure Deployment"
Cohesion: 0.15
Nodes (13): Container App smart-reminder-api, Container App smart-reminder-beat, Azure App Services 3-Service Deploy Guide, Container App smart-reminder-worker, Azure Container Registry ACR, Azure App Service FastAPI Backend, Azure App Service Celery Worker, Azure Blob Storage Audio Files (+5 more)

### Community 11 - "App Middleware & Startup"
Cohesion: 0.2
Nodes (5): AuditMiddleware, _extract_user_id(), FastAPI application entry point. Configures CORS, audit middleware, and mounts r, Best-effort extraction of user_id from JWT for audit logging., Log every API request with user identity, status code, and latency.

### Community 12 - "Reminder Templates"
Cohesion: 0.22
Nodes (11): Bug Celery Task Enqueue Not Error-Checked, Bug No Idempotency Duplicate Webhook, enqueue_reminder_eta, _handle_system_failure, recover_missed_reminders Beat Task, _schedule_next_occurrence, _schedule_retry, SMS Fallback Mechanism (+3 more)

### Community 13 - "Translation Service"
Cohesion: 0.2
Nodes (9): create_template(), delete_template(), list_templates(), Template CRUD router — save/apply reusable reminder configurations., Delete a template and its audio blob., List all templates for the current user., Create a new template by uploading an audio file alongside reminder settings., Save an existing reminder as a reusable template (copies its audio blob). (+1 more)

### Community 14 - "Audio Recording UI"
Cohesion: 0.2
Nodes (8): list_languages(), Translation preview endpoint. Translates text from English into the selected lan, Return all supported target languages as {code: name} pairs., Translate *text* to *target_lang* and return the preview.      The caller must e, translate_preview(), Google Translate wrapper using deep-translator (free, no API key required). Tran, Translate *text* from English to *target_lang*.      Raises ValueError for unsup, translate_text()

### Community 17 - "Database Schema"
Cohesion: 0.4
Nodes (4): Generate SQL without a live DB connection (used by --sql flag)., Run migrations against a live DB connection., run_migrations_offline(), run_migrations_online()

### Community 18 - "Health Server"
Cohesion: 0.4
Nodes (5): Contacts Table, Database Schema SHR_V1, Groups Table, Reminders Table, Users Table

### Community 23 - "Azure App Service Setup"
Cohesion: 0.5
Nodes (3): get_db(), SQLAlchemy database engine, session, and base model setup., Dependency that provides a database session per request.

### Community 24 - "Celery App Config"
Cohesion: 0.67
Nodes (3): CELERY_POOL solo for Azure App Service, entrypoint.sh APP_ROLE dispatcher, Azure App Service Setup Guide APP_ROLE

## Knowledge Gaps
- **159 isolated node(s):** `Generate SQL without a live DB connection (used by --sql flag).`, `Run migrations against a live DB connection.`, `initial  Revision ID: 171bbe9d0e08 Revises:  Create Date: 2026-04-25 15:57:22.05`, `add is_deleted to reminders  Revision ID: b1a2c3d4e5f6 Revises: 171bbe9d0e08 Cre`, `add email fallback fields to reminders  Revision ID: c2d3e4f5a6b7 Revises: b1a2c` (+154 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **32 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `voice_status_callback()` connect `Pydantic Schemas` to `Celery Worker Tasks`, `Reminder Routing & Scheduling`?**
  _High betweenness centrality (0.081) - this node is a cross-community bridge._
- **Why does `Reminder` connect `ORM Data Models` to `Reminder Routing & Scheduling`, `Pydantic Schemas`?**
  _High betweenness centrality (0.071) - this node is a cross-community bridge._
- **Are the 11 inferred relationships involving `Reminder` (e.g. with `TrendPoint` and `AnalyticsResponse`) actually correct?**
  _`Reminder` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Are the 9 inferred relationships involving `ReminderTemplate` (e.g. with `TrendPoint` and `AnalyticsResponse`) actually correct?**
  _`ReminderTemplate` has 9 INFERRED edges - model-reasoned connections that need verification._
- **Are the 8 inferred relationships involving `Group` (e.g. with `TrendPoint` and `AnalyticsResponse`) actually correct?**
  _`Group` has 8 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Generate SQL without a live DB connection (used by --sql flag).`, `Run migrations against a live DB connection.`, `initial  Revision ID: 171bbe9d0e08 Revises:  Create Date: 2026-04-25 15:57:22.05` to the rest of the system?**
  _159 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `React UI Components` be split into smaller, more focused modules?**
  _Cohesion score 0.05 - nodes in this community are weakly interconnected._