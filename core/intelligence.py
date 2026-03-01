import json
import logging
import os
import re
import requests
import httpx
from typing import AsyncGenerator
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
    Makes ONLY ONE call to the AI to slash latency in half, completely replacing fragile Regex routing.
    Returns JSON: {"action": "scan", "target": "..."} OR {"action": "chat", "message": "..."}
    """
    system_prompt = """You are Sentra.AI, an expert cybersecurity assistant.
The user will provide a message. Determine if they want to initiate a vulnerability scan on a specific target (IP or domain), run a shell command, provision/setup a server, attack a server, OR if they are asking a security-related question/chatting.

RULES:
1. You MUST respond ONLY with a raw JSON object. Do NOT wrap it in ```json blocks. No conversational filler.
2. If the user wants to initiate a vulnerability scan (e.g. nmap, nikto, dirb) on a target (or implied target), output:
{"action": "scan", "target": "<ip_or_domain_or_localhost>"} 
If they specify tools, include them: {"action": "scan", "target": "<target>", "tools": ["nmap", ...]}
3. If the user wants to run an arbitrary shell command (EXCEPT vulnerability scanners - use rule 2 for that), output:
{"action": "shell", "command": "<the full shell command>"}
4. If the user explicitly asks to ATTACK, PEN-TEST, BRUTE FORCE, or PURPLE TEAM a target, output:
{"action": "attack", "target": "<ip_or_domain_or_localhost>"}
5. If the user asks to SETUP, PROVISION, HARDEN, or CONNECT TO a server/host, output:
{"action": "setup", "target": "<ip_or_domain_or_localhost_if_provided>"}
6. If the user is just asking a question (e.g. "What is Nmap?", "hello"), output a helpful, detailed response:
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


async def ask_kimi_stream(prompt: str, system_prompt: str = "You are Sentra.AI, a cybersecurity expert.") -> AsyncGenerator[str, None]:
    """
    Asynchronous streaming call to OpenRouter. Yields tokens.
    """
    settings = get_settings()
    api_key = settings.get("openrouter_api_key") or os.getenv("OPENROUTER_API_KEY")

    if not api_key or "your-key-here" in api_key:
        yield "Error: OpenRouter API Key is missing. Please configure it in the UI Settings."
        return

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
        "temperature": 0.3, # Low temp for factual security reporting
        "stream": True
    }

    try:
        async with httpx.AsyncClient() as client:
            async with client.stream("POST", OPENROUTER_URL, headers=headers, json=payload, timeout=60) as response:
                if response.status_code != 200:
                    text_error = await response.aread()
                    yield f"AI Error ({response.status_code}): {text_error.decode('utf-8')}"
                    return
                
                async for chunk in response.aiter_lines():
                    if chunk.startswith("data: "):
                        data_str = chunk[6:]
                        if data_str == "[DONE]":
                            break
                        try:
                            data = json.loads(data_str)
                            if "choices" in data and len(data["choices"]) > 0:
                                delta = data["choices"][0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    yield content
                        except Exception:
                            pass
    except Exception as e:
        yield f"Connection Failed: {e}"


async def stream_chat_intent(message: str) -> AsyncGenerator[dict, None]:
    """
    Reads tokens from the LLM, infers the action dynamically mid-stream,
    yields intermediate status events, and finally yields the parsed JSON.
    """
    system_prompt = """You are Sentra.AI, an expert cybersecurity assistant.
The user will provide a message. Determine if they want to initiate a vulnerability scan on a specific target (IP or domain), run a shell command, provision/setup a server, attack a server, OR if they are asking a security-related question/chatting.

RULES:
1. You MUST respond ONLY with a raw JSON object. Do NOT wrap it in ```json blocks. No conversational filler.
2. If the user wants to initiate a vulnerability scan (e.g. nmap, nikto, dirb) on a target (or implied target), output:
{"action": "scan", "target": "<ip_or_domain_or_localhost>"} 
If they specify tools, include them: {"action": "scan", "target": "<target>", "tools": ["nmap", ...]}
3. If the user wants to run an arbitrary shell command (EXCEPT vulnerability scanners - use rule 2 for that), output:
{"action": "shell", "command": "<the full shell command>"}
4. If the user explicitly asks to ATTACK, PEN-TEST, BRUTE FORCE, or PURPLE TEAM a target, output:
{"action": "attack", "target": "<ip_or_domain_or_localhost>"}
5. If the user asks to SETUP, PROVISION, HARDEN, or CONNECT TO a server/host, output:
{"action": "setup", "target": "<ip_or_domain_or_localhost_if_provided>"}
6. If the user is just asking a question (e.g. "What is Nmap?", "hello"), output a helpful, detailed response:
{"action": "chat", "message": "<your response>"}
"""
    
    buffer = ""
    action_sent = False
    
    async for token in ask_kimi_stream(message, system_prompt=system_prompt):
        # Pass up API errors immediately if they occur
        if "Error:" in token or "Connection Failed:" in token or "AI Error" in token:
            yield {"type": "final_intent", "data": {"action": "chat", "message": token}}
            return
            
        buffer += token
        
        # Try to excitedly deduce the action mid-stream to update the UI Loader!
        if not action_sent:
            action_match = re.search(r'"action"\s*:\s*"([^"]+)"', buffer)
            if action_match:
                action = action_match.group(1)
                
                # Yield the exact loader text we want to show based on the AI's internal thought process!
                if action == "chat":
                    yield {"type": "status", "data": "Generating Answer..."}
                elif action == "shell":
                    yield {"type": "status", "data": "Writing Command..."}
                elif action == "scan":
                    yield {"type": "status", "data": "Preparing Scan Engine..."}
                elif action == "setup":
                    yield {"type": "status", "data": "Initializing Provisioning Agent..."}
                elif action == "attack":
                    yield {"type": "status", "data": "Verifying Purple Team Auth..."}
                else:
                    yield {"type": "status", "data": f"Processing {action} request..."}
                    
                action_sent = True
                
    # Once the stream is entirely complete, parse the final JSON buffer
    try:
        clean = buffer.replace("```json", "").replace("```", "").strip()
        final_json = json.loads(clean)
        yield {"type": "final_intent", "data": final_json}
    except Exception as e:
        logger.error(f"Failed to parse Streaming Unified AI Response: {e} | Buffer: {buffer}")
        yield {"type": "final_intent", "data": {"action": "chat", "message": "I processed that, but encountered a formatting error on my end. Could you rephrase?"}}



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
