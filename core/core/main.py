from fastapi import FastAPI
from .api.job_routes import router as job_router
from .api.document_routes import router as document_router
from .config.settings import get_settings
import uvicorn
from contextlib import asynccontextmanager

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    yield
    # Shutdown

app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
    lifespan=lifespan
)

# Include routers
app.include_router(job_router, prefix=settings.API_PREFIX)
app.include_router(document_router, prefix=settings.API_PREFIX)

@app.get("/")
async def root():
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "docs_url": "/docs",
        "api_prefix": settings.API_PREFIX
    }

if __name__ == "__main__":
    uvicorn.run(
        "core.core.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        workers=4
    )
