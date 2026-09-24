import sqlite3
import asyncio
import httpx
import time
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

app = FastAPI(title="PingGuard Ultimate Pro")
DB_NAME = "database.db"
live_logs = ["[SYSTEM] PingGuard Ultimate RGB Glass Engine Initialized..."]
graph_data = {"labels": [], "data": []}

def log_msg(text):
    timestamp = time.strftime('%H:%M:%S')
    live_logs.append(f"[{timestamp}] {text}")
    if len(live_logs) > 50: live_logs.pop(0)
    
    # Update graph data
    graph_data["labels"].append(timestamp)
    if len(graph_data["labels"]) > 15:
        graph_data["labels"].pop(0)
        graph_data["data"].pop(0)

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # Jobs table update (Added stats)
    cursor.execute('''CREATE TABLE IF NOT EXISTS jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        label TEXT, url TEXT, interval INTEGER, status TEXT DEFAULT 'Active',
        total_pings INTEGER DEFAULT 0, fail_count INTEGER DEFAULT 0)''')
    # Settings table for Telegram
    cursor.execute('''CREATE TABLE IF NOT EXISTS settings (
        id INTEGER PRIMARY KEY, tg_token TEXT, tg_chat TEXT)''')
    
    # Insert default settings row if empty
    cursor.execute("SELECT id FROM settings WHERE id=1")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO settings (id, tg_token, tg_chat) VALUES (1, '', '')")
        
    conn.commit()
    conn.close()

init_db()

class Job(BaseModel):
    label: str
    url: str
    interval: int

class Settings(BaseModel):
    tg_token: str
    tg_chat: str

