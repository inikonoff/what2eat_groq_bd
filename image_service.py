import os
import asyncio
import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
import aiofiles
from pathlib import Path

from config import (
    IMAGE_PROVIDER_PRIORITY, ENABLE_IMAGE_CACHE, IMAGE_CACHE_DIR,
    GEMINI_DAILY_LIMIT, REPLICATE_FALLBACK_ENABLED,
    MAX_CACHE_SIZE_MB, CACHE_TTL_DAYS, CACHE_CLEANUP_INTERVAL_HOURS,
    IMAGE_CACHE_CLEANUP_ENABLED
)

from gemini_image import gemini_service
from replicate_image import replicate_service

logger = logging.getLogger(__name__)

class CacheManager:
    """Менеджер кэширования изображений"""
    
    def __init__(self, cache_dir: str = IMAGE_CACHE_DIR):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_index_file = self.cache_dir / "index.json"
        self.cache_index = self._load_index()
        self.last_cleanup = datetime.now()
    
    def _load_index(self) -> Dict[str, Dict]:
        """Загружает индекс кэша из файла"""
        try:
            if self.cache_index_file.exists():
                with open(self.cache_index_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Ошибка загрузки индекса кэша: {e}")
        
        return {}
    
    def _save_index(self):
        """Сохраняет индекс кэша в файл"""
        try:
            with open(self.cache_index_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache_index, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Ошибка сохранения индекса кэша: {e}")
    
    def _generate_cache_key(self, dish_name: str, recipe_text: str = None) -> str:
        """Генерирует уникальный ключ для кэширования"""
        text_to_hash = dish_name.lower().strip()
        if recipe_text:
            # Берем первые 1000 символов рецепта для хэша
            text_to_hash += recipe_text[:1000]
        
        return hashlib.md5(text_to_hash.encode()).hexdigest()
    
    def get_cache_path(self, cache_key: str) -> Path:
        """Возвращает путь к файлу в кэше"""
        return self.cache_dir / f"{cache_key}.jpg"
    
    async def get_cached_image(self, dish_name: str, recipe_text: str = None) -> Optional[bytes]:
        """
        Получает изображение из кэша если оно существует и не устарело
        
        Returns:
            bytes: Данные изображения или None
        """
        if not ENABLE_IMAGE_CACHE:
            return None
        
        cache_key = self._generate_cache_key(dish_name, recipe_text)
        cache_path = self.get_cache_path(cache_key)
        
        # Проверяем существование файла
        if not cache_path.exists():
            return None
        
        # Проверяем запись в индексе
        cache_info = self.cache_index.get(cache_key)
        if not cache_info:
            return None
        
        # Проверяем TTL
        created_at = datetime.fromisoformat(cache_info.get('created_at', '2000-01-01'))
        if datetime.now() - created_at > timedelta(days=CACHE_TTL_DAYS):
            # Удаляем устаревший файл
            try:
                cache_path.unlink()
                del self.cache_index[cache_key]
                self._save_index()
            except Exception as e:
                logger.error(f"Ошибка удаления устаревшего кэша {cache_key}: {e}")
            return None
        
        # Читаем файл
        try:
            async with aiofiles.open(cache_path, 'rb') as f:
                image_data = await f.read()
                logger.debug(f"Кэш попадание для {dish_name[:50]}...")
                return image_data
        except Exception as e:
            logger.error(f"Ошибка чтения кэша {cache_key}: {e}")
            return None
    
    async def cache_image(self, dish_name: str, recipe_text: str, image_data: bytes) -> bool:
        """
        Сохраняет изображение в кэш
        
        Returns:
            bool: True если сохранение успешно
        """
        if not ENABLE_IMAGE_CACHE:
            return False
        
        cache_key = self._generate_cache_key(dish_name, recipe_text)
        cache_path = self.get_cache_path(cache_key)
        
        try:
            # Сохраняем изображение
            async with aiofiles.open(cache_path, 'wb') as f:
                await f.write(image_data)
            
            # Обновляем индекс
            self.cache_index[cache_key] = {
                'dish_name': dish_name[:100],
                'created_at': datetime.now().isoformat(),
                'size_kb': len(image_data) / 1024,
                'recipe_hash': hashlib.md5((recipe_text or '').encode()).hexdigest()[:8]
            }
            self._save_index()
            
            logger.debug(f"Изображение {dish_name[:50]}... сохранено в кэш")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка сохранения в кэш {cache_key}: {e}")
            return False
    
    async def cleanup_cache(self, force: bool = False) -> Dict[str, Any]:
        """
        Очищает кэш от устаревших и избыточных файлов
        
        Args:
            force: Принудительная очистка без проверки интервала
            
        Returns:
            Dict: Статистика очистки
        """
        if not IMAGE_CACHE_CLEANUP_ENABLED and not force:
            return {"skipped": "cleanup disabled"}
        
        # Проверяем интервал очистки
        if not force and (datetime.now() - self.last_cleanup < timedelta(hours=CACHE_CLEANUP_INTERVAL_HOURS)):
            return {"skipped": "cleanup interval not reached"}
        
        self.last_cleanup = datetime.now()
        
        stats = {
            "total_files_before": 0,
            "total_size_before_mb": 0,
            "removed_files": 0,
            "removed_size_mb": 0,
            "errors": 0
        }
        
        try:
            # Собираем информацию о всех файлах
            cache_files = []
            for cache_key, info in self.cache_index.items():
                cache_path = self.get_cache_path(cache_key)
                if cache_path.exists():
                    file_size = cache_path.stat().st_size
                    cache_files.append({
                        'key': cache_key,
                        'path': cache_path,
                        'size': file_size,
                        'created_at': datetime.fromisoformat(info.get('created_at', '2000-01-01')),
                        'info': info
                    })
            
            stats["total_files_before"] = len(cache_files)
            stats["total_size_before_mb"] = sum(f['size'] for f in cache_files) / (1024 * 1024)
            
            # 1. Удаляем устаревшие файлы (по TTL)
            for cache_file in cache_files[:]:  # Копируем для безопасного удаления
                if datetime.now() - cache_file['created_at'] > timedelta(days=CACHE_TTL_DAYS):
                    try:
                        cache_file['path'].unlink()
                        del self.cache_index[cache_file['key']]
                        stats["removed_files"] += 1
                        stats["removed_size_mb"] += cache_file['size'] / (1024 * 1024)
                        cache_files.remove(cache_file)
                    except Exception as e:
                        logger.error(f"Ошибка удаления устаревшего кэша {cache_file['key']}: {e}")
                        stats["errors"] += 1
            
            # 2. Удаляем избыточные файлы если превышен лимит размера
            current_size_mb = sum(f['size'] for f in cache_files) / (1024 * 1024)
            if current_size_mb > MAX_CACHE_SIZE_MB:
                # Сортируем по дате создания (старые первыми)
                cache_files.sort(key=lambda x: x['created_at'])
                
                while cache_files and current_size_mb > MAX_CACHE_SIZE_MB * 0.8:  # Оставляем 80% лимита
                    cache_file = cache_files.pop(0)
                    try:
                        cache_file['path'].unlink()
                        del self.cache_index[cache_file['key']]
                        stats["removed_files"] += 1
                        stats["removed_size_mb"] += cache_file['size'] / (1024 * 1024)
                        current_size_mb -= cache_file['size'] / (1024 * 1024)
                    except Exception as e:
                        logger.error(f"Ошибка удаления избыточного кэша {cache_file['key']}: {e}")
                        stats["errors"] += 1
            
            # Сохраняем обновленный индекс
            self._save_index()
            
            # Логируем результат
            logger.info(f"✅ Очистка кэша завершена. Удалено {stats['removed_files']} файлов, "
                       f"освобождено {stats['removed_size_mb']:.1f}MB")
            
            return stats
            
        except Exception as e:
            logger.error(f"Ошибка при очистке кэша: {e}", exc_info=True)
            stats["errors"] += 1
            return stats
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Возвращает статистику кэша"""
        total_size = 0
        file_count = 0
        oldest = None
        newest = None
        
        for cache_key, info in self.cache_index.items():
            cache_path = self.get_cache_path(cache_key)
            if cache_path.exists():
                file_count += 1
                total_size += cache_path.stat().st_size
                
                created_at = datetime.fromisoformat(info.get('created_at', '2000-01-01'))
                if oldest is None or created_at < oldest:
                    oldest = created_at
                if newest is None or created_at > newest:
                    newest = created_at
        
        return {
            "enabled": ENABLE_IMAGE_CACHE,
            "file_count": file_count,
            "total_size_mb": total_size / (1024 * 1024),
            "max_size_mb": MAX_CACHE_SIZE_MB,
            "ttl_days": CACHE_TTL_DAYS,
            "oldest_file": oldest.isoformat() if oldest else None,
            "newest_file": newest.isoformat() if newest else None,
            "cleanup_enabled": IMAGE_CACHE_CLEANUP_ENABLED,
            "last_cleanup": self.last_cleanup.isoformat()
        }


class ImageGenerationService:
    """Умный сервис генерации изображений с приоритетом Gemini и кэшированием"""
    
    def __init__(self):
        self.gemini_service = gemini_service
        self.replicate_service = replicate_service
        self.cache_manager = CacheManager()
        
        # Статистика
        self.stats = {
            "total_requests": 0,
            "cache_hits": 0,
            "gemini_success": 0,
            "gemini_failures": 0,
            "replicate_success": 0,
            "replicate_failures": 0,
            "gemini_daily_used": 0,
            "last_reset_date": datetime.now().date().isoformat()
        }
        
        # Периодическая очистка кэша
        self._start_periodic_cleanup()
        
        logger.info("✅ ImageGenerationService инициализирован")
    
    def _start_periodic_cleanup(self):
        """Запускает периодическую очистку кэша"""
        if IMAGE_CACHE_CLEANUP_ENABLED:
            asyncio.create_task(self._periodic_cleanup())
            logger.info(f"Периодическая очистка кэша запущена (интервал: {CACHE_CLEANUP_INTERVAL_HOURS}ч)")
    
    async def _periodic_cleanup(self):
        """Фоновая задача для периодической очистки кэша"""
        while True:
            try:
                await asyncio.sleep(CACHE_CLEANUP_INTERVAL_HOURS * 3600)
                await self.cache_manager.cleanup_cache()
            except Exception as e:
                logger.error(f"Ошибка в фоновой очистке кэша: {e}")
    
    async def generate_dish_image(
        self, 
        dish_name: str, 
        recipe_text: str = None,
        visual_desc: str = None
    ) -> Optional[bytes]:
        """
        Генерирует изображение блюда с интеллектуальным выбором провайдера
        
        Приоритет:
        1. Проверка кэша
        2. Gemini/Imagen (если не превышен дневной лимит)
        3. Replicate/flux-1.1-pro (резерв)
        
        Args:
            dish_name: Название блюда
            recipe_text: Полный текст рецепта
            visual_desc: Визуальное описание от LLM
            
        Returns:
            bytes: Изображение в формате JPEG или None
        """
        self.stats["total_requests"] += 1
        
        # 1. Проверяем кэш
        cached_image = await self.cache_manager.get_cached_image(dish_name, recipe_text)
        if cached_image:
            self.stats["cache_hits"] += 1
            logger.info(f"Кэш попадание для: {dish_name[:50]}...")
            return cached_image
        
        # 2. Сбрасываем счетчик в новый день
        self._reset_daily_counter()
        
        # 3. Выбираем провайдера в зависимости от настроек
        if IMAGE_PROVIDER_PRIORITY == "gemini_first":
            image_bytes = await self._try_gemini_first(dish_name, recipe_text, visual_desc)
        elif IMAGE_PROVIDER_PRIORITY == "replicate_only":
            image_bytes = await self._try_replicate_only(dish_name, recipe_text, visual_desc)
        else:
            # По умолчанию gemini_first
            image_bytes = await self._try_gemini_first(dish_name, recipe_text, visual_desc)
        
        # 4. Сохраняем в кэш если получили изображение
        if image_bytes:
            await self.cache_manager.cache_image(dish_name, recipe_text, image_bytes)
        
        return image_bytes
    
    async def _try_gemini_first(
        self, 
        dish_name: str, 
        recipe_text: str = None,
        visual_desc: str = None
    ) -> Optional[bytes]:
        """
        Пробуем Gemini, затем Replicate как fallback
        """
        # Проверяем дневной лимит Gemini
        if self.stats["gemini_daily_used"] < GEMINI_DAILY_LIMIT:
            try:
                logger.info(f"Пробуем Gemini для: {dish_name[:50]}...")
                image_bytes = await self.gemini_service.generate(dish_name, recipe_text, visual_desc)
                
                if image_bytes:
                    self.stats["gemini_success"] += 1
                    self.stats["gemini_daily_used"] += 1
                    return image_bytes
                else:
                    self.stats["gemini_failures"] += 1
                    
            except Exception as e:
                self.stats["gemini_failures"] += 1
                logger.error(f"Gemini ошибка для {dish_name}: {e}")
        
        else:
            logger.info(f"Дневной лимит Gemini исчерпан ({self.stats['gemini_daily_used']}/{GEMINI_DAILY_LIMIT})")
        
        # Пробуем Replicate как fallback
        if REPLICATE_FALLBACK_ENABLED:
            try:
                logger.info(f"Пробуем Replicate (fallback) для: {dish_name[:50]}...")
                image_bytes = await self.replicate_service.generate(dish_name, recipe_text, visual_desc)
                
                if image_bytes:
                    self.stats["replicate_success"] += 1
                    return image_bytes
                else:
                    self.stats["replicate_failures"] += 1
                    
            except Exception as e:
                self.stats["replicate_failures"] += 1
                logger.error(f"Replicate ошибка для {dish_name}: {e}")
        
        return None
    
    async def _try_replicate_only(
        self, 
        dish_name: str, 
        recipe_text: str = None,
        visual_desc: str = None
    ) -> Optional[bytes]:
        """
        Используем только Replicate
        """
        try:
            logger.info(f"Пробуем Replicate для: {dish_name[:50]}...")
            image_bytes = await self.replicate_service.generate(dish_name, recipe_text, visual_desc)
            
            if image_bytes:
                self.stats["replicate_success"] += 1
                return image_bytes
            else:
                self.stats["replicate_failures"] += 1
                
        except Exception as e:
            self.stats["replicate_failures"] += 1
            logger.error(f"Replicate ошибка для {dish_name}: {e}")
        
        return None
    
    def _reset_daily_counter(self):
        """Сбрасывает дневной счетчик Gemini при наступлении нового дня"""
        today = datetime.now().date()
        last_reset = datetime.fromisoformat(self.stats["last_reset_date"]).date()
        
        if today > last_reset:
            self.stats["gemini_daily_used"] = 0
            self.stats["last_reset_date"] = today.isoformat()
            logger.info(f"Сброс дневного счетчика Gemini. Сегодня: {today}")
    
    async def test_services(self) -> Dict[str, bool]:
        """
        Тестирует подключение ко всем сервисам
        
        Returns:
            Dict: Результаты тестирования каждого сервиса
        """
        results = {}
        
        try:
            # Тест Gemini
            gemini_ok = await self.gemini_service.test_connection()
            results["gemini"] = gemini_ok
            logger.info(f"Gemini тест: {'✅' if gemini_ok else '❌'}")
        except Exception as e:
            results["gemini"] = False
            logger.error(f"Gemini тест ошибка: {e}")
        
        try:
            # Тест Replicate
            replicate_ok = await self.replicate_service.test_connection()
            results["replicate"] = replicate_ok
            logger.info(f"Replicate тест: {'✅' if replicate_ok else '❌'}")
        except Exception as e:
            results["replicate"] = False
            logger.error(f"Replicate тест ошибка: {e}")
        
        # Тест кэша
        cache_stats = self.cache_manager.get_cache_stats()
        results["cache"] = cache_stats["enabled"]
        logger.info(f"Кэш тест: {'✅' if cache_stats['enabled'] else '❌'}")
        
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Возвращает статистику генерации
        
        Returns:
            Dict: Детальная статистика
        """
        cache_stats = self.cache_manager.get_cache_stats()
        
        return {
            "total_requests": self.stats["total_requests"],
            "cache_hits": self.stats["cache_hits"],
            "cache_hit_rate": (
                self.stats["cache_hits"] / self.stats["total_requests"] * 100 
                if self.stats["total_requests"] > 0 else 0
            ),
            "gemini": {
                "success": self.stats["gemini_success"],
                "failures": self.stats["gemini_failures"],
                "daily_used": self.stats["gemini_daily_used"],
                "daily_limit": GEMINI_DAILY_LIMIT
            },
            "replicate": {
                "success": self.stats["replicate_success"],
                "failures": self.stats["replicate_failures"]
            },
            "provider_priority": IMAGE_PROVIDER_PRIORITY,
            "replicate_fallback": REPLICATE_FALLBACK_ENABLED,
            "cache": cache_stats,
            "last_reset": self.stats["last_reset_date"]
        }
    
    async def cleanup(self):
        """Очистка ресурсов"""
        # Очищаем кэш при завершении
        await self.cache_manager.cleanup_cache(force=True)
        logger.info("✅ ImageGenerationService очищен")


# Синглтон
image_service = ImageGenerationService()