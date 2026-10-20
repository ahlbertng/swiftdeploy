# SwiftDeploy

[![CI](https://github.com/ahlbertng/swiftdeploy/actions/workflows/deploy.yaml/badge.svg)](https://github.com/ahlbertng/swiftdeploy/actions/workflows/deploy.yaml)
![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-API-009688?logo=fastapi&logoColor=white)
![Docker Compose](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)
![OPA](https://img.shields.io/badge/Policy-OPA-7D9B00)

SwiftDeploy is a deployment automation demo for a containerized FastAPI service. Describe the deployment in `manifest.yaml`; the Python CLI renders Docker Compose and Nginx configuration, deploys the stack, checks health and policy, and records events for an audit report.

It brings together four parts of a deployment workflow:

- **Configuration generation** from a manifest and Jinja templates
- **Policy checks** with Open Policy Agent (OPA)
- **Service and deployment observability** through FastAPI and Prometheus metrics
- **Deployment history and audit reports** for reviewing what happened

## 📦 What is in this repository?

| Path | Purpose |
| --- | --- |
| [`swiftdeploy`](./swiftdeploy) | CLI for rendering configuration, deploying, checking status, and creating audit reports |
| [`manifest.yaml`](./manifest.yaml) | Service, network, Nginx, and OPA settings |
| [`templates/`](./templates) | Jinja templates for generated Compose and Nginx configuration |
| [`app/`](./app) | FastAPI service, runtime dependencies, and test dependencies |
| [`policies/`](./policies) | OPA infrastructure and canary policies with Rego tests |
| [`tests/`](./tests) | Python endpoint and chaos-control tests |
| [`.github/workflows/deploy.yaml`](./.github/workflows/deploy.yaml) | CI checks and container integration workflow |

Generated `docker-compose.yml` and `nginx.conf` files are created from the manifest and templates; they are intentionally not committed.

## 🏗️ Architecture

                     manifest.yaml
                          │
                          ▼
                ┌───────────────────┐
                │    SwiftDeploy    │
                │    Python CLI     │
                └─────────┬─────────┘
                          │
          ┌───────────────┼────────────────┐
          ▼               ▼                ▼
      Jinja2             OPA             Docker
     templates         policies          Compose
          │               │                │
          ▼               │                ▼
   nginx.conf +           │          application
   docker-compose.yml     │                │
          │               │                │
          └───────────────┼────────────────┘
                          ▼
                        Nginx
                          │
                          ▼
                     application
                          │
                ┌─────────┴─────────┐
                ▼                   ▼
             /healthz            /metrics
                                    │
                          ┌─────────┴─────────┐
                          ▼                   ▼
                     error rate             P99
                     throughput             uptime
                     chaos                  mode
                          │
                          ▼
                         OPA
                          │
                ┌─────────┴─────────┐
                ▼                   ▼
          infra policy        canary policy
                │                   │
                └─────────┬─────────┘
                          ▼
                   deploy / promote
                          │
                          ▼
                    history.jsonl
                          │
                          ▼
                    audit_report.md
```

## 🧰 CLI commands

| Command    | Responsibility                                      |
|------------|-----------------------------------------------------|
| `init`     | Generate Compose and Nginx configuration             |
| `validate` | Preflight check of configuration and dependencies   |
| `deploy`   | Policy-check, deploy, and health-check              |
| `promote`  | Switch canary/stable mode and verify it             |
| `status`   | Continuously observe application + policies         |
| `audit`    | Turn event history into an audit report             |
| `teardown` | Remove the deployment                               |

Run `./swiftdeploy` without a command to see the supported command syntax.

## ✅ Four layers of validation

1. **Configuration validation** (`validate`): is the deployment configuration valid?
2. **Runtime health** (`/healthz`): is the application alive and responding?
3. **Policy validation** (OPA): does the current state satisfy the defined operational rules?
4. **Observability** (`/metrics`, `status`, `history.jsonl`, `audit_report.md`): what is happening, and what happened?

## 🔄 Deployment lifecycle

### `./swiftdeploy deploy`

```
manifest
   ↓
load configuration
   ↓
check infrastructure policy
   ↓
generate Compose + Nginx
   ↓
docker compose up
   ↓
wait for /healthz
   ↓
record deployment
```

Set `SWIFTDEPLOY_REQUIRE_OPA=1` to make policy gates fail when OPA is
unavailable instead of warning and continuing. It is enabled in CI; leaving it
unset preserves the default local-development behavior.

### `./swiftdeploy promote stable`

When currently on canary:

```
canary
   ↓
scrape metrics
   ↓
calculate error rate + P99
   ↓
check canary policy
   ↓
allowed?
   ├── NO  → stop
   └── YES
         ↓
    change manifest
         ↓
    regenerate Compose
         ↓
    recreate app
         ↓
    verify /healthz
         ↓
       stable
```

### 📊 `./swiftdeploy status`

```
metrics
   ↓
calculate operational state
   ↓
query OPA
   ↓
display dashboard
   ↓
record history
   ↓
repeat every 5 seconds
```

### `./swiftdeploy audit`

```
history.jsonl
      ↓
parse events
      ↓
identify violations
      ↓
summarize promotions
      ↓
audit_report.md
```

## 📊 `status`: the operational dashboard

`status` is a deployment observability console. Every 5 seconds it scrapes `/metrics` and collects application, policy, and host information.

```
        /metrics
           │
           ▼
    scrape_metrics()
           │
   ┌───────┴────────┐
   ▼                ▼
traffic stats    app state
   │                │
   ├── req/s        ├── uptime
   ├── error rate   ├── mode
   └── P99          └── chaos
           │
           ▼
      OPA policies
       /        \
 infra policy   canary policy
```

**Application metrics**

- **Req/s**: throughput
- **Error rate**: percentage of 5xx responses
- **P99 latency**: tail latency
- Also reads uptime, current deployment mode, and chaos state

**Policy evaluation**

The dashboard displays service metrics and asks OPA whether they meet the configured policies:

```python
query_opa(manifest, "swiftdeploy/canary", canary_input)  # canary safety
query_opa(manifest, "swiftdeploy/infra", host_stats)     # host/infrastructure
```

Example output:

```
Infrastructure Policy: ✔ PASS
Canary Safety Policy:  ✔ PASS
```

```
Infrastructure Policy: ✘ FAIL
  ↳ disk free below threshold

Canary Safety Policy: ✘ FAIL
  ↳ error rate exceeds threshold
```

Metrics tell you **what is happening**. Policy tells you **whether that is acceptable** under your rules.

## 🧪 Chaos engineering

The app exposes its chaos state as a metric, which `status` displays:

The `POST /chaos` control endpoint is available only in canary mode and requires
the `X-Chaos-Token` request header. Set `CHAOS_TOKEN` in the environment before
generating or starting the Compose stack; if it is unset, the endpoint is
disabled. Keep this token private and do not commit it.

```python
chaos_val = int(metrics.get("chaos_active", 0))
```

| Value | State   |
|-------|---------|
| 0     | none    |
| 1     | slow    |
| 2     | error   |

This is shown next to throughput, errors, latency, deployment mode, and policy compliance, which gives a clear demo workflow:

```
Normal
  ↓
Inject chaos
  ↓
Latency/errors change
  ↓
Metrics reflect degradation
  ↓
OPA evaluates canary safety
  ↓
Promotion can be blocked
```

## 🧾 `history.jsonl`: the event trail

SwiftDeploy calls `append_history(...)` throughout the program. The file is [JSON Lines](https://jsonlines.org/): each line is an independent JSON event.

Events recorded:

- `deploy`
- `promote`
- `teardown`
- `policy_check`
- `opa_unavailable`
- `metrics_scrape_failed`
- `status_scrape`

Example:

```json
{"timestamp":"...","event":"deploy","mode":"canary"}
{"timestamp":"...","event":"policy_check","gate":"pre_deploy","allowed":true}
{"timestamp":"...","event":"status_scrape","req_s":4.2}
```

## 🧾 `audit`: operational history as a report

```bash
./swiftdeploy audit
```

Reads `history.jsonl` and writes `audit_report.md` with three sections:

- **Timeline**: deploy, promote, teardown, policy checks, OPA unavailable, metrics scrape failures
- **Policy violations**: found in both `policy_check` events and live `status_scrape` events
- **Mode changes**: e.g. `canary → stable`, `stable → canary`

```
Application
    ↓
SwiftDeploy events
    ↓
history.jsonl
    ↓
audit
    ↓
audit_report.md
```

## 🚀 Getting started

### Requirements

- Python 3.11 (the version used by CI) for the CLI and tests
- Docker Engine with the Docker Compose plugin

The app runs in a Python container. The local CLI uses PyYAML, Jinja2, and psutil.

### Build and deploy

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install pyyaml jinja2 psutil

docker build -t swiftdeploy:latest .
./swiftdeploy init
docker compose config --quiet
./swiftdeploy deploy
```

The default manifest deploys the app in canary mode. Once deployment is healthy,
the service is available at `http://localhost:5050`. Useful endpoints:

| Endpoint | Purpose |
| --- | --- |
| `/healthz` | Service health and deployment metadata |
| `/metrics` | Prometheus-format metrics |
| `POST /chaos` | Authenticated chaos controls; canary mode only |

### Protect and use chaos controls

The chaos endpoint is disabled unless `CHAOS_TOKEN` is set. Export a private
token before deploying if you want to use it:

```bash
export CHAOS_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
./swiftdeploy deploy
```

Send the token in the `X-Chaos-Token` header to activate a test scenario or
recover the service:

```bash
curl -X POST http://localhost:5050/chaos \
  -H "X-Chaos-Token: $CHAOS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"mode":"error","rate":0.5}'

curl -X POST http://localhost:5050/chaos \
  -H "X-Chaos-Token: $CHAOS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"mode":"recover"}'
```

### Run tests

```bash
python -m pip install -r app/requirements-test.txt
python -m pytest tests/
```

The test requirements include the app's runtime requirements, plus pytest and
httpx. The Docker image installs only `app/requirements.txt`.

## ⚙️ CI workflow

The GitHub Actions workflow runs Python linting and tests, checks and tests the
OPA policies, generates the deployment configuration, validates it with
`docker compose config`, then deploys the container stack and checks its health.
CI requires OPA to be available for the pre-deployment policy gate.

Set `SWIFTDEPLOY_REQUIRE_OPA=1` locally to make the CLI fail if OPA is
unavailable. By default, an unavailable OPA service produces a warning and the
CLI continues, which is useful during local development.

## 🧹 Tear down

Use `./swiftdeploy teardown` to stop and remove the stack and its volumes. Add
`--clean` to also remove generated configuration files.
