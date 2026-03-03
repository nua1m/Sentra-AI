# Sentra.AI — Intelligent Security Assessment Agent

> ⚠️ **NOTICE:** Sentra.AI is currently a **Work In Progress**. Features, UI, and APIs are subject to change continuously.

An AI-powered security assessment engine that autonomously selects and executes security tools based on target reconnaissance. Unlike static scanners, Sentra uses an intelligent agent pipeline: it runs Nmap first, then asks AI which follow-up tools are relevant, executes them dynamically, and generates remediation playbooks.

## ✨ Key Features

| Feature | Description |
|---------|-------------|
| **Intelligent Agent Pipeline** | AI decides which tools to run based on Nmap findings |
| **Pluggable Tool Registry** | 4 tools (Nmap, Nikto, SSLScan, Gobuster) — easily extensible |
| **AI Threat Analysis** | Kimi k2.5 cross-references CVE/NVD databases |
| **Conversation Memory** | Ask follow-up questions about scan results |
| **Automated Remediation** | Generates OS-specific fix scripts with MITRE ATT&CK mapping |
| **Risk Scoring** | 0–10 heuristic based on ports, vulns, and severity |
| **PDF Reports** | Professional audit reports with findings and fixes |
| **Strict Verification** | `sentra-verify.txt` prevents unauthorized scanning |

## 📋 Requirements

- **Python 3.11+**
- **Node.js 18+** (for dashboard)
- **[Nmap](https://nmap.org/download.html)** (required — core reconnaissance tool)
- **[OpenRouter API Key](https://openrouter.ai/)** (free tier works with Kimi models)

### Optional Tools (auto-detected)
| Tool | Install | Purpose |
|------|---------|---------|
| Nikto | Docker: `docker pull frapsoft/nikto` | Web vulnerability scanning |
| SSLScan | `choco install sslscan` / `apt install sslscan` | TLS/SSL certificate audit |
| Gobuster | `choco install gobuster` / `apt install gobuster` | Directory enumeration |

> The agent will only select tools that are installed. If only Nmap is available, it works fine — just fewer scan layers.

## 🛠️ Installation

```bash
# 1. Clone
git clone https://github.com/nua1m/Sentra-AI.git
cd Sentra-AI

# 2. Backend
python -m venv venv
# Windows: .\venv\Scripts\activate
# Linux/Mac: source venv/bin/activate
pip install -r requirements.txt

# 3. Environment
# Copy .env.example to .env and add your API key:
# OPENROUTER_API_KEY=sk-or-v1-your-key-here

# 4. Frontend
cd dashboard
npm install
```

## 🚀 Running

### Method A: Docker Compose (Recommended)
This approach pre-installs all critical hacking tools (Nmap, Nikto, Playwright, etc.) into a cohesive containerized environment, ensuring the Agent runs flawlessly regardless of your host OS.
```bash
# Start the full stack (Frontend, Backend, and Agent Tools)
docker-compose up --build
```
> Dashboard runs at `http://localhost:5173`
> API runs at `http://localhost:8000`

### Method B: Manual Python & Node Setup
If you prefer running natively, open **two terminals**:

**Terminal 1 — Backend API:**
```bash
# Ensure Nmap and dependencies are installed natively on your OS!
playwright install chromium
# Activate your venv first!
uvicorn core.app:app --reload
```
> API runs at `http://localhost:8000`

**Terminal 2 — Web Dashboard:**
```bash
cd dashboard
npm install && npm run dev
```
> Dashboard at `http://localhost:5173`

### Using the Dashboard
1. Open `http://localhost:5173`
2. Type **"Scan localhost"** in the chat
3. Watch the agent:
   - **Phase 1**: Nmap scans the target
   - **Phase 2**: AI selects follow-up tools based on open ports
   - **Phase 3**: AI analyzes all findings
   - **Phase 4**: Remediation playbooks generated
4. Click tabs to view each tool's raw output
5. Ask follow-up questions: *"What's the biggest risk?"*

### Using the CLI
```bash
python sentra.py
# Then type: scan localhost
```

## 🧪 Testing & Code Quality

```bash
# Run all tests (25 tests)
python -m pytest tests/ -v

# Lint check (0 errors expected)
ruff check core/

# Security scan
bandit -r core/ -ll
```

### Test Coverage
| Module | Tests | Covers |
|--------|-------|--------|
| Tool Registry | 10 | Port triggers, availability, commands |
| Intelligence | 5 | Intent detection, AI tool selection, fallback |
| Remediation | 6 | OS detection, port parsing, fix structure |
| Risk Scoring | 4 | Boundary values, severity weights |

## 📁 Project Structure

```
Sentra-AI/
├── core/                       # Backend
│   ├── main.py                 # FastAPI app + dynamic scan pipeline
│   ├── tools.py                # Pluggable tool registry (4 tools)
│   ├── intelligence.py         # AI: intent, tool selection, memory
│   ├── remediation.py          # Fix playbook generator
│   ├── security.py             # Target ownership verification
│   ├── database.py             # SQLite persistence
│   └── reporting.py            # PDF report generation
├── dashboard/                  # React + Vite + Tailwind v4
│   └── src/
│       ├── components/         # ResultCard, Sidebar, AgentTerminal
│       └── pages/              # ChatPage, HistoryPage
├── tests/
│   └── test_core.py            # 25 tests (pytest)
├── pyproject.toml              # Ruff + pytest config
├── sentra.py                   # CLI client
├── requirements.txt            # Python deps
└── .env                        # Config (not in git)
```

## 🔒 Target Verification

| Target Type | Verification |
|-------------|-------------|
| `localhost`, `127.0.0.1` | Auto-allowed |
| Private IPs (`192.168.x.x`, `10.x.x.x`) | Auto-allowed |
| Public domains | Must host `sentra-verify.txt` on web root |

## 🐳 Testing with DVWA

Test against a real vulnerable target:
```bash
docker run -d --name dvwa -p 80:80 vulnerables/web-dvwa
# Then scan "localhost" in Sentra
```

## 🔧 Troubleshooting

| Issue | Solution |
|-------|----------|
| "Nmap not found" | Install Nmap and add to PATH |
| "Docker not running" | Start Docker Desktop for Nikto |
| "API Key missing" | Check `.env` file |
| Frontend won't start | Run `npm install` in `dashboard/` |
| Ruff errors after editing | Run `ruff check core/ --fix` |

## 📜 License
MIT License

## 👤 Author
Final Year Project — Cybersecurity
