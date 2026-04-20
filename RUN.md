# 🚀 How to Run the Smart Reminder System

Follow these steps to get your full-stack application running on your local machine.

## 1. Prerequisites
- **Python 3.8+** installed.
- **Node.js** installed.
- **ngrok** installed (for Twilio webhooks).
- **ffmpeg** installed (required for browser-recorded audio transcoding).
- A **Twilio account** with a Voice-enabled phone number.

---

## 2. Backend Setup

1.  **Navigate to the backend directory:**
    ```bash
    cd backend
    ```

2.  **Create a virtual environment:**
    ```bash
    python -m venv venv
    .\venv\Scripts\activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment Variables:**
    Create a `.env` file in the `backend/` directory (use `.env.example` as a template):
    ```env
    SECRET_KEY=your_random_secret_key
    TWILIO_ACCOUNT_SID=AC...
    TWILIO_AUTH_TOKEN=your_token
    TWILIO_PHONE_NUMBER=+1...
    PUBLIC_BASE_URL=https://your-ngrok-url.ngrok-free.app
    ```

5.  **Start the Backend:**
    ```bash
    uvicorn app.main:app --reload
    ```
    The API will be available at `http://localhost:8000`.

---

## 3. ngrok Setup (Critical for Twilio)

Twilio needs a public URL to call your webhook when someone picks up the phone.

1.  **Start ngrok on port 8000:**
    ```bash
    ngrok http 8000
    ```

2.  **Update Backend .env:**
    Copy the `Forwarding` URL from ngrok (e.g., `https://abc-123.ngrok-free.app`) and paste it as `PUBLIC_BASE_URL` in your backend `.env`.

---

## 4. Frontend Setup

1.  **Navigate to the frontend directory:**
    ```bash
    cd frontend
    ```

2.  **Install dependencies:**
    ```bash
    npm install
    ```

3.  **Start the Frontend:**
    ```bash
    npm run dev
    ```
    The app will be available at `http://localhost:5173`.

---

## 5. Using the App

1.  **Signup:** Create an account.
2.  **Create Reminder:**
    - Enter a title.
    - Enter a phone number (start with `+` followed by country code).
    - Select a future date and time.
    - Record a voice message or upload an audio file.
3.  **Wait:** When the scheduled time arrives, the background scheduler will trigger Twilio to call the phone number and play your message.

> [!TIP]
> **Twilio Trial Accounts:** Remember that if you are using a Twilio trial, you can only call **verified** phone numbers. Make sure to verify your phone number in the Twilio console first.

---
