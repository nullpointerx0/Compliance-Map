import os
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    """
    Configuration settings for the Ghost Kitchen Compliance application.
    Loads values from environment variables or a .env file.
    """
    DATABASE_URL: str = "sqlite:///./data/compliance.db"
    SCRAPER_MOCK: bool = True
    MATCH_THRESHOLD: float = 0.85
    AMBIGUOUS_THRESHOLD: float = 0.60
    RANDOM_DELAY_MIN: float = 2.0
    RANDOM_DELAY_MAX: float = 5.0

    CITIES: List[str] = [
        "Bengaluru",
        "Mumbai",
        "Delhi",
        "Hyderabad",
        "Chennai",
        "Pune",
        "Kolkata",
        "Ahmedabad",
        "Jaipur",
        "Lucknow"
    ]
    PLATFORMS: List[str] = ["swiggy", "zomato"]

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
