import json
import os
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException
from app.core.config import settings
from app.utils.logging import get_api_logger
from app.core.security import decode_access_token
from app.core.websocket_manager import WebSocketManager


# Import database and models first
from app.core.database import create_tables, drop_tables


# Import API routers
from app.api.endpoints import auth as auth_api
from app.api.endpoints import pdf as pdf_api
from app.api.endpoints import chat as chat_api
from app.routers import pages as pages_router


logger = get_api_logger("Main")

# Get the absolute path to the app directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{
        settings.API_V1_STR}/openapi.json",
)

ws_manager = WebSocketManager()


# Mount static files
app.mount(
    "/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static"
)

# Configure templates
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
templates.env.filters["fromjson"] = lambda x: json.loads(x) if x else {}
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


# WebSocket CORS configuration
@app.middleware("http")
async def websocket_cors(request: Request, call_next):
    if request.headers.get("upgrade", "").lower() == "websocket":
        return await call_next(request)
    response = await call_next(request)
    return response


@app.middleware("http")
async def add_auth_header(request: Request, call_next):
    # Check for token in cookie
    token = request.cookies.get("access_token")

    # If token exists in cookie, add it to headers
    if token and "authorization" not in request.headers:
        request.headers.__dict__["_list"].append(
            (b"authorization", f"Bearer {token}".encode())
        )

    response = await call_next(request)
    return response


# Add WebSocket exception handler
@app.exception_handler(WebSocketDisconnect)
async def websocket_disconnect_handler(request: Request, exc: WebSocketDisconnect):
    logger.info(f"WebSocket disconnected with code: {exc.code}")
    return None


# Include routers
app.include_router(
    auth_api.router,
    prefix=f"{
        settings.API_V1_STR}/auth",
    tags=["auth"],
)
app.include_router(
    pdf_api.router,
    prefix=f"{
        settings.API_V1_STR}/pdf",
    tags=["pdf"],
)
app.include_router(
    chat_api.router,
    prefix=f"{
        settings.API_V1_STR}/chat",
    tags=["chat"],
)
app.include_router(pages_router.router, tags=["pages"])


@app.on_event("startup")
async def startup_event():
    logger.info("Starting up application")
    if settings.DROP_DB_ON_STARTUP:
        logger.warning("Dropping all tables due to DROP_DB_ON_STARTUP setting")
        drop_tables()
    logger.info("Creating all tables")
    create_tables()
    logger.info("Application startup complete")


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if "application/json" in request.headers.get("accept", ""):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
    raise exc


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
