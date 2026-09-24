import sqlite3
import asyncio
import httpx
import time
from fastapi import FastAPI, Header
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional

app = FastAPI(title="PingGuard Multi-User 3D")
DB_NAME = "database.db"

# Memory state for logs and graphs per user
user_logs = {}
user_graphs = {}

def log_msg(username, text):
    if username not in user_logs:
        user_logs[username] = []
        user_graphs[username] = {"labels": [], "data": []}
        
    timestamp = time.strftime('%H:%M:%S')
    user_logs[username].append(f"[{timestamp}] {text}")
    if len(user_logs[username]) > 50: user_logs[username].pop(0)
    
    user_graphs[username]["labels"].append(timestamp)
    if len(user_graphs[username]["labels"]) > 15:
        user_graphs[username]["labels"].pop(0)
        user_graphs[username]["data"].pop(0)

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # Table creations
    cursor.execute('''CREATE TABLE IF NOT EXISTS jobs (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, label TEXT, url TEXT, interval INTEGER, status TEXT DEFAULT 'Active', total_pings INTEGER DEFAULT 0, fail_count INTEGER DEFAULT 0)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS settings (username TEXT PRIMARY KEY, tg_token TEXT, tg_chat TEXT)''')
    
    # Auto-upgrade older databases to support multi-user
    try: cursor.execute("ALTER TABLE jobs ADD COLUMN username TEXT DEFAULT 'default'")
    except: pass
    try: cursor.execute("ALTER TABLE settings ADD COLUMN username TEXT DEFAULT 'default'")
    except: pass
    
    conn.commit()
    conn.close()

init_db()

class JobData(BaseModel):
    id: Optional[int] = None
    label: str
    url: str
    interval: int

class SettingsData(BaseModel):
    tg_token: str
    tg_chat: str

