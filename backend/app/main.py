from fastapi import FastAPI
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    version="0.1.0",
)

@app.get("/")
async def root():
    return {"message": "Welcome to AutoFlow API", "version": "0.1.0", "docs": "/docs"}

@app.get("/health")
async def health_check():
    return {"status": "ok"}
