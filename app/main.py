import os

import httpx
from fastapi import FastAPI, Request, WebSocketDisconnect
from fastapi.exceptions import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# Import API routers
from app.api.endpoints import auth as auth_api
from app.api.endpoints import chat as chat_api
from app.api.endpoints import pdf as pdf_api
from app.core.config import settings
# Import database and models first
from app.core.database import create_tables, drop_tables
from app.core.jinja_filters import dict_item, fromjson
from app.core.middleware import (add_auth_header, auth_middleware,
                                 websocket_cors)
from app.core.websocket_manager import WebSocketManager
from app.routers import pages as pages_router
from app.utils.logging import get_api_logger

logger = get_api_logger("Main")

# Get the absolute path to the app directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",)


ws_manager = WebSocketManager()


# Mount static files
app.mount(
    "/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static"
)

# Configure templates
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
templates.env.filters["fromjson"] = fromjson
templates.env.filters["dict_item"] = dict_item
app.state.templates = templates

# Set up CORS with WebSocket support
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your actual domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)
app.middleware("http")(auth_middleware)
app.middleware("http")(websocket_cors)
app.middleware("http")(add_auth_header)


# Add WebSocket exception handler
@ app.exception_handler(WebSocketDisconnect)
async def websocket_disconnect_handler(request: Request, exc: WebSocketDisconnect):
    logger.info(f"WebSocket disconnected with code: {exc.code}")
    return None


@ app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if "application/json" in request.headers.get("accept", ""):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
    raise exc


# Include routers
app.include_router(
    auth_api.router,
    prefix=f"{settings.API_V1_STR}/auth",
    tags=["auth"],
)
app.include_router(
    pdf_api.router,
    prefix=f"{settings.API_V1_STR}/pdf",
    tags=["pdf"],
)
app.include_router(
    chat_api.router,
    prefix=f"{settings.API_V1_STR}/chat",
    tags=["chat"],
)
app.include_router(pages_router.router, tags=["pages"])


@ app.on_event("startup")
async def startup_event():
    logger.info("Starting up application")
    if settings.DROP_DB_ON_STARTUP:
        logger.warning("Dropping all tables due to DROP_DB_ON_STARTUP setting")
        drop_tables()
    logger.info("Creating all tables")
    create_tables()
    logger.info("Application startup complete")


@app.get("/health")
async def health_check():
    try:
        # Check if models are ready
        if not os.path.exists("/tmp/.models_ready"):
            raise HTTPException(status_code=503, detail="Models not ready")

        # Check Ollama
        async with httpx.AsyncClient() as client:
            ollama_response = await client.get("http://localhost:11434/api/tags")
            if ollama_response.status_code != 200:
                raise HTTPException(status_code=503, detail="Ollama not ready")

            # Verify models are present
            models = ollama_response.json().get("models", [])
            required_models = {"llama3.2:3b", "nomic-embed-text:latest"}
            available_models = {m["name"] for m in models}

            if not required_models.issubset(available_models):
                raise HTTPException(
                    status_code=503, detail="Required models not available")

        return {
            "status": "healthy",
            "ollama": "ready",
            "models": {
                "status": "ready",
                "available": list(available_models)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    # Configure Uvicorn with WebSocket support
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        ws_max_size=16777216,  # 16MB max WebSocket message size
        ws_ping_interval=20,  # Send ping frames every 20 seconds
        ws_ping_timeout=20,  # Wait 20 seconds for pong response
    )
