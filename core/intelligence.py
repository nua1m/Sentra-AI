import json
import logging
import os
import re
import requests
from dotenv import load_dotenv

from .database import get_settings

load_dotenv()
logger = logging.getLogger("sentra.intelligence")

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

def ask_kimi(prompt: str, system_prompt: str = "You are Sentra.AI, a cybersecurity expert.") -> str:
    """
    Synchronous call to OpenRouter.
    """
    # Fetch API Key and Model dynamically from DB
    settings = get_settings()
    api_key = settings.get("openrouter_api_key")
    
    # Fallback to env file if db setting is empty
    if not api_key:
        api_key = os.getenv("OPENROUTER_API_KEY")

    if not api_key or "your-key-here" in api_key:
        logger.error(f"API Key Invalid. Value: {api_key}")
        return "Error: OpenRouter API Key is missing. Please configure it in the UI Settings."

    model = settings.get("ai_model", "moonshotai/kimi-k2.5")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "X-Title": "Sentra.AI CLI"
    }

    payload = {
        "model": model,
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




def process_chat_query(message: str) -> dict:
    """
    Determines user intent from CLI input AND generates a response if it's a chat.
    Makes only ONE call to the AI to slash latency in half.
    Returns JSON: {"action": "scan", "target": "..."} OR {"action": "chat", "message": "..."}
    """
    # 1. Tool-specific scan request (e.g. "run nmap on localhost", "nmap 192.168.1.1")
    tool_names = ["nmap", "nikto", "sslscan", "gobuster"]
    tool_pattern = "|".join(tool_names)
    tool_match = re.search(
        rf"^(?:can\s+you\s+|could\s+you\s+|can\s+u\s+|please\s+)?(?:run|execute|use|start)?\s*({tool_pattern})\s+(?:on\s+|against\s+)?([a-zA-Z0-9.-]+)$",
        message.strip(), re.IGNORECASE
    )
    if tool_match:
        return {"action": "scan", "target": tool_match.group(2), "tools": [tool_match.group(1).lower()]}

    # 2. General scan request (e.g. "scan localhost", "check example.com")
    scan_match = re.search(r"^(?:can\s+you\s+|could\s+you\s+|can\s+u\s+|please\s+)?(?:scan|check|test|analyze)\s+([a-zA-Z0-9.-]+)$", message.strip(), re.IGNORECASE)
    if scan_match:
        return {"action": "scan", "target": scan_match.group(1)}

    # 3. Attack/Purple Team request
    attack_match = re.search(r"^(?:can\s+you\s+|could\s+you\s+|can\s+u\s+|please\s+)?(?:attack|hack|exploit|purple\s+team)\s+([a-zA-Z0-9.-]+)$", message.strip(), re.IGNORECASE)
    if attack_match:
        return {"action": "attack", "target": attack_match.group(1)}

    # 4. Unified AI Call for everything else
    system_prompt = """You are Sentra.AI, an expert cybersecurity assistant.
The user will provide a message. Determine if they want to initiate a vulnerability scan on a specific target (IP or domain), run a shell command, OR if they are asking a security-related question/chatting.

RULES:
1. You MUST respond ONLY with a raw JSON object. Do NOT wrap it in ```json blocks. No conversational filler.
2. If the user wants to initiate a vulnerability scan (e.g. nmap, nikto, dirb) on a target, output:
{"action": "scan", "target": "<ip_or_domain>"}
3. If the user wants to run a shell command (EXCEPT vulnerability scanners - use rule 2 for that), output:
{"action": "shell", "command": "<the full shell command>"}
4. If the user explicitly asks to ATTACK, PEN-TEST, or PURPLE TEAM a target, output:
{"action": "attack", "target": "<ip_or_domain>"}
5. If the user is just asking a question (e.g. "What is Nmap?", "hello"), output a helpful, detailed response:
{"action": "chat", "message": "<your response>"}
"""

    try:
        response_text = ask_kimi(message, system_prompt=system_prompt)

        # Intercept string-based authentication/connection API errors from ask_kimi
        if response_text.startswith("Error: OpenRouter API Key") or "AI Error" in response_text or "Connection Failed" in response_text:
            return {"action": "chat", "message": f"API Error: {response_text}"}

        # Strip markdown code blocks if present
        clean = response_text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean)
    except Exception as e:
        logger.error(f"Failed to parse Unified AI Response: {e}")
        # Fallback if AI fails to return valid JSON
        return {"action": "chat", "message": "I processed that, but encountered a formatting error on my end. Could you rephrase?"}


