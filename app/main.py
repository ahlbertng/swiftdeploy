import os
import time
import random
import asyncio

from datetime import datetime, timezone
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

# Environment
MODE        = os.getenv("MODE", "stable").lower()
APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
APP_PORT    = int(os.getenv("APP_PORT", "3000"))

START_TIME  = time.time()

# Chaos state (in-memory) 

chaos_state: dict = {"mode": None}   # keys: mode, duration, rate, until

app = FastAPI(title="SwiftDeploy Service")


# Middleware: canary header + chaos simulation

@app.middleware("http")
async def canary_and_chaos_middleware(request: Request, call_next):

    # Chaos: error rate — only in canary mode

    if MODE == "canary" and chaos_state.get("mode") == "error":
        rate = chaos_state.get("rate", 0.0)
        if random.random() < rate:
            response = JSONResponse(
                status_code=500,
                content={"error": "chaos-induced failure", "mode": MODE}
            )
            response.headers["X-Mode"] = "canary"
            return response

    # Chaos: slow mode, only in canary mode

    if MODE == "canary" and chaos_state.get("mode") == "slow":
        until = chaos_state.get("until", 0)
        duration = chaos_state.get("duration", 0)
        if time.time() < until:
            await asyncio.sleep(duration)

    response = await call_next(request)

    # Canary header on every response

    if MODE == "canary":
        response.headers["X-Mode"] = "canary"

    return response


# Routes 
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
    uptime = round(time.time() - START_TIME, 2)
    return {
        "status": "ok",
        "uptime_seconds": uptime,
        "mode": MODE,
        "version": APP_VERSION,
    }


@app.post("/chaos")
async def chaos(request: Request):

    # Only available in canary mode

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
        chaos_state["until"]    = time.time() + 300  # active for 5 minutes
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

    else:
        return JSONResponse(
            status_code=400,
            content={"error": f"unknown chaos mode: {chaos_mode}. Use slow, error, or recover"}
        )


# Entrypoint

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=APP_PORT, reload=False)