<div align="center">

![Sentra Logo](docs/res/sentra-logo.png)

# `Sentra-AI`

<p align="center">
    <strong>Autonomous Cybersecurity Assessment Platform</strong>
</p>

</div>

## Overview

Sentra-AI is an autonomous cybersecurity assessment platform powered by AI agents. It combines generative AI with established open-source security tools to perform bounded, defensive security assessments on authorized systems, networks, and applications.

Rather than relying only on static rulesets, Sentra-AI uses agentic workflow coordination to guide tool selection, explain findings, and present remediation-oriented output in a more understandable form.

## Architecture

The current deployment is a direct Agent0-based stack with Sentra branding:

1. **Agent0 Runtime (`/python`, `/prompts`)**: Core autonomous agent execution, tool orchestration, reasoning loop, and scan workflows.
2. **Sentra Web UI (`/webui`)**: Customized Agent0 frontend for chat-driven security assessment and process visibility.
3. **Container Runtime (`Dockerfile`, `docker-compose.yml`)**: Dockerized runtime for consistent local demo deployment.

> Note: the `/api` directory exists from earlier architecture work, but it is not part of the active runtime path for the current demo deployment.

## Quick Start

### Prerequisites
- Docker & Docker Compose
- API Keys for the LLM Provider (e.g., OpenRouter)

### Setup

1. Clone the repository
2. Copy `.env.example` to `.env` and fill in your API keys and credentials:
   ```bash
   cp .env.example .env
   ```
   *Make sure you set `OPENROUTER_API_KEY` for the AI model to function.*
3. Run the complete stack using Docker Compose:
   ```bash
   docker-compose up -d --build
   ```

### Accessing the Platform
- **Sentra Web UI**: http://localhost:50001

### Local Scan Targets

Sentra is intended to scan authorized local lab targets. The main demo targets are:

- **DVWA**
  - Browser URL: `http://localhost:8081`
  - Sentra target: `http://dvwa`
- **OWASP Juice Shop**
  - Browser URL: `http://localhost:3001`
  - Sentra target: `http://juice-shop:3000`

Optional demo pages in [`demo-sites/`](demo-sites) can also be scanned if you are serving them locally, for example:

- **Vulnerable Demo Page**
  - Browser URL: `http://localhost:8082`
  - Sentra target: `http://sentra-demo-vulnerable`
- **Remediated Demo Page**
  - Browser URL: `http://localhost:8083`
  - Sentra target: `http://sentra-demo-remediated`

Important notes:

- Use the `localhost` URLs only from your host browser.
- When prompting Sentra from inside the Dockerized runtime, prefer internal targets such as `http://dvwa` and `http://juice-shop:3000`.
- Do not expose intentionally vulnerable demo targets to the public internet.

### Sample Prompts

These prompts work well for local testing and viva demonstrations:

```text
Assess http://dvwa and summarize the main findings in plain language with remediation guidance.
```

```text
Run a full security audit on http://dvwa with CVE enrichment and a security workflow checklist.
```

```text
Assess http://juice-shop:3000 and summarize the main findings in plain language with remediation guidance.
```

```text
Run a full audit on http://juice-shop:3000.
```

```text
Check whether http://juice-shop:3000 exposes notable paths or directories and summarize any findings.
```

### Rebuild / Restart Docker Runtime

Use these commands when you change files (especially under [`/webui`](Sentra-AI/webui)) and need the running container to pick up updates.

1. Rebuild and recreate the runtime container:
   ```bash
   docker compose up -d --build sentra
   ```

2. Optional: restart only (no rebuild):
   ```bash
   docker compose restart sentra
   ```

3. Verify container health and UI availability:
   ```bash
   docker compose ps
   curl -I http://localhost:50001
   ```

Expected result:
- service `sentra` becomes `healthy`
- HTTP returns `200 OK` on `http://localhost:50001`

## Features

- **Autonomous Scanning**: Provide a target and the agent selects tools/steps dynamically.
- **Live Process Visibility**: Track reasoning and execution flow directly in chat/process groups.
- **Readable Findings Output**: Security results and remediation guidance in natural-language report format.
- **Direct UI Runtime**: No separate API service required for the main demo experience.

## Technical Details

- **Runtime**: Python 3.12+, Agent Zero framework
- **Frontend**: Customized Agent0 Web UI (`/webui`)
- **Containerization**: Docker, Docker Compose

## License

This project is licensed under the MIT License - see the LICENSE file for details.
