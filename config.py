import os
from dataclasses import dataclass
from dotenv import load_dotenv

# Загружаем переменные из .env
load_dotenv()


@dataclass(frozen=True)
class Config:
    bot_token: str = os.getenv("BOT_TOKEN", "").strip()
    backend_url: str = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")
    request_timeout: float = float(os.getenv("REQUEST_TIMEOUT", "15"))


config = Config()
