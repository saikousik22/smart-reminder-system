# Code Review & Bug Report

## Critical Issues

### 1. **Timezone Validation Mismatch** (HIGH SEVERITY)
**Location:** `frontend/src/pages/CreateReminder.jsx` (line 207-230) & `backend/app/routers/reminder_router.py` (line 189)

**Problem:**
- Frontend validates scheduled time in **user's local timezone**
- Backend validates in **UTC**
- These can conflict, causing valid times to be rejected

**Example:** User in UTC+5:30 schedules for tomorrow 2 AM. Frontend validates OK. When converted to ISO, it becomes today 8:30 PM UTC. If backend's current UTC time is already past 8:30 PM, the reminder is rejected.

**Fix:** Convert to UTC on frontend before validation, OR validate on both sides with timezone awareness.

---

### 2. **Missing Recurrence End Date Backend Validation** (HIGH SEVERITY)
**Location:** `backend/app/routers/reminder_router.py` (lines 206-209)

**Problem:**
- Frontend validates `recurrence_end_date >= scheduled_date` (line 220-224)
- Backend does NOT validate this
- A direct API call could set `recurrence_end_date` before `scheduled_time`

**Impact:** Scheduler would try to create next occurrences for invalid date ranges

**Fix:** Add validation after line 206:
```python
if parsed_end_date and parsed_end_date < parsed_time:
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Recurrence end date must be on or after scheduled time"
    )
```

---

## Moderate Issues

### 3. **Incorrect Status Handling on Partial Updates**
**Location:** `backend/app/routers/reminder_router.py` (lines 366-367)

**Problem:**
- Status is only reset to `pending` if `scheduled_time` OR `audio_file` are updated
- If you update ONLY `retry_count` on a reminder in `calling` status, it stays `calling` without resetting

**Impact:** Inconsistent reminder state

**Fix:**
```python
# Line 366-367, add:
if title is not None or phone_number is not None:
    # Only reset if modifying core reminder details
    if scheduled_time is not None or audio_file is not None:
        reminder.status = "pending"
```

---

### 4. **Login Redirect Could Fail on Certain URLs**
**Location:** `frontend/src/api/axios.js` (lines 12-16)

**Problem:**
```javascript
if (!window.location.pathname.includes('/login') && !window.location.pathname.includes('/signup')) {
```

- This uses `.includes()` which is vulnerable to URL patterns like `/not-login` or `/user/login-history`
- Better to use exact path matching

**Fix:**
```javascript
const currentPath = window.location.pathname;
const isAuthPage = currentPath === '/login' || currentPath === '/signup';
if (!isAuthPage) {
    window.location.href = '/login';
}
```

---

### 5. **Celery Task Enqueue Not Error-Checked**
**Location:** `backend/app/tasks.py` (line 72)

**Problem:**
```python
trigger_call.delay(r.id)
```

- No error handling if Celery queue is unreachable
- Reminder marked `processing` but task never enqueued silently fails

**Fix:**
```python
try:
    trigger_call.delay(r.id)
except Exception as exc:
    logger.error(f"Failed to enqueue trigger_call for reminder {r.id}: {exc}")
    r.status = "failed"
```

---

## Minor Issues

### 6. **E164 Phone Validation Not Fully Spec-Compliant**
**Location:** `backend/app/schemas.py` (line 10) & `backend/app/routers/reminder_router.py` (line 166)

**Pattern:** `^\+[1-9]\d{1,14}$`

**Problem:** E.164 spec allows `+[1-9]{1,3}\d{0,14}` (1-15 digits total). Current regex requires at least 2 digits after country code.

**Impact:** Minimal (rare edge case), but could reject valid numbers like `+7` for Russia in some contexts.

---

### 7. **Transient Audio File Not Cleaned on Transcode Error**
**Location:** `backend/app/routers/reminder_router.py` (line 149)

**Problem:**
```python
transcode_to_wav(temp_path, converted_path)
try:
    os.remove(temp_path)
except OSError:
    logger.warning(...)
```

- If `transcode_to_wav()` raises an exception, `temp_path` is never deleted
- Exception is raised on line 56-69, skipping the cleanup

**Fix:** Move `try/except` outside transcode call:
```python
try:
    transcode_to_wav(temp_path, converted_path)
finally:
    try:
        os.remove(temp_path)
    except OSError:
        logger.warning(...)
```

---

### 8. **No Idempotency Check on Duplicate Webhook Calls**
**Location:** `backend/app/routers/voice_router.py` (lines 88-148)

**Problem:**
- If Twilio sends duplicate status callbacks (network retry), the second one will:
  - Try to schedule another retry (line 130)
  - Send duplicate SMS (line 139)
  
**Note:** Line 69 checks `fallback_sent` flag, but the retry on line 130 still runs twice

**Impact:** Potential duplicate retries if callback fires twice

**Fix:** Check if already in final state before scheduling retry:
```python
if reminder.status == "calling":
    reminder.status = new_status
    # ... rest of logic
```

---

### 9. **CORS Configuration Not Validated**
**Location:** `backend/app/config.py` (lines 42-43)

**Problem:**
- Default CORS origins hardcoded to localhost
- Environment variable override not clearly documented
- No validation that provided CORS origins are valid URLs

**Risk:** In production, accidental misconfiguration could allow unwanted origins

---

### 10. **No Cleanup on Reminder Deletion If File Removal Fails**
**Location:** `backend/app/routers/reminder_router.py` (lines 429-433)

**Problem:**
- If `delete_audio_file()` fails, the DB record is already deleted
- User can't retry deletion; file is orphaned

**Impact:** Disk space leak, not functionality issue

---

## Recommendations Summary

| Severity | Issues | Action |
|----------|--------|--------|
| **Critical** | Timezone mismatch, missing validation | Fix immediately |
| **High** | Recurrence end date validation | Fix before release |
| **Moderate** | Status handling, redirect logic, task queuing | Fix in next sprint |
| **Low** | Phone validation, file cleanup, CORS config | Document or refactor |

