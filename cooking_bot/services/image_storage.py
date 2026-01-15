"""
Сервис для хранения изображений
"""
import logging
from typing import Optional, List, Dict, Any
from urllib.parse import urlparse
import aiohttp
import aiofiles
from config import APP_CONFIG
import os

logger = logging.getLogger(__name__)

class ImageStorage:
    """Сервис для работы с изображениями"""
    
    def __init__(self):
        self.storage_dir = os.path.join(APP_CONFIG.temp_dir, "images")
        os.makedirs(self.storage_dir, exist_ok=True)
    
    async def download_image(self, url: str, filename: str = None) -> Optional[str]:
        """
        Загрузка изображения по URL
        
        Args:
            url: URL изображения
            filename: Имя файла (опционально)
            
        Returns:
            Путь к скачанному файлу или None
        """
        if not filename:
            # Генерируем имя файла из URL
            parsed = urlparse(url)
            filename = os.path.basename(parsed.path) or "image.jpg"
            # Добавляем хеш для уникальности
            import hashlib
            url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
            name, ext = os.path.splitext(filename)
            filename = f"{name}_{url_hash}{ext}"
        
        filepath = os.path.join(self.storage_dir, filename)
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        async with aiofiles.open(filepath, 'wb') as f:
                            await f.write(await response.read())
                        
                        logger.debug(f"Изображение скачано: {filepath}")
                        return filepath
                    else:
                        logger.error(f"Ошибка загрузки изображения: {response.status}")
                        return None
                        
        except Exception as e:
            logger.error(f"Ошибка при загрузке изображения: {e}")
            return None
    
    async def cleanup_old_images(self, max_age_hours: int = 24):
        """Очистка старых изображений"""
        import time
        current_time = time.time()
        removed_count = 0
        
        try:
            for filename in os.listdir(self.storage_dir):
                filepath = os.path.join(self.storage_dir, filename)
                if os.path.isfile(filepath):
                    file_age = current_time - os.path.getmtime(filepath)
                    
                    if file_age > max_age_hours * 3600:
                        try:
                            os.remove(filepath)
                            removed_count += 1
                            logger.debug(f"Удалено старое изображение: {filename}")
                        except Exception as e:
                            logger.warning(f"Не удалось удалить файл {filename}: {e}")
            
            if removed_count > 0:
                logger.info(f"Очищено {removed_count} старых изображений")
                
        except Exception as e:
            logger.error(f"Ошибка при очистке изображений: {e}")
    
    async def get_image_info(self, filepath: str) -> Optional[Dict[str, Any]]:
        """Получение информации об изображении"""
        if not os.path.exists(filepath):
            return None
        
        try:
            import PIL.Image
            from PIL import Image as PILImage
            
            with PILImage.open(filepath) as img:
                return {
                    'format': img.format,
                    'size': img.size,
                    'mode': img.mode,
                    'file_size': os.path.getsize(filepath),
                    'filename': os.path.basename(filepath)
                }
        except Exception as e:
            logger.error(f"Ошибка получения информации об изображении: {e}")
            return None
    
    async def resize_image(self, filepath: str, max_size: tuple = (512, 512)) -> Optional[str]:
        """Изменение размера изображения"""
        try:
            import PIL.Image
            from PIL import Image as PILImage
            
            with PILImage.open(filepath) as img:
                img.thumbnail(max_size, PILImage.Resampling.LANCZOS)
                
                # Сохраняем с новым именем
                name, ext = os.path.splitext(filepath)
                resized_path = f"{name}_resized{ext}"
                img.save(resized_path, quality=85)
                
                return resized_path
                
        except Exception as e:
            logger.error(f"Ошибка изменения размера изображения: {e}")
            return None
    
    async def convert_to_jpeg(self, filepath: str) -> Optional[str]:
        """Конвертация изображения в JPEG"""
        try:
            import PIL.Image
            from PIL import Image as PILImage
            
            with PILImage.open(filepath) as img:
                # Конвертируем в RGB если нужно
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Сохраняем как JPEG
                name, _ = os.path.splitext(filepath)
                jpeg_path = f"{name}.jpg"
                img.save(jpeg_path, 'JPEG', quality=90)
                
                return jpeg_path
                
        except Exception as e:
            logger.error(f"Ошибка конвертации в JPEG: {e}")
            return None

# Глобальный экземпляр
image_storage = ImageStorage()
