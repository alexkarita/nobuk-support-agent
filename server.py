"""FastAPI web demo: a minimal chat UI backed by the agent."""
import logging

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from agent import chat

app = FastAPI(title="Nobuk Support Agent")
log = logging.getLogger("nobuk")


class Message(BaseModel):
    session_id: str = "default"
    message: str


@app.post("/chat")
def chat_endpoint(msg: Message):
    try:
        return {"reply": chat(msg.session_id, msg.message)}
    except Exception:
        log.exception("chat failed")
        return {"reply": "Sorry, I'm having trouble right now. Please try again shortly."}


PAGE = """<!doctype html>
<html><head><title>Nobuk Support</title>
<style>
body{font-family:system-ui;max-width:640px;margin:2rem auto;background:#f6f7f9}
#log{background:#fff;border-radius:8px;padding:1rem;height:60vh;overflow:auto}
.u{color:#2563eb}.a{color:#111}
#row{display:flex;gap:.5rem;margin-top:1rem}
input{flex:1;padding:.6rem;border-radius:6px;border:1px solid #ccc}
button{padding:.6rem 1rem;border:0;border-radius:6px;background:#2563eb;color:#fff}
</style></head><body>
<h2>Nobuk Support</h2>
<div id="log"></div>
<div id="row"><input id="in" placeholder="Ask about payment links, subscriptions..."><button id="btn">Send</button></div>
<script>
const sid = crypto.randomUUID();
const log = document.getElementById('log'), input = document.getElementById('in');

function add(cls, who, text) {
  const p = document.createElement('p'); p.className = cls;
  const b = document.createElement('b'); b.textContent = who + ': ';
  p.append(b, document.createTextNode(text));
  log.append(p); log.scrollTop = log.scrollHeight;
}

async function send() {
  const m = input.value.trim(); if (!m) return;
  input.value = ''; add('u', 'You', m);
  try {
    const r = await fetch('/chat', {method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({session_id: sid, message: m})});
    const d = await r.json(); add('a', 'Agent', d.reply);
  } catch (e) { add('a', 'Agent', 'Connection problem, please try again.'); }
}

document.getElementById('btn').onclick = send;
input.addEventListener('keydown', e => { if (e.key === 'Enter') send(); });
</script></body></html>"""


@app.get("/", response_class=HTMLResponse)
def index():
    return PAGE