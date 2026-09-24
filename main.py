import sqlite3
import asyncio
import httpx
import time
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

app = FastAPI(title="PingGuard Enterprise")
DB_NAME = "database.db"
live_logs = ["[SYSTEM] Enterprise Engine Initialized... Ready."]

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
        <div class="job-card">
            <div class="job-info">
                <div class="job-header">
                    <h4>{r[1]}</h4>
                    <div class="status-badge"><span class="pulse-dot"></span>{r[4].upper()}</div>
                </div>
                <a href="{r[2]}" target="_blank" class="job-url">{r[2]}</a>
                <div class="job-meta">Check Interval: {r[3]} mins</div>
            </div>
            <button class="btn-icon" onclick="delJob({r[0]})" title="Delete Monitor">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
            </button>
        </div>
        """
    
    if not jobs_list:
        jobs_list = """
        <div class="empty-state">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>
            <p>No servers added yet. Add a URL below to start monitoring.</p>
        </div>
        """

    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>PingGuard | Enterprise Uptime</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
        
        <!-- ADSTERRA AD CODE YAHAN PASTE KAREIN -->
        
        <style>
            :root {
                --bg: #050505;
                --card-bg: rgba(255, 255, 255, 0.03);
                --border: rgba(255, 255, 255, 0.08);
                --text: #ededed;
                --text-muted: #888;
                --primary: #00f2fe;
                --primary-dark: #4facfe;
                --danger: #ff4757;
            }
            body {
                background-color: var(--bg);
                background-image: radial-gradient(circle at top left, rgba(79, 172, 254, 0.1), transparent 40%),
                                  radial-gradient(circle at bottom right, rgba(0, 242, 254, 0.05), transparent 40%);
                color: var(--text);
                font-family: 'Inter', sans-serif;
                margin: 0; padding: 40px 20px;
                min-height: 100vh; display: flex; flex-direction: column; align-items: center;
            }
            .container { width: 100%; max-width: 800px; z-index: 10; }
            .header { text-align: center; margin-bottom: 40px; }
            .header h1 { font-size: 42px; font-weight: 700; margin: 0; background: linear-gradient(to right, #fff, #888); -webkit-background-clip: text; -webkit-text-fill-color: transparent; letter-spacing: -1px; }
            .header p { color: var(--text-muted); font-size: 16px; margin-top: 8px; }
            
            .glass-panel {
                background: var(--card-bg); border: 1px solid var(--border);
                backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px);
                border-radius: 16px; padding: 30px; margin-bottom: 30px;
                box-shadow: 0 4px 30px rgba(0, 0, 0, 0.1);
            }
            .glass-panel h3 { margin-top: 0; font-size: 18px; font-weight: 600; margin-bottom: 20px; color: #fff; display: flex; align-items: center; gap: 8px; }
            
            .input-group { margin-bottom: 15px; }
            input {
                width: 100%; padding: 14px 16px; background: rgba(0,0,0,0.4);
                border: 1px solid var(--border); border-radius: 10px;
                color: #fff; font-family: 'Inter', sans-serif; font-size: 14px;
                box-sizing: border-box; outline: none; transition: 0.3s ease;
            }
            input:focus { border-color: var(--primary-dark); box-shadow: 0 0 0 4px rgba(79, 172, 254, 0.1); }
            
            .btn-glow {
                width: 100%; padding: 14px; border: none; border-radius: 10px;
                background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
                color: #000; font-weight: 700; font-size: 16px; font-family: 'Inter', sans-serif;
                cursor: pointer; transition: 0.3s ease; box-shadow: 0 10px 20px rgba(0, 242, 254, 0.2);
            }
            .btn-glow:hover { transform: translateY(-2px); box-shadow: 0 15px 25px rgba(0, 242, 254, 0.4); }
            
            .job-card {
                background: rgba(0,0,0,0.3); border: 1px solid var(--border);
                border-radius: 12px; padding: 20px; margin-bottom: 15px;
                display: flex; justify-content: space-between; align-items: center;
                transition: 0.3s ease;
            }
            .job-card:hover { border-color: rgba(255,255,255,0.2); background: rgba(255,255,255,0.05); }
            .job-header { display: flex; align-items: center; gap: 15px; margin-bottom: 6px; }
            .job-header h4 { margin: 0; font-size: 16px; font-weight: 600; color: #fff; }
            .job-url { color: var(--primary); text-decoration: none; font-size: 14px; transition: 0.2s; }
            .job-url:hover { text-decoration: underline; }
            .job-meta { color: var(--text-muted); font-size: 12px; margin-top: 8px; }
            
            .status-badge {
                display: inline-flex; align-items: center; gap: 6px;
                background: rgba(46, 213, 115, 0.1); color: #2ed573;
                padding: 4px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; letter-spacing: 0.5px;
            }
            .pulse-dot { width: 8px; height: 8px; background-color: #2ed573; border-radius: 50%; display: inline-block; animation: pulse 2s infinite; }
            @keyframes pulse { 0% { box-shadow: 0 0 0 0 rgba(46, 213, 115, 0.4); } 70% { box-shadow: 0 0 0 6px rgba(46, 213, 115, 0); } 100% { box-shadow: 0 0 0 0 rgba(46, 213, 115, 0); } }
            
            .btn-icon { background: rgba(255, 71, 87, 0.1); color: var(--danger); border: 1px solid rgba(255, 71, 87, 0.2); width: 40px; height: 40px; border-radius: 10px; display: flex; align-items: center; justify-content: center; cursor: pointer; transition: 0.3s; }
            .btn-icon:hover { background: var(--danger); color: #fff; transform: scale(1.05); }
            .btn-icon svg { width: 18px; height: 18px; }
            
            .log-box { background: rgba(0,0,0,0.6); color: #00ff00; padding: 20px; height: 180px; overflow-y: auto; font-family: 'Courier New', monospace; font-size: 13px; border-radius: 12px; border: 1px solid rgba(0, 255, 0, 0.1); line-height: 1.5; }
            
            .empty-state { text-align: center; padding: 30px; color: var(--text-muted); }
            .empty-state svg { width: 48px; height: 48px; opacity: 0.5; margin-bottom: 10px; }
            
            .footer { text-align: center; margin-top: 20px; }
            .upi-support { display: inline-flex; align-items: center; gap: 8px; background: rgba(255,255,255,0.05); border: 1px solid var(--border); color: #fff; padding: 12px 24px; border-radius: 30px; text-decoration: none; font-weight: 500; font-size: 14px; transition: 0.3s; }
            .upi-support:hover { background: rgba(255,255,255,0.1); transform: translateY(-2px); }
            
            /* Custom Scrollbar for Logs */
            ::-webkit-scrollbar { width: 8px; }
            ::-webkit-scrollbar-track { background: rgba(0,0,0,0.2); border-radius: 10px; }
            ::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.2); border-radius: 10px; }
            ::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.4); }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>PingGuard</h1>
                <p>Enterprise-Grade 24/7 Server Uptime Monitor</p>
            </div>
            
            <div class="glass-panel">
                <h3>
                    <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="16"></line><line x1="8" y1="12" x2="16" y2="12"></line></svg>
                    Deploy New Monitor
                </h3>
                <form id="form">
                    <div class="input-group">
                        <input type="text" id="label" placeholder="Project Name (e.g., AI Discord Bot)" required autocomplete="off">
                    </div>
                    <div class="input-group">
                        <input type="url" id="url" placeholder="https://your-project.onrender.com" required autocomplete="off">
                    </div>
                    <div class="input-group">
                        <input type="number" id="interval" value="5" min="1" max="60" placeholder="Check Interval (Minutes)" required>
                    </div>
                    <button type="submit" class="btn-glow">Initialize Monitor</button>
                </form>
            </div>

            <div class="glass-panel">
                <h3>
                    <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline></svg>
                    Active Infrastructures
                </h3>
                <div id="jobs">REPLACE_JOBS_HTML</div>
            </div>

            <div class="glass-panel">
                <h3>
                    <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 17l6-6-2-5-6 1 1 5-3 5"></path><path d="M12 22v-4"></path><path d="M20 17l-6-6 2-5 6 1-1 5 3 5"></path></svg>
                    System Terminal
                </h3>
                <div id="logs" class="log-box">Awaiting connection...</div>
            </div>

            <div class="footer">
                <a href="upi://pay?pa=YOUR_UPI_ID_HERE@okicici&pn=PingGuard&cu=INR" class="upi-support">
                    <span>☕</span> Buy me a coffee via UPI
                </a>
                <p style="color: var(--text-muted); font-size: 12px; margin-top: 15px;">Powered by PingGuard Enterprise</p>
            </div>
        </div>

        <script>
            document.getElementById('form').onsubmit = async (e) => {
                e.preventDefault();
                const btn = e.target.querySelector('button');
                btn.innerText = "Deploying...";
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
                else { alert(data.msg); btn.innerText = "Initialize Monitor"; }
            };
            async function delJob(id) { 
                if(confirm("Stop monitoring this server?")) {
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
    log_msg(f"Started monitoring node: {job.label}")
    return {"status": "ok"}

@app.post("/del/{jid}")
def del_job(jid: int):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM jobs WHERE id = ?", (jid,))
    conn.commit()
    conn.close()
    log_msg(f"Terminated monitor ID: {jid}")
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
                            log_msg(f"Ping [{label}] STATUS: {r.status_code}")
                        except Exception as ex:
                            log_msg(f"Ping [{label}] STATUS: OFFLINE (Timeout)")
        except Exception:
            pass

@app.on_event("startup")
def startup():
    asyncio.create_task(pinger())
