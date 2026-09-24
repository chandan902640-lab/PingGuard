import sqlite3
import asyncio
import httpx
import time
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

app = FastAPI(title="PingGuard White Glass")
DB_NAME = "database.db"
live_logs = ["[SYSTEM] PingGuard White Glass Engine Initialized..."]

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
        <div class="glass-item server-item">
            <div>
                <h4>{r[1]}</h4>
                <a href="{r[2]}" target="_blank">{r[2]}</a>
                <p>Interval: {r[3]} mins | Status: <span style="color: #059669; font-weight: 700;">{r[4]}</span></p>
            </div>
            <button class="delete-btn" onclick="delJob({r[0]})">Delete</button>
        </div>
        """
    
    if not jobs_list:
        jobs_list = "<div class='empty-state'><p>Abhi koi server added nahi hai. 'Deploy New' me jaakar URL add karein!</p></div>"

    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>PingGuard | White Frosted Glass</title>
        <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap" rel="stylesheet">
        
        <style>
            body { 
                background: #f1f5f9; /* Off-white / light slate base */
                color: #1e293b; 
                font-family: 'Poppins', sans-serif; 
                margin: 0; padding: 0; 
                display: flex; height: 100vh; overflow: hidden;
                position: relative;
            }
            
            /* Light Pastel Floating Blobs for Glass Blur Effect */
            .blob-1 {
                position: absolute; top: -10%; left: -10%; width: 500px; height: 500px;
                background: #bae6fd; /* Light Blue */ 
                border-radius: 50%; filter: blur(80px); opacity: 0.8; z-index: -1;
                animation: float1 15s infinite alternate ease-in-out;
            }
            .blob-2 {
                position: absolute; bottom: -20%; right: -10%; width: 600px; height: 600px;
                background: #e9d5ff; /* Light Purple/Pink */
                border-radius: 50%; filter: blur(100px); opacity: 0.7; z-index: -1;
                animation: float2 18s infinite alternate ease-in-out;
            }
            .blob-3 {
                position: absolute; top: 30%; left: 30%; width: 400px; height: 400px;
                background: #fef08a; /* Light Yellow */
                border-radius: 50%; filter: blur(90px); opacity: 0.6; z-index: -1;
                animation: float3 20s infinite alternate ease-in-out;
            }
            
            @keyframes float1 { 0% { transform: translate(0, 0); } 100% { transform: translate(100px, 100px); } }
            @keyframes float2 { 0% { transform: translate(0, 0); } 100% { transform: translate(-150px, -100px); } }
            @keyframes float3 { 0% { transform: translate(0, 0) scale(1); } 100% { transform: translate(100px, -50px) scale(1.2); } }

            /* TRUE White Glassmorphism */
            .glass-panel {
                background: rgba(255, 255, 255, 0.65) !important;
                backdrop-filter: blur(24px) saturate(120%) !important;
                -webkit-backdrop-filter: blur(24px) saturate(120%) !important;
                border: 1px solid rgba(255, 255, 255, 0.9) !important;
                box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.05) !important;
            }
            
            /* Left Sidebar */
            .sidebar {
                width: 250px;
                padding: 30px 20px;
                display: flex; flex-direction: column;
                z-index: 10;
                border-right: 1px solid rgba(255, 255, 255, 0.6);
            }
            
            .brand {
                font-size: 28px; font-weight: 700; color: #0f172a;
                text-align: center; margin-bottom: 40px;
            }
            .brand span { color: #3b82f6; }
            
            /* Sidebar Buttons */
            .menu-btn {
                background: rgba(255, 255, 255, 0.4); color: #334155;
                border: 1px solid rgba(255, 255, 255, 0.8);
                border-radius: 12px;
                padding: 15px 20px; margin-bottom: 15px;
                font-size: 15px; font-weight: 600; font-family: 'Poppins', sans-serif;
                text-align: left; cursor: pointer; transition: all 0.3s ease;
                display: flex; align-items: center; gap: 10px;
                box-shadow: 0 2px 5px rgba(0,0,0,0.02);
            }
            
            .menu-btn:hover {
                background: rgba(255, 255, 255, 0.8);
                transform: translateX(5px);
            }
            
            .menu-btn.active {
                background: #ffffff;
                color: #2563eb;
                border: 1px solid #ffffff;
                box-shadow: 0 5px 15px rgba(37, 99, 235, 0.1);
            }
            
            /* Main Content Area */
            .main-content {
                flex: 1; padding: 40px; overflow-y: auto; z-index: 10;
            }
            
            .content-section { display: none; animation: fadeIn 0.4s ease; }
            .content-section.active { display: block; }
            @keyframes fadeIn { from { opacity: 0; transform: scale(0.98); } to { opacity: 1; transform: scale(1); } }
            
            h2 { font-size: 26px; font-weight: 600; margin-top: 0; margin-bottom: 25px; color: #0f172a; border-bottom: 1px solid rgba(0,0,0,0.05); padding-bottom: 15px;}
            
            /* Main Cards */
            .glass-card {
                border-radius: 24px; padding: 35px; margin-bottom: 25px;
            }
            
            /* Input Fields */
            .input-group { margin-bottom: 20px; }
            input {
                width: 100%; padding: 15px 20px; 
                border-radius: 12px; 
                border: 1px solid rgba(255, 255, 255, 0.9);
                background: rgba(255, 255, 255, 0.5);
                color: #0f172a; font-family: 'Poppins', sans-serif; font-size: 15px;
                box-sizing: border-box; outline: none; transition: 0.3s;
                box-shadow: inset 0 2px 4px rgba(0,0,0,0.02);
            }
            input::placeholder { color: #94a3b8; }
            input:focus { 
                background: rgba(255, 255, 255, 0.9); 
                border-color: #3b82f6;
                box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.1);
            }
            
            /* Main Buttons */
            .glass-btn {
                width: 100%; padding: 16px; border: none; border-radius: 12px;
                background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
                color: #ffffff; font-weight: 600; font-size: 16px; font-family: 'Poppins', sans-serif;
                box-shadow: 0 10px 20px rgba(37, 99, 235, 0.2);
                cursor: pointer; transition: 0.3s;
            }
            .glass-btn:hover { 
                transform: translateY(-2px); 
                box-shadow: 0 15px 25px rgba(37, 99, 235, 0.3); 
            }
            
            /* Individual Server Items */
            .glass-item {
                background: rgba(255, 255, 255, 0.6);
                border: 1px solid rgba(255, 255, 255, 0.9);
                border-radius: 16px;
                display: flex; justify-content: space-between; align-items: center; padding: 20px;
                margin-bottom: 15px; transition: 0.3s;
                box-shadow: 0 4px 6px rgba(0,0,0,0.02);
            }
            .glass-item:hover { background: #ffffff; transform: translateY(-2px); box-shadow: 0 8px 15px rgba(0,0,0,0.05); }
            
            .server-item h4 { margin: 0 0 5px 0; font-size: 18px; color: #0f172a; }
            .server-item a { color: #3b82f6; text-decoration: none; font-size: 15px; }
            .server-item a:hover { text-decoration: underline; }
            .server-item p { margin: 8px 0 0 0; font-size: 14px; color: #64748b; }
            
            .delete-btn {
                background: rgba(239, 68, 68, 0.1); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.2);
                padding: 10px 20px; font-size: 13px; font-weight: 600; border-radius: 8px; cursor: pointer; transition: 0.2s;
            }
            .delete-btn:hover { background: #ef4444; color: #fff; }
            
            .empty-state { text-align: center; padding: 40px; color: #64748b; font-weight: 500; }
            
            /* Terminal/Logs */
            .logs-container { 
                background: rgba(255, 255, 255, 0.7); 
                border: 1px solid rgba(255, 255, 255, 0.9);
                color: #059669; padding: 25px; height: 350px; overflow-y: auto; 
                border-radius: 16px; font-family: monospace; font-size: 14px; line-height: 1.6;
                box-shadow: inset 0 2px 10px rgba(0,0,0,0.02);
            }
            
            ::-webkit-scrollbar { width: 6px; }
            ::-webkit-scrollbar-track { background: transparent; }
            ::-webkit-scrollbar-thumb { background: rgba(0, 0, 0, 0.15); border-radius: 10px; }
            ::-webkit-scrollbar-thumb:hover { background: rgba(0, 0, 0, 0.3); }
        </style>
    </head>
    <body>
        
        <!-- Faint Animated Pastel Blobs for Glass Effect -->
        <div class="blob-1"></div>
        <div class="blob-2"></div>
        <div class="blob-3"></div>

        <div class="sidebar glass-panel">
            <div class="brand">Ping<span>Guard</span></div>
            
            <button class="menu-btn active" onclick="switchTab('dashboard', this)">
                🏠 Active Monitors
            </button>
            <button class="menu-btn" onclick="switchTab('deploy', this)">
                🚀 Deploy New
            </button>
            <button class="menu-btn" onclick="switchTab('logs', this)">
                💻 System Terminal
            </button>
        </div>

        <div class="main-content">
            
            <div id="dashboard" class="content-section active">
                <div class="glass-card glass-panel">
                    <h2>Active Infrastructures</h2>
                    <div id="jobs">REPLACE_JOBS_HTML</div>
                </div>
            </div>

            <div id="deploy" class="content-section">
                <div class="glass-card glass-panel" style="max-width: 600px; margin: 0 auto;">
                    <h2>Deploy Monitor Engine</h2>
                    <form id="form">
                        <div class="input-group">
                            <input type="text" id="label" placeholder="Project Name (e.g. API Server)" required autocomplete="off">
                        </div>
                        <div class="input-group">
                            <input type="url" id="url" placeholder="https://target-server.com" required autocomplete="off">
                        </div>
                        <div class="input-group">
                            <input type="number" id="interval" value="5" placeholder="Ping Interval (Mins)" required>
                        </div>
                        <button type="submit" class="glass-btn" id="submitBtn">Start Pinging</button>
                    </form>
                </div>
            </div>

            <div id="logs" class="content-section">
                <div class="glass-card glass-panel">
                    <h2>Live Server Logs</h2>
                    <div id="logs-feed" class="logs-container">Awaiting connection...</div>
                </div>
            </div>

        </div>

        <script>
            function switchTab(tabId, btnElement) {
                document.querySelectorAll('.content-section').forEach(sec => sec.classList.remove('active'));
                document.querySelectorAll('.menu-btn').forEach(btn => btn.classList.remove('active'));
                
                document.getElementById(tabId).classList.add('active');
                btnElement.classList.add('active');
            }

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
                let logsBox = document.getElementById('logs-feed');
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
