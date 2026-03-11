import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.api import register_routers
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    version="0.1.0",
)

# Set all CORS enabled origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 自动注册所有API路由
register_routers(app)

@app.get("/health")
async def health_check():
    return {"status": "ok"}

# Serve Static Files (Frontend) if configured
# This allows the backend to serve the frontend in the single-container production image
serve_static = os.getenv("SERVE_STATIC_FILES", "false").lower() == "true"
static_dir = os.getenv("STATIC_FILES_DIR", "/app/static")

if serve_static:
    if os.path.isdir(static_dir):
        # Mount static files at the root
        # html=True allows serving index.html for the root path
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
    else:
        print(f"Warning: Static files directory {static_dir} not found. Skipping static file serving.")
else:
    # Only define the root welcome message if NOT serving frontend
    @app.get("/")
    async def root():
        return {"message": "Welcome to AutoFlow API", "version": "0.1.0", "docs": "/docs"}
