"""Fake business data + ticket store for the demo agent."""
import json
import os
import urllib.request
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

DATA_FILE = Path(__file__).parent / "tickets.json"
ESCALATIONS_FILE = Path(__file__).parent / "escalations.json"

ORDERS = {
    "NB-1001": {"status": "delivered", "item": "Collection page setup", "total": 0.0, "email": "jane@example.com"},
    "NB-1002": {"status": "shipped", "item": "Payment link bundle", "total": 0.0, "email": "jane@example.com"},
    "NB-1003": {"status": "processing", "item": "Subscription plan", "total": 0.0, "email": "bob@example.com"},
}

_tickets = json.loads(DATA_FILE.read_text()) if DATA_FILE.exists() else []
_escalations = json.loads(ESCALATIONS_FILE.read_text()) if ESCALATIONS_FILE.exists() else []


def get_order_status(order_id: str) -> dict:
    return ORDERS.get(order_id.upper(), {"error": f"Order {order_id} not found"})


def create_refund(order_id: str, reason: str) -> dict:
    order = ORDERS.get(order_id.upper())
    if not order:
        return {"error": f"Order {order_id} not found"}
    if order["status"] != "delivered":
        return {"error": f"Order {order_id} is not delivered yet; cannot refund."}
    return {"refund_id": f"R-{order_id.upper()}", "amount": order["total"], "status": "approved"}


def create_ticket(subject: str, description: str, priority: str = "normal") -> dict:
    ticket = {"id": f"T{len(_tickets)+1001}", "type": "ticket", "subject": subject, "description": description, "priority": priority, "status": "open", "created_at": datetime.utcnow().isoformat()}
    _tickets.append(ticket)
    DATA_FILE.write_text(json.dumps(_tickets, indent=2))
    return ticket


def _post_webhook(payload: dict):
    url = os.getenv("TICKET_WEBHOOK_URL")
    if not url:
        return None
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return {"status": resp.status, "body": resp.read().decode("utf-8", errors="ignore")[:500]}
    except Exception as e:
        return {"error": str(e)}


def _post_zendesk(subject: str, description: str):
    subdomain = os.getenv("ZENDESK_SUBDOMAIN")
    email = os.getenv("ZENDESK_EMAIL")
    token = os.getenv("ZENDESK_API_TOKEN")
    if not (subdomain and email and token):
        return None
    import base64
    auth = base64.b64encode(f"{email}/token:{token}".encode()).decode()
    data = json.dumps({"ticket": {"subject": subject, "comment": {"body": description}, "priority": "high", "status": "open"}}).encode("utf-8")
    req = urllib.request.Request(f"https://{subdomain}.zendesk.com/api/v2/tickets.json", data=data, headers={"Content-Type": "application/json", "Authorization": f"Basic {auth}"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            t = result.get("ticket", {})
            return {"ticket_id": t.get("id"), "view_url": t.get("url") or f"https://{subdomain}.zendesk.com/agent/tickets/{t.get('id')}"}
    except Exception as e:
        return {"error": str(e)}
    domain = os.getenv("FRESHDESK_DOMAIN")  # e.g. nobuk.freshdesk.com
    api_key = os.getenv("FRESHDESK_API_KEY")
    if not (domain and api_key):
        return None
    import base64
    auth = base64.b64encode(f"{api_key}:X".encode()).decode()
    data = json.dumps({"subject": subject, "description": description, "priority": priority, "status": 2}).encode("utf-8")
    req = urllib.request.Request(f"https://{domain}/api/v2/tickets", data=data, headers={"Content-Type": "application/json", "Authorization": f"Basic {auth}"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return {"ticket_id": result.get("id"), "view_url": result.get("helpdesk_ticket", {}).get("url") or f"https://{domain}/a/tickets/{result.get('id')}"}
    except Exception as e:
        return {"error": str(e)}


def escalate_to_human(reason: str, transcript=None) -> dict:
    # pull live transcript if not passed
    if transcript is None:
        try:
            import agent as _agent
            sid = getattr(_agent, "CURRENT_SESSION", None)
            if sid is not None:
                transcript = _agent.get_transcript(sid)
        except Exception:
            transcript = []

    subject = f"Nobuk support escalation: {reason[:60]}"
    transcript_text = "\n".join(f"[{m['role']}] {m['text']}" for m in (transcript or []))
    description = f"Reason: {reason}\n\n--- Conversation ---\n{transcript_text}"

    ticket_id = f"H{len(_escalations) + 2001}"
    record = {
        "id": ticket_id,
        "type": "escalation",
        "subject": subject,
        "reason": reason,
        "transcript": transcript or [],
        "status": "open",
        "priority": "high",
        "created_at": datetime.utcnow().isoformat(),
    }

    external = _post_zendesk(subject, description) or _post_freshdesk(subject, description) or _post_webhook({"ticket_id": ticket_id, "subject": subject, "description": description})
    if external:
        record["external"] = external

    _escalations.append(record)
    ESCALATIONS_FILE.write_text(json.dumps(_escalations, indent=2))

    return {
        "escalated": True,
        "ticket_id": ticket_id,
        "transcript_lines": len(transcript or []),
        "external": external,
        "message": "A Nobuk human agent will take over this conversation shortly. Your ticket number is " + ticket_id + ".",
    }