async def send_telegram_alert(msg: str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT tg_token, tg_chat FROM settings WHERE id=1")
    row = cursor.fetchone()
    conn.close()
    
    if row and row[0] and row[1]:
        tg_token, tg_chat = row[0], row[1]
        tg_url = f"https://api.telegram.org/bot{tg_token}/sendMessage"
        try:
            async with httpx.AsyncClient() as client:
                await client.post(tg_url, json={"chat_id": tg_chat, "text": f"🔴 PingGuard ALERT:\n{msg}"})
        except:
            pass

@app.get("/", response_class=HTMLResponse)
def read_root():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, label, url, interval, status, total_pings, fail_count FROM jobs")
    rows = cursor.fetchall()
    
    cursor.execute("SELECT tg_token, tg_chat FROM settings WHERE id=1")
    settings = cursor.fetchone()
    tg_token = settings[0] if settings else ""
    tg_chat = settings[1] if settings else ""
    conn.close()
    
    jobs_list = ""
    for r in rows:
        total = r[5]
        fails = r[6]
        uptime_pct = 100.0 if total == 0 else round(((total - fails) / total) * 100, 2)
        
        jobs_list += f"""
        <div class="glass-item server-item">
            <div style="width: 100%;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                    <div>
                        <h4>{r[1]}</h4>
                        <a href="{r[2]}" target="_blank">{r[2]}</a>
                    </div>
                    <button class="delete-btn" onclick="delJob({r[0]})">Delete</button>
                </div>
                
                <div class="stats-grid">
                    <div class="stat-box">
                        <div class="stat-label">Total Pings</div>
                        <div class="stat-val" style="color: #3b82f6;">{total}</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-label">Uptime</div>
                        <div class="stat-val" style="color: #10b981; text-shadow: 0 0 8px rgba(16,185,129,0.4);">{uptime_pct}%</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-label">Failures</div>
                        <div class="stat-val" style="color: #ef4444;">{fails}</div>
                    </div>
                </div>
            </div>
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
        <title>PingGuard | Ultimate RGB Glass</title>
        <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap" rel="stylesheet">
        <!-- Chart.js for Live Graph -->
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        
        <style>
            body { 
                background: #f1f5f9; color: #1e293b; font-family: 'Poppins', sans-serif; 
                margin: 0; padding: 0; display: flex; height: 100vh; overflow: hidden; position: relative;
            }
            
            /* Animated Blobs */
            .blob-1 { position: absolute; top: -10%; left: -10%; width: 500px; height: 500px; background: #bae6fd; border-radius: 50%; filter: blur(80px); opacity: 0.8; z-index: -1; animation: float1 15s infinite alternate ease-in-out; }
            .blob-2 { position: absolute; bottom: -20%; right: -10%; width: 600px; height: 600px; background: #e9d5ff; border-radius: 50%; filter: blur(100px); opacity: 0.7; z-index: -1; animation: float2 18s infinite alternate ease-in-out; }
            .blob-3 { position: absolute; top: 30%; left: 30%; width: 400px; height: 400px; background: #fef08a; border-radius: 50%; filter: blur(90px); opacity: 0.6; z-index: -1; animation: float3 20s infinite alternate ease-in-out; }
            
            @keyframes float1 { 0% { transform: translate(0, 0); } 100% { transform: translate(100px, 100px); } }
            @keyframes float2 { 0% { transform: translate(0, 0); } 100% { transform: translate(-150px, -100px); } }
            @keyframes float3 { 0% { transform: translate(0, 0) scale(1); } 100% { transform: translate(100px, -50px) scale(1.2); } }

            .glass-panel {
                background: rgba(255, 255, 255, 0.65) !important; backdrop-filter: blur(24px) saturate(120%) !important;
                -webkit-backdrop-filter: blur(24px) saturate(120%) !important; border: 1px solid rgba(255, 255, 255, 0.9) !important;
                box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.05) !important;
            }
            
            /* Sidebar */
            .sidebar { width: 260px; padding: 30px 20px; display: flex; flex-direction: column; z-index: 10; border-right: 1px solid rgba(255, 255, 255, 0.6); }
            .brand { font-size: 28px; font-weight: 700; color: #0f172a; text-align: center; margin-bottom: 40px; }
            .brand span { color: #3b82f6; }
            
            /* RGB Blinking Dots */
            .dot-blink { width: 12px; height: 12px; border-radius: 50%; display: inline-block; margin-right: 8px; animation: rgb-blink 5s infinite; }
            .dot-1 { animation-delay: 0s; } .dot-2 { animation-delay: 1s; } .dot-3 { animation-delay: 2s; } .dot-4 { animation-delay: 3s; } .dot-5 { animation-delay: 4s; }
            
            @keyframes rgb-blink { 
                0% { background-color: #ff6b00; box-shadow: 0 0 0 0 rgba(255, 107, 0, 0.8); } 8% { box-shadow: 0 0 0 8px rgba(255, 107, 0, 0); }
                20% { background-color: #00ff00; box-shadow: 0 0 0 0 rgba(0, 255, 0, 0.8); } 28% { box-shadow: 0 0 0 8px rgba(0, 255, 0, 0); }
                40% { background-color: #ff003c; box-shadow: 0 0 0 0 rgba(255, 0, 60, 0.8); } 48% { box-shadow: 0 0 0 8px rgba(255, 0, 60, 0); }
                60% { background-color: #ffea00; box-shadow: 0 0 0 0 rgba(255, 234, 0, 0.8); } 68% { box-shadow: 0 0 0 8px rgba(255, 234, 0, 0); }
                80% { background-color: #00e5ff; box-shadow: 0 0 0 0 rgba(0, 229, 255, 0.8); } 88% { box-shadow: 0 0 0 8px rgba(0, 229, 255, 0); }
                100% { background-color: #ff6b00; box-shadow: 0 0 0 0 rgba(255, 107, 0, 0.8); } 
            }

            .menu-btn {
                background: rgba(255, 255, 255, 0.4); color: #334155; border: 1px solid rgba(255, 255, 255, 0.8);
                border-radius: 12px; padding: 15px; margin-bottom: 12px; font-size: 14px; font-weight: 600; 
                text-align: left; cursor: pointer; transition: all 0.3s ease; display: flex; align-items: center; box-shadow: 0 2px 5px rgba(0,0,0,0.02);
            }
            .menu-btn:hover { background: rgba(255, 255, 255, 0.8); transform: translateX(5px); }
            .menu-btn.active { background: #ffffff; color: #2563eb; border: 1px solid #ffffff; box-shadow: 0 5px 15px rgba(37, 99, 235, 0.1); }
            
            .main-content { flex: 1; padding: 30px 40px; overflow-y: auto; z-index: 10; }
            .content-section { display: none; animation: fadeIn 0.4s ease; }
            .content-section.active { display: block; }
            @keyframes fadeIn { from { opacity: 0; transform: scale(0.98); } to { opacity: 1; transform: scale(1); } }
            
            h2 { font-size: 24px; font-weight: 600; margin-top: 0; margin-bottom: 25px; color: #0f172a; border-bottom: 1px solid rgba(0,0,0,0.05); padding-bottom: 15px;}
            
            .glass-card { border-radius: 24px; padding: 30px; margin-bottom: 25px; }
            
            .input-group { margin-bottom: 20px; }
            input {
                width: 100%; padding: 15px 20px; border-radius: 12px; border: 1px solid rgba(255, 255, 255, 0.9);
                background: rgba(255, 255, 255, 0.5); color: #0f172a; font-family: 'Poppins', sans-serif; font-size: 14px;
                box-sizing: border-box; outline: none; transition: 0.3s; box-shadow: inset 0 2px 4px rgba(0,0,0,0.02);
            }
            input:focus { background: rgba(255, 255, 255, 0.9); border-color: #3b82f6; box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.1); }
            
            .glass-btn {
                width: 100%; padding: 15px; border: none; border-radius: 12px; background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
                color: #ffffff; font-weight: 600; font-size: 15px; cursor: pointer; transition: 0.3s; box-shadow: 0 10px 20px rgba(37, 99, 235, 0.2);
            }
            .glass-btn:hover { transform: translateY(-2px); box-shadow: 0 15px 25px rgba(37, 99, 235, 0.3); }
            
            .glass-item {
                background: rgba(255, 255, 255, 0.6); border: 1px solid rgba(255, 255, 255, 0.9); border-radius: 16px;
                display: flex; flex-direction: column; padding: 20px; margin-bottom: 20px; transition: 0.3s; box-shadow: 0 4px 6px rgba(0,0,0,0.02);
            }
            .glass-item:hover { background: #ffffff; transform: translateY(-2px); box-shadow: 0 8px 15px rgba(0,0,0,0.05); }
            
            .server-item h4 { margin: 0 0 5px 0; font-size: 18px; color: #0f172a; }
            .server-item a { color: #3b82f6; text-decoration: none; font-size: 14px; }
            
            .stats-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 15px; margin-top: 10px; }
            .stat-box { background: rgba(255,255,255,0.5); border: 1px solid rgba(255,255,255,0.8); border-radius: 10px; padding: 12px; text-align: center; }
            .stat-label { font-size: 12px; color: #64748b; font-weight: 500; margin-bottom: 5px; text-transform: uppercase; letter-spacing: 0.5px;}
            .stat-val { font-size: 20px; font-weight: 700; }
            
            .delete-btn { background: rgba(239, 68, 68, 0.1); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.2); padding: 8px 15px; font-size: 12px; font-weight: 600; border-radius: 8px; cursor: pointer; transition: 0.2s; }
            .delete-btn:hover { background: #ef4444; color: #fff; }
            
            .logs-container { background: rgba(255, 255, 255, 0.7); border: 1px solid rgba(255, 255, 255, 0.9); color: #059669; padding: 20px; height: 350px; overflow-y: auto; border-radius: 16px; font-family: monospace; font-size: 13px; line-height: 1.6; }
            .chart-container { height: 350px; width: 100%; }
        </style>
    </head>
    <body>
        
        <div class="blob-1"></div>
        <div class="blob-2"></div>
        <div class="blob-3"></div>

        <div class="sidebar glass-panel">
            <div class="brand">Ping<span>Guard</span></div>
            
            <button class="menu-btn active" onclick="switchTab('dashboard', this)"><span class="dot-blink dot-1"></span> Active Monitors</button>
            <button class="menu-btn" onclick="switchTab('analytics', this)"><span class="dot-blink dot-2"></span> Network Graph</button>
            <button class="menu-btn" onclick="switchTab('deploy', this)"><span class="dot-blink dot-3"></span> Deploy New</button>
            <button class="menu-btn" onclick="switchTab('alerts', this)"><span class="dot-blink dot-4"></span> Alert Settings</button>
            <button class="menu-btn" onclick="switchTab('logs', this)"><span class="dot-blink dot-5"></span> System Terminal</button>
        </div>

        <div class="main-content">
            
            <!-- Dashboard Tab -->
            <div id="dashboard" class="content-section active">
                <div class="glass-card glass-panel">
                    <h2>Live Infrastructures</h2>
                    <div id="jobs">REPLACE_JOBS_HTML</div>
                </div>
            </div>

            <!-- Graph Analytics Tab -->
            <div id="analytics" class="content-section">
                <div class="glass-card glass-panel">
                    <h2>Network Response Graph</h2>
                    <div class="chart-container">
                        <canvas id="liveChart"></canvas>
                    </div>
                </div>
            </div>

            <!-- Deploy Tab -->
            <div id="deploy" class="content-section">
                <div class="glass-card glass-panel" style="max-width: 600px; margin: 0 auto;">
                    <h2>Deploy Monitor Engine</h2>
                    <form id="form">
                        <div class="input-group"><input type="text" id="label" placeholder="Project Name (e.g. API Server)" required></div>
                        <div class="input-group"><input type="url" id="url" placeholder="https://target-server.com" required></div>
                        <div class="input-group"><input type="number" id="interval" value="5" placeholder="Ping Interval (Mins)" required></div>
                        <button type="submit" class="glass-btn" id="submitBtn">Deploy Server</button>
                    </form>
                </div>
            </div>
            
            <!-- Alerts Tab -->
            <div id="alerts" class="content-section">
                <div class="glass-card glass-panel" style="max-width: 600px; margin: 0 auto;">
                    <h2>Telegram Notification Setup</h2>
                    <form id="alertForm">
                        <div class="input-group">
                            <label style="font-size:12px; font-weight:600; color:#64748b;">Bot Token (From @BotFather)</label>
                            <input type="text" id="tg_token" value="REPLACE_TG_TOKEN" placeholder="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11">
                        </div>
                        <div class="input-group">
                            <label style="font-size:12px; font-weight:600; color:#64748b;">Your Chat ID</label>
                            <input type="text" id="tg_chat" value="REPLACE_TG_CHAT" placeholder="123456789">
                        </div>
                        <button type="submit" class="glass-btn" id="alertBtn" style="background: linear-gradient(135deg, #10b981 0%, #059669 100%);">Save Alert Settings</button>
                    </form>
                </div>
            </div>

            <!-- Logs Tab -->
            <div id="logs" class="content-section">
                <div class="glass-card glass-panel">
                    <h2>Live Server Feed</h2>
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
                const btn = document.getElementById('submitBtn'); btn.innerText = "Deploying...";
                let res = await fetch('/add', {
                    method: 'POST', headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ label: document.getElementById('label').value, url: document.getElementById('url').value, interval: parseInt(document.getElementById('interval').value) })
                });
                let data = await res.json();
                if(data.status === 'ok') { location.reload(); } else { alert(data.msg); btn.innerText = "Deploy Server"; }
            };
            
            document.getElementById('alertForm').onsubmit = async (e) => {
                e.preventDefault();
                const btn = document.getElementById('alertBtn'); btn.innerText = "Saving...";
                await fetch('/settings', {
                    method: 'POST', headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ tg_token: document.getElementById('tg_token').value, tg_chat: document.getElementById('tg_chat').value })
                });
                btn.innerText = "Saved Successfully!";
                setTimeout(() => btn.innerText = "Save Alert Settings", 2000);
            };
            
            async function delJob(id) { 
                if(confirm("Stop monitoring this server?")) { await fetch('/del/' + id, { method: 'POST' }); location.reload(); }
            }
            
            // Chart.js Graph Initialization
            const ctx = document.getElementById('liveChart').getContext('2d');
            let liveChart = new Chart(ctx, {
                type: 'line',
                data: { labels: [], datasets: [{ label: 'Network Activity (Live)', data: [], borderColor: '#3b82f6', backgroundColor: 'rgba(59, 130, 246, 0.2)', borderWidth: 3, tension: 0.4, fill: true, pointBackgroundColor: '#10b981', pointRadius: 5 }] },
                options: { responsive: true, maintainAspectRatio: false, scales: { y: { beginAtZero: true, grid: { color: 'rgba(0,0,0,0.05)' } }, x: { grid: { display: false } } }, plugins: { legend: { labels: { font: { family: 'Poppins', size: 14 } } } } }
            });

            // Fetch Logs and Graph Data
            setInterval(async () => {
                let res = await fetch('/data');
                let data = await res.json();
                
                // Update Logs
                let logsBox = document.getElementById('logs-feed');
                let isScrolledToBottom = logsBox.scrollHeight - logsBox.clientHeight <= logsBox.scrollTop + 1;
                logsBox.innerText = data.logs.join('\\n');
                if (isScrolledToBottom) { logsBox.scrollTop = logsBox.scrollHeight; }
                
                // Update Graph
                liveChart.data.labels = data.graph.labels;
                liveChart.data.datasets[0].data = data.graph.data;
                liveChart.update();
            }, 3000);
        </script>
    </body>
    </html>
    """
    html = html.replace("REPLACE_JOBS_HTML", jobs_list)
    html = html.replace("REPLACE_TG_TOKEN", tg_token)
    html = html.replace("REPLACE_TG_CHAT", tg_chat)
    return html

@app.post("/add")
def add_job(job: Job):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO jobs (label, url, interval) VALUES (?, ?, ?)", (job.label, job.url, job.interval))
    conn.commit()
    conn.close()
    log_msg(f"Deployed new monitor: {job.label}")
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

@app.post("/settings")
def update_settings(s: Settings):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE settings SET tg_token=?, tg_chat=? WHERE id=1", (s.tg_token, s.tg_chat))
    conn.commit()
    conn.close()
    return {"status": "ok"}

@app.get("/data")
def get_data():
    return {"logs": live_logs, "graph": graph_data}

async def pinger():
    while True:
        await asyncio.sleep(30) # Checks every 30 secs for testing (you can change logic later)
        try:
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("SELECT id, label, url, total_pings, fail_count FROM jobs")
            rows = cursor.fetchall()
            
            if rows:
                async with httpx.AsyncClient(timeout=10) as client:
                    for r in rows:
                        jid, label, url, total_pings, fail_count = r
                        new_total = total_pings + 1
                        success = False
                        
                        start_time = time.time()
                        try:
                            resp = await client.get(url)
                            if resp.status_code == 200:
                                success = True
                                log_msg(f"Signal [{label}] STATUS: SECURE (200 OK)")
                            else:
                                log_msg(f"Signal [{label}] ALERT: Status {resp.status_code}")
                        except Exception:
                            log_msg(f"Signal [{label}] CRITICAL: Server Offline!")
                            
                        # Graph Data (Response Time Simulation for aesthetics if success, 0 if fail)
                        resp_time = int((time.time() - start_time) * 1000) if success else 0
                        graph_data["data"].append(resp_time if success else 0)
                        
                        new_fail = fail_count if success else fail_count + 1
                        cursor.execute("UPDATE jobs SET total_pings=?, fail_count=? WHERE id=?", (new_total, new_fail, jid))
                        conn.commit()
                        
                        # Send Telegram Alert on Failure
                        if not success:
                            await send_telegram_alert(f"Server '{label}' ({url}) is NOT responding!")
            conn.close()
        except Exception:
            pass

@app.on_event("startup")
def startup():
    asyncio.create_task(pinger())
