import sqlite3
import asyncio
import httpx
import time
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

app = FastAPI(title="PingGuard Live")
DB_NAME = "database.db"
live_logs = ["[SYSTEM] PingGuard Engine started successfully."]

def log_msg(text):
    live_logs.append(f"[{time.strftime('%H:%M:%S')}] {text}")
    if len(live_logs) > 50: live_logs.pop(0)

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS jobs (id INTEGER PRIMARY KEY AUTOINCREMENT, label TEXT, url TEXT, interval INTEGER, status TEXT DEFAULT 'active')''')
    conn.commit()
    conn.close()

init_db()

class Job(BaseModel):
    label: str
    url: str
    interval: int

@app.get("/", response_class=HTMLResponse)
def read_root():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, label, url, interval, status FROM jobs")
    rows = cursor.fetchall()
    conn.close()
    
    jobs_list = ""
    for r in rows:
        jobs_list += f"""
        <div style="background:#111; border:1px solid #0ff; padding:12px; margin-bottom:10px; border-radius:6px; display:flex; justify-content:space-between; align-items:center;">
            <div>
                <b style="color:#fff; font-size:15px;">{r[1]}</b><br>
                <a href="{r[2]}" target="_blank" style="color:#0ff; font-size:13px; text-decoration:none;">{r[2]}</a>
                <div style="font-size:11px; color:#888; margin-top:3px;">Interval: {r[3]} mins | Status: <span style="color:#0f0;">{r[4]}</span></div>
            </div>
            <button onclick="delJob({r[0]})" style="background:#d9534f; color:white; border:none; padding:6px 12px; border-radius:4px; cursor:pointer;">Delete</button>
        </div>
        """
    
    if not jobs_list:
        jobs_list = "<p style='color:#777; text-align:center;'>Abhi koi server added nahi hai. Apna URL niche dalein!</p>"

    # HTML without f-string prefix to avoid format errors
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>PingGuard - Keep Servers Awake 24/7</title>
        
        <!-- ADSTERRA AD CODE YAHAN PASTE KAREIN (Baad mein) -->
        
        <style>
            body { background: #050505; color: #0ff; font-family: monospace; padding: 20px; max-width: 750px; margin: auto; }
            input, button { background: #111; color: #0ff; border: 1px solid #0ff; padding: 10px; margin: 6px 0; width: 100%; box-sizing: border-box; border-radius: 4px; font-family: monospace; }
            .btn-deploy { background: #0ff; color: #000; font-weight: bold; cursor: pointer; transition: 0.2s; }
            .btn-deploy:hover { background: #0cc; }
            .box { border: 1px solid #0ff; padding: 18px; margin-bottom: 20px; border-radius: 8px; background: #0a0a0a; }
        </style>
    </head>
    <body>
        <h1 style="color:#0f0; text-align:center;">🛡️ PingGuard</h1>
        <p style="color:#aaa; text-align:center;">Free 24/7 Uptime Monitor for Render, Heroku & Bots</p>
        
        <div class="box">
            <h3 style="margin-top:0; color:#fff;">Add Server to Monitor</h3>
            <form id="form">
                <input type="text" id="label" placeholder="Project Name (e.g. My Discord Bot)" required>
                <input type="url" id="url" placeholder="https://your-project.onrender.com" required>
                <input type="number" id="interval" value="5" placeholder="Check Interval (mins)" required>
                <button type="submit" class="btn-deploy">Start Pinging</button>
            </form>
        </div>

        <div class="box">
            <h3 style="margin-top:0; color:#fff;">Active Servers</h3>
            <div id="jobs">REPLACE_JOBS_HTML</div>
        </div>

        <div class="box">
            <h3 style="margin-top:0; color:#fff;">Live System Logs</h3>
            <div id="logs" style="background:#000; color:#0f0; padding:12px; height:140px; overflow-y:auto; font-size:12px; border-radius:4px;">Loading logs...</div>
        </div>

        <!-- UPI SUPPORT BUTTON -->
        <div style="text-align: center; margin-top: 30px; margin-bottom: 20px;">
            <p style="color:#888; font-size:12px;">This tool runs on free servers. If it helps you, consider buying me a coffee!</p>
            <a href="upi://pay?pa=YOUR_UPI_ID_HERE@okicici&pn=PingGuard&cu=INR" style="background:#0f0; color:#000; padding:10px 20px; text-decoration:none; border-radius:5px; font-weight:bold; display:inline-block;">☕ Support via UPI</a>
        </div>

        <script>
            document.getElementById('form').onsubmit = async (e) => {
                e.preventDefault();
                let res = await fetch('/add', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        label: document.getElementById('label').value,
                        url: document.getElementById('url').value,
                        interval: parseInt(document.getElementById('interval').value)
                    })
                });
                let data = await res.json();
                if(data.status === 'ok') { location.reload(); }
                else { alert(data.msg); }
            };
            async function delJob(id) { await fetch('/del/' + id, { method: 'POST' }); location.reload(); }
            setInterval(async () => {
                let res = await fetch('/logs');
                let data = await res.json();
                document.getElementById('logs').innerText = data.logs.join('\\n');
            }, 3000);
        </script>
    </body>
    </html>
    """
    return html.replace("REPLACE_JOBS_HTML", jobs_list)

@app.post("/add")
def add_job(job: Job):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO jobs (label, url, interval) VALUES (?, ?, ?)", (job.label, job.url, job.interval))
    conn.commit()
    conn.close()
    log_msg(f"Started monitoring: {job.label}")
    return {"status": "ok"}

@app.post("/del/{jid}")
def del_job(jid: int):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM jobs WHERE id = ?", (jid,))
    conn.commit()
    conn.close()
    log_msg(f"Stopped monitor ID: {jid}")
    return {"status": "ok"}

@app.get("/logs")
def get_logs():
    return {"logs": live_logs}

async def pinger():
    while True:
        await asyncio.sleep(60)
        try:
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("SELECT label, url FROM jobs")
            rows = cursor.fetchall()
            conn.close()
            if rows:
                async with httpx.AsyncClient(timeout=10) as client:
                    for label, url in rows:
                        try:
                            r = await client.get(url)
                            log_msg(f"Ping [{label}]: {r.status_code}")
                        except Exception as ex:
                            log_msg(f"Ping [{label}]: Failed")
        except Exception:
            pass

@app.on_event("startup")
def startup():
    asyncio.create_task(pinger())
