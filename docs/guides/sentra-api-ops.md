# Sentra API Operations

This guide covers the FastAPI service that wraps Sentra (Agent0) for scan automation.

## Prerequisites

- Docker Desktop running
- Valid keys in `.env`:
  - `OPENROUTER_API_KEY`
  - `SENTRA_API_KEY`
  - `AGENT0_API_KEY`

## Start Services

```bash
docker compose up -d --build
```

Expected services:

- `sentra-ai` (Agent runtime)
- `sentra-api` (FastAPI)
- `sentra-postgres` (scan persistence)

## Quick Health Check

```bash
curl http://localhost:8000/health
```

Expected shape:

```json
{"status":"ok","agent0":"ok","database":"ok"}
```

## Smoke Test the Scan Lifecycle

Run the built-in smoke runner:

```bash
python api/smoke_scan.py --api-key "<SENTRA_API_KEY>" --target "example.com" --scan-type quick
```

What this validates:

1. `POST /api/v1/scans` creates a job
2. polling `GET /api/v1/scans/{id}` reaches `completed`
3. summary/findings are persisted and readable

## Manual API Flow

Create scan:

```bash
curl -X POST http://localhost:8000/api/v1/scans \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <SENTRA_API_KEY>" \
  -d '{"target":"localhost","scan_type":"full"}'
```

Read scan:

```bash
curl http://localhost:8000/api/v1/scans/<SCAN_ID> \
  -H "X-API-Key: <SENTRA_API_KEY>"
```

Stream logs:

```bash
curl -N http://localhost:8000/api/v1/scans/<SCAN_ID>/stream \
  -H "Accept: text/event-stream" \
  -H "X-API-Key: <SENTRA_API_KEY>"
```

## Troubleshooting

- API stuck in `running`
  - Check: `docker logs sentra-api`
  - Check: `docker logs sentra-ai`
- Agent connectivity issues
  - Verify `AGENT0_INTERNAL_URL=http://agent0:80`
  - Restart services: `docker compose down && docker compose up -d --build`
- Invalid key errors
  - Confirm `SENTRA_API_KEY` request header and `.env` value match
