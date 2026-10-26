import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ASTROLOGY_API_KEY = os.getenv("ASTROLOGY_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY is missing in .env")

if not ASTROLOGY_API_KEY:
    raise ValueError("ASTROLOGY_API_KEY is missing in .env")
