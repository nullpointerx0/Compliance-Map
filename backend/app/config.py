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
    SCRAPER_MODE: str = "mock"
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

CITY_COORDS = {
    "Bengaluru": [
        (12.9352, 77.6245, "Koramangala"),
        (12.9716, 77.5946, "Indiranagar"),
        (12.9279, 77.6271, "HSR Layout"),
        (13.0358, 77.5970, "Hebbal"),
        (12.9141, 77.6101, "Jayanagar"),
        (12.9698, 77.7499, "Whitefield"),
        (12.9592, 77.6974, "Marathahalli"),
        (12.8995, 77.5765, "Banashankari"),
        (13.0012, 77.5757, "Rajajinagar"),
        (12.9365, 77.5538, "Vijayanagar"),
    ],
    "Mumbai": [
        (19.0760, 72.8777, "Bandra"),
        (19.1136, 72.8697, "Andheri"),
        (18.9220, 72.8347, "Colaba"),
        (19.0596, 72.8295, "Worli"),
        (19.1197, 72.9051, "Powai"),
        (19.0178, 72.8478, "Dadar"),
        (19.0330, 72.8679, "Sion"),
        (19.1663, 72.9500, "Mulund"),
        (18.9941, 72.8261, "Parel"),
        (19.2183, 72.9781, "Thane"),
    ],
    "Delhi": [
        (28.6139, 77.2090, "Connaught Place"),
        (28.5355, 77.3910, "Noida Sector 18"),
        (28.4595, 77.0266, "Gurgaon"),
        (28.6469, 77.2172, "Civil Lines"),
        (28.5672, 77.2100, "Lajpat Nagar"),
        (28.6304, 77.2177, "Karol Bagh"),
        (28.5921, 77.2292, "Defence Colony"),
        (28.7041, 77.1025, "Rohini"),
        (28.5494, 77.2001, "Saket"),
        (28.6562, 77.2410, "Model Town"),
    ],
    "Hyderabad": [
        (17.4400, 78.4983, "Banjara Hills"),
        (17.4239, 78.4738, "Jubilee Hills"),
        (17.3850, 78.4867, "Gachibowli"),
        (17.4486, 78.3908, "Miyapur"),
        (17.4947, 78.5249, "Secunderabad"),
        (17.3616, 78.4747, "Kondapur"),
        (17.4127, 78.5478, "LB Nagar"),
        (17.4924, 78.3718, "Kukatpally"),
        (17.3753, 78.5957, "Dilsukhnagar"),
        (17.4469, 78.5594, "Uppal"),
    ],
    "Chennai": [
        (13.0827, 80.2707, "Nungambakkam"),
        (13.0569, 80.2425, "T Nagar"),
        (12.9516, 80.2389, "Velachery"),
        (13.1067, 80.2960, "Anna Nagar"),
        (13.0012, 80.2565, "Adyar"),
        (12.9249, 80.1000, "Tambaram"),
        (13.0358, 80.2685, "Egmore"),
        (13.0839, 80.2424, "Kilpauk"),
        (13.1186, 80.2325, "Ambattur"),
        (12.9716, 80.2209, "Guindy"),
    ],
    "Pune": [
        (18.5204, 73.8567, "Koregaon Park"),
        (18.5314, 73.8446, "Kalyani Nagar"),
        (18.4529, 73.8496, "Katraj"),
        (18.5679, 73.9143, "Viman Nagar"),
        (18.5089, 73.8160, "Kothrud"),
        (18.4968, 73.8559, "Swargate"),
        (18.5805, 73.9027, "Hadapsar"),
        (18.5362, 73.8777, "Wanowrie"),
        (18.6186, 73.8037, "Pimpri"),
        (18.6298, 73.7997, "Chinchwad"),
    ],
    "Kolkata": [
        (22.5726, 88.3639, "Park Street"),
        (22.5354, 88.3476, "Behala"),
        (22.6075, 88.4273, "Salt Lake"),
        (22.5200, 88.3692, "Tollygunge"),
        (22.5854, 88.4219, "Lake Town"),
        (22.5448, 88.3426, "Alipore"),
        (22.5679, 88.4302, "Phool Bagan"),
        (22.5958, 88.3867, "Dum Dum"),
        (22.5080, 88.3832, "Garia"),
        (22.6208, 88.4015, "Barasat"),
    ],
    "Ahmedabad": [
        (23.0225, 72.5714, "CG Road"),
        (23.0395, 72.5565, "Navrangpura"),
        (23.0732, 72.5143, "Chandkheda"),
        (22.9903, 72.5003, "Satellite"),
        (23.0469, 72.6270, "Nikol"),
        (23.0017, 72.5220, "Jodhpur"),
        (22.9952, 72.5618, "Maninagar"),
        (23.0760, 72.6255, "Naroda"),
        (23.0316, 72.5847, "Ghatlodia"),
        (22.9716, 72.6265, "Vatva"),
    ],
    "Jaipur": [
        (26.9124, 75.7873, "C Scheme"),
        (26.8827, 75.8163, "Malviya Nagar"),
        (26.9260, 75.8235, "Vaishali Nagar"),
        (26.9043, 75.7397, "Raja Park"),
        (26.8685, 75.8044, "Sanganer"),
        (26.9492, 75.7376, "Sikar Road"),
        (26.9197, 75.7884, "Tonk Road"),
        (26.8741, 75.7762, "Sitapura"),
        (26.9268, 75.8156, "Mansarovar"),
        (26.9339, 75.8059, "Ajmer Road"),
    ],
    "Lucknow": [
        (26.8467, 80.9462, "Hazratganj"),
        (26.8600, 80.9191, "Gomti Nagar"),
        (26.8100, 80.9900, "Aliganj"),
        (26.8952, 80.9972, "Indira Nagar"),
        (26.8436, 81.0025, "Faizabad Road"),
        (26.8235, 80.9450, "Aminabad"),
        (26.8600, 81.0200, "Chinhat"),
        (26.8038, 80.9423, "Alambagh"),
        (26.9124, 80.9521, "Sitapur Road"),
        (26.8560, 81.0430, "Raibareli Road"),
    ],
}

