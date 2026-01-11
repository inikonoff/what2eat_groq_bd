import os
from dotenv import load_dotenv

load_dotenv()

# API ключи
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
REPLICATE_API_KEY = os.getenv("REPLICATE_API_KEY")

# Supabase (PostgreSQL)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Настройки генерации изображений
IMAGE_PROVIDER_PRIORITY = os.getenv("IMAGE_PROVIDER_PRIORITY", "gemini_first")  # gemini_first, replicate_only
ENABLE_IMAGE_CACHE = os.getenv("ENABLE_IMAGE_CACHE", "true").lower() == "true"
GEMINI_DAILY_LIMIT = int(os.getenv("GEMINI_DAILY_LIMIT", "50"))
REPLICATE_FALLBACK_ENABLED = os.getenv("REPLICATE_FALLBACK_ENABLED", "true").lower() == "true"

# Настройки кэширования
IMAGE_CACHE_DIR = os.getenv("IMAGE_CACHE_DIR", "image_cache")
MAX_CACHE_SIZE_MB = int(os.getenv("MAX_CACHE_SIZE_MB", "1000"))  # 1GB
CACHE_TTL_DAYS = int(os.getenv("CACHE_TTL_DAYS", "30"))
CACHE_CLEANUP_INTERVAL_HOURS = int(os.getenv("CACHE_CLEANUP_INTERVAL_HOURS", "24"))

# Настройки изображений
IMAGE_QUALITY = int(os.getenv("IMAGE_QUALITY", "85"))
MAX_IMAGE_SIZE_MB = int(os.getenv("MAX_IMAGE_SIZE_MB", "5"))
DEFAULT_IMAGE_FORMAT = os.getenv("DEFAULT_IMAGE_FORMAT", "JPEG")

# Настройки Groq
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_MAX_TOKENS = int(os.getenv("GROQ_MAX_TOKENS", "2000"))
SPEECH_LANGUAGE = os.getenv("SPEECH_LANGUAGE", "ru-RU")

# Логирование
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_TO_FILE = os.getenv("LOG_TO_FILE", "false").lower() == "true"
LOG_FILE_PATH = os.getenv("LOG_FILE_PATH", "logs/bot.log")

# Админ
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

# Папки
TEMP_DIR = "temp"
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(IMAGE_CACHE_DIR, exist_ok=True)

# Ограничения
MAX_HISTORY_MESSAGES = 8
MAX_PRODUCTS_LENGTH = 2000
MAX_RECIPE_LENGTH = 4000

# Периодические задачи
IMAGE_CACHE_CLEANUP_ENABLED = os.getenv("IMAGE_CACHE_CLEANUP_ENABLED", "true").lower() == "true"