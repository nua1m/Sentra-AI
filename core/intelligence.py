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

import re

def process_chat_query(message: str) -> dict:
    """
    Determines user intent from CLI input AND generates a response if it's a chat.
    Makes only ONE call to the AI to slash latency in half.
    Returns JSON: {"action": "scan", "target": "..."} OR {"action": "chat", "message": "..."}
    """
    # 1. Faster Regex Check (Skips AI entirely for obvious commands)
    scan_match = re.search(r"^(?:scan|check|test|analyze)\s+([a-zA-Z0-9.-]+)$", message.strip(), re.IGNORECASE)
    if scan_match:
        return {"action": "scan", "target": scan_match.group(1)}
        
    # 2. Unified AI Call for everything else
    system_prompt = """You are Sentra.AI, an expert cybersecurity assistant.
The user will provide a message. Determine if they want to initiate a vulnerability scan on a specific target (IP or domain), OR if they are asking a security-related question/chatting.

RULES:
1. You MUST respond ONLY with a raw JSON object. Do NOT wrap it in ```json blocks. No conversational filler.
2. If the user wants to scan a target, output:
{"action": "scan", "target": "<ip_or_domain>"}

3. If the user is just asking a question (e.g. "What is Nmap?", "hello"), output a helpful, detailed response:
{"action": "chat", "message": "<your response>"}
"""
    
    try:
        response_text = ask_kimi(message, system_prompt=system_prompt)
        
        # Strip markdown code blocks if present
        clean = response_text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean)
    except Exception as e:
        logger.error(f"Failed to parse Unified AI Response: {e}")
        # Fallback if AI fails to return valid JSON
        return {"action": "chat", "message": "I processed that, but encountered a formatting error on my end. Could you rephrase?"}
