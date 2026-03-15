# Sentra Lab Operations (DVWA + Juice Shop)

This guide sets up a temporary vulnerable-target lab for local testing with Sentra.

## Scope and Safety

- Use only on your own machine or approved test infrastructure.
- Do not expose these containers to the internet.
- Keep scans restricted to local lab targets.

## Prerequisites

- Docker Desktop is running.
- Sentra runtime is available via the main compose file in [`docker-compose.yml`](../../docker-compose.yml).

## Start Sentra + Lab Targets

Run from the Sentra project root:

docker compose -f docker-compose.yml -f docker-compose.lab.yml up -d --build

This starts:

- Sentra runtime container from [`docker-compose.yml`](../../docker-compose.yml)
- DVWA container from [`docker-compose.lab.yml`](../../docker-compose.lab.yml)
- Juice Shop container from [`docker-compose.lab.yml`](../../docker-compose.lab.yml)

## Verify Containers

docker compose -f docker-compose.yml -f docker-compose.lab.yml ps

Expected local URLs:

- Sentra UI: http://localhost:50001
- DVWA: http://localhost:8081
- Juice Shop: http://localhost:3001

## Demo Target List

Use these targets in Sentra scans:

- http://dvwa
- http://juice-shop:3000

Notes:

- The internal hostnames above work because all services share the same compose network.
- Do **not** use `http://localhost:8081` as a scan target from Sentra. Inside the `sentra-ai` container, `localhost` points to the Sentra container itself, not DVWA.
- Use localhost URLs only from your host browser for manual checks.

## Stop Lab (Keep Data)

docker compose -f docker-compose.yml -f docker-compose.lab.yml stop

## Stop and Remove Lab Containers

docker compose -f docker-compose.yml -f docker-compose.lab.yml down

## Cleanup (Optional)

If you also want to remove Sentra persisted volume data:

docker compose -f docker-compose.yml -f docker-compose.lab.yml down -v
