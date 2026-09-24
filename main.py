import sqlite3
import asyncio
import httpx
import time
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

app = FastAPI(title="PingGuard Pro")
DB_NAME = "database.db"
live_logs = ["[SYSTEM] PingGuard Pro Engine Initialized..."]

def log_msg(text):
    live_logs.append(f"[{time.strftime('%H:%M:%S')}] {text}")
    if len(live_logs) > 50: live_logs.pop(0)

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS jobs (id INTEGER PRIMARY KEY AUTOINCREMENT, label TEXT, url TEXT, interval INTEGER, status TEXT DEFAULT 'Active')''')
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
        <div class="server-item">
            <div class="server-info">
                <div style="display:flex; align-items:center; gap:10px;">
                    <h4>{r[1]}</h4>
                    <span class="badge">{r[4]}</span>
                </div>
                <a href="{r[2]}" target="_blank">{r[2]}</a>
                <p>Check Interval: {r[3]} minutes</p>
            </div>
            <button class="btn-delete" onclick="delJob({r[0]})">Delete</button>
        </div>
        """
    
    if not jobs_list:
        jobs_list = """
        <div style="text-align:center; padding: 40px 20px; color: #6b7280;">
            <p>No servers added yet. Add your first URL below.</p>
        </div>
        """

    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>PingGuard | Uptime Monitor</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
        
        <!-- ADSTERRA AD CODE YAHAN PASTE KAREIN -->
        
        <style>
            body { background-color: #f3f4f6; color: #1f2937; font-family: 'Inter', sans-serif; margin: 0; padding: 0; }
            
            /* Navbar */
            .navbar { background: white; padding: 16px 32px; border-bottom: 1px solid #e5e7eb; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 1px 2px rgba(0,0,0,0.05); }
            .navbar-brand { font-size: 22px; font-weight: 700; color: #111827; letter-spacing: -0.5px; }
            .navbar-brand span { color: #2563eb; }
            
            /* Container */
            .container { max-width: 850px; margin: 40px auto; padding: 0 20px; }
            
            /* Cards */
            .card { background: white; border-radius: 12px; padding: 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.1), 0 1px 2px rgba(0,0,0,0.06); border: 1px solid #e5e7eb; margin-bottom: 24px; }
            .card-title { font-size: 18px; font-weight: 600; margin-top: 0; border-bottom: 1px solid #f3f4f6; padding-bottom: 12px; margin-bottom: 20px; color: #111827; }
            
            /* Form Elements */
            .form-group { margin-bottom: 16px; }
            label { display: block; font-size: 14px; font-weight: 500; margin-bottom: 6px; color: #374151; }
            input { width: 100%; padding: 12px 14px; border: 1px solid #d1d5db; border-radius: 8px; font-size: 14px; box-sizing: border-box; font-family: 'Inter', sans-serif; transition: all 0.2s; }
            input:focus { outline: none; border-color: #3b82f6; box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.1); }
            
            /* Buttons */
            .btn { background: #2563eb; color: white; border: none; padding: 12px 20px; border-radius: 8px; font-weight: 600; font-size: 14px; cursor: pointer; width: 100%; transition: background 0.2s; box-shadow: 0 1px 2px rgba(0,0,0,0.05); }
            .btn:hover { background: #1d4ed8; }
            
            /* Server List Items */
            .server-item { display: flex; justify-content: space-between; align-items: center; padding: 16px; border: 1px solid #e5e7eb; border-radius: 8px; margin-bottom: 12px; transition: all 0.2s; }
            .server-item:hover { border-color: #d1d5db; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
            .server-info h4 { margin: 0 0 4px 0; font-size: 16px; font-weight: 600; color: #111827; }
            .server-info a { color: #2563eb; text-decoration: none; font-size: 14px; font-weight: 500; }
            .server-info a:hover { text-decoration: underline; }
            .server-info p { margin: 6px 0 0 0; font-size: 13px; color: #6b7280; }
            
            .badge { background: #dcfce7; color: #166534; padding: 4px 10px; border-radius: 20px; font-size: 12px; font-weight: 600; }
            
            .btn-delete { background: #fee2e2; color: #991b1b; padding: 8px 16px; border: none; border-radius: 6px; cursor: pointer; font-size: 13px; font-weight: 600; transition: 0.2s; }
            .btn-delete:hover { background: #fca5a5; }
            
            /* Terminal/Logs */
            .logs { background: #111827; color: #10b981; padding: 16px; border-radius: 8px; font-family: 'Courier New', monospace; font-size: 13px; height: 160px; overflow-y: auto; line-height: 1.6; border: 1px solid #374151; }
            
            /* Footer */
            .footer { text-align: center; margin-top: 40px; margin-bottom: 40px; }
            .upi-btn { display: inline-block; background: white; color: #111827; border: 1px solid #d1d5db; padding: 10px 20px; border-radius: 8px; text-decoration: none; font-weight: 600; font-size: 14px; box-shadow: 0 1px 2px rgba(0,0,0,0.05); transition: 0.2s; }
            .upi-btn:hover { background: #f9fafb; border-color: #9ca3af; }
        </style>
    </head>
    <body>
        
        <div class="navbar">
            <div class="navbar-brand">Ping<span>Guard</span></div>
            <div style="font-size: 14px; color: #6b7280; font-weight: 500;">Free Uptime Monitor</div>
        </div>

        <div class="container">
            
            <div class="card">
                <h3 class="card-title">Add Server to Monitor</h3>
                <form id="form">
                    <div class="form-group">
                        <label for="label">Project Name</label>
                        <input type="text" id="label" placeholder="e.g., Discord Bot API" required autocomplete="off">
                    </div>
                    <div class="form-group">
                        <label for="url">Project URL</label>
                        <input type="url" id="url" placeholder="https://your-project.onrender.com" required autocomplete="off">
                    </div>
                    <div class="form-group">
                        <label for="interval">Check Interval (Minutes)</label>
                        <input type="number" id="interval" value="5" min="1" max="60" required>
                    </div>
                    <button type="submit" class="btn" id="submitBtn">Start Monitoring</button>
                </form>
            </div>

            <div class="card">
                <h3 class="card-title">Active Servers</h3>
                <div id="jobs">REPLACE_JOBS_HTML</div>
            </div>

            <div class="card">
                <h3 class="card-title">System Logs</h3>
                <div id="logs" class="logs">Loading logs...</div>
            </div>

            <div class="footer">
                <p style="color: #6b7280; font-size: 14px; margin-bottom: 12px;">Supported entirely by community donations.</p>
                <a href="upi://pay?pa=YOUR_UPI_ID_HERE@okicici&pn=PingGuard&cu=INR" class="upi-btn">☕ Support via UPI</a>
            </div>

        </div>

        <script>
            document.getElementById('form').onsubmit = async (e) => {
                e.preventDefault();
                const btn = document.getElementById('submitBtn');
                btn.innerText = "Adding...";
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
                else { alert(data.msg); btn.innerText = "Start Monitoring"; }
            };
            
            async function delJob(id) { 
                if(confirm("Are you sure you want to delete this monitor?")) {
                    await fetch('/del/' + id, { method: 'POST' }); 
                    location.reload(); 
                }
            }
            
            setInterval(async () => {
                let res = await fetch('/logs');
                let data = await res.json();
                let logsBox = document.getElementById('logs');
                let isScrolledToBottom = logsBox.scrollHeight - logsBox.clientHeight <= logsBox.scrollTop + 1;
                logsBox.innerText = data.logs.join('\\n');
                if (isScrolledToBottom) {
                    logsBox.scrollTop = logsBox.scrollHeight;
                }
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
    log_msg(f"Deleted monitor ID: {jid}")
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
                            log_msg(f"Ping [{label}] STATUS: {r.status_code} OK")
                        except Exception as ex:
                            log_msg(f"Ping [{label}] STATUS: Failed")
        except Exception:
            pass

@app.on_event("startup")
def startup():
    asyncio.create_task(pinger())
