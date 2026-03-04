FROM agent0ai/agent-zero

# Pre-install core Sentra-AI security tools
# Trimmed to essentials only for fast build times
# hydra/medusa available for Sentra to install at runtime if needed for cred auditing
RUN apt-get update -qq && \
    apt-get install -y --no-install-recommends \
        nmap \
        nikto \
        gobuster \
        curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create wordlists directory (rockyou.txt mounted from host via docker-compose)
RUN mkdir -p /usr/share/wordlists
