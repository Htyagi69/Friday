# 🤖 Friday — Personal AI Voice Assistant

**Friday** is a real-time AI voice assistant inspired by the concept of JARVIS from the Iron Man universe.

Instead of interacting through a traditional text-based chatbot interface, Friday is designed around **real-time voice interaction**, allowing users to speak naturally and receive AI-generated responses through voice.

The project combines **Google Gemini Live, WebSockets, FastAPI, PostgreSQL, Prisma, and Firebase Cloud Messaging** to create a persistent, conversational AI assistant.

---

## ✨ Features

### 🎙️ Real-Time Voice Conversation

- Speak naturally with Friday using your microphone.
- Real-time audio is streamed between the browser and backend.
- AI responses are returned as audio.
- Supports input and output audio transcription.

### 🧠 Gemini Live Integration

Friday uses Google's **Gemini Live API** for real-time conversational AI.

Instead of following a traditional:

```text
Audio → Speech-to-Text → LLM → Text-to-Speech → Audio
```

pipeline, Friday communicates with the live model through a persistent real-time connection.

```text
User Voice
     ↓
Gemini Live
     ↓
AI Reasoning
     ↓
Voice Response
```

### ⚡ WebSocket Communication

A persistent WebSocket connection is used for real-time communication between the browser and FastAPI backend.

```text
Browser
   ⇅
WebSocket
   ⇅
FastAPI
   ⇅
Gemini Live
```

This allows audio and conversational events to be exchanged without repeatedly creating HTTP requests.

### 💬 Persistent Conversations

Friday maintains conversation sessions so that users can continue previous conversations.

The backend manages:

- Sessions
- Messages
- User transcripts
- Assistant transcripts
- Active conversation state

### 🗂️ Conversation Management

Users can maintain multiple conversation sessions.

Friday can:

- Create a new session
- Continue an existing session
- Switch between sessions
- Store conversation history
- Generate short conversation titles
- Maintain context for ongoing conversations

### 🔔 Push Notifications

Firebase Cloud Messaging is integrated for notifications.

Friday can send notifications to registered devices, allowing the assistant to communicate important events even when the main interface is not actively being used.

### 💾 Persistent Storage

Conversation information is persisted using PostgreSQL.

Prisma is used as the database access layer.

### 🎨 JARVIS-Inspired HUD

The frontend provides a futuristic HUD-style interface containing:

- Live transcript
- Assistant status
- Connection status
- Thinking state
- Microphone controls
- Animated visual elements

---

# 🧠 Core Architecture

```text
                         ┌─────────────────────────┐
                         │        Browser          │
                         │                         │
                         │   JARVIS HUD / UI       │
                         │                         │
                         │   Microphone            │
                         │   Audio Player          │
                         │   Transcript            │
                         └────────────┬────────────┘
                                      │
                                WebSocket
                                      │
                                      ▼
                         ┌─────────────────────────┐
                         │        FastAPI          │
                         │                         │
                         │ WebSocket Manager       │
                         │ Session Manager         │
                         │ Conversation Logic     │
                         │ Notification API        │
                         └────────────┬────────────┘
                                      │
                              Gemini Live API
                                      │
                                      ▼
                         ┌─────────────────────────┐
                         │     Gemini Live Model   │
                         │                         │
                         │   Audio Input           │
                         │   AI Processing         │
                         │   Audio Output          │
                         │   Transcriptions        │
                         └─────────────────────────┘

                                      │
                                      │
                         ┌────────────▼────────────┐
                         │       PostgreSQL        │
                         │                         │
                         │ Users                   │
                         │ Sessions                │
                         │ Messages                │
                         │ Device Tokens            │
                         └─────────────────────────┘

                                      │
                                      ▼
                         ┌─────────────────────────┐
                         │   Firebase Cloud        │
                         │      Messaging          │
                         │                         │
                         │     Push Notifications  │
                         └─────────────────────────┘
```

---

# 🎙️ Real-Time Voice Architecture

The main goal of Friday is **low-latency voice interaction**.

The browser establishes a WebSocket connection:

```text
Browser
   │
   │ WebSocket
   ▼
FastAPI
   │
   │ Live Connection
   ▼
Gemini Live
```

Audio is streamed through the connection rather than uploading a complete recording and waiting for a traditional request/response cycle.

---

# 🔄 Conversation Flow

A typical conversation follows this flow:

