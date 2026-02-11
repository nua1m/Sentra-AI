import os
import requests
import logging
import json
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("sentra.intelligence")

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "moonshotai/kimi-k2.5"

def ask_kimi(prompt: str, system_prompt: str = "You are Sentra.AI, a cybersecurity expert.") -> str:
    """
    Synchronous call to OpenRouter (Kimi k2.5).
    """
    # Reload env to pick up changes without restart
    load_dotenv(override=True)
    api_key = os.getenv("OPENROUTER_API_KEY")

    if not api_key or "your-key-here" in api_key:
        logger.error(f"API Key Invalid. Value: {api_key}")
        return "Error: OpenRouter API Key is missing or default. Check .env."

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "X-Title": "Sentra.AI CLI"
    }

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3 # Low temp for factual security reporting
    }

    try:
        resp = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=60)
        if resp.status_code == 200:
            data = resp.json()
            return data['choices'][0]['message']['content']
        else:
            return f"AI Error ({resp.status_code}): {resp.text}"
    except Exception as e:
        return f"Connection Failed: {e}"

def analyze_results(nmap_output: str, nikto_output: str = "No Nikto scan performed.") -> str:
    prompt = f"""
    Analyze these security scan results (Nmap + Nikto) and provide a concise assessment:
    
    === NMAP SCAN ===
    {nmap_output[:3000]}
    
    === NIKTO WEB SCAN ===
    {nikto_output[:3000]}
    
    Format as:
    1. **Summary**: What is running?
    2. **Risks**: Potential vulnerabilities (if any obvious versions).
    3. **Recommendations**: Basic hardening steps.
    """
    return ask_kimi(prompt)

def classify_intent(message: str) -> dict:
    """
    Determines user intent from CLI input.
    Returns JSON: {"action": "scan"|"chat", "target": "..."}
    """
    prompt = f"""
    Extract intent from: "{message}"
    Return JSON only:
    {{
        "action": "scan" or "chat",
        "target": "IP/Domain" or null,
        "scan_type": "full" or "quick"
    }}
    If user wants to scan, set action=scan. If just talking, action=chat.
    """
    
    try:
        response = ask_kimi(prompt, system_prompt="You are a JSON extractor. Output ONLY JSON.")
        # Strip markdown code blocks if present
        clean = response.replace("```json", "").replace("```", "").strip()
        return json.loads(clean)
    except:
        return {"action": "chat", "target": None}
