"""FastAPI web demo: branded chat UI + admin dashboard."""
import os
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel

import agent
from agent import chat
import tickets

app = FastAPI(title="Nobuk Support Agent")


class Message(BaseModel):
    session_id: str = "web"
    message: str


class Feedback(BaseModel):
    session_id: str = "web"
    rating: str
    comment: str = ""


class Reply(BaseModel):
    message: str


def _require_admin(request: Request):
    """Protect admin-only endpoints with the PIN (query param or header)."""
    key = request.query_params.get("key") or request.headers.get("X-Admin-Key")
    if key != ADMIN_PIN:
        raise HTTPException(status_code=401, detail="admin key required")


@app.post("/chat")
def chat_endpoint(msg: Message):
    import re
    reply = chat(msg.session_id, msg.message)
    m = re.search(r"H\d{4}", reply)
    return {"reply": reply, "ticket_id": (m.group(0) if m else None)}


@app.get("/chat/history")
def chat_history(session_id: str = "web"):
    """Return the stored transcript so a page refresh keeps the conversation."""
    return {"messages": agent.get_transcript(session_id)}


@app.post("/feedback")
def feedback_endpoint(fb: Feedback):
    return tickets.record_feedback(fb.session_id, fb.rating, fb.comment)


FAVICON = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
<rect width="64" height="64" rx="14" fill="#2fb5b0"/>
<text x="32" y="44" font-family="Inter,Segoe UI,sans-serif" font-size="36" font-weight="800" fill="#fff" text-anchor="middle">N</text>
</svg>"""


@app.get("/favicon.svg")
def favicon():
    return Response(content=FAVICON, media_type="image/svg+xml")


@app.get("/favicon.ico")
def favicon_ico():
    return Response(content=FAVICON, media_type="image/svg+xml")


@app.get("/health")
def health():
    return {"status": "ok", "service": "nobuk-support-agent"}


@app.get("/api/tickets")
def api_tickets(request: Request):
    _require_admin(request)
    return tickets._tickets


@app.get("/api/escalations")
def api_escalations(request: Request):
    _require_admin(request)
    return tickets._escalations


@app.get("/api/analytics")
def api_analytics(request: Request):
    _require_admin(request)
    return tickets.get_analytics()


@app.post("/api/escalations/{ticket_id}/resolve")
def resolve_escalation(ticket_id: str, request: Request):
    _require_admin(request)
    for e in tickets._escalations:
        if e["id"] == ticket_id:
            e["status"] = "resolved"
            tickets.ESCALATIONS_FILE.write_text(__import__("json").dumps(tickets._escalations, indent=2))
            return {"ok": True}
    raise HTTPException(status_code=404, detail="not found")


@app.post("/api/escalations/{ticket_id}/reply")
def reply_escalation(ticket_id: str, body: Reply, request: Request):
    _require_admin(request)
    if not tickets.add_reply(ticket_id, body.message):
        raise HTTPException(status_code=404, detail="not found")
    return {"ok": True}


@app.get("/api/escalations/{ticket_id}/replies")
def escalation_replies(ticket_id: str):
    """Customer-facing: returns only the support replies + status (no transcript)."""
    t = tickets.get_ticket(ticket_id)
    if not t:
        raise HTTPException(status_code=404, detail="not found")
    return {"status": t.get("status"), "replies": t.get("replies", [])}


CHAT_PAGE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Nobuk Support</title>
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<style>
:root{--teal:#2fb5b0;--teal2:#0b99a2;--navy:#0f172a;--bg:#f1f5f9;--card:#fff;--muted:#64748b}
*{box-sizing:border-box}body{margin:0;font-family:Inter,system-ui,-apple-system,Segoe UI,Roboto,sans-serif;background:var(--bg);color:var(--navy)}
header{background:linear-gradient(135deg,var(--teal),var(--teal2));color:#fff;padding:1rem 1.25rem;display:flex;align-items:center;gap:.75rem;box-shadow:0 2px 8px rgba(0,0,0,.1)}
header h1{margin:0;font-size:1.15rem}header p{margin:0;font-size:.8rem;opacity:.9}
.logo{width:36px;height:36px;border-radius:10px;background:#fff;color:var(--teal);display:grid;place-items:center;font-weight:800}
main{max-width:760px;margin:1rem auto;padding:0 1rem}
.chat{background:var(--card);border-radius:14px;box-shadow:0 4px 16px rgba(0,0,0,.06);display:flex;flex-direction:column;height:70vh;overflow:hidden}
#log{flex:1;overflow:auto;padding:1rem;display:flex;flex-direction:column;gap:.6rem}
.msg{max-width:80%;padding:.7rem .9rem;border-radius:12px;line-height:1.45;font-size:.95rem;animation:pop .15s ease}
.msg.user{align-self:flex-end;background:var(--teal);color:#fff;border-bottom-right-radius:4px}
.msg.agent{align-self:flex-start;background:#eef2f7;color:var(--navy);border-bottom-left-radius:4px}
.msg .meta{font-size:.7rem;opacity:.7;margin-top:.3rem}
.typing{align-self:flex-start;background:#eef2f7;padding:.7rem .9rem;border-radius:12px;display:none;gap:4px}
.typing span{width:7px;height:7px;background:var(--muted);border-radius:50%;animation:bounce 1.2s infinite}
.typing span:nth-child(2){animation-delay:.2s}.typing span:nth-child(3){animation-delay:.4s}
@keyframes bounce{0%,80%,100%{transform:translateY(0)}40%{transform:translateY(-6px)}}
@keyframes pop{from{opacity:0;transform:translateY(4px)}to{opacity:1;transform:translateY(0)}}
.quick{display:flex;gap:.4rem;flex-wrap:wrap;padding:.6rem 1rem;border-top:1px solid #e2e8f0}
.quick button{border:1px solid #cbd5e1;background:#fff;border-radius:999px;padding:.35rem .75rem;font-size:.8rem;cursor:pointer;color:var(--navy)}
.quick button:hover{background:var(--teal);color:#fff;border-color:var(--teal)}
.row{display:flex;gap:.5rem;padding:.75rem 1rem;border-top:1px solid #e2e8f0}
.row input{flex:1;padding:.65rem .85rem;border:1px solid #cbd5e1;border-radius:10px;font-size:.95rem}
.row button{background:var(--teal);color:#fff;border:0;border-radius:10px;padding:.65rem 1.1rem;font-weight:600;cursor:pointer}
.row button:hover{background:var(--teal2)}
.feedback{display:flex;gap:.3rem;margin-top:.3rem}
.feedback button{border:0;background:transparent;cursor:pointer;font-size:.9rem;opacity:.6}
.feedback button:hover{opacity:1}
footer{text-align:center;color:var(--muted);font-size:.75rem;margin:1rem 0}
a.admin{color:var(--teal);text-decoration:none;font-weight:600}
button.reset{background:transparent;border:1px solid #cbd5e1;color:var(--muted);border-radius:999px;padding:.25rem .7rem;font-size:.75rem;cursor:pointer}
button.reset:hover{background:#fff;color:var(--navy)}
.disc{text-align:center;color:var(--muted);font-size:.75rem;margin:1rem 0 0}
</style></head><body>
<header><div class="logo">N</div><div><h1>Nobuk Support</h1><p>Auto-reconciliation & instant reports · 24/7 AI agent</p></div></header>
<main>
<div class="chat">
  <div id="log"></div>
  <div class="typing" id="typing"><span></span><span></span><span></span></div>
  <div class="quick">
    <button onclick="quick('What is Nobuk?')">What is Nobuk?</button>
    <button onclick="quick('How do I create a payment link?')">Payment links</button>
    <button onclick="quick('Does Nobuk hold my funds?')">Funds</button>
    <button onclick="quick('How do subscriptions work?')">Subscriptions</button>
    <button onclick="quick('I want to talk to a human')">Talk to human</button>
  </div>
  <div class="row">
    <input id="in" placeholder="Ask about Nobuk..." onkeydown="if(event.key==='Enter')send()">
    <button onclick="send()">Send</button>
  </div>
</div>
<p class="disc">You are chatting with an AI agent. For urgent issues, ask to talk to a human and we will connect you.</p>
<footer><button class="reset" onclick="resetChat()">Reset chat</button> &nbsp;|&nbsp; Need the agent view? <a class="admin" href="/admin">Open admin dashboard &rarr;</a></footer>
</main>
<script>
const SID=localStorage.getItem('nobuk_sid')||('web-'+Math.random().toString(36).slice(2));
localStorage.setItem('nobuk_sid',SID);
const log=document.getElementById('log'), typing=document.getElementById('typing');
function addMsg(text,cls,withFeedback=false){
  const d=document.createElement('div');d.className='msg '+cls;
  d.innerHTML=text.replace(/\n/g,'<br>');
  if(withFeedback){const fb=document.createElement('div');fb.className='feedback';fb.innerHTML='<button onclick="fb(this,\'up\')">👍</button><button onclick="fb(this,\'down\')">👎</button>';d.appendChild(fb);}
  log.appendChild(d);log.scrollTop=log.scrollHeight;
}
function quick(t){document.getElementById('in').value=t;send();}
const WELCOME='\u{1F44B} Hi! I\'m the Nobuk support agent. Ask me anything about payments, reconciliation, or subscriptions.';
let currentTicket=null,lastReplyCount=0,pollTimer=null;

async function restore(){
  try{
    const r=await fetch('/chat/history?session_id='+encodeURIComponent(SID));
    const d=await r.json();
    if(d.messages && d.messages.length){d.messages.forEach(m=>addMsg(m.text, m.role==='user'?'user':'agent'));}
    else{addMsg(WELCOME,'agent');}
  }catch(e){addMsg(WELCOME,'agent');}
}
function resetChat(){
  localStorage.removeItem('nobuk_sid');
  location.reload();
}
restore();
async function send(){
  const i=document.getElementById('in');const m=i.value.trim();if(!m)return;i.value='';
  addMsg(m,'user');typing.style.display='flex';log.scrollTop=log.scrollHeight;
  try{
    const r=await fetch('/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({session_id:SID,message:m})});
    const d=await r.json();typing.style.display='none';addMsg(d.reply,'agent',true);
    if(d.ticket_id){currentTicket=d.ticket_id;lastReplyCount=0;startPolling();}
  }catch(e){typing.style.display='none';addMsg('Sorry, connection issue. Please try again.','agent');}
}
function startPolling(){
  if(pollTimer)clearInterval(pollTimer);
  pollTimer=setInterval(async()=>{
    if(!currentTicket)return;
    try{
      const r=await fetch('/api/escalations/'+currentTicket+'/replies');
      const t=await r.json();
      const replies=t.replies||[];
      if(replies.length>lastReplyCount){for(let i=lastReplyCount;i<replies.length;i++){addMsg('?? Nobuk support team: '+replies[i].message,'agent',false);}lastReplyCount=replies.length;}
      if(t.status==='resolved'){clearInterval(pollTimer);pollTimer=null;addMsg('? This ticket has been resolved by the Nobuk team.','agent');}
    }catch(e){}
  },4000);
}
async function fb(btn,rating){const card=btn.closest('.msg');await fetch('/feedback',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({session_id:SID,rating:rating})});btn.style.opacity='1';btn.disabled=true;}
</script></body></html>"""

