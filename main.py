from fastapi import FastAPI
from datetime import datetime

app = FastAPI(
    title="FinBrain API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

@app.get("/")
def root():
    return {
        "message": "Welcome to FinBrain API",
        "status": "operational",
        "timestamp": datetime.utcnow().isoformat(),
        "docs_url": "/docs"
    }

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.get("/api/v1/status")
def api_status():
    return {"api_version": "v1", "status": "active"}

@app.get("/test")
def test():
    return {"message": "Server is working!", "time": datetime.utcnow().isoformat()}
