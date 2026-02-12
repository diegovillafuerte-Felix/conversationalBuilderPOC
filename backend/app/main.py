"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import init_db, close_db, async_session_maker
from app.routes import chat, admin
from app.seed.users import seed_sample_users
from app.core.config_loader import reload_configs, get_agent_ids
from app.core.agent_registry import initialize_agent_registry, AgentRegistryError
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

    # Initialize agent registry (loads and validates all agent configs)
    try:
        initialize_agent_registry()
        logger.info("Agent registry initialized and validated")
    except AgentRegistryError as e:
        logger.critical(f"Agent registry initialization failed: {e}")
        raise  # Prevent startup with invalid configuration

    # Seed sample users (for development)
    async with async_session_maker() as db:
        await seed_sample_users(db)
    logger.info("Sample users seeded")

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
