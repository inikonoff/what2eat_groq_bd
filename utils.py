import os
import logging
from groq import AsyncGroq
from config import GROQ_API_KEY

logger = logging.getLogger(__name__)

class VoiceProcessor:
    """Обработка голосовых сообщений через Groq Whisper"""
    
    def __init__(self):
        # Используем тот же ключ, что и для генерации текста
        if not GROQ_API_KEY:
            logger.error("GROQ_API_KEY не установлен!")
            self.client = None
        else:
            self.client = AsyncGroq(api_key=GROQ_API_KEY)
    
    async def process_voice(self, file_path: str) -> str:
        """
        Преобразует аудиофайл (ogg/mp3/wav) в текст через Whisper
        """
        if not self.client:
            logger.error("Клиент Groq не инициализирован")
            return ""

        if not os.path.exists(file_path):
            logger.error(f"Файл не найден: {file_path}")
            return ""
            
        try:
            # Groq поддерживает OGG напрямую, конвертация не нужна!
            with open(file_path, "rb") as file:
                transcription = await self.client.audio.transcriptions.create(
                    file=(file_path, file.read()),
                    model="whisper-large-v3", # Самая мощная модель
                    response_format="text"
                )
            
            text = transcription.strip()
            logger.info(f"Голос распознан: {text[:50]}...")
            return text
            
        except Exception as e:
            logger.error(f"Ошибка распознавания речи через Groq: {e}")
            return ""
