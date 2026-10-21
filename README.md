# Nobuk Support Agent

A professional AI customer-support agent for **Nobuk** (nobuk.africa), built
with Python, Google Gemini, and FastAPI. Includes a branded web chat, an
admin dashboard, ticketing/escalation with full transcripts, and feedback
analytics.

## Features
- 💬 Branded web chat with quick replies, typing indicator, feedback
- 🧠 Knowledge-base RAG over Nobuk docs (English + Swahili)
- 🛠️ Tool use: order lookup, refunds, tickets, human escalation
- 📋 Admin dashboard: tickets, escalations, analytics, resolve button
- 💾 Persistent storage (JSON; easy to swap for SQLite/Postgres)
- 🔁 Automatic model fallback & retry on network errors
- 🚀 Deploy-ready: `Procfile` (Render) + `Dockerfile` (Hugging Face)

## Setup

1. Copy `.env.example` to `.env` and add your Gemini API key.
2. Install dependencies:

   ```
   pip install -r requirements.txt
   ```

## Run

- CLI: `python cli.py`
- Web: `python -m uvicorn server:app --reload` → http://127.0.0.1:8000
- Admin: http://127.0.0.1:8000/admin

## Try

- "What is Nobuk?"
- "How do I create a payment link?"
- "Does Nobuk hold my funds?"
- "What's the status of order NB-1001?"
- "Refund order NB-1001, it arrived broken"
- "I want to talk to a human because my payment failed"

## Deploy

- **Render:** connect this repo, set `GEMINI_API_KEY` in env vars, deploy.
- **Hugging Face Spaces:** create a Docker Space, set `GEMINI_API_KEY` secret.
- **Local demo:** `python -m uvicorn server:app --reload`

## Extend

- Add more docs to `knowledge_base/` for better answers.
- Replace JSON storage in `tickets.py` with a real database.
- Wire `ZENDESK_*` env vars to create real tickets in Zendesk.
- Swap keyword search in `kb.py` for embeddings for larger docs.
