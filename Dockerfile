FROM agent0ai/agent-zero

# Pre-install core Sentra-AI security tools
# Trimmed to essentials only for fast build times
# Keep the runtime lean and focused on bounded reconnaissance and web assessment
RUN apt-get update -qq && \
    apt-get install -y --no-install-recommends \
        nmap \
        nikto \
        gobuster \
        curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create wordlists directory and include a small built-in demo list
RUN mkdir -p /usr/share/wordlists
COPY wordlists /usr/share/wordlists

# Apply Sentra UI customizations over upstream Agent0 web UI
COPY webui /a0/webui
COPY python /a0/python
COPY api /a0/api

# Apply Sentra runtime branding overrides used by OpenRouter request metadata
COPY models.py /a0/models.py
COPY conf/model_providers.yaml /a0/conf/model_providers.yaml