ADMIN_PAGE = r"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Nobuk Admin</title>
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<style>
:root{--teal:#2fb5b0;--bg:#f1f5f9;--card:#fff;--muted:#64748b}
*{box-sizing:border-box}body{margin:0;font-family:Inter,system-ui,sans-serif;background:var(--bg);color:#0f172a}
header{background:linear-gradient(135deg,var(--teal),#0b99a2);color:#fff;padding:1rem 1.25rem}
header h1{margin:0;font-size:1.2rem}header p{margin:.2rem 0 0;font-size:.8rem;opacity:.9}
main{max-width:1100px;margin:1rem auto;padding:0 1rem}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:.75rem;margin-bottom:1rem}
.card{background:var(--card);border-radius:12px;padding:1rem;box-shadow:0 2px 8px rgba(0,0,0,.05)}
.card .n{font-size:1.8rem;font-weight:800;color:var(--teal)}.card .l{font-size:.75rem;color:var(--muted);text-transform:uppercase}
section{background:var(--card);border-radius:12px;padding:1rem;margin-bottom:1rem;box-shadow:0 2px 8px rgba(0,0,0,.05)}
section h2{margin:.2rem 0 1rem;font-size:1rem}
table{width:100%;border-collapse:collapse;font-size:.85rem}
th,td{padding:.5rem .6rem;text-align:left;border-bottom:1px solid #e2e8f0;vertical-align:top}
th{color:var(--muted);font-weight:600;font-size:.75rem;text-transform:uppercase}
tr:hover{background:#f8fafc}
.badge{padding:.15rem .5rem;border-radius:999px;font-size:.7rem;font-weight:600}
.badge.open{background:#fef3c7;color:#92400e}.badge.resolved{background:#dcfce7;color:#166534}
button.resolve{border:0;background:var(--teal);color:#fff;border-radius:6px;padding:.3rem .6rem;cursor:pointer;font-size:.75rem}
button.resolve:hover{background:#0b99a2}
.transcript{max-height:160px;overflow:auto;background:#f8fafc;padding:.4rem;border-radius:6px;font-size:.75rem;white-space:pre-wrap}
.transcript .u{color:#2563eb;font-weight:600}
.transcript .a{color:#0f172a;font-weight:600}
.transcript .line{display:block;margin:.15rem 0}
a.back{color:var(--teal);text-decoration:none;font-weight:600}
</style></head><body>
<header><h1>Nobuk Admin Dashboard</h1><p>Tickets, escalations and feedback at a glance</p></header>
<main>
<div class="cards" id="cards"></div>
<section><h2>Escalations</h2><div id="esc"></div></section>
<section><h2>Support Tickets</h2><div id="tix"></div></section>
<footer style="margin-top:1rem"><a class="back" href="/">← Back to chat</a></footer>
</main>
<script>
const KEY=new URLSearchParams(location.search).get('key')||'';
async function load(){
  if(document.activeElement && (document.activeElement.tagName==='INPUT' || document.activeElement.tagName==='TEXTAREA')) return;
  const saved={}; document.querySelectorAll('input[id^="reply-"]').forEach(i=>saved[i.id]=i.value);
  const a=await fetch('/api/analytics?key='+KEY).then(r=>r.json());
  document.getElementById('cards').innerHTML=`
    <div class="card"><div class="n">${a.tickets}</div><div class="l">Tickets</div></div>
    <div class="card"><div class="n">${a.escalations}</div><div class="l">Escalations</div></div>
    <div class="card"><div class="n">${a.open_escalations}</div><div class="l">Open</div></div>
    <div class="card"><div class="n">${a.feedback_up}</div><div class="l">👍 Feedback</div></div>
    <div class="card"><div class="n">${a.feedback_down}</div><div class="l">👎 Feedback</div></div>`;
  const esc=await fetch('/api/escalations?key='+KEY).then(r=>r.json());
  document.getElementById('esc').innerHTML=table(esc,true);
  const tix=await fetch('/api/tickets?key='+KEY).then(r=>r.json());
  document.getElementById('tix').innerHTML=table(tix,false);
  Object.keys(saved).forEach(id=>{const el=document.getElementById(id); if(el) el.value=saved[id];});
}
function table(rows,isEsc){
  if(!rows.length)return '<p style="color:#64748b">None yet.</p>';
  let h='<table><thead><tr><th>ID</th><th>Subject</th><th>Status</th><th>Created</th>'+(isEsc?'<th>Transcript</th><th></th>':'<th>Description</th>')+'</tr></thead><tbody>';
  for(const r of rows){
    const badge=r.status==='open'?'open':'resolved';
    const tLines=(r.transcript||[]).map(m=>`<span class="line"><span class="${m.role==='user'?'u':'a'}">${m.role==='user'?'Customer':'Nobuk Agent'}:</span> ${m.text}</span>`).join('');
  const repliesHtml=(r.replies||[]).map(rep=>`<span class="line"><span style="color:#16a34a;font-weight:600">Support team:</span> ${rep.message}</span>`).join('');
  const extra=isEsc?`<td><div class="transcript">${tLines}${repliesHtml?'<hr style="border:0;border-top:1px dashed #cbd5e1;margin:.3rem 0">'+repliesHtml:''}</div><div style="margin-top:.4rem;display:flex;gap:.3rem"><input id="reply-${r.id}" placeholder="Reply to customer..." style="flex:1;padding:.3rem;border:1px solid #cbd5e1;border-radius:6px;font-size:.75rem"><button class="resolve" onclick="replyTicket('${r.id}')">Send reply</button></div></td><td>${r.status==='open'?`<button class="resolve" onclick="resolve('${r.id}')">Resolve</button>`:''}</td>`:`<td>${r.description||''}</td>`;
    h+=`<tr><td>${r.id}</td><td>${r.subject||r.reason||''}</td><td><span class="badge ${badge}">${r.status}</span></td><td>${(r.created_at||'').slice(0,16)}</td>${extra}</tr>`;
  }
  return h+'</tbody></table>';
}
async function resolve(id){await fetch('/api/escalations/'+id+'/resolve?key='+KEY,{method:'POST'});load();}
async function replyTicket(id){const inp=document.getElementById('reply-'+id);const msg=inp.value.trim();if(!msg)return;await fetch('/api/escalations/'+id+'/reply?key='+KEY,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:msg})});inp.value='';load();}
load();setInterval(load,8000);
</script></body></html>"""


@app.get("/", response_class=HTMLResponse)
def index():
    return CHAT_PAGE


ADMIN_PIN = os.getenv("ADMIN_PIN", "nobuk2026")


@app.get("/admin", response_class=HTMLResponse)
def admin(request: Request):
    if request.query_params.get("key") != ADMIN_PIN:
        return HTMLResponse("""<!doctype html><html><head><title>Admin Login</title>
<style>body{font-family:system-ui;display:grid;place-items:center;height:100vh;margin:0;background:#f1f5f9}
form{background:#fff;padding:2rem;border-radius:12px;box-shadow:0 4px 16px rgba(0,0,0,.08);text-align:center}
input{padding:.6rem;border:1px solid #cbd5e1;border-radius:8px;margin:.5rem 0;width:200px}
button{background:#2fb5b0;color:#fff;border:0;border-radius:8px;padding:.6rem 1.2rem;cursor:pointer;font-weight:600}
h2{margin:0 0 .5rem}</style></head><body>
<form onsubmit="location.href='/admin?key='+encodeURIComponent(document.getElementById('p').value);return false">
<h2>Admin Access</h2><p style="color:#64748b;font-size:.85rem">Enter PIN to continue</p>
<input id="p" type="password" placeholder="PIN" autofocus><br>
<button type="submit">Unlock</button></form></body></html>""")
    return ADMIN_PAGE
