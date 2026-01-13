"""Felix Services Gateway - Main entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import (
    remittances,
    snpl,
    topups,
    billpay,
    wallet,
    financial_data,
    campaigns,
)


settings = get_settings()

app = FastAPI(
    title="Felix Services Gateway",
    description="Mock backend services for Felix conversational platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers with API prefix
api_prefix = settings.api_prefix

app.include_router(remittances.router, prefix=api_prefix)
app.include_router(snpl.router, prefix=api_prefix)
app.include_router(topups.router, prefix=api_prefix)
app.include_router(billpay.router, prefix=api_prefix)
app.include_router(wallet.router, prefix=api_prefix)
app.include_router(financial_data.router, prefix=api_prefix)
app.include_router(campaigns.router, prefix=api_prefix)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Felix Services Gateway",
        "version": "1.0.0",
        "status": "running",
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
