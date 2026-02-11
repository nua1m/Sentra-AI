"""
Sentra.AI Remediation Module
Generates actionable fix commands from scan findings.
"""
import re
import logging
from typing import Dict, List, Optional
from .intelligence import ask_kimi

logger = logging.getLogger("sentra.remediation")

# ============================================
# FIX DATABASE - Known vulnerability patterns
# ============================================
FIX_DATABASE = {
    # SMB/Windows File Sharing
    "445/tcp": {
        "description": "SMB (Windows File Sharing) - High risk for ransomware/lateral movement",
        "severity": "HIGH",
        "windows": [
            "# Disable SMBv1 (EternalBlue mitigation)",
            "Set-SmbServerConfiguration -EnableSMB1Protocol $false -Force",
            "",
            "# Block SMB from external networks",
            "netsh advfirewall firewall add rule name=\"Block SMB Inbound\" dir=in action=block protocol=tcp localport=445"
        ],
        "linux": [
            "# Disable Samba if not needed",
            "sudo systemctl stop smbd && sudo systemctl disable smbd",
            "",
            "# Or block via firewall",
            "sudo ufw deny 445/tcp"
        ]
    },
    
    # RPC/DCOM
    "135/tcp": {
        "description": "MSRPC - Used for DCOM, potential for RPC exploits",
        "severity": "MEDIUM",
        "windows": [
            "# Block RPC from external networks",
            "netsh advfirewall firewall add rule name=\"Block RPC Inbound\" dir=in action=block protocol=tcp localport=135"
        ],
        "linux": [
            "# RPC typically not used on Linux",
            "sudo ufw deny 135/tcp"
        ]
    },
    
    # Telnet
    "23/tcp": {
        "description": "Telnet - Unencrypted remote access (CRITICAL)",
        "severity": "CRITICAL",
        "windows": [
            "# Disable Telnet server",
            "Stop-Service tlntsvr -Force",
            "Set-Service tlntsvr -StartupType Disabled"
        ],
        "linux": [
            "# Disable and remove telnet",
            "sudo systemctl stop telnet.socket && sudo systemctl disable telnet.socket",
            "sudo apt remove telnetd -y  # Debian/Ubuntu"
        ]
    },
    
    # FTP
    "21/tcp": {
        "description": "FTP - Unencrypted file transfer",
        "severity": "MEDIUM",
        "windows": [
            "# If FTP not needed, disable it",
            "Stop-Service ftpsvc -Force",
            "Set-Service ftpsvc -StartupType Disabled"
        ],
        "linux": [
            "# Switch to SFTP instead of FTP",
            "sudo systemctl stop vsftpd && sudo systemctl disable vsftpd"
        ]
    },
    
    # HTTP (may need hardening)
    "80/tcp": {
        "description": "HTTP - Unencrypted web traffic",
        "severity": "LOW",
        "windows": [
            "# Redirect HTTP to HTTPS (IIS)",
            "# Install URL Rewrite module, then add redirect rule",
            "# Or enforce HTTPS-only in application"
        ],
        "linux": [
            "# Redirect HTTP to HTTPS (Apache)",
            "sudo a2enmod rewrite",
            "# Add to .htaccess: RewriteRule ^(.*)$ https://%{HTTP_HOST}%{REQUEST_URI} [L,R=301]"
        ]
    }
}

# Nikto finding patterns
NIKTO_FIXES = {
    "directory indexing": {
        "description": "Directory listing enabled - exposes file structure",
        "severity": "MEDIUM",
        "windows": [
            "# Disable directory browsing in IIS",
            "Set-WebConfigurationProperty -pspath 'IIS:\\Sites\\Default Web Site' -filter /system.webServer/directoryBrowse -name enabled -value false"
        ],
        "linux": [
            "# Disable directory listing (Apache)",
            "echo 'Options -Indexes' | sudo tee -a /var/www/html/.htaccess"
        ]
    },
    "x-frame-options": {
        "description": "Missing X-Frame-Options header - clickjacking risk",
        "severity": "MEDIUM",
        "windows": [
            "# Add header in IIS via web.config",
            "# <customHeaders><add name=\"X-Frame-Options\" value=\"SAMEORIGIN\" /></customHeaders>"
        ],
        "linux": [
            "# Add header in Apache",
            "echo 'Header always set X-Frame-Options \"SAMEORIGIN\"' | sudo tee -a /etc/apache2/conf-available/security.conf"
        ]
    },
    "x-content-type-options": {
        "description": "Missing X-Content-Type-Options header",
        "severity": "LOW",
        "windows": [
            "# Add in web.config",
            "# <add name=\"X-Content-Type-Options\" value=\"nosniff\" />"
        ],
        "linux": [
            "# Add header in Apache",
            "sudo a2enmod headers",
            "echo 'Header always set X-Content-Type-Options \"nosniff\"' | sudo tee -a /etc/apache2/conf-available/security.conf"
        ]
    },
    "osvdb": {
        "description": "Known vulnerability in OSVDB database",
        "severity": "HIGH",
        "windows": ["# Update the affected software to the latest version"],
        "linux": ["sudo apt update && sudo apt upgrade -y"]
    }
}


