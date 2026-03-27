import os

from dotenv import load_dotenv
from pathlib import Path

# go up one level from backend/ to find .env at project root
load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

# required
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY is missing from .env — the app cannot start without it")

# optional — add when you have an OpenAI key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")