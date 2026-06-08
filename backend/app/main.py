from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import init_db

# Initialize SQLite database and tables
init_db()

app = FastAPI(
    title="Ghost Kitchen Compliance API",
    description="API for the Ghost Kitchen Compliance Map project for BT232AT.",
    version="1.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In development, allow all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """
    Root endpoint returning basic information about the API service.
    """
    return {
        "message": "Ghost Kitchen Compliance Map API is running",
        "version": "1.0.0",
        "cities_configured": len(settings.CITIES)
    }

@app.get("/api/health")
async def health():
    """
    Health check endpoint for container monitoring.
    """
    return {"status": "healthy"}
