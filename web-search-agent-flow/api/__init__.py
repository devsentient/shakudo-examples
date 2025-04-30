"""API routes for the multi-agent system."""
from fastapi import FastAPI

def register_routes(app: FastAPI):
    """Register all API routes with the FastAPI application."""
    # Import route modules
    from .job import register_job_routes
    from .steps import router as steps_router
    from .realtime import router as realtime_router
    from .debug import router as debug_router
    from .health import router as health_router
    
    # Register routers
    register_job_routes(app)  # Job routes have a custom registration function
    app.include_router(steps_router)
    app.include_router(realtime_router)
    app.include_router(debug_router)
    app.include_router(health_router)
    
    # Root endpoint for API info
    @app.get("/", tags=["root"])
    async def root():
        """Root endpoint with API information."""
        return {
            "name": "Agent Flow Multi-Agent System API",
            "version": "1.0.0",
            "description": "Generated multi-agent system service"
        }