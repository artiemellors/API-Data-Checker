"""FastAPI application — entry point for the backend server."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routers import export, results, scans, stream
from .storage.db import db_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise the database on startup, clean up on shutdown."""
    await db_manager.initialize()
    yield
    await db_manager.close()


app = FastAPI(
    title="Retailer API Checker",
    description=(
        "Discover and sample publicly accessible APIs embedded in retailer websites. "
        "Detects constructor.io, Algolia, Bazaarvoice and 40+ other third-party services."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(scans.router, prefix="/api")
app.include_router(results.router, prefix="/api")
app.include_router(export.router, prefix="/api")
app.include_router(stream.router, prefix="/api")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