```text
User speaks
     ↓
Browser captures microphone audio
     ↓
WebSocket
     ↓
FastAPI
     ↓
Gemini Live
     ↓
AI generates response
     ↓
Audio response
     ↓
FastAPI
     ↓
WebSocket
     ↓
Browser
     ↓
Friday speaks
```

This architecture allows the interaction to feel closer to a live conversation than a conventional chatbot.

---

# 🗂️ Session Architecture

Friday separates conversations into sessions.

```text
User
 │
 ├── Session 1
 │     ├── User message
 │     ├── Friday response
 │     └── User message
 │
 ├── Session 2
 │     ├── User message
 │     └── Friday response
 │
 └── Session 3
       ├── User message
       └── Friday response
```

Each session can maintain its own conversation history.

This makes it possible to switch between different conversations without mixing their context.

---

# 💾 Database Architecture

PostgreSQL stores the persistent state of the application.

A simplified data model looks like:

```text
User
 │
 ├── Sessions
 │      │
 │      └── Messages
 │
 └── Device Tokens
```

### User

Stores user-level information.

### Session

Represents an individual conversation.

### Messages

Stores conversation transcripts.

### Device Tokens

Stores registered device/browser tokens used for Firebase notifications.

---

# 🔔 Push Notification Architecture

Friday uses **Firebase Cloud Messaging (FCM)** for push notifications.

```text
Friday Backend
      │
      ▼
Firebase Cloud Messaging
      │
      ▼
Registered Browser / Device
      │
      ▼
Notification
```

The browser registers an FCM token with the backend.

The backend stores the token and can later use it to send notifications.

---

# 🔐 Device Registration Flow

```text
Browser
   │
   ▼
Request Notification Permission
   │
   ▼
Generate FCM Token
   │
   ▼
POST /register-device
   │
   ▼
FastAPI
   │
   ▼
PostgreSQL
```

When a notification needs to be sent:

```text
Backend
   │
   ▼
Retrieve Device Token
   │
   ▼
Firebase Cloud Messaging
   │
   ▼
Browser Notification
```

---

# 🛠️ Tech Stack

## Frontend

- HTML
- CSS
- JavaScript
- WebSocket API
- Web Audio API
- Firebase Cloud Messaging

## Backend

- Python
- FastAPI
- Uvicorn
- WebSockets

## AI

- Google Gemini Live API
- `google-genai`

## Database

- PostgreSQL
- Prisma

## Notifications

- Firebase Cloud Messaging
- Firebase Admin SDK
- Web Push / FCM

## Deployment

- Vercel
- Render / Railway

---

# 📂 Project Structure

```text
Friday/
│
├── server/
│   ├── main.py
│   ├── routes/
│   ├── services/
│   ├── conversation/
│   ├── notifications/
│   ├── prisma/
│   │   └── schema.prisma
│   ├── pyproject.toml
│   └── ...
│
├── frontend/
│   ├── Google-Jarvis.html
│   ├── script.js
│   ├── style.css
│   ├── service-worker.js
│   └── assets/
│       └── Friday.png
│
└── README.md
```

> Adjust this structure to match the actual repository structure.

---

# ⚙️ API Overview

Some of the important backend endpoints include:

### Create Session

```http
POST /sessions
```

Creates a new conversation session.

### Live Voice Connection

```text
WebSocket /ws/live/{sessionId}
```

Creates a real-time voice connection for a specific conversation session.

### Register Device

```http
POST /register-device
```

Registers the browser/device's FCM token.

### Test Notification

```http
POST /test-notify
```

Used to test Firebase push notification delivery.

---

# 🔑 Environment Variables

Example configuration:

```env
GEMINI_API_KEY=your_gemini_api_key

DATABASE_URL=your_postgresql_connection_string

FIREBASE_PROJECT_ID=your_project_id
FIREBASE_PRIVATE_KEY=your_private_key
FIREBASE_CLIENT_EMAIL=your_client_email
```

Frontend Firebase configuration may include:

```env
VITE_FIREBASE_API_KEY=your_api_key
VITE_FIREBASE_AUTH_DOMAIN=your_auth_domain
VITE_FIREBASE_PROJECT_ID=your_project_id
VITE_FIREBASE_STORAGE_BUCKET=your_storage_bucket
VITE_FIREBASE_MESSAGING_SENDER_ID=your_sender_id
VITE_FIREBASE_APP_ID=your_app_id
VITE_FIREBASE_VAPID_KEY=your_vapid_public_key
```

