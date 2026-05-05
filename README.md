# SwiftDeploy

A declarative CLI tool that generates all infrastructure configs from a single `manifest.yaml` and manages your container stack lifecycle.

## Prerequisites

- Docker & Docker Compose v2
- Python 3.10+
- PyYAML + Jinja2: `pip install pyyaml jinja2`

## Project Structure

```
swiftdeploy/
├── manifest.yaml              # Single source of truth — only file you edit
├── swiftdeploy                # CLI tool
├── Dockerfile                 # Builds swift-deploy-1-node:latest
├── app/
│   ├── main.py                # FastAPI service
│   └── requirements.txt
├── templates/
│   ├── nginx.conf.j2          # Nginx config template
│   └── docker-compose.yml.j2  # Docker Compose template
├── generated/                 # Auto-generated — never edit manually
│   ├── nginx.conf
│   └── docker-compose.yml
└── README.md
```

## Quick Start

### 1. Build the image
```bash
docker build -t swift-deploy-1-node:latest .
```

### 2. Make the CLI executable
```bash
chmod +x swiftdeploy
```

### 3. Deploy
```bash
./swiftdeploy deploy
```

Service is now available at `http://localhost:8080`


## Subcommand Walkthrough

### `init`
Parses `manifest.yaml` and generates `generated/nginx.conf` and `generated/docker-compose.yml` from templates.
```bash
./swiftdeploy init
```

### `validate`
Runs 5 pre-flight checks before deployment:
1. `manifest.yaml` exists and is valid YAML
2. All required fields are present and non-empty
3. Docker image exists locally
4. Nginx port is not already bound on the host
5. Generated `nginx.conf` is syntactically valid

```bash
./swiftdeploy validate
```
Exits non-zero if any check fails.

### `deploy`
Runs `init`, brings up the stack, and blocks until health checks pass (60s timeout).
```bash
./swiftdeploy deploy
```

### `promote`
Switches the service between `stable` and `canary` mode with a rolling restart of the app container only.
```bash
./swiftdeploy promote canary
./swiftdeploy promote stable
```
- Updates `mode` in `manifest.yaml` in-place
- Regenerates `docker-compose.yml`
- Restarts only the `app` container
- Confirms the new mode by hitting `/healthz`

### `teardown`
Stops and removes all containers, networks, and volumes.
```bash
./swiftdeploy teardown           # stop stack
./swiftdeploy teardown --clean   # stop stack + delete generated configs
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Welcome message with mode, version, timestamp |
| GET | `/healthz` | Liveness check with uptime in seconds |
| POST | `/chaos` | Simulate degraded behaviour (canary only) |

### Chaos modes (canary only)
```bash
# Slow — sleep N seconds per request
curl -X POST http://localhost:8080/chaos \
  -H "Content-Type: application/json" \
  -d '{"mode": "slow", "duration": 3}'

# Error rate — return 500 on ~50% of requests
curl -X POST http://localhost:8080/chaos \
  -H "Content-Type: application/json" \
  -d '{"mode": "error", "rate": 0.5}'

# Recover — cancel all chaos
curl -X POST http://localhost:8080/chaos \
  -H "Content-Type: application/json" \
  -d '{"mode": "recover"}'
```

## Architecture

```
Client → nginx (port 8080) → app (port 3000, internal only)
```

- Service port is never exposed directly — all traffic routes through Nginx
- Nginx adds `X-Deployed-By: swiftdeploy` header to all responses
- Nginx forwards `X-Mode` header from upstream
- Nginx returns JSON error bodies on 502/503/504
- Containers run as non-root with dropped Linux capabilities
- Image is under 300MB