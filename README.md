# Sentra.AI - AI-Powered Security Consultant

An intelligent CLI-based security assessment tool that combines Nmap scanning, Nikto web vulnerability scanning, and AI-powered analysis to provide actionable security recommendations.

## 🚀 Features

- **Unified Scanning** - Combines Nmap (port scanning) + Nikto (web vulnerabilities)
- **AI Analysis** - Uses Kimi k2.5 via OpenRouter to interpret results and provide recommendations
- **Strict Verification** - Prevents unauthorized scanning with `sentra-verify.txt` validation
- **PDF Reports** - Export professional audit reports
- **Matrix-Themed CLI** - Clean, professional terminal interface using Rich

## 📋 Requirements

### System Requirements
- Python 3.11+
- [Nmap](https://nmap.org/download.html) (Windows installer)
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (for Nikto web scanning)

### API Keys
- [OpenRouter API Key](https://openrouter.ai/) (free tier available)

## 🛠️ Installation

```bash
# Clone the repository
git clone https://github.com/nua1m/Sentra-AI.git
cd Sentra-AI

# Create virtual environment
python -m venv venv
.\venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your OpenRouter API key
```

## ⚙️ Configuration

Create a `.env` file in the project root:

```env
OPENROUTER_API_KEY=sk-or-v1-your-key-here
MODEL=moonshotai/kimi-k2.5
```

## 🏃 Running

### 1. Start the Backend
```bash
uvicorn core.main:app --reload
```

### 2. Start the CLI (in a new terminal)
```bash
python sentra.py
```

### 3. Scan a Target
```
USER@SENTRA: scan localhost
```

## 📁 Project Structure

```
Dev/
├── core/                    # Backend modules
│   ├── main.py              # FastAPI application
│   ├── scanner.py           # Nmap & Nikto wrappers
│   ├── intelligence.py      # AI integration (OpenRouter/Kimi)
│   ├── security.py          # Target verification logic
│   └── reporting.py         # PDF report generation
├── sentra.py                # CLI client (Rich UI)
├── requirements.txt         # Python dependencies
└── .env                     # Configuration (not in git)
```

## 🔒 Strict Verification (Option A)

To scan a public target, you must prove ownership by hosting a file:

1. Create `sentra-verify.txt` on the target's web root
2. File must contain your verification token
3. Sentra will check `http://<target>/sentra-verify.txt` before scanning

**Bypass**: Localhost and private IPs (192.168.x.x, 10.x.x.x) skip verification.

## 🐳 Testing with DVWA

To test the web scanner, run a vulnerable web app:

```bash
docker run -d --name dvwa -p 80:80 vulnerables/web-dvwa
```

Then scan: `scan localhost`

## 📄 PDF Reports

After each scan, you'll be prompted to export a PDF report containing:
- Executive Summary (AI-generated)
- Technical Details (Nmap output)
- Web Vulnerabilities (Nikto findings)

## 🔧 Troubleshooting

| Issue | Solution |
|-------|----------|
| "Nmap not found" | Install Nmap and restart terminal |
| "Docker not running" | Start Docker Desktop |
| "API Key missing" | Check `.env` file |
| Nikto empty | Ensure Docker is running before starting backend |

## 📜 License

MIT License - See LICENSE file

## 👤 Author

Final Year Project - Cybersecurity
