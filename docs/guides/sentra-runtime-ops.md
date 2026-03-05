# Sentra Runtime Operations (Direct Agent0)

This is the active operations guide for the current Sentra deployment model.

Sentra runs directly on the customized Agent0 runtime and web UI (no separate FastAPI scan service required for demo operation).

## Prerequisites

- Docker Desktop running
- Valid keys in `.env` (at minimum):
  - `OPENROUTER_API_KEY`

## Start Services

```bash
docker compose up -d --build
```

Expected core services:

- `sentra-ai` (Agent0 runtime + Sentra UI)

Optional legacy services may still exist in compose (for old architecture experiments), but they are not required for the current demo flow.

## Quick Health Check

### 1) Container health

```bash
docker compose ps
```

Expected: `sentra-ai` is `Up` and `healthy`.

### 2) UI availability

```bash
curl -I http://localhost:50001
```

Expected: `HTTP/1.1 200 OK`.

## Demo Runtime Verification

Before demo, verify these UI/runtime items:

1. Branding loads from `webui` override (Sentra title/logo/favicon)
2. No forced JSON response format in chat outputs
3. Speech/microphone UI controls are removed (as requested for this build)
4. New chat works and agent responds normally

## Restart / Recovery

Soft restart:

```bash
docker compose restart agent0
```

Rebuild when frontend/prompt changes are not visible:

```bash
docker compose build agent0
docker compose up -d agent0
```

## Troubleshooting

- UI not reflecting latest changes:
  - Rebuild image (`docker compose build agent0`) and recreate container (`docker compose up -d agent0`)
  - Hard refresh browser (disable cache in devtools if needed)
- Chat output format regresses:
  - Re-check prompt files under `prompts/`
  - Restart `agent0`
- Service appears down:
  - `docker compose ps`
  - `docker compose logs --tail=200 agent0`

## Legacy API Mode (Deprecated)

The older API-first flow is documented in `sentra-api-ops.md` for reference only.
Use it only if you intentionally run the separate FastAPI/PostgreSQL scan stack.

