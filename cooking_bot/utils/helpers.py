"""
Хелперы и вспомогательные функции
"""
import re
import random
import string
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
import hashlib
import asyncio
import logging

logger = logging.getLogger(__name__)

class Helpers:
    """Вспомогательные функции"""
    
    @staticmethod
    def generate_session_id(length: int = 16) -> str:
        """Генерация ID сессии"""
        chars = string.ascii_letters + string.digits
        return ''.join(random.choice(chars) for _ in range(length))
    
    @staticmethod
    def format_time_ago(dt: datetime) -> str:
        """
        Форматирование времени в человекочитаемый вид
        
        Examples:
            "5 минут назад", "2 часа назад", "вчера"
        """
        now = datetime.now()
        diff = now - dt
        
        if diff.days > 365:
            years = diff.days // 365
            return f"{years} год назад" if years == 1 else f"{years} лет назад"
        
        if diff.days > 30:
            months = diff.days // 30
            return f"{months} месяц назад" if months == 1 else f"{months} месяцев назад"
        
        if diff.days > 0:
            if diff.days == 1:
                return "вчера"
            elif diff.days < 7:
                return f"{diff.days} дня назад"
            else:
                weeks = diff.days // 7
                return f"{weeks} неделю назад" if weeks == 1 else f"{weeks} недель назад"
        
        if diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} час назад" if hours == 1 else f"{hours} часов назад"
        
        if diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} минуту назад" if minutes == 1 else f"{minutes} минут назад"
        
        return "только что"
    
    @staticmethod
    def truncate_text(text: str, max_length: int, ellipsis: str = "...") -> str:
        """Обрезка текста с добавлением многоточия"""
        if len(text) <= max_length:
            return text
        
        return text[:max_length - len(ellipsis)] + ellipsis
    
    @staticmethod
    def extract_hashtags(text: str) -> List[str]:
        """Извлечение хэштегов из текста"""
        return re.findall(r'#(\w+)', text)
    
    @staticmethod
    def calculate_md5(text: str) -> str:
        """Вычисление MD5 хэша"""
        return hashlib.md5(text.encode()).hexdigest()
    
    @staticmethod
    def split_into_chunks(text: str, chunk_size: int = 4000) -> List[str]:
        """
        Разделение текста на части по размеру
        
        Args:
            text: Исходный текст
            chunk_size: Максимальный размер части
            
        Returns:
            Список частей текста
        """
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        current_chunk = ""
        
        # Разделяем по абзацам
        paragraphs = text.split('\n\n')
        
        for paragraph in paragraphs:
            if len(current_chunk) + len(paragraph) + 2 <= chunk_size:
                current_chunk += paragraph + '\n\n'
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = paragraph + '\n\n'
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    @staticmethod
    def parse_duration(duration_str: str) -> Optional[int]:
        """
        Парсинг строки с длительностью в минуты
        
        Examples:
            "30 минут" -> 30
            "1.5 часа" -> 90
            "2 ч 30 мин" -> 150
        """
        if not duration_str:
            return None
        
        duration_str = duration_str.lower()
        total_minutes = 0
        
        # Паттерны для парсинга
        patterns = [
            (r'(\d+)\s*час', 60),           # часы
            (r'(\d+)\s*ч', 60),             # ч
            (r'(\d+)\s*минут', 1),          # минуты
            (r'(\d+)\s*мин', 1),            # мин
            (r'(\d+\.?\d*)\s*час', 60),     # дробные часы
        ]
        
        for pattern, multiplier in patterns:
            matches = re.findall(pattern, duration_str)
            for match in matches:
                try:
                    value = float(match) if '.' in match else int(match)
                    total_minutes += value * multiplier
                except ValueError:
                    continue
        
        return int(total_minutes) if total_minutes > 0 else None
    
    @staticmethod
    def format_duration(minutes: int) -> str:
        """Форматирование длительности в минутах в читаемый вид"""
        if minutes < 60:
            return f"{minutes} мин"
        
        hours = minutes // 60
        remaining_minutes = minutes % 60
        
        if remaining_minutes == 0:
            return f"{hours} ч"
        
        return f"{hours} ч {remaining_minutes} мин"
    
    @staticmethod
    def extract_ingredients(text: str) -> List[Tuple[str, Optional[str]]]:
        """
        Извлечение ингредиентов из текста рецепта
        
        Returns:
            Список кортежей (ингредиент, количество)
        """
        ingredients = []
        
        # Паттерны для извлечения ингредиентов
        patterns = [
            r'([\w\s]+)\s*-\s*([\d\.]+\s*\w+)',  # Ингредиент - количество
            r'([\d\.]+\s*\w+)\s+([\w\s]+)',      # Количество ингредиент
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if len(match) == 2:
                    ingredients.append((match[0].strip(), match[1].strip()))
        
        return ingredients
    
    @staticmethod
    async def with_timeout(coro, timeout: float, default=None):
        """
        Выполнение корутины с таймаутом
        
        Args:
            coro: Корутина
            timeout: Таймаут в секундах
            default: Значение по умолчанию при таймауте
            
        Returns:
            Результат корутины или default
        """
        try:
            return await asyncio.wait_for(coro, timeout=timeout)
        except asyncio.TimeoutError:
            logger.warning(f"Таймаут операции ({timeout} сек)")
            return default
        except Exception as e:
            logger.error(f"Ошибка в операции с таймаутом: {e}")
            return default
    
    @staticmethod
    def create_pagination(current_page: int, total_pages: int, max_buttons: int = 5) -> List[Dict[str, Any]]:
        """
        Создание структуры пагинации
        
        Returns:
            Список кнопок для пагинации
        """
        if total_pages <= 1:
            return []
        
        buttons = []
        
        # Всегда показываем первую страницу
        if current_page > 0:
            buttons.append({"text": "⬅️", "page": current_page - 1})
        
        # Показываем кнопки вокруг текущей страницы
        start_page = max(0, current_page - max_buttons // 2)
        end_page = min(total_pages, start_page + max_buttons)
        
        # Корректируем start_page если нужно
        if end_page - start_page < max_buttons and start_page > 0:
            start_page = max(0, end_page - max_buttons)
        
        for page in range(start_page, end_page):
            if page == current_page:
                buttons.append({"text": f"• {page + 1} •", "page": page})
            else:
                buttons.append({"text": str(page + 1), "page": page})
        
        # Всегда показываем последнюю страницу если не входит в диапазон
        if end_page < total_pages:
            buttons.append({"text": "...", "page": -1})  # Разделитель
            buttons.append({"text": str(total_pages), "page": total_pages - 1})
        
        # Кнопка следующей страницы
        if current_page < total_pages - 1:
            buttons.append({"text": "➡️", "page": current_page + 1})
        
        return buttons
    
    @staticmethod
    def safe_get(data: Dict, *keys, default=None):
        """
        Безопасное получение значения из словаря по цепочке ключей
        
        Example:
            safe_get(data, 'user', 'name', 'first', default='Unknown')
        """
        current = data
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        return current
    
    @staticmethod
    def format_bytes(size: int) -> str:
        """Форматирование размера в байтах в читаемый вид"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
