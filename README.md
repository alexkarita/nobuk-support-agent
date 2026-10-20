# Nobuk Support Agent

A Python customer-support agent for Nobuk (nobuk.africa), using the Google
Gemini API with tool use, a knowledge base, fake orders/refunds, tickets,
and human escalation. Includes a CLI and a web demo.

## Setup (Visual Studio: File -> Open -> Folder, pick this folder)

1. Copy `.env.example` to `.env` and add your Gemini API key.
2. Install dependencies:

   ```
   pip install -r requirements.txt google-genai
   ```

## Run

- CLI: `python cli.py`
- Web: `python -m uvicorn server:app --reload` then open http://127.0.0.1:8000

## Try

- "What is Nobuk?"
- "How do I create a payment link?"
- "Does Nobuk hold my funds?"
- "How do subscriptions work?"
- "I want to talk to a human"

## Extend

- Add more docs to `knowledge_base/` for better answers.
- Replace fake functions in `tickets.py` with real API/DB calls.
- Swap the keyword search in `kb.py` for embeddings for larger docs.
