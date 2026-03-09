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

# Apply Sentra UI customizations over upstream Agent0 web UI
COPY webui /a0/webui

# Apply Sentra runtime branding overrides used by OpenRouter request metadata
COPY models.py /a0/models.py
COPY conf/model_providers.yaml /a0/conf/model_providers.yaml
