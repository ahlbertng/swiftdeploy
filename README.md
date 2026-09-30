# SwiftDeploy

A declarative deployment CLI. You describe your deployment in `manifest.yaml`, and SwiftDeploy generates the config, deploys it, checks it against policy, observes it, and records everything it does.

it combines **config generation**, **policy enforcement (OPA)**, **live observability**, and an **audit trail** in one Python CLI.

## Architecture

```
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

## Commands

| Command    | Responsibility                                      |
|------------|-----------------------------------------------------|
| `init`     | Generate deployment configuration                   |
| `validate` | Preflight check of configuration and dependencies   |
| `deploy`   | Policy-check, deploy, and health-check              |
| `promote`  | Switch canary/stable mode and verify it             |
| `status`   | Continuously observe application + policies         |
| `audit`    | Turn event history into an audit report             |
| `teardown` | Remove the deployment                               |

## Four layers of validation

1. **Configuration validation** (`validate`): is the deployment configuration valid?
2. **Runtime health** (`/healthz`): is the application alive and responding?
3. **Policy validation** (OPA): does the current state satisfy the defined operational rules?
4. **Observability** (`/metrics`, `status`, `history.jsonl`, `audit_report.md`): what is happening, and what happened?

## Deployment lifecycle

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

### `./swiftdeploy status`

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

## `status`: the operational dashboard

`status` is a small deployment observability console. Every 5 seconds it scrapes `/metrics` and collects application, policy, and host information.

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

The dashboard doesn't only display numbers, it asks OPA whether they are acceptable:

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

## Chaos engineering

Chaos is part of the control plane, not just a README claim. The app exposes its chaos state as a metric, and `status` maps it:

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

## `history.jsonl`: the event trail

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

## `audit`: operational history as a report

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

## Quick start

```bash
./swiftdeploy init
./swiftdeploy validate
./swiftdeploy deploy
./swiftdeploy status
./swiftdeploy promote stable
./swiftdeploy audit
./swiftdeploy teardown
```
