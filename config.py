import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
BOT_NAME = os.getenv("BOT_NAME", "PIT DIVERSÃO")
DATABASE_PATH = os.getenv("DATABASE_PATH", str(BASE_DIR / "data" / "pit_diversao.db"))
