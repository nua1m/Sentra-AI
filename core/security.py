import logging
import re

import requests

logger = logging.getLogger("sentra.security")

# Targets that are safe to scan without verification
WHITELISTED_DOMAINS = [
    "scanme.nmap.org",
    "testphp.vulnweb.com",
    "demo.testfire.net"
]

def is_private_ip(target: str) -> bool:
    """
    Checks if the target is a private/local IP address.
    Private IPs are allowed for testing without verification files.
    """
    private_patterns = [
        r'^127\.',
        r'^10\.',
        r'^172\.(1[6-9]|2[0-9]|3[0-1])\.',
        r'^192\.168\.',
        r'^localhost$',
        r'^::1$'
    ]
    return any(re.match(pattern, target, re.IGNORECASE) for pattern in private_patterns)

def verify_target_ownership(target: str) -> bool:
    """
    STRICT MODE: Checks for 'sentra-verify.txt' on the target.
    Returns True if:
    1. Target is a private IP/localhost.
    2. Target is in the whitelist.
    3. Target hosts a 'sentra-verify.txt' file accessible via HTTP/HTTPS.
    """
    # 1. Bypass for Private/Local IPs
    if is_private_ip(target):
        logger.info(f"Target {target} is private/local. Verification bypassed.")
        return True

    # 2. Bypass for Whitelisted Domains
    if target.lower() in WHITELISTED_DOMAINS:
        logger.info(f"Target {target} is whitelisted.")
        return True

    # 3. HTTP Verification check
    try:
        # Normalize URL
        base_url = f"http://{target}" if not target.startswith("http") else target

        verify_url = f"{base_url}/sentra-verify.txt"
        logger.info(f"Checking for verification file at: {verify_url}")

        # Timeout 5s
        response = requests.get(verify_url, timeout=5)

        if response.status_code == 200:
            # Check for specific content signature if we want strictness later
            # For now, existence is enough
            logger.info(f"Verification file found on {target}.")
            return True
        else:
            logger.warning(f"Verification file check failed: Status {response.status_code}")
            return False

    except requests.RequestException as e:
        logger.error(f"Verification check failed for {target}: {e}")
        return False