def detect_os_from_scan(nmap_output: str) -> str:
    """
    Attempts to detect target OS from Nmap output.
    Returns 'windows', 'linux', or 'unknown'.
    """
    nmap_lower = nmap_output.lower()
    
    # Windows indicators
    windows_indicators = ["microsoft", "windows", "msrpc", "microsoft-ds", "netbios"]
    if any(ind in nmap_lower for ind in windows_indicators):
        return "windows"
    
    # Linux indicators
    linux_indicators = ["ubuntu", "debian", "centos", "linux", "openssh", "apache"]
    if any(ind in nmap_lower for ind in linux_indicators):
        return "linux"
    
    return "unknown"


def parse_open_ports(nmap_output: str) -> List[str]:
    """
    Extracts open ports from Nmap output.
    Returns list like ['22/tcp', '80/tcp', '445/tcp']
    """
    ports = []
    for line in nmap_output.split("\n"):
        # Match lines like "22/tcp  open  ssh"
        match = re.match(r"(\d+/tcp)\s+open", line)
        if match:
            ports.append(match.group(1))
    return ports


def generate_fixes(nmap_output: str, nikto_output: str = "", os_hint: Optional[str] = None) -> Dict:
    """
    Main function to generate remediation commands.
    
    Returns:
    {
        "os_detected": "windows",
        "findings": [
            {
                "port": "445/tcp",
                "description": "SMB...",
                "severity": "HIGH",
                "commands": ["...", "..."]
            }
        ],
        "ai_recommendations": "..."
    }
    """
    # Detect OS if not provided
    detected_os = os_hint or detect_os_from_scan(nmap_output)
    logger.info(f"OS Detection: {detected_os}")
    
    findings = []
    
    # 1. Process Nmap ports
    open_ports = parse_open_ports(nmap_output)
    for port in open_ports:
        if port in FIX_DATABASE:
            fix_info = FIX_DATABASE[port]
            commands = fix_info.get(detected_os, fix_info.get("windows", []))
            findings.append({
                "source": "nmap",
                "port": port,
                "description": fix_info["description"],
                "severity": fix_info["severity"],
                "commands": commands
            })
    
    # 2. Process Nikto findings
    nikto_lower = nikto_output.lower()
    for pattern, fix_info in NIKTO_FIXES.items():
        if pattern in nikto_lower:
            commands = fix_info.get(detected_os, fix_info.get("linux", []))
            findings.append({
                "source": "nikto",
                "finding": pattern,
                "description": fix_info["description"],
                "severity": fix_info["severity"],
                "commands": commands
            })
    
    # 3. AI fallback for complex findings
    ai_recommendations = ""
    if len(findings) < 2 or "unknown" in detected_os:
        # Ask AI for additional recommendations
        ai_recommendations = _ask_ai_for_fixes(nmap_output, nikto_output, detected_os)
    
    return {
        "os_detected": detected_os,
        "findings": findings,
        "ai_recommendations": ai_recommendations
    }


def _ask_ai_for_fixes(nmap_output: str, nikto_output: str, os_type: str) -> str:
    """
    Asks AI to generate fix commands for findings not in our database.
    """
    prompt = f"""
    Based on these scan results, generate specific remediation commands.
    Target OS appears to be: {os_type}
    
    === NMAP ===
    {nmap_output[:2000]}
    
    === NIKTO ===
    {nikto_output[:2000]}
    
    For each vulnerability found, provide:
    1. What the issue is
    2. The exact command to fix it (copy-pasteable)
    3. Mark severity as CRITICAL, HIGH, MEDIUM, or LOW
    
    Format as a numbered list. Focus on actionable commands, not general advice.
    """
    
    return ask_kimi(prompt, system_prompt="You are a Blue Team security engineer. Generate safe, specific remediation commands.")


def format_fixes_for_display(fixes_data: Dict) -> str:
    """
    Formats fixes for CLI display with Rich-compatible markdown.
    """
    lines = []
    lines.append(f"**Detected OS:** {fixes_data['os_detected'].upper()}")
    lines.append("")
    
    if not fixes_data["findings"]:
        lines.append("No specific fixes found in database. See AI recommendations below.")
    else:
        for i, finding in enumerate(fixes_data["findings"], 1):
            severity = finding["severity"]
            severity_color = {"CRITICAL": "red", "HIGH": "red", "MEDIUM": "yellow", "LOW": "green"}.get(severity, "white")
            
            lines.append(f"### Fix #{i}: [{severity}] {finding['description']}")
            if "port" in finding:
                lines.append(f"*Source: Nmap - Port {finding['port']}*")
            else:
                lines.append(f"*Source: Nikto - {finding.get('finding', 'Web vulnerability')}*")
            
            lines.append("```powershell" if fixes_data["os_detected"] == "windows" else "```bash")
            lines.extend(finding["commands"])
            lines.append("```")
            lines.append("")
    
    if fixes_data.get("ai_recommendations"):
        lines.append("### Additional AI Recommendations")
        lines.append(fixes_data["ai_recommendations"])
    
    return "\n".join(lines)
