"""
backend/main.py
────────────────
Standalone FastAPI application entry point for Phase 1.

NOTE for Phase 5 integration:
  If teammate adds their own main.py, remove this file and instead import `router`
  from backend.api.routes and mount it on their app with:
      app.include_router(router)
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes import router

app = FastAPI(
    title="Fraud Rule Engine — AI Layer",
    description=(
        "Adaptive fraud/anomaly rule engine with AI investigator.\n"
        "Phase 1: mock data. Phase 5: real backend integration."
    ),
    version="0.1.0-phase1",
)

# Allow the Vite dev server (port 5173) to call the API during development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/", include_in_schema=False)
async def root():
    return {"status": "ok", "phase": 1, "docs": "/docs"}
