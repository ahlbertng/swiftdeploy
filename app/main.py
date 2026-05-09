import os
import time
import random
import asyncio
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, PlainTextResponse

from prometheus_client import (
    Counter, Histogram, Gauge,
    generate_latest, CONTENT_TYPE_LATEST, REGISTRY
)

# Env
MODE        = os.getenv("MODE", "stable").lower()
APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
APP_PORT    = int(os.getenv("APP_PORT", "3000"))
START_TIME  = time.time()

# Prometheus metrics

http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status_code"]
)
http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["method", "path"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)
app_uptime_seconds = Gauge("app_uptime_seconds", "Seconds since app start")
app_mode_gauge     = Gauge("app_mode", "0=stable 1=canary")
chaos_active_gauge = Gauge("chaos_active", "0=none 1=slow 2=error")

# Chaos state

chaos_state: dict = {"mode": None}

app = FastAPI(title="SwiftDeploy Service")

# Middleware for metrics and chaos injection

@app.middleware("http")
async def metrics_and_chaos_middleware(request: Request, call_next):
    # Update gauges
    app_uptime_seconds.set(time.time() - START_TIME)
    app_mode_gauge.set(1 if MODE == "canary" else 0)
    chaos_mode = chaos_state.get("mode")
    if chaos_mode == "slow":
        chaos_active_gauge.set(1)
    elif chaos_mode == "error":
        chaos_active_gauge.set(2)
    else:
        chaos_active_gauge.set(0)

    # Chaos: error injection (canary only)

    if MODE == "canary" and chaos_mode == "error":
        rate = chaos_state.get("rate", 0.0)
        if random.random() < rate:
            http_requests_total.labels(
                method=request.method,
                path=request.url.path,
                status_code="500"
            ).inc()
            resp = JSONResponse(
                status_code=500,
                content={"error": "chaos-induced failure", "mode": MODE}
            )
            resp.headers["X-Mode"] = "canary"
            return resp

    # Chaos: slow injection (canary only)

    if MODE == "canary" and chaos_mode == "slow":
        if time.time() < chaos_state.get("until", 0):
            await asyncio.sleep(chaos_state.get("duration", 0))

    # Time the real request

    start = time.time()
    response = await call_next(request)
    elapsed = time.time() - start

    path = request.url.path
    http_requests_total.labels(
        method=request.method,
        path=path,
        status_code=str(response.status_code)
    ).inc()
    http_request_duration_seconds.labels(
        method=request.method,
        path=path
    ).observe(elapsed)

    if MODE == "canary":
        response.headers["X-Mode"] = "canary"
    return response

# Routes
# Note: chaos endpoint is POST /chaos with JSON body {"mode": "slow|error|recover", "duration": 5, "rate": 0.5} 
@app.get("/")
async def root():
    return {
        "message": f"Welcome to SwiftDeploy Service — running in {MODE.upper()} mode",
        "mode": MODE,
        "version": APP_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

@app.get("/healthz")
async def healthz():
    return {
        "status": "ok",
        "uptime_seconds": round(time.time() - START_TIME, 2),
        "mode": MODE,
        "version": APP_VERSION,
    }

@app.get("/metrics")
async def metrics():
    app_uptime_seconds.set(time.time() - START_TIME)
    data = generate_latest(REGISTRY)
    return PlainTextResponse(data.decode("utf-8"), media_type=CONTENT_TYPE_LATEST)

@app.post("/chaos")
async def chaos(request: Request):
    if MODE != "canary":
        return JSONResponse(
            status_code=403,
            content={"error": "chaos endpoint only available in canary mode"}
        )
    body = await request.json()
    chaos_mode = body.get("mode")

    if chaos_mode == "slow":
        duration = int(body.get("duration", 5))
        chaos_state["mode"]     = "slow"
        chaos_state["duration"] = duration
        chaos_state["until"]    = time.time() + 300
        return {"message": f"chaos activated: slow mode for {duration}s per request"}

    elif chaos_mode == "error":
        rate = float(body.get("rate", 0.5))
        chaos_state["mode"] = "error"
        chaos_state["rate"] = rate
        return {"message": f"chaos activated: error rate {rate*100:.0f}%"}

    elif chaos_mode == "recover":
        chaos_state.clear()
        chaos_state["mode"] = None
        return {"message": "chaos cancelled — service recovered"}

    return JSONResponse(
        status_code=400,
        content={"error": f"unknown chaos mode: {chaos_mode}. Use slow, error, or recover"}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=APP_PORT, reload=False)