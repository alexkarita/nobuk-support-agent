"""Core AI support agent built on the Google Gemini API."""
import os
import time
import urllib.request
import json

from dotenv import load_dotenv
from google import genai
from google.genai import types

import tickets
from kb import search_kb

load_dotenv()

MODELS = [m.strip() for m in (os.getenv("MODEL", "gemini-3.8-flash") + "," + os.getenv("FALLBACK_MODELS", "")).replace(" ", "").split(",") if m.strip()]
SYSTEM_PROMPT = """You are a friendly customer support agent for Nobuk (nobuk.africa),
an auto-reconciliation and instant reports platform for African businesses.
Guidelines:
- Answer questions about Nobuk using search_knowledge_base first.
- Use tools to look up orders, process refunds, or file tickets.
- You cannot cancel a subscription directly; create a ticket instead if a customer wants that.
- Escalate to a human when the customer asks, is very upset, or you cannot help.
- Never invent order IDs, prices, or policies. Ask for clarification if unclear.
- Be concise and helpful.
"""

_transcripts = {}  # session_id -> list of {"role": ..., "text": ...}


def record(session_id, role, text):
    _transcripts.setdefault(session_id, []).append({"role": role, "text": text})


def get_transcript(session_id):
    return _transcripts.get(session_id, [])


def search_knowledge_base(query: str) -> str:
    """Search Nobuk's help docs for policies and FAQs."""
    return search_kb(query)


def get_order_status(order_id: str) -> dict:
    """Look up an order's status by order ID."""
    return tickets.get_order_status(order_id)


def create_refund(order_id: str, reason: str) -> dict:
    """Refund a delivered order."""
    return tickets.create_refund(order_id, reason)


def create_ticket(subject: str, description: str, priority: str = "normal") -> dict:
    """File a support ticket for issues that need follow-up."""
    return tickets.create_ticket(subject, description, priority)


def escalate_to_human(reason: str) -> dict:
    """Hand the conversation off to a human agent."""
    return tickets.escalate_to_human(reason)


TOOLS = [search_knowledge_base, get_order_status, create_refund, create_ticket, escalate_to_human]

_client = None
_sessions = {}
CURRENT_SESSION = None


def _get_client():
    global _client
    if _client is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("Set GEMINI_API_KEY in your .env file")
        _client = genai.Client(api_key=api_key)
    return _client


def _new_chat(model):
    return _get_client().chats.create(
        model=model,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            tools=TOOLS,
        ),
    )


CURRENT_SESSION = None


def chat(session_id: str, user_message: str) -> str:
    global CURRENT_SESSION
    record(session_id, "user", user_message)
    CURRENT_SESSION = session_id

    delay = 0.5
    try:
        for _attempt in range(2):
            for model in MODELS:
                try:
                    if session_id not in _sessions or _sessions[session_id][0] != model:
                        _sessions[session_id] = (model, _new_chat(model))
                    reply = _sessions[session_id][1].send_message(user_message)
                    text = (reply.text or "").strip()
                    if not text:
                        text = "Okay!"
                    record(session_id, "assistant", text)
                    return text
                except Exception as e:
                    msg = str(e)
                    retryable = any(code in msg for code in ("503", "504", "429", "ReadError", "WinError", "UNAVAILABLE", "NOT_FOUND"))
                    if not retryable:
                        raise
                    _sessions.pop(session_id, None)
                    time.sleep(delay)
                    delay *= 2
                    continue
        raise RuntimeError("All Gemini models are currently unavailable. Please try again in a moment.")
    finally:
        CURRENT_SESSION = None