**Never commit API keys, Firebase service-account credentials, private keys, or `.env` files to GitHub.**

---

# ▶️ Running Locally

### Clone the repository

```bash
git clone https://github.com/htyagi5/Friday.git

cd Friday
```

### Install backend dependencies

```bash
pip install -e .
```

Or use your Python environment/package manager according to the project's configuration.

### Configure environment variables

Create the required `.env` file.

### Start PostgreSQL

Make sure PostgreSQL is running and the configured database is accessible.

### Run Prisma

Run the appropriate Prisma database commands configured for the project.

### Start FastAPI

```bash
uvicorn main:app --reload
```

The backend will run locally, typically on:

```text
http://127.0.0.1:8000
```

### Start the frontend

Serve the frontend through a local development server.

For example:

```bash
python -m http.server 5500
```

Then open the frontend in your browser.

---

# 🌍 Deployment

Friday separates the frontend and backend services.

```text
                    Friday
                       │
            ┌──────────┴──────────┐
            │                     │
            ▼                     ▼
        Frontend               Backend
        Vercel                 Render
                                  │
                     ┌────────────┼────────────┐
                     │            │            │
                     ▼            ▼            ▼
                 Gemini       PostgreSQL      FCM
                  Live          Database    Notifications
```

The production WebSocket connection uses `wss://` rather than `ws://`.

---

# 🧠 Engineering Challenges

Building Friday involved solving several real-time engineering problems.

### Real-Time Audio

Unlike a normal REST API, voice interaction requires continuous data flow.

```text
Audio Input
    ↓
WebSocket
    ↓
Gemini Live
    ↓
Audio Output
```

### WebSocket Lifecycle

The backend needs to correctly handle:

- Connection establishment
- Disconnection
- Reconnection
- Session switching
- Audio streaming
- Concurrent send/receive operations

### Conversation State

Friday maintains the relationship between:

```text
User
 ↓
Session
 ↓
Gemini Live Connection
 ↓
Messages
```

This prevents different conversations from being mixed together.

### Persistent Conversation History

The application stores transcripts separately from the live model connection so that previous conversations can be restored or continued.

### Push Notifications

FCM introduces another asynchronous communication path:

```text
Backend
   ↓
FCM
   ↓
Browser
```

This required handling browser permissions, FCM tokens, service workers, and backend token registration.

---

# 📚 What I Learned

Building Friday gave me practical experience with:

- Real-time AI applications
- Google Gemini Live API
- Multimodal AI
- Audio streaming
- WebSockets
- FastAPI
- Python async programming
- PostgreSQL
- Prisma
- Session management
- Conversation persistence
- Firebase Cloud Messaging
- Service workers
- Browser notifications
- Web Audio APIs
- Production CORS configuration
- WebSocket deployment
- Frontend/backend architecture
- Cloud deployment

---

# 🔮 Future Improvements

Possible improvements include:

- 🗣️ Wake-word detection
- 🎧 Better interruption/barge-in handling
- 🧠 Long-term memory
- 🛠️ Tool/function calling
- 🏠 Smart-home integration
- 📅 Calendar integration
- 📧 Email integration
- 🔎 Web search capabilities
- ⏰ Persistent scheduled reminders
- 📱 Native mobile client
- 🔊 Improved voice controls
- 🧩 Modular skill/plugin architecture
- 🔐 Improved authentication and authorization

---

# 🎯 Project Goal

The goal of Friday is not to build another text-based AI chatbot.

The project explores how to build an assistant that feels more like a **real-time conversational system**:

```text
          ┌─────────────────────┐
          │       FRIDAY        │
          │                     │
          │   👂 Listen         │
          │   🧠 Understand      │
          │   💭 Process        │
          │   🗣️ Respond        │
          │   💾 Remember       │
          │   🔔 Notify         │
          └─────────────────────┘
```

The project is an ongoing exploration of **real-time AI, voice interfaces, persistent memory, and event-driven backend systems**.

---

# 👨‍💻 Author

**Harshit Tyagi**

Computer Science & Engineering @ AKGEC

Interested in:

- Backend Development
- Full-Stack Development
- Generative AI
- Real-Time Systems
- Voice AI
- Cloud Technologies

GitHub: **@htyagi5**

---

## ⭐ Support

If you find Friday interesting, consider giving the repository a ⭐.

Built with curiosity, AI, WebSockets, and a lot of debugging. 🤖
