import sqlite3
import asyncio
import httpx
import time
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

app = FastAPI(title="PingGuard 3D Glass")
DB_NAME = "database.db"
live_logs = ["[SYSTEM] PingGuard Glass Engine Initialized..."]

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
        <div class="glass-card server-item">
            <div>
                <h4>{r[1]}</h4>
                <a href="{r[2]}" target="_blank">{r[2]}</a>
                <p>Interval: {r[3]} mins | Status: <span style="color: #27ae60; font-weight: bold;">{r[4]}</span></p>
            </div>
            <button class="glass-btn delete-btn" onclick="delJob({r[0]})">Delete</button>
        </div>
        """
    
    if not jobs_list:
        jobs_list = "<p style='text-align:center; color:#7f8c8d; padding:20px;'>Abhi koi server added nahi hai. Apna URL add karein!</p>"

    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>PingGuard | 3D Glass UI</title>
        <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600&display=swap" rel="stylesheet">
        
        <style>
            body { 
                background: #e0e5ec; /* Light gray background matching your Spline image */
                color: #2c3e50; 
                font-family: 'Poppins', sans-serif; 
                margin: 0; padding: 30px 15px; 
                display: flex; flex-direction: column; align-items: center;
            }
            .container { max-width: 800px; width: 100%; }
            
            /* The 3D Glass / Neumorphism Effect for Cards */
            .glass-card {
                background: rgba(224, 229, 236, 0.4);
                backdrop-filter: blur(15px);
                -webkit-backdrop-filter: blur(15px);
                border: 1px solid rgba(255, 255, 255, 0.6);
                border-radius: 20px;
                padding: 25px;
                margin-bottom: 25px;
                box-shadow: 9px 9px 16px rgb(163,177,198,0.6), -9px -9px 16px rgba(255,255,255, 0.8);
            }
            
            /* Pill Navigation Buttons (Like your screenshot) */
            .nav-container { display: flex; gap: 15px; justify-content: center; margin-bottom: 30px; flex-wrap: wrap; }
            .glass-pill {
                padding: 12px 30px;
                border-radius: 30px;
                background: #e0e5ec;
                color: #34495e;
                font-weight: 600;
                font-size: 15px;
                border: 1px solid rgba(255,255,255,0.4);
                box-shadow: 6px 6px 12px #babecc, -6px -6px 12px #ffffff;
                cursor: pointer; transition: all 0.2s ease;
                display: flex; align-items: center; gap: 8px;
            }
            .glass-pill:hover { 
                box-shadow: 2px 2px 5px #babecc, -2px -2px 5px #ffffff; 
                transform: translateY(2px); 
            }
            .glass-pill.active {
                box-shadow: inset 4px 4px 8px #babecc, inset -4px -4px 8px #ffffff;
                color: #3498db;
            }
            
            h2 { margin-top: 0; font-weight: 600; color: #2c3e50; border-bottom: 2px solid rgba(255,255,255,0.5); padding-bottom: 10px; }
            
            /* Input Fields (Sunken 3D effect) */
            .input-group { margin-bottom: 15px; }
            input {
                width: 100%; padding: 14px; 
                border-radius: 12px;
                border: none;
                background: #e0e5ec;
                box-shadow: inset 5px 5px 10px #babecc, inset -5px -5px 10px #ffffff;
                color: #34495e; font-family: 'Poppins', sans-serif; font-size: 14px;
                box-sizing: border-box; outline: none; transition: 0.3s;
            }
            input:focus { box-shadow: inset 2px 2px 5px #babecc, inset -2px -2px 5px #ffffff; }
            
            /* Submit Button (Raised 3D effect) */
            .glass-btn {
                width: 100%; padding: 14px; border: none; border-radius: 12px;
                background: #3498db; color: white; font-weight: 600; font-size: 16px; font-family: 'Poppins', sans-serif;
                box-shadow: 5px 5px 10px #babecc, -5px -5px 10px #ffffff;
                cursor: pointer; transition: 0.2s;
            }
            .glass-btn:hover { 
                background: #2980b9; 
                transform: translateY(2px); 
                box-shadow: 2px 2px 5px #babecc, -2px -2px 5px #ffffff; 
            }
            
            .delete-btn { background: #e74c3c; width: auto; padding: 10px 20px; font-size: 13px; }
            .delete-btn:hover { background: #c0392b; }
            
            .server-item { display: flex; justify-content: space-between; align-items: center; padding: 20px; }
            .server-item h4 { margin: 0 0 5px 0; font-size: 16px; }
            .server-item a { color: #3498db; text-decoration: none; font-size: 14px; font-weight: 500;}
            .server-item a:hover { text-decoration: underline; }
            .server-item p { margin: 8px 0 0 0; font-size: 12px; color: #7f8c8d; }
            
            /* Terminal/Logs (Sunken 3D effect) */
            .logs { 
                background: #e0e5ec; 
                box-shadow: inset 5px 5px 10px #babecc, inset -5px -5px 10px #ffffff; 
                color: #27ae60; padding: 20px; height: 160px; overflow-y: auto; 
                border-radius: 12px; font-family: monospace; font-size: 13px; font-weight: 600; line-height: 1.6; 
            }
            
            /* Custom Scrollbar for logs */
            ::-webkit-scrollbar { width: 8px; }
            ::-webkit-scrollbar-track { background: transparent; }
            ::-webkit-scrollbar-thumb { background: #babecc; border-radius: 10px; }
        </style>
    </head>
    <body>
        
        <div class="container">
            <!-- 3D Glass Pill Navigation -->
            <div class="nav-container">
                <div class="glass-pill active">🏠 Dashboard</div>
                <div class="glass-pill">⚙️ Settings</div>
                <div class="glass-pill">📊 Analytics</div>
            </div>

            <div class="glass-card">
                <h2>Deploy Monitor</h2>
                <form id="form">
                    <div class="input-group">
                        <input type="text" id="label" placeholder="Project Name (e.g. My Bot)" required autocomplete="off">
                    </div>
                    <div class="input-group">
                        <input type="url" id="url" placeholder="https://your-project.onrender.com" required autocomplete="off">
                    </div>
                    <div class="input-group">
                        <input type="number" id="interval" value="5" placeholder="Check Interval (Mins)" required>
                    </div>
                    <button type="submit" class="glass-btn" id="submitBtn">Start Pinging</button>
                </form>
            </div>

            <div class="glass-card">
                <h2>Active Servers</h2>
                <div id="jobs">REPLACE_JOBS_HTML</div>
            </div>

            <div class="glass-card">
                <h2>Live Logs</h2>
                <div id="logs" class="logs">Loading logs...</div>
            </div>
        </div>

        <script>
            document.getElementById('form').onsubmit = async (e) => {
                e.preventDefault();
                const btn = document.getElementById('submitBtn');
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
                else { alert(data.msg); btn.innerText = "Start Pinging"; }
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
                if (isScrolledToBottom) { logsBox.scrollTop = logsBox.scrollHeight; }
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
                            log_msg(f"Ping [{label}] STATUS: Failed/Offline")
        except Exception:
            pass

@app.on_event("startup")
def startup():
    asyncio.create_task(pinger())
