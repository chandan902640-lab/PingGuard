import sqlite3
import asyncio
import httpx
import time
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

app = FastAPI(title="PingGuard Cyber-Glass")
DB_NAME = "database.db"
live_logs = ["[SYSTEM] PingGuard Cyber-Glass Engine Initialized..."]

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
                <p>Interval: {r[3]} mins | Status: <span style="color: #00ffcc; font-weight: bold; text-shadow: 0 0 5px #00ffcc;">{r[4]}</span></p>
            </div>
            <button class="neon-btn delete-btn" onclick="delJob({r[0]})">Delete</button>
        </div>
        """
    
    if not jobs_list:
        jobs_list = "<div class='empty-state'><p>No active monitors. Add a URL in the 'Deploy' tab.</p></div>"

    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>PingGuard | Cyber Glass UI</title>
        <link href="https://fonts.googleapis.com/css2?family=Rajdhani:wght@500;600;700&display=swap" rel="stylesheet">
        
        <style>
            :root {
                --bg-dark: #0a0e17;
                --glass-bg: rgba(16, 22, 37, 0.6);
                --glass-border: rgba(0, 255, 204, 0.2);
                --neon-cyan: #00ffcc;
                --neon-blue: #0088ff;
                --neon-red: #ff0055;
                --text-main: #e0f2fe;
                --text-muted: #8ba2b5;
            }
            
            body { 
                background-color: var(--bg-dark); 
                background-image: 
                    radial-gradient(circle at 15% 50%, rgba(0, 136, 255, 0.08), transparent 25%),
                    radial-gradient(circle at 85% 30%, rgba(0, 255, 204, 0.08), transparent 25%);
                color: var(--text-main); 
                font-family: 'Rajdhani', sans-serif; 
                margin: 0; padding: 0; 
                display: flex; height: 100vh; overflow: hidden;
            }
            
            /* Sidebar (Left Menu) */
            .sidebar {
                width: 250px;
                background: var(--glass-bg);
                backdrop-filter: blur(20px);
                border-right: 1px solid var(--glass-border);
                padding: 30px 20px;
                display: flex;
                flex-direction: column;
                box-shadow: 5px 0 25px rgba(0,0,0,0.5);
                z-index: 10;
            }
            
            .brand {
                font-size: 28px; font-weight: 700; color: #fff;
                text-align: center; margin-bottom: 40px; letter-spacing: 2px;
                text-shadow: 0 0 10px var(--neon-cyan);
            }
            .brand span { color: var(--neon-cyan); }
            
            .menu-btn {
                background: transparent; color: var(--text-muted);
                border: 1px solid transparent; border-radius: 8px;
                padding: 15px 20px; margin-bottom: 15px;
                font-size: 18px; font-weight: 600; font-family: 'Rajdhani', sans-serif;
                text-align: left; cursor: pointer; transition: all 0.3s;
                display: flex; align-items: center; gap: 10px;
            }
            
            .menu-btn:hover {
                background: rgba(0, 255, 204, 0.05); color: #fff;
                border: 1px solid var(--glass-border);
            }
            
            /* The Glowing Neon Active State */
            .menu-btn.active {
                background: rgba(0, 255, 204, 0.1);
                color: var(--neon-cyan);
                border: 1px solid var(--neon-cyan);
                box-shadow: 0 0 15px rgba(0, 255, 204, 0.3), inset 0 0 10px rgba(0, 255, 204, 0.2);
                text-shadow: 0 0 5px var(--neon-cyan);
            }
            
            /* Main Content Area */
            .main-content {
                flex: 1; padding: 40px; overflow-y: auto;
                position: relative;
            }
            
            /* Hide all sections by default, show only active */
            .content-section { display: none; animation: fadeIn 0.4s ease; }
            .content-section.active { display: block; }
            
            @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
            
            h2 { font-size: 24px; font-weight: 600; margin-top: 0; margin-bottom: 25px; border-bottom: 1px solid var(--glass-border); padding-bottom: 15px; color: #fff; }
            
            /* Glass Cards */
            .glass-card {
                background: var(--glass-bg);
                backdrop-filter: blur(15px);
                border: 1px solid var(--glass-border);
                border-radius: 12px; padding: 25px; margin-bottom: 25px;
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            }
            
            /* Form Inputs */
            .input-group { margin-bottom: 20px; }
            input {
                width: 100%; padding: 15px; 
                background: rgba(0,0,0,0.4);
                border: 1px solid rgba(255,255,255,0.1); border-radius: 8px;
                color: #fff; font-family: 'Rajdhani', sans-serif; font-size: 16px;
                box-sizing: border-box; outline: none; transition: 0.3s;
            }
            input:focus { border-color: var(--neon-blue); box-shadow: 0 0 10px rgba(0, 136, 255, 0.3); }
            
            /* Neon Buttons */
            .neon-btn {
                width: 100%; padding: 15px; border: 1px solid var(--neon-blue); border-radius: 8px;
                background: rgba(0, 136, 255, 0.1); color: var(--neon-blue);
                font-weight: 700; font-size: 18px; font-family: 'Rajdhani', sans-serif; letter-spacing: 1px;
                cursor: pointer; transition: 0.3s; text-transform: uppercase;
            }
            .neon-btn:hover { 
                background: var(--neon-blue); color: #fff;
                box-shadow: 0 0 20px rgba(0, 136, 255, 0.6); 
            }
            
            .delete-btn {
                width: auto; padding: 8px 15px; font-size: 14px;
                border-color: var(--neon-red); color: var(--neon-red); background: rgba(255, 0, 85, 0.1);
            }
            .delete-btn:hover { background: var(--neon-red); box-shadow: 0 0 15px rgba(255, 0, 85, 0.5); }
            
            .server-item { display: flex; justify-content: space-between; align-items: center; padding: 20px; }
            .server-item h4 { margin: 0 0 5px 0; font-size: 18px; color: #fff; }
            .server-item a { color: var(--neon-blue); text-decoration: none; font-size: 15px; }
            .server-item a:hover { text-shadow: 0 0 5px var(--neon-blue); }
            .server-item p { margin: 8px 0 0 0; font-size: 14px; color: var(--text-muted); }
            
            .empty-state { text-align: center; padding: 40px; color: var(--text-muted); border: 1px dashed var(--glass-border); border-radius: 12px; }
            
            /* Terminal/Logs */
            .logs-container { 
                background: rgba(0,0,0,0.7); border: 1px solid rgba(0, 255, 204, 0.3);
                color: var(--neon-cyan); padding: 20px; height: 300px; overflow-y: auto; 
                border-radius: 8px; font-family: 'Courier New', monospace; font-size: 14px; line-height: 1.6; 
                box-shadow: inset 0 0 20px rgba(0,0,0,0.8);
            }
            
            ::-webkit-scrollbar { width: 6px; }
            ::-webkit-scrollbar-track { background: rgba(0,0,0,0.3); }
            ::-webkit-scrollbar-thumb { background: var(--glass-border); border-radius: 10px; }
            ::-webkit-scrollbar-thumb:hover { background: var(--neon-cyan); }
        </style>
    </head>
    <body>
        
        <!-- Sidebar Menu -->
        <div class="sidebar">
            <div class="brand">Ping<span>Guard</span></div>
            
            <button class="menu-btn active" onclick="switchTab('dashboard', this)">
                ⚡ Active Monitors
            </button>
            <button class="menu-btn" onclick="switchTab('deploy', this)">
                🚀 Deploy New
            </button>
            <button class="menu-btn" onclick="switchTab('logs', this)">
                💻 System Terminal
            </button>
        </div>

        <!-- Main Content Area -->
        <div class="main-content">
            
            <!-- Dashboard Tab (Shows active servers) -->
            <div id="dashboard" class="content-section active">
                <div class="glass-card">
                    <h2>Active Infrastructures</h2>
                    <div id="jobs">REPLACE_JOBS_HTML</div>
                </div>
            </div>

            <!-- Deploy Tab (Add new server form) -->
            <div id="deploy" class="content-section">
                <div class="glass-card" style="max-width: 600px; margin: 0 auto;">
                    <h2>Initialize Monitor Engine</h2>
                    <form id="form">
                        <div class="input-group">
                            <input type="text" id="label" placeholder="Project Tag (e.g. Node API)" required autocomplete="off">
                        </div>
                        <div class="input-group">
                            <input type="url" id="url" placeholder="https://target-server.com" required autocomplete="off">
                        </div>
                        <div class="input-group">
                            <input type="number" id="interval" value="5" placeholder="Ping Interval (Mins)" required>
                        </div>
                        <button type="submit" class="neon-btn" id="submitBtn">Engage Monitor</button>
                    </form>
                </div>
            </div>

            <!-- Logs Tab (Live terminal) -->
            <div id="logs" class="content-section">
                <div class="glass-card">
                    <h2>Live Server Feed</h2>
                    <div id="logs-feed" class="logs-container">Awaiting connection...</div>
                </div>
            </div>

        </div>

        <script>
            // Tab Switching Logic
            function switchTab(tabId, btnElement) {
                // Hide all sections
                document.querySelectorAll('.content-section').forEach(sec => sec.classList.remove('active'));
                // Remove active class from all buttons
                document.querySelectorAll('.menu-btn').forEach(btn => btn.classList.remove('active'));
                
                // Show target section and highlight clicked button
                document.getElementById(tabId).classList.add('active');
                btnElement.classList.add('active');
            }

            // Add Server Logic
            document.getElementById('form').onsubmit = async (e) => {
                e.preventDefault();
                const btn = document.getElementById('submitBtn');
                btn.innerText = "Processing...";
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
                else { alert(data.msg); btn.innerText = "Engage Monitor"; }
            };
            
            // Delete Server Logic
            async function delJob(id) { 
                if(confirm("Terminate this monitor instance?")) {
                    await fetch('/del/' + id, { method: 'POST' }); 
                    location.reload(); 
                }
            }
            
            // Fetch Logs Logic
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
    log_msg(f"Initiated monitoring sequence for: {job.label}")
    return {"status": "ok"}

@app.post("/del/{jid}")
def del_job(jid: int):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM jobs WHERE id = ?", (jid,))
    conn.commit()
    conn.close()
    log_msg(f"Terminated instance ID: {jid}")
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
                            log_msg(f"Signal [{label}] ST: {r.status_code} - SECURE")
                        except Exception as ex:
                            log_msg(f"Signal [{label}] ALERT: OFFLINE/DROPPED")
        except Exception:
            pass

@app.on_event("startup")
def startup():
    asyncio.create_task(pinger())