# ═══════════════════════════════════════════════════════════════
# AGENT: AI TOOL SELECTION (v2)
# ═══════════════════════════════════════════════════════════════

def select_tools(nmap_output: str, available_tools: list) -> list:
    """
    AI decides which follow-up tools to run after Nmap based on findings.
    Returns a list of tool names to execute.
    """
    tool_descriptions = "\n".join(
        f"- {t['name']}: {t['description']} (triggers on ports: {', '.join(t['ports'])})"
        for t in available_tools
    )

    prompt = f"""You are a security assessment agent. Based on the Nmap scan results below, decide which follow-up tools to run.

AVAILABLE TOOLS:
{tool_descriptions}

NMAP SCAN RESULTS:
{nmap_output[:3000]}

RULES:
1. Select ONLY tools whose relevant ports are open in the Nmap results.
2. If no web ports (80, 443, 8080, 8443) are open, do NOT select web-focused tools.
3. If port 443 is open, select sslscan for TLS audit.
4. If any web port is open, select nikto for vulnerability scanning.
5. Respond with ONLY a raw JSON array of tool names. Example: ["nikto", "sslscan"]
6. If no follow-up tools are appropriate, respond with: []
"""

    try:
        response = ask_kimi(prompt, system_prompt="You are a security tool orchestrator. Respond ONLY with JSON.")
        clean = response.replace("```json", "").replace("```", "").strip()
        selected = json.loads(clean)
        if isinstance(selected, list):
            # Validate tool names
            valid_names = {t['name'] for t in available_tools}
            return [name for name in selected if name in valid_names]
    except Exception as e:
        logger.error(f"AI tool selection failed: {e}")

    # Fallback: use port-based heuristic
    logger.info("Falling back to port-based tool selection")
    return [t['name'] for t in available_tools if any(
        f"{p}/tcp" in nmap_output or f" {p}/" in nmap_output
        for p in t['ports']
    )]


# ═══════════════════════════════════════════════════════════════
# CONVERSATION MEMORY (v2)
# ═══════════════════════════════════════════════════════════════

# In-memory per-scan conversation history
_conversation_memory: dict = {}

def chat_with_context(message: str, scan_id: str | None = None, scan_data: dict | None = None) -> str:
    """
    AI chat with scan context awareness. Enables follow-up questions about results.
    """
    # Build conversation history
    if scan_id not in _conversation_memory:
        _conversation_memory[scan_id] = []

    history = _conversation_memory.get(scan_id, [])

    # Build system prompt with scan context
    system_prompt = "You are Sentra.AI, an expert cybersecurity assistant."

    if scan_data:
        context = f"""
You have access to the following scan data for context:
- Target: {scan_data.get('target', 'unknown')}
- Risk Score: {scan_data.get('risk_score', 'N/A')}/10 ({scan_data.get('risk_label', 'N/A')})
- Open Ports Summary: {scan_data.get('nmap', 'No data')[:500]}
- AI Analysis: {scan_data.get('analysis', 'No analysis')[:1000]}
- Tools Used: {', '.join(scan_data.get('tools_used', ['nmap', 'nikto']))}

Use this context to answer the user's follow-up questions precisely. Reference specific findings and ports when relevant.
"""
        system_prompt += context

    # Build messages with recent history (keep last 6 turns)
    messages = [{"role": "system", "content": system_prompt}]
    for turn in history[-6:]:
        messages.append(turn)
    messages.append({"role": "user", "content": message})

    try:
        load_dotenv(override=True)
        api_key = os.getenv("OPENROUTER_API_KEY")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "X-Title": "Sentra.AI"
        }

        payload = {
            "model": MODEL,
            "messages": messages,
            "temperature": 0.3
        }

        resp = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=60)
        if resp.status_code == 200:
            reply = resp.json()['choices'][0]['message']['content']

            # Save to memory
            if scan_id:
                _conversation_memory.setdefault(scan_id, [])
                _conversation_memory[scan_id].append({"role": "user", "content": message})
                _conversation_memory[scan_id].append({"role": "assistant", "content": reply})

            return reply
        return f"AI Error ({resp.status_code}): {resp.text}"
    except Exception as e:
        return f"Connection Failed: {e}"
