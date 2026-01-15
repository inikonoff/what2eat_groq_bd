"""
Обработка голосовых сообщений
"""
import os
import asyncio
import speech_recognition as sr
from pydub import AudioSegment
from config import MODEL_CONFIG, APP_CONFIG
import logging

logger = logging.getLogger(__name__)

class VoiceProcessor:
    """Класс для обработки голосовых сообщений"""
    
    def __init__(self):
        self.recognizer = sr.Recognizer()
    
    async def convert_ogg_to_wav(self, ogg_path: str) -> str:
        """Конвертация OGG в WAV"""
        wav_path = ogg_path.replace('.ogg', '.wav')
        
        # Используем asyncio.to_thread для блокирующей операции
        await asyncio.to_thread(self._convert, ogg_path, wav_path)
        
        return wav_path
    
    def _convert(self, input_path: str, output_path: str):
        """Синхронная конвертация"""
        try:
            audio = AudioSegment.from_ogg(input_path)
            audio.export(output_path, format='wav')
            logger.debug(f"Аудио сконвертировано: {input_path} -> {output_path}")
        except Exception as e:
            logger.error(f"Ошибка конвертации аудио: {e}")
            raise
    
    async def recognize_speech(self, wav_path: str) -> str:
        """Распознавание речи из WAV файла"""
        return await asyncio.to_thread(self._recognize_sync, wav_path)
    
    def _recognize_sync(self, wav_path: str) -> str:
        """Синхронное распознавание речи"""
        try:
            with sr.AudioFile(wav_path) as source:
                # Настраиваем для шумной среды
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio_data = self.recognizer.record(source)
                
                # Распознавание через Google Speech Recognition
                text = self.recognizer.recognize_google(
                    audio_data,
                    language=MODEL_CONFIG.speech_language,
                    show_all=False
                )
                
                logger.debug(f"Речь распознана: {text}")
                return text
                
        except sr.UnknownValueError:
            logger.warning("Речь не распознана (UnknownValueError)")
            raise Exception("Речь не распознана. Попробуйте говорить четче.")
        except sr.RequestError as e:
            logger.error(f"Ошибка сервиса распознавания: {e}")
            raise Exception("Ошибка сервиса распознавания речи. Попробуйте позже.")
        except Exception as e:
            logger.error(f"Ошибка при распознавании: {e}")
            raise Exception(f"Ошибка обработки аудио: {e}")
    
    async def process_voice(self, voice_file_path: str) -> str:
        """Полный процесс обработки голосового сообщения"""
        ogg_path = None
        wav_path = None
        
        try:
            ogg_path = voice_file_path
            
            # Конвертируем в WAV
            wav_path = await self.convert_ogg_to_wav(ogg_path)
            
            # Распознаем речь
            text = await self.recognize_speech(wav_path)
            
            return text
            
        finally:
            # Очищаем временные файлы
            self._cleanup_files([ogg_path, wav_path])
    
    def _cleanup_files(self, file_paths):
        """Удаление временных файлов"""
        for file_path in file_paths:
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    logger.debug(f"Удален временный файл: {file_path}")
                except Exception as e:
                    logger.warning(f"Не удалось удалить файл {file_path}: {e}")
    
    async def process_voice_message(self, voice_data: bytes) -> str:
        """Обработка голосового сообщения из bytes"""
        # Сохраняем временный файл
        temp_file = os.path.join(APP_CONFIG.temp_dir, f"voice_{os.urandom(8).hex()}.ogg")
        
        try:
            with open(temp_file, 'wb') as f:
                f.write(voice_data)
            
            return await self.process_voice(temp_file)
            
        finally:
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except:
                    pass