async def send_telegram_alert(username: str, msg: str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT tg_token, tg_chat FROM settings WHERE username=?", (username,))
    row = cursor.fetchone()
    conn.close()
    
    if row and row[0] and row[1]:
        tg_url = f"https://api.telegram.org/bot{row[0]}/sendMessage"
        try:
            async with httpx.AsyncClient() as client:
                await client.post(tg_url, json={"chat_id": row[1], "text": f"🔴 [{username.upper()}] ALERT:\n{msg}"})
        except: pass

@app.get("/", response_class=HTMLResponse)
def read_root():
    # Pure Frontend HTML with JS Logic for Multi-User
    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>PingGuard | Workspace Cloud</title>
        <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800&display=swap" rel="stylesheet">
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        
        <style>
            body { background: #f1f5f9; color: #1e293b; font-family: 'Poppins', sans-serif; margin: 0; padding: 0; display: flex; height: 100vh; overflow: hidden; position: relative; }
            
            /* Animated Background */
            .blob-1 { position: absolute; top: -10%; left: -10%; width: 500px; height: 500px; background: #bae6fd; border-radius: 50%; filter: blur(80px); opacity: 0.8; z-index: -1; animation: float1 15s infinite alternate ease-in-out; }
            .blob-2 { position: absolute; bottom: -20%; right: -10%; width: 600px; height: 600px; background: #e9d5ff; border-radius: 50%; filter: blur(100px); opacity: 0.7; z-index: -1; animation: float2 18s infinite alternate ease-in-out; }
            
            @keyframes float1 { 0% { transform: translate(0, 0); } 100% { transform: translate(100px, 100px); } }
            @keyframes float2 { 0% { transform: translate(0, 0); } 100% { transform: translate(-150px, -100px); } }

            /* LOGIN SCREEN */
            #login-screen { position: absolute; top: 0; left: 0; width: 100%; height: 100%; display: flex; justify-content: center; align-items: center; z-index: 100; backdrop-filter: blur(25px); background: rgba(255,255,255,0.4); }
            .login-box { background: rgba(255,255,255,0.7); border: 2px solid #fff; border-radius: 30px; padding: 50px; text-align: center; box-shadow: 20px 20px 40px rgba(0,0,0,0.05), -20px -20px 40px #fff; width: 400px; }
            .login-box h1 { font-weight: 800; font-size: 32px; margin-bottom: 5px; color: #0f172a; }
            .login-box p { color: #64748b; margin-bottom: 30px; font-weight: 500; }

            /* UNIQUE 3D NEON INPUTS (Dhansa Hua) */
            .neon-input {
                width: 100%; padding: 18px 25px; border-radius: 20px; 
                border: 2px solid rgba(255,255,255,0.6);
                background: #eef2f6; color: #0f172a; font-family: 'Poppins', sans-serif; font-size: 15px; font-weight: 600;
                box-sizing: border-box; outline: none; transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); 
                /* Inner carving shadow */
                box-shadow: inset 6px 6px 12px #cbd5e1, inset -6px -6px 12px #ffffff;
            }
            .neon-input:focus { 
                background: #ffffff; 
                border-color: #00f2fe; 
                /* Neon glow pop-out */
                box-shadow: inset 2px 2px 5px rgba(0,0,0,0.05), 0 0 20px rgba(0, 242, 254, 0.5), 0 0 5px #00f2fe; 
            }
            .input-group label { display:block; text-align:left; font-size:13px; font-weight:700; color:#475569; margin-left:15px; margin-bottom:8px; text-transform:uppercase; letter-spacing:1px; }
            .input-group { margin-bottom: 25px; }

            /* 3D OUTSET BUTTONS */
            .glass-btn {
                width: 100%; padding: 18px; border: 1px solid rgba(255,255,255,0.8); border-radius: 20px; 
                background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
                color: #ffffff; font-weight: 700; font-size: 16px; cursor: pointer; transition: 0.2s; text-transform: uppercase; letter-spacing: 1px;
                box-shadow: 8px 8px 20px rgba(0, 242, 254, 0.3), -8px -8px 20px rgba(255, 255, 255, 0.9), inset 2px 2px 5px rgba(255,255,255,0.5);
            }
            .glass-btn:active { box-shadow: inset 6px 6px 12px rgba(0,0,0,0.1), inset -6px -6px 12px rgba(255,255,255,0.5); transform: translateY(3px); }

            /* Sidebar */
            .sidebar { width: 260px; padding: 30px 20px; display: flex; flex-direction: column; z-index: 10; background: linear-gradient(135deg, rgba(255,255,255,0.7), rgba(255,255,255,0.3)); box-shadow: 15px 0 30px rgba(0,0,0,0.05); border-right: 1px solid rgba(255, 255, 255, 0.8); backdrop-filter: blur(20px); }
            .brand { font-size: 26px; font-weight: 800; color: #0f172a; text-align: center; margin-bottom: 20px; }
            .brand span { color: #3b82f6; }
            .user-badge { background: #fff; padding: 8px 15px; border-radius: 30px; font-size: 12px; font-weight: 700; color: #10b981; text-align: center; margin-bottom: 40px; box-shadow: inset 2px 2px 5px rgba(0,0,0,0.05); cursor:pointer;}
            .user-badge:hover { background: #fee2e2; color: #ef4444; }

            /* RGB Dots */
            .dot-blink { width: 12px; height: 12px; border-radius: 50%; display: inline-block; margin-right: 8px; animation: rgb-blink 5s infinite; }
            .dot-1 { animation-delay: 0s; } .dot-2 { animation-delay: 1s; } .dot-3 { animation-delay: 2s; } .dot-4 { animation-delay: 3s; }
            @keyframes rgb-blink { 
                0% { background-color: #ff6b00; box-shadow: 0 0 0 0 rgba(255, 107, 0, 0.8); } 8% { box-shadow: 0 0 0 8px rgba(255, 107, 0, 0); }
                30% { background-color: #00ff00; box-shadow: 0 0 0 0 rgba(0, 255, 0, 0.8); } 38% { box-shadow: 0 0 0 8px rgba(0, 255, 0, 0); }
                60% { background-color: #00e5ff; box-shadow: 0 0 0 0 rgba(0, 229, 255, 0.8); } 68% { box-shadow: 0 0 0 8px rgba(0, 229, 255, 0); }
                100% { background-color: #ff6b00; box-shadow: 0 0 0 0 rgba(255, 107, 0, 0.8); } 
            }

            .menu-btn { background: rgba(230, 240, 250, 0.5); color: #334155; border: 1px solid rgba(255, 255, 255, 0.8); border-radius: 15px; padding: 15px; margin-bottom: 12px; font-size: 14px; font-weight: 600; text-align: left; cursor: pointer; transition: all 0.3s ease; display: flex; align-items: center; box-shadow: 4px 4px 10px rgba(0,0,0,0.03), -4px -4px 10px rgba(255,255,255,0.8); }
            .menu-btn:hover { background: rgba(255, 255, 255, 0.9); transform: translateY(-2px); }
            .menu-btn.active { background: #ffffff; color: #2563eb; box-shadow: inset 4px 4px 8px rgba(0,0,0,0.05), inset -4px -4px 8px rgba(255,255,255,1); border: 1px solid rgba(255,255,255,0.4); }
            
            /* Main Content */
            #app-screen { display: none; width: 100%; height: 100%; }
            .main-content { flex: 1; padding: 30px 40px; overflow-y: auto; z-index: 10; }
            .content-section { display: none; animation: fadeIn 0.4s ease; }
            .content-section.active { display: block; }
            @keyframes fadeIn { from { opacity: 0; transform: scale(0.98); } to { opacity: 1; transform: scale(1); } }
            
            h2 { font-size: 26px; font-weight: 700; margin-top: 0; margin-bottom: 25px; color: #0f172a; border-bottom: 1px solid rgba(0,0,0,0.05); padding-bottom: 15px; text-shadow: 1px 1px 2px rgba(255,255,255,0.8);}
            
            .glass-card { border-radius: 30px; padding: 40px; margin-bottom: 25px; background: linear-gradient(135deg, rgba(255,255,255,0.6), rgba(255,255,255,0.3)); border: 2px solid rgba(255, 255, 255, 0.8); box-shadow: 15px 15px 35px rgba(0, 0, 0, 0.05), -15px -15px 35px rgba(255, 255, 255, 0.8), inset 2px 2px 5px rgba(255, 255, 255, 1); backdrop-filter: blur(20px); }
            
            /* Server Item Card */
            .glass-item { background: linear-gradient(135deg, rgba(255,255,255,0.8), rgba(255,255,255,0.5)); border: 2px solid rgba(255, 255, 255, 0.9); border-radius: 20px; display: flex; flex-direction: column; padding: 25px; margin-bottom: 25px; transition: 0.3s; box-shadow: 10px 10px 20px rgba(0,0,0,0.04), -10px -10px 20px rgba(255,255,255,0.9); }
            .glass-item:hover { transform: translateY(-4px); box-shadow: 15px 15px 25px rgba(0,0,0,0.06), -10px -10px 25px rgba(255,255,255,1); }
            .server-item h4 { font-size: 20px; color: #0f172a; margin: 0 0 5px 0; display: flex; align-items: center; gap: 8px;}
            .live-indicator { width: 12px; height: 12px; background-color: #10b981; border-radius: 50%; display: inline-block; box-shadow: 0 0 12px #10b981; animation: live-pulse 1.5s infinite; }
            @keyframes live-pulse { 0% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); } 70% { box-shadow: 0 0 0 8px rgba(16, 185, 129, 0); } 100% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); } }
            
            .stats-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 20px; margin-top: 20px; }
            .stat-box { background: rgba(245, 250, 255, 0.7); border-radius: 16px; padding: 18px; text-align: center; box-shadow: inset 4px 4px 8px rgba(0,0,0,0.03), inset -4px -4px 8px rgba(255,255,255,0.9); }
            .stat-label { font-size: 12px; color: #64748b; font-weight: 700; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 1px;}
            .stat-val { font-size: 26px; font-weight: 800; }
            
            .neon-box-blue { border: 1px solid rgba(59, 130, 246, 0.4); } .neon-box-blue .stat-val { color: #3b82f6; text-shadow: 0 0 15px rgba(59, 130, 246, 0.5); }
            .neon-box-green { border: 1px solid rgba(16, 185, 129, 0.4); } .neon-box-green .stat-val { color: #10b981; text-shadow: 0 0 15px rgba(16, 185, 129, 0.5); }
            .neon-box-red { border: 1px solid rgba(239, 68, 68, 0.4); } .neon-box-red .stat-val { color: #ef4444; text-shadow: 0 0 15px rgba(239, 68, 68, 0.5); }
            
            .action-btns { display: flex; gap: 10px; }
            .neon-edit-btn, .neon-delete-btn { padding: 10px 20px; font-size: 13px; font-weight: 700; border-radius: 12px; cursor: pointer; transition: 0.2s; }
            .neon-edit-btn { background: rgba(59, 130, 246, 0.1); color: #3b82f6; border: 1px solid rgba(59, 130, 246, 0.4); box-shadow: 4px 4px 10px rgba(59, 130, 246, 0.1), -4px -4px 10px rgba(255, 255, 255, 0.9); }
            .neon-edit-btn:hover { background: #3b82f6; color: #fff; box-shadow: 0 0 20px rgba(59, 130, 246, 0.6); transform: translateY(-2px); }
            
            .neon-delete-btn { background: rgba(239, 68, 68, 0.1); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.4); box-shadow: 4px 4px 10px rgba(239, 68, 68, 0.1), -4px -4px 10px rgba(255, 255, 255, 0.9); }
            .neon-delete-btn:hover { background: #ef4444; color: #fff; box-shadow: 0 0 20px rgba(239, 68, 68, 0.6); transform: translateY(-2px); }
            
            .empty-state { text-align: center; padding: 50px; color: #64748b; font-weight: 600; font-size: 18px;}
            .logs-container { background: rgba(230, 240, 250, 0.6); border: 1px solid rgba(255, 255, 255, 0.9); color: #059669; padding: 25px; height: 350px; overflow-y: auto; border-radius: 20px; font-family: monospace; font-size: 14px; line-height: 1.6; box-shadow: inset 6px 6px 15px rgba(0,0,0,0.05), inset -6px -6px 15px rgba(255,255,255,0.9); }
            .chart-container { height: 350px; width: 100%; }
        </style>
    </head>
    <body>
        <div class="blob-1"></div>
        <div class="blob-2"></div>

        <!-- AUTH LOGIN SCREEN -->
        <div id="login-screen">
            <div class="login-box">
                <h1>Workspace</h1>
                <p>Enter unique name to access your data</p>
                <div class="input-group">
                    <input type="text" id="workspaceInput" class="neon-input" placeholder="e.g. chandan_admin" autocomplete="off" onkeypress="if(event.key === 'Enter') login()">
                </div>
                <button class="glass-btn" onclick="login()">Enter Dashboard</button>
            </div>
        </div>

        <!-- MAIN APP -->
        <div id="app-screen">
            <div class="sidebar">
                <div class="brand">Ping<span>Guard</span></div>
                <div class="user-badge" onclick="logout()" title="Click to Logout">👤 <span id="displayUser"></span></div>
                
                <button class="menu-btn active" onclick="switchTab('dashboard', this)"><span class="dot-blink dot-1"></span> Active Monitors</button>
                <button class="menu-btn" onclick="switchTab('analytics', this)"><span class="dot-blink dot-2"></span> Network Graph</button>
                <button class="menu-btn" onclick="switchTab('deploy', this)"><span class="dot-blink dot-3"></span> Deploy Server</button>
                <button class="menu-btn" onclick="switchTab('alerts', this)"><span class="dot-blink dot-4"></span> Alert Settings</button>
            </div>

            <div class="main-content">
                <div id="dashboard" class="content-section active">
                    <div class="glass-card">
                        <h2>Live Infrastructures</h2>
                        <div id="jobs-container">Loading...</div>
                    </div>
                </div>

                <div id="analytics" class="content-section">
                    <div class="glass-card"><h2>Network Response Graph</h2><div class="chart-container"><canvas id="liveChart"></canvas></div></div>
                    <div class="glass-card"><h2>Live Server Logs</h2><div id="logs-feed" class="logs-container">Awaiting connection...</div></div>
                </div>

                <div id="deploy" class="content-section">
                    <div class="glass-card" style="max-width: 650px; margin: 0 auto;">
                        <h2 id="formTitle">Deploy Monitor Engine</h2>
                        <form id="form">
                            <input type="hidden" id="job_id">
                            <div class="input-group">
                                <label>Project Name</label>
                                <input type="text" id="label" class="neon-input" placeholder="e.g. Node API" required>
                            </div>
                            <div class="input-group">
                                <label>Target URL</label>
                                <input type="url" id="url" class="neon-input" placeholder="https://target-server.com" required>
                            </div>
                            <div class="input-group">
                                <label>Ping Interval (Mins)</label>
                                <input type="number" id="interval" class="neon-input" value="5" required>
                            </div>
                            <button type="submit" class="glass-btn" id="submitBtn">Deploy Server</button>
                        </form>
                    </div>
                </div>
                
                <div id="alerts" class="content-section">
                    <div class="glass-card" style="max-width: 650px; margin: 0 auto;">
                        <h2>Telegram Notification Setup</h2>
                        <form id="alertForm">
                            <div class="input-group">
                                <label>Bot Token (From @BotFather)</label>
                                <input type="text" id="tg_token" class="neon-input" placeholder="123456:ABC-DEF1234ghIkl">
                            </div>
                            <div class="input-group">
                                <label>Your Chat ID</label>
                                <input type="text" id="tg_chat" class="neon-input" placeholder="123456789">
                            </div>
                            <button type="submit" class="glass-btn" id="alertBtn" style="background: linear-gradient(135deg, #10b981 0%, #059669 100%);">Save Alert Settings</button>
                        </form>
                    </div>
                </div>
            </div>
        </div>

        <script>
            let currentUser = localStorage.getItem('pg_workspace');
            let liveChart;

            function initApp() {
                if (!currentUser) {
                    document.getElementById('login-screen').style.display = 'flex';
                    document.getElementById('app-screen').style.display = 'none';
                    document.getElementById('workspaceInput').focus();
                } else {
                    document.getElementById('login-screen').style.display = 'none';
                    document.getElementById('app-screen').style.display = 'flex';
                    document.getElementById('displayUser').innerText = currentUser;
                    
                    const ctx = document.getElementById('liveChart').getContext('2d');
                    if(liveChart) liveChart.destroy();
                    liveChart = new Chart(ctx, {
                        type: 'line',
                        data: { labels: [], datasets: [{ label: 'Response Time (ms)', data: [], borderColor: '#3b82f6', backgroundColor: 'rgba(59, 130, 246, 0.2)', borderWidth: 3, tension: 0.4, fill: true, pointBackgroundColor: '#10b981', pointRadius: 5 }] },
                        options: { responsive: true, maintainAspectRatio: false, scales: { y: { beginAtZero: true, grid: { color: 'rgba(0,0,0,0.05)' } }, x: { grid: { display: false } } } }
                    });
                    
                    fetchData();
                    setInterval(fetchData, 3000);
                }
            }

            function login() {
                const user = document.getElementById('workspaceInput').value.trim().toLowerCase();
                if (user) { localStorage.setItem('pg_workspace', user); currentUser = user; initApp(); }
            }

            function logout() {
                if(confirm("Logout from this workspace?")) { localStorage.removeItem('pg_workspace'); currentUser = null; location.reload(); }
            }

            function switchTab(tabId, btnElement) {
                document.querySelectorAll('.content-section').forEach(sec => sec.classList.remove('active'));
                document.querySelectorAll('.menu-btn').forEach(btn => btn.classList.remove('active'));
                document.getElementById(tabId).classList.add('active');
                btnElement.classList.add('active');
                
                if(tabId === 'deploy' && !document.getElementById('job_id').value) {
                    document.getElementById('formTitle').innerText = 'Deploy Monitor Engine';
                    document.getElementById('submitBtn').innerText = 'Deploy Server';
                }
            }

            async function fetchData() {
                if(!currentUser) return;
                try {
                    let res = await fetch('/api/data', { headers: { 'X-User': currentUser } });
                    let data = await res.json();
                    
                    // Render Jobs
                    let html = "";
                    if(data.jobs.length === 0) {
                        html = "<div class='empty-state'>No servers deployed in this workspace yet.</div>";
                    } else {
                        data.jobs.forEach(j => {
                            let uptime = j.total === 0 ? 100.0 : ((j.total - j.fails) / j.total * 100).toFixed(1);
                            html += `
                            <div class="glass-item server-item">
                                <div style="display:flex; justify-content:space-between; align-items:center;">
                                    <div><h4><span class="live-indicator"></span> ${j.label}</h4><a href="${j.url}" target="_blank">${j.url}</a></div>
                                    <div class="action-btns">
                                        <button class="neon-edit-btn" onclick="editJob(${j.id}, '${j.label}', '${j.url}', ${j.interval})">Edit</button>
                                        <button class="neon-delete-btn" onclick="delJob(${j.id})">Delete</button>
                                    </div>
                                </div>
                                <div class="stats-grid">
                                    <div class="stat-box neon-box-blue"><div class="stat-label">Total Pings</div><div class="stat-val">${j.total}</div></div>
                                    <div class="stat-box neon-box-green"><div class="stat-label">Uptime</div><div class="stat-val">${uptime}%</div></div>
                                    <div class="stat-box neon-box-red"><div class="stat-label">Failures</div><div class="stat-val">${j.fails}</div></div>
                                </div>
                            </div>`;
                        });
                    }
                    document.getElementById('jobs-container').innerHTML = html;
                    
                    // Update Settings if not typing
                    if(!document.getElementById('tg_token').matches(':focus') && !document.getElementById('tg_chat').matches(':focus')){
                        document.getElementById('tg_token').value = data.settings.tg_token;
                        document.getElementById('tg_chat').value = data.settings.tg_chat;
                    }
                    
                    // Update Logs & Graph
                    let logsBox = document.getElementById('logs-feed');
                    let isScrolledToBottom = logsBox.scrollHeight - logsBox.clientHeight <= logsBox.scrollTop + 1;
                    logsBox.innerText = data.logs.join('\\n');
                    if (isScrolledToBottom) { logsBox.scrollTop = logsBox.scrollHeight; }
                    
                    liveChart.data.labels = data.graph.labels;
                    liveChart.data.datasets[0].data = data.graph.data;
                    liveChart.update();
                } catch(e) {}
            }

            document.getElementById('form').onsubmit = async (e) => {
                e.preventDefault();
                const btn = document.getElementById('submitBtn'); btn.innerText = "Processing...";
                let payload = {
                    id: document.getElementById('job_id').value ? parseInt(document.getElementById('job_id').value) : null,
                    label: document.getElementById('label').value,
                    url: document.getElementById('url').value,
                    interval: parseInt(document.getElementById('interval').value)
                };
                await fetch('/api/job', { method: 'POST', headers: {'Content-Type': 'application/json', 'X-User': currentUser}, body: JSON.stringify(payload) });
                
                // Reset form
                document.getElementById('form').reset();
                document.getElementById('job_id').value = '';
                btn.innerText = "Deploy Server";
                switchTab('dashboard', document.querySelectorAll('.menu-btn')[0]);
                fetchData();
            };

            function editJob(id, label, url, interval) {
                document.getElementById('job_id').value = id;
                document.getElementById('label').value = label;
                document.getElementById('url').value = url;
                document.getElementById('interval').value = interval;
                document.getElementById('formTitle').innerText = 'Edit Monitor Details';
                document.getElementById('submitBtn').innerText = 'Update Server Details';
                switchTab('deploy', document.querySelectorAll('.menu-btn')[2]);
            }

            async function delJob(id) { 
                if(confirm("Stop monitoring and delete this server?")) { 
                    await fetch('/api/del/' + id, { method: 'POST', headers: {'X-User': currentUser} }); 
                    fetchData(); 
                }
            }

            document.getElementById('alertForm').onsubmit = async (e) => {
                e.preventDefault();
                const btn = document.getElementById('alertBtn'); btn.innerText = "Saving...";
                await fetch('/api/settings', {
                    method: 'POST', headers: {'Content-Type': 'application/json', 'X-User': currentUser},
                    body: JSON.stringify({ tg_token: document.getElementById('tg_token').value, tg_chat: document.getElementById('tg_chat').value })
                });
                btn.innerText = "Saved Successfully!";
                setTimeout(() => btn.innerText = "Save Alert Settings", 2000);
            };

            // Start App
            initApp();
        </script>
    </body>
    </html>
    """
    return html

@app.get("/api/data")
def get_data(x_user: str = Header("default")):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, label, url, interval, status, total_pings, fail_count FROM jobs WHERE username=?", (x_user,))
    jobs = [{"id": r[0], "label": r[1], "url": r[2], "interval": r[3], "status": r[4], "total": r[5], "fails": r[6]} for r in cursor.fetchall()]
    
    cursor.execute("SELECT tg_token, tg_chat FROM settings WHERE username=?", (x_user,))
    s = cursor.fetchone()
    settings = {"tg_token": s[0], "tg_chat": s[1]} if s else {"tg_token": "", "tg_chat": ""}
    conn.close()
    
    logs = user_logs.get(x_user, ["[SYSTEM] Workspace active... Awaiting connection."])
    graph = user_graphs.get(x_user, {"labels": [], "data": []})
    return {"jobs": jobs, "settings": settings, "logs": logs, "graph": graph}

@app.post("/api/job")
def save_job(job: JobData, x_user: str = Header("default")):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    if job.id:
        cursor.execute("UPDATE jobs SET label=?, url=?, interval=? WHERE id=? AND username=?", (job.label, job.url, job.interval, job.id, x_user))
        log_msg(x_user, f"Updated Monitor: {job.label}")
    else:
        cursor.execute("INSERT INTO jobs (username, label, url, interval) VALUES (?, ?, ?, ?)", (x_user, job.label, job.url, job.interval))
        log_msg(x_user, f"Deployed New Monitor: {job.label}")
    conn.commit()
    conn.close()
    return {"status": "ok"}

@app.post("/api/del/{jid}")
def del_job(jid: int, x_user: str = Header("default")):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM jobs WHERE id = ? AND username = ?", (jid, x_user))
    conn.commit()
    conn.close()
    log_msg(x_user, f"Deleted Monitor ID: {jid}")
    return {"status": "ok"}

@app.post("/api/settings")
def update_settings(s: SettingsData, x_user: str = Header("default")):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT username FROM settings WHERE username=?", (x_user,))
    if cursor.fetchone():
        cursor.execute("UPDATE settings SET tg_token=?, tg_chat=? WHERE username=?", (s.tg_token, s.tg_chat, x_user))
    else:
        cursor.execute("INSERT INTO settings (username, tg_token, tg_chat) VALUES (?, ?, ?)", (x_user, s.tg_token, s.tg_chat))
    conn.commit()
    conn.close()
    return {"status": "ok"}

async def pinger():
    while True:
        await asyncio.sleep(30)
        try:
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("SELECT id, username, label, url, total_pings, fail_count FROM jobs")
            rows = cursor.fetchall()
            
            if rows:
                async with httpx.AsyncClient(timeout=10) as client:
                    for r in rows:
                        jid, uname, label, url, total_pings, fail_count = r
                        new_total = total_pings + 1
                        success = False
                        
                        start_time = time.time()
                        try:
                            resp = await client.get(url)
                            if resp.status_code == 200:
                                success = True
                                log_msg(uname, f"Signal [{label}] STATUS: SECURE (200 OK)")
                            else:
                                log_msg(uname, f"Signal [{label}] ALERT: Status {resp.status_code}")
                        except Exception:
                            log_msg(uname, f"Signal [{label}] CRITICAL: Server Offline!")
                            
                        resp_time = int((time.time() - start_time) * 1000) if success else 0
                        
                        if uname not in user_graphs:
                            user_graphs[uname] = {"labels": [], "data": []}
                        user_graphs[uname]["data"].append(resp_time if success else 0)
                        
                        new_fail = fail_count if success else fail_count + 1
                        cursor.execute("UPDATE jobs SET total_pings=?, fail_count=? WHERE id=?", (new_total, new_fail, jid))
                        conn.commit()
                        
                        if not success:
                            await send_telegram_alert(uname, f"Server '{label}' ({url}) is NOT responding!")
            conn.close()
        except Exception:
            pass

@app.on_event("startup")
def startup():
    asyncio.create_task(pinger())
