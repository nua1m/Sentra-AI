# Sentra.AI - AI-Powered Security Consultant

An intelligent security assessment tool that combines Nmap scanning, Nikto web vulnerability scanning, and AI-powered analysis to provide actionable security recommendations and automated remediation playbooks.

## 🚀 Features

- **Unified Scanning** - Combines Nmap (port scanning) + Nikto (web vulnerabilities)
- **AI Analysis & Remediation** - Uses Kimi k2.5 via OpenRouter to interpret results and generate tactical fix scripts.
- **Web Dashboard** - A sleek, modern SaaS UI built with React, Vite, and Tailwind CSS v4.
- **Rich CLI** - A Matrix-themed terminal interface using Python Rich for terminal lovers.
- **Strict Verification** - Prevents unauthorized scanning with `sentra-verify.txt` validation.
- **PDF Reports** - Export professional audit reports containing findings and fixes.

## 📋 Requirements

### System Requirements
- Python 3.11+
- Node.js 18+ (for Web Dashboard)
- [Nmap](https://nmap.org/download.html) (Windows installer or `apt install nmap`)
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) or Docker Engine (required for Nikto web scanning)

### API Keys
- [OpenRouter API Key](https://openrouter.ai/) (free tier available with Kimi models)

## 🛠️ Installation

```bash
# 1. Clone the repository
git clone https://github.com/nua1m/Sentra-AI.git
cd Sentra-AI

# 2. Backend Setup
python -m venv venv
# Windows: .\venv\Scripts\activate
# Linux/Mac: source venv/bin/activate
pip install -r requirements.txt

# 3. Configure Environment
# Create .env in the root based on .env.example
# Add OPENROUTER_API_KEY=sk-or-v1-your-key-here

# 4. Frontend Setup
cd dashboard
npm install
```

## ⚙️ Configuration

Create a `.env` file in the project root:

```env
OPENROUTER_API_KEY=sk-or-v1-your-key-here
MODEL=moonshotai/kimi-k2.5
```

## 🏃 How to Launch the UI & Backend

You need to run both the Backend API and the Frontend Dashboard simultaneously in two separate terminal windows.

**Terminal 1 (Start the Backend API):**
```bash
# 1. Open a new terminal and ensure you are in the project root directory

# 2. Ensure your Python virtual environment is activated!
# Windows cmd: venv\Scripts\activate.bat
# Windows PS: .\venv\Scripts\Activate.ps1
# Mac/Linux: source venv/bin/activate

uvicorn core.main:app --reload
```
*The API is now running at `http://localhost:8000`*

**Terminal 2 (Start the Web Dashboard UI):**
```bash
# 1. Open a new terminal and ensure you are in the project root directory
# 2. Navigate into the dashboard folder
cd dashboard

# 3. Start the UI
npm run dev
```
*The UI is now running at `http://localhost:5173`*

### 🚀 Access the Dashboard
1. Open your web browser and go to `http://localhost:5173`.
2. Toggle Dark Mode using the Sun/Moon icon in the top right.
3. Type **"Scan localhost"** in the Intelligent Remediation input box to begin a test scan!

### Option B: Command Line Interface (CLI)

**Terminal 1 (Backend API):**
```bash
cd Sentra-AI
uvicorn core.main:app --reload
```

**Terminal 2 (CLI Client):**
```bash
cd Sentra-AI
python sentra.py
```
*Inside the CLI, run: `scan localhost`*

## 📁 Project Structure

```
Dev/
├── core/                    # Backend modules
│   ├── main.py              # FastAPI application (uvicorn entrypoint)
│   ├── scanner.py           # Nmap & Nikto subprocess wrappers
│   ├── intelligence.py      # AI integration (OpenRouter/Kimi)
│   ├── remediation.py       # Automated fix playbook generation
│   ├── security.py          # Target ownership verification logic
│   └── database.py          # SQLite persistence layer
├── dashboard/               # Frontend React Application
│   ├── src/                 # React components (TopBar, Sidebar, ChatPage)
│   └── index.css            # Tailwind v4 theme configuration
├── sentra.py                # Legacy CLI client (Rich UI)
├── requirements.txt         # Python dependencies
└── .env                     # Configuration (not in git)
```

## 🔒 Strict Verification

To scan a public target (e.g., `example.com`), you must prove ownership:
1. Create `sentra-verify.txt` on the target's web root.
2. The file must contain your verification token.
3. Sentra will check `http://<target>/sentra-verify.txt` before scanning.

**Bypass**: Localhost and private IPs (192.168.x.x, 10.x.x.x) skip verification automatically.

## 🐳 Testing with DVWA

To test the web scanner locally without permission issues, run a vulnerable web app:

```bash
docker run -d --name dvwa -p 80:80 vulnerables/web-dvwa
```
Then scan targeting `localhost`.

## 📄 PDF Reports

After a scan finishes, you can export a professional PDF containing:
- Executive Summary (AI-generated)
- Technical Net Scan Details (Nmap)
- Web Vulnerabilities (Nikto)
- **Actionable Remediation Playbooks** (Commands + Descriptions)

## 🔧 Troubleshooting

| Issue | Solution |
|-------|----------|
| "Nmap not found" | Install Nmap and ensure it is in your system PATH. |
| "Docker not running" | Start Docker Desktop before running a scan. |
| "API Key missing" | Check `.env` file in the root directory. |
| Nikto timeouts/errors | Ensure port 80/443 mapping is correct if testing on Docker targets. |
| Frontend won't start | Run `npm install` inside the `dashboard/` folder first. |

## 📜 License
MIT License

## 👤 Author
Final Year Project - Cybersecurity
