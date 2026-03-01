"""
Digital Human Backend - Main Entry Point
FastAPI server with WebSocket support for real-time interaction
"""
import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn

from api.websocket_handler import router as ws_router
from api.reflection_api import router as reflection_router
from db.init_db import init_databases


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup resources"""
    # Startup
    print("Initializing databases...")
    init_databases()
    print("Backend server ready!")
    yield
    # Shutdown
    print("Shutting down...")


app = FastAPI(
    title="Digital Human API",
    description="Multi-agent digital human companion system",
    version="0.1.0",
    lifespan=lifespan
)

# CORS configuration
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(ws_router)
app.include_router(reflection_router, prefix="/api")


@app.get("/")
async def root():
    return {"message": "Digital Human API is running", "version": "0.1.0"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", 8000)),
        reload=True
    )
