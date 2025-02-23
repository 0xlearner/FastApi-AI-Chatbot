import json
import os
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException
from app.core.config import settings
from app.utils.logging import get_api_logger

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
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)



# Mount static files
app.mount(
    "/static",
    StaticFiles(directory=os.path.join(BASE_DIR, "static")),
    name="static"
)

# Configure templates
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
templates.env.filters["fromjson"] = lambda x: json.loads(x) if x else {}
app.state.templates = templates

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_api.router, prefix=f"{settings.API_V1_STR}/auth", tags=["auth"])
app.include_router(pdf_api.router, prefix=f"{settings.API_V1_STR}/pdf", tags=["pdf"])
app.include_router(chat_api.router, prefix=f"{settings.API_V1_STR}/chat", tags=["chat"])
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
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail}
        )
    raise exc

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)