import os
import asyncio
import base64
import json
import logging
from typing import Optional, Dict, Any
import aiohttp
from datetime import datetime
from config import GEMINI_API_KEY, IMAGE_QUALITY

logger = logging.getLogger(__name__)

class GeminiImageService:
    """Генерация изображений через Google Gemini (Imagen)"""
    
    # Константы для моделей
    MODELS = {
        "imagen-3": "imagen-3.0-generate-001",
        "imagen-3-fast": "imagen-3.0-fast-generate-001",
        "imagen-2": "imagen-2.0-generate-001",
    }
    
    # Настройки безопасности для еды
    SAFETY_SETTINGS = [
        {
            "category": "HARM_CATEGORY_HARASSMENT",
            "threshold": "BLOCK_NONE"
        },
        {
            "category": "HARM_CATEGORY_HATE_SPEECH", 
            "threshold": "BLOCK_NONE"
        },
        {
            "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
            "threshold": "BLOCK_NONE"
        },
        {
            "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
            "threshold": "BLOCK_NONE"
        }
    ]
    
    def __init__(self, model: str = "imagen-3-fast"):
        """
        Инициализация сервиса Gemini
        
        Args:
            model: Модель для генерации (imagen-3, imagen-3-fast, imagen-2)
        """
        self.api_key = GEMINI_API_KEY
        self.model_id = self.MODELS.get(model, self.MODELS["imagen-3-fast"])
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
        self.generation_config = {
            "candidate_count": 1,
            "aspect_ratio": "1:1",  # Квадрат для Telegram
            "add_watermark": False,
            "safety_settings": self.SAFETY_SETTINGS
        }
        
        if not self.api_key:
            logger.error("GEMINI_API_KEY не установлен в .env файле")
            raise ValueError("GEMINI_API_KEY не найден")
    
    async def generate(
        self, 
        dish_name: str, 
        recipe_text: str = None,
        visual_desc: str = None
    ) -> Optional[bytes]:
        """
        Генерирует изображение блюда через Google Imagen
        
        Args:
            dish_name: Название блюда
            recipe_text: Полный текст рецепта
            visual_desc: Визуальное описание от LLM
            
        Returns:
            bytes: Изображение в формате JPEG/PNG или None при ошибке
        """
        start_time = datetime.now()
        
        try:
            # 1. Создаем промпт
            prompt = self._create_prompt(dish_name, recipe_text, visual_desc)
            logger.debug(f"Gemini промпт для {dish_name[:50]}...")
            
            # 2. Генерируем изображение
            image_data = await self._generate_image(prompt)
            
            if not image_data:
                logger.error(f"Gemini не вернул изображение для {dish_name}")
                return None
            
            # 3. Оптимизируем изображение
            optimized_image = await self._optimize_image(image_data)
            
            # 4. Логируем успех
            duration = (datetime.now() - start_time).total_seconds()
            logger.info(f"✅ Gemini сгенерировал {dish_name} за {duration:.1f}с, размер: {len(optimized_image) / 1024:.1f}KB")
            
            return optimized_image
            
        except aiohttp.ClientError as e:
            logger.error(f"Сетевая ошибка Gemini для {dish_name}: {e}")
            return None
        except Exception as e:
            logger.error(f"Критическая ошибка Gemini для {dish_name}: {e}", exc_info=True)
            return None
    
    def _create_prompt(self, dish_name: str, recipe_text: str = None, visual_desc: str = None) -> str:
        """
        Создает детальный промпт для генерации изображения еды
        
        Args:
            dish_name: Название блюда
            recipe_text: Текст рецепта
            visual_desc: Визуальное описание
            
        Returns:
            str: Оптимизированный промпт
        """
        # Извлекаем ключевые ингредиенты
        ingredients = self._extract_ingredients(recipe_text, visual_desc)
        
        # Определяем стиль блюда
        style = self._determine_style(dish_name, ingredients)
        
        # Создаем промпт
        prompt_parts = [
            f"Professional food photography of {dish_name}.",
            f"Ingredients: {ingredients}." if ingredients else "",
            f"Style: {style}.",
            "High quality, restaurant presentation.",
            "Natural window lighting, soft shadows.",
            "Shallow depth of field, blurred background.",
            "Clean plate on rustic wooden table.",
            "Appetizing, vibrant colors, fresh look.",
            "No text, no watermark, no logos.",
            "No people, no hands, no utensils in frame.",
            "Square aspect ratio 1:1.",
            "1024x1024 resolution, sharp focus on food."
        ]
        
        # Фильтруем пустые части
        prompt = " ".join(filter(None, prompt_parts))
        
        # Ограничиваем длину промпта
        max_length = 1000
        if len(prompt) > max_length:
            prompt = prompt[:max_length] + "..."
        
        return prompt.strip()
    
    def _extract_ingredients(self, recipe_text: str = None, visual_desc: str = None) -> str:
        """
        Извлекает ключевые ингредиенты из текста
        
        Returns:
            str: Список ингредиентов через запятую
        """
        ingredients = []
        
        # Пробуем из визуального описания
        if visual_desc:
            # Упрощаем описание
            simple_desc = visual_desc.lower()
            # Убираем лишние слова
            for word in ["professional", "photography", "photo", "image", "picture", "of"]:
                simple_desc = simple_desc.replace(word, "")
            ingredients.append(simple_desc.strip())
        
        # Пробуем из рецепта
        if recipe_text:
            # Ищем раздел с ингредиентами
            lines = recipe_text.split('\n')
            in_ingredients = False
            
            for line in lines:
                line_lower = line.lower()
                
                # Начало раздела ингредиентов
                if any(keyword in line_lower for keyword in ["ингредиент", "состав", "продукт", "ingredient", "ingredients"]):
                    in_ingredients = True
                    continue
                
                # Конец раздела
                if in_ingredients and any(keyword in line_lower for keyword in ["приготовлен", "инструкц", "шаг", "instruction", "steps"]):
                    break
                
                # Собираем ингредиенты
                if in_ingredients and len(line.strip()) > 2:
                    # Убираем маркеры списка
                    clean_line = line.strip().lstrip('-•* ').strip()
                    if clean_line and len(clean_line) < 100:  # Не слишком длинные строки
                        ingredients.append(clean_line)
                        if len(ingredients) >= 5:  # Максимум 5 ингредиентов
                            break
        
        # Если ничего не нашли, используем общее описание
        if not ingredients:
            return "fresh ingredients, beautifully presented"
        
        # Берем уникальные, ограничиваем количество
        unique_ingredients = []
        seen = set()
        for ing in ingredients:
            if ing not in seen and len(ing) > 2:
                seen.add(ing)
                unique_ingredients.append(ing)
        
        return ", ".join(unique_ingredients[:5])  # Максимум 5 ингредиентов
    
    def _determine_style(self, dish_name: str, ingredients: str) -> str:
        """
        Определяет стиль презентации блюда
        
        Returns:
            str: Описание стиля
        """
        dish_lower = dish_name.lower()
        ingredients_lower = ingredients.lower()
        
        # Определяем тип кухни
        cuisine_keywords = {
            "italian": ["pasta", "pizza", "risotto", "bruschetta", "tiramisu"],
            "asian": ["sushi", "ramen", "stir fry", "curry", "dumpling"],
            "french": ["ratatouille", "quiche", "crepe", "souffle", "croissant"],
            "mexican": ["taco", "burrito", "guacamole", "enchilada", "quesadilla"],
            "russian": ["борщ", "блины", "пельмени", "окрошка", "салат оливье"],
            "dessert": ["cake", "pie", "cookie", "ice cream", "chocolate", "десерт", "торт"]
        }
        
        cuisine = "international"
        for cuisine_name, keywords in cuisine_keywords.items():
            if any(keyword in dish_lower or keyword in ingredients_lower for keyword in keywords):
                cuisine = cuisine_name
                break
        
        # Определяем уровень презентации
        presentation = "restaurant quality"
        if any(word in dish_lower for word in ["simple", "basic", "easy", "quick", "простой", "быстрый"]):
            presentation = "home-style, rustic"
        elif any(word in dish_lower for word in ["gourmet", "fine dining", "luxury", "премиум"]):
            presentation = "fine dining, gourmet"
        
        return f"{cuisine} {presentation}"
    
    async def _generate_image(self, prompt: str) -> Optional[bytes]:
        """
        Выполняет запрос к Gemini API для генерации изображения
        
        Args:
            prompt: Текстовый промпт
            
        Returns:
            bytes: Сгенерированное изображение
        """
        url = f"{self.base_url}/models/{self.model_id}:generateContent?key={self.api_key}"
        
        headers = {
            "Content-Type": "application/json"
        }
        
        payload = {
            "contents": [{
                "parts": [{
                    "text": prompt
                }]
            }],
            "generationConfig": self.generation_config
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload, timeout=30) as response:
                    
                    if response.status == 200:
                        response_data = await response.json()
                        
                        # Извлекаем изображение из ответа
                        if "candidates" in response_data and response_data["candidates"]:
                            candidate = response_data["candidates"][0]
                            if "content" in candidate and "parts" in candidate["content"]:
                                for part in candidate["content"]["parts"]:
                                    if "inlineData" in part:
                                        image_data = part["inlineData"]["data"]
                                        return base64.b64decode(image_data)
                    
                    # Логируем ошибку
                    error_text = await response.text()
                    logger.error(f"Gemini API ошибка {response.status}: {error_text[:200]}")
                    return None
                    
        except asyncio.TimeoutError:
            logger.error("Gemini API timeout (30 секунд)")
            return None
    
    async def _optimize_image(self, image_data: bytes) -> bytes:
        """
        Оптимизирует изображение: сжатие, изменение размера и т.д.
        
        Args:
            image_data: Исходное изображение
            
        Returns:
            bytes: Оптимизированное изображение
        """
        try:
            from PIL import Image
            import io
            
            # Открываем изображение
            img = Image.open(io.BytesIO(image_data))
            
            # Конвертируем в RGB если нужно
            if img.mode in ('RGBA', 'LA', 'P'):
                # Создаем белый фон для прозрачных изображений
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            
            # Изменяем размер если слишком большое
            max_size = 1024
            if max(img.size) > max_size:
                ratio = max_size / max(img.size)
                new_size = tuple(int(dim * ratio) for dim in img.size)
                img = img.resize(new_size, Image.Resampling.LANCZOS)
            
            # Оптимизируем качество
            output = io.BytesIO()
            img.save(output, format='JPEG', quality=IMAGE_QUALITY, optimize=True)
            
            return output.getvalue()
            
        except ImportError:
            logger.warning("PIL не установлен, пропускаем оптимизацию изображения")
            return image_data
        except Exception as e:
            logger.error(f"Ошибка оптимизации изображения: {e}")
            return image_data
    
    async def test_connection(self) -> bool:
        """
        Тестирует подключение к Gemini API
        
        Returns:
            bool: True если подключение успешно
        """
        try:
            url = f"{self.base_url}/models?key={self.api_key}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    return response.status == 200
                    
        except Exception as e:
            logger.error(f"Ошибка тестирования Gemini: {e}")
            return False

# Синглтон
gemini_service = GeminiImageService()