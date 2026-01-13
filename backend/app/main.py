"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import init_db, close_db, async_session_maker
from app.routes import chat, admin
from app.seed.agents import run_seeds
from app.core.config_loader import reload_configs, get_agent_ids
from app.core.routing_registry import initialize_routing_registry, RoutingRegistryError
from app.clients.service_client import get_service_client

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if get_settings().debug else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info(f"Starting {settings.app_name}...")
    await init_db()
    logger.info("Database initialized")

    # Pre-load JSON configs into cache
    reload_configs()
    agent_ids = get_agent_ids()
    logger.info(f"Loaded {len(agent_ids)} agent configs from JSON: {agent_ids}")

    # Run seeds (populates DB from JSON for runtime, seeds sample users)
    async with async_session_maker() as db:
        await run_seeds(db)
    logger.info("Seeds completed")

    # Initialize and validate routing registry
    async with async_session_maker() as db:
        try:
            await initialize_routing_registry(db)
            logger.info("Routing registry initialized and validated")
        except RoutingRegistryError as e:
            logger.critical(f"Routing validation failed: {e}")
            raise  # Prevent startup with invalid routing

    # Check services gateway (non-blocking warning only)
    try:
        service_client = get_service_client()
        result = await service_client.health_check()
        if result.success:
            logger.info("Services gateway is healthy")
        else:
            logger.warning(f"Services gateway check failed: {result.error}")
    except Exception as e:
        logger.warning(f"Could not verify services gateway: {e}")

    yield

    # Shutdown
    logger.info("Shutting down...")
    await close_db()
    logger.info("Database connections closed")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="Felix Conversational Orchestrator - A multi-agent conversational AI system",
    version="0.1.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,  # Restricted to configured origins
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
    max_age=600,
)

# Include routers
app.include_router(chat.router)
app.include_router(admin.router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.app_name,
        "status": "running",
        "version": "0.1.0",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint with dependency verification."""
    health_status = {
        "status": "healthy",
        "checks": {}
    }

    # Check services gateway connectivity
    try:
        service_client = get_service_client()
        result = await service_client.health_check()
        health_status["checks"]["services_gateway"] = {
            "status": "healthy" if result.success else "unhealthy",
            "error": result.error if not result.success else None,
        }
        if not result.success:
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["checks"]["services_gateway"] = {
            "status": "unknown",
            "error": str(e),
        }
        health_status["status"] = "degraded"

    return health_status


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
    )
