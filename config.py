import os
from dotenv import load_dotenv
from typing import Optional
from dataclasses import dataclass

load_dotenv()

@dataclass
class DatabaseConfig:
    url: str
    min_connections: int = 1
    max_connections: int = 10
    statement_cache_size: int = 0
    
    def __post_init__(self):
        if not self.url:
            raise ValueError("DATABASE_URL не найден в переменных окружения!")

@dataclass
class APIConfig:
    telegram_token: str
    groq_api_key: str
    unsplash_access_key: Optional[str] = None
    replicate_api_key: Optional[str] = None  # Для генерации изображений
    
    def __post_init__(self):
        if not self.telegram_token:
            raise ValueError("TELEGRAM_TOKEN не найден!")
        if not self.groq_api_key:
            raise ValueError("GROQ_API_KEY не найден!")

@dataclass
class ModelConfig:
    groq_model: str = "llama-3.3-70b-versatile"
    groq_max_tokens: int = 2000
    speech_language: str = "ru-RU"
    replicate_model: str = "stability-ai/stable-diffusion"  # Для изображений

@dataclass
class AppConfig:
    temp_dir: str = "temp"
    max_history_messages: int = 10
    session_ttl_minutes: int = 60
    image_cache_ttl_hours: int = 24

# Создание экземпляров конфигурации
DB_CONFIG = DatabaseConfig(
    url=os.getenv("DATABASE_URL", ""),
    min_connections=int(os.getenv("DB_MIN_CONNECTIONS", "1")),
    max_connections=int(os.getenv("DB_MAX_CONNECTIONS", "10"))
)

API_CONFIG = APIConfig(
    telegram_token=os.getenv("TELEGRAM_TOKEN", ""),
    groq_api_key=os.getenv("GROQ_API_KEY", ""),
    unsplash_access_key=os.getenv("UNSPLASH_ACCESS_KEY"),
    replicate_api_key=os.getenv("REPLICATE_API_KEY")
)

MODEL_CONFIG = ModelConfig()

APP_CONFIG = AppConfig()

# Создаем временную папку
os.makedirs(APP_CONFIG.temp_dir, exist_ok=True)

# Backward compatibility (для существующего кода)
TELEGRAM_TOKEN = API_CONFIG.telegram_token
GROQ_API_KEY = API_CONFIG.groq_api_key
UNSPLASH_ACCESS_KEY = API_CONFIG.unsplash_access_key
DATABASE_URL = DB_CONFIG.url
SPEECH_LANGUAGE = MODEL_CONFIG.speech_language
GROQ_MODEL = MODEL_CONFIG.groq_model
GROQ_MAX_TOKENS = MODEL_CONFIG.groq_max_tokens
TEMP_DIR = APP_CONFIG.temp_dir
MAX_HISTORY_MESSAGES = APP_CONFIG.max_history_messages
