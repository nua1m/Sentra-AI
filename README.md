<div align="center">

# `Sentra-AI`

<p align="center">
    <strong>Autonomous Cybersecurity Assessment Platform</strong>
</p>

</div>

## Overview

Sentra-AI is an autonomous cybersecurity assessment platform powered by AI agents. It leverages the power of generative AI and various security tools to perform comprehensive security audits on target systems, networks, and applications. 

Rather than relying on static rulesets, Sentra-AI utilizes dynamic agentic behavior to intelligently navigate, scan, and report on vulnerabilities, attempting to uncover deep attack vectors that traditional scanners might miss.

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

### Rebuild / Restart Docker Runtime

Use these commands when you change files (especially under [`/webui`](Sentra-AI/webui)) and need the running container to pick up updates.

1. Rebuild and recreate the runtime container:
   ```bash
   docker compose up -d --build agent0
   ```

2. Optional: restart only (no rebuild):
   ```bash
   docker compose restart agent0
   ```

3. Verify container health and UI availability:
   ```bash
   docker compose ps
   curl -I http://localhost:50001
   ```

Expected result:
- service `agent0` becomes `healthy`
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
