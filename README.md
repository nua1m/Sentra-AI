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

The system consists of three main components:

1. **Sentra API (`/api`)**: A FastAPI-based backend that orchestrates scan jobs, manages data persistence (via PostgreSQL), and handles Server-Sent Events (SSE) streaming of live logs to the client.
2. **Agent0 Engine (`/a0` & `/python`)**: The core AI engine built upon the Agent Zero framework. It executes the actual security scanning strategies, utilizes specialized tools, and streams autonomous reasoning and execution logs back to the API.
3. **Web UI (`/webui`)**: A React frontend interface for users to initiate scans, view real-time logs, and analyze the structured final JSON findings report.

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
- **Sentra API Docs**: http://localhost:8000/docs
- **Sentra Web UI** (if running separately): Configure your frontend to point to `http://localhost:8000`

## Features

- **Autonomous Scanning**: Simply provide a target, and the AI will determine the best tools and strategies to test that target.
- **Live Logging**: Watch the AI's thought process and terminal execution in real-time as the scan progresses.
- **Structured Findings**: At the end of the scan, receive a standardized vulnerability report including CVEs, CVSS scores, and remediation advice.
- **Microservice Architecture**: Fully containerized and scalable design.

## Technical Details

- **Backend**: Python 3.12+, FastAPI, SQLAlchemy (Async), PostgreSQL
- **AI Core**: Agent Zero framework, httpx, asyncio
- **Containerization**: Docker, Docker Compose

## License

This project is licensed under the MIT License - see the LICENSE file for details.
