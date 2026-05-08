# SwiftDeploy

A declarative container stack manager that generates and manages Docker Compose + Nginx configurations from a single `manifest.yaml` file.

## Prerequisites

- Docker
- Python 3.12+
- PyYAML and Jinja2: `pip install pyyaml jinja2`

## Setup

```bash
git clone https://github.com/ahlbertng/swiftdeploy
cd swiftdeploy
chmod +x swiftdeploy
```

## Build the Docker Image

```bash
docker build -t ahlbert-swiftdeploy:latest .
```

## Subcommands

### init
Generates `nginx.conf` and `docker-compose.yml` in the root folder from templates.
```bash
./swiftdeploy init
```

### validate
Validates the manifest, checks the Docker image exists, port availability, and nginx config syntax.
```bash
./swiftdeploy validate
```

### deploy
Runs init, brings up the full stack (app + nginx), and waits for health checks.
```bash
./swiftdeploy deploy
```

### promote
Switches the app between stable and canary mode and restarts the stack.
```bash
./swiftdeploy promote canary
./swiftdeploy promote stable
```

### teardown
Stops and removes all containers, networks and volumes.
```bash
./swiftdeploy teardown
```

## Endpoints

- `GET /` — Welcome message with current mode and version
- `GET /healthz` — Health check with uptime and mode
- `POST /chaos` — Inject chaos (canary mode only)