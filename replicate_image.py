import os
import asyncio
import base64
import logging
from typing import Optional, Dict, Any
import replicate
from datetime import datetime
from config import REPLICATE_API_KEY, IMAGE_QUALITY

logger = logging.getLogger(__name__)

class ReplicateImageService:
    """Генерация изображений через Replicate (flux-1.1-pro)"""
    
    # Доступные модели
    MODELS = {
        "flux-1.1-pro": "black-forest-labs/flux-1.1-pro",
        "flux-kontext-pro": "black-forest-labs/flux-kontext-pro",
        "sdxl": "stability-ai/sdxl",
        "realvisxl": "sgriebel/realvisxl-v4.0"
    }
    
    # Параметры по умолчанию для каждой модели
    MODEL_PARAMS = {
        "flux-1.1-pro": {
            "guidance_scale": 7.5,
            "num_inference_steps": 30,
            "aspect_ratio": "1:1",
            "negative_prompt": "text, watermark, logo, people, hands, blurry, cartoon, 3d render, drawing, bad quality, ugly"
        },
        "flux-kontext-pro": {
            "guidance_scale": 7.0,
            "num_inference_steps": 28,
            "aspect_ratio": "1:1",
            "negative_prompt": "text, watermark, logo, people, hands, blurry, cartoon, 3d render, drawing"
        },
        "sdxl": {
            "guidance_scale": 7.5,
            "num_inference_steps": 25,
            "negative_prompt": "text, watermark, logo, people, hands, blurry"
        },
        "realvisxl": {
            "guidance_scale": 7.0,
            "num_inference_steps": 30,
            "negative_prompt": "text, watermark, logo, people, hands, blurry"
        }
    }
    
    def __init__(self, model: str = "flux-1.1-pro"):
        """
        Инициализация Replicate сервиса
        
        Args:
            model: Идентификатор модели (flux-1.1-pro, flux-kontext-pro, sdxl, realvisxl)
        """
        self.api_key = REPLICATE_API_KEY
        self.model_id = self.MODELS.get(model, self.MODELS["flux-1.1-pro"])
        self.model_params = self.MODEL_PARAMS.get(model, self.MODEL_PARAMS["flux-1.1-pro"])
        
        if not self.api_key:
            logger.error("REPLICATE_API_KEY не установлен в .env файле")
            raise ValueError("REPLICATE_API_KEY не найден")
        
        # Инициализируем клиент
        self.client = replicate.Client(api_token=self.api_key)
        logger.info(f"✅ Replicate инициализирован с моделью {model}")
    
    async def generate(
        self, 
        dish_name: str, 
        recipe_text: str = None,
        visual_desc: str = None
    ) -> Optional[bytes]:
        """
        Генерирует изображение блюда через Replicate
        
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
            logger.debug(f"Replicate промпт для {dish_name[:50]}...")
            
            # 2. Подготавливаем параметры
            params = self._prepare_parameters(prompt)
            
            # 3. Генерируем изображение
            logger.info(f"Запуск генерации через Replicate: {dish_name}")
            image_url = await self._run_generation(params)
            
            if not image_url:
                logger.error(f"Replicate не вернул URL изображения для {dish_name}")
                return None
            
            # 4. Скачиваем изображение
            image_data = await self._download_image(image_url)
            
            if not image_data:
                logger.error(f"Не удалось скачать изображение для {dish_name}")
                return None
            
            # 5. Оптимизируем изображение
            optimized_image = await self._optimize_image(image_data)
            
            # 6. Логируем успех
            duration = (datetime.now() - start_time).total_seconds()
            logger.info(f"✅ Replicate сгенерировал {dish_name} за {duration:.1f}с, размер: {len(optimized_image) / 1024:.1f}KB")
            
            return optimized_image
            
        except replicate.exceptions.ModelError as e:
            logger.error(f"Ошибка модели Replicate для {dish_name}: {e}")
            return None
        except replicate.exceptions.ReplicateError as e:
            logger.error(f"Ошибка Replicate API для {dish_name}: {e}")
            return None
        except Exception as e:
            logger.error(f"Критическая ошибка Replicate для {dish_name}: {e}", exc_info=True)
            return None
    
    def _create_prompt(self, dish_name: str, recipe_text: str = None, visual_desc: str = None) -> str:
        """
        Создает промпт для Replicate модели
        
        Args:
            dish_name: Название блюда
            recipe_text: Текст рецепта
            visual_desc: Визуальное описание
            
        Returns:
            str: Оптимизированный промпт для Replicate
        """
        # Извлекаем ключевые элементы
        elements = self._extract_key_elements(recipe_text, visual_desc)
        
        # Определяем стиль
        style = self._determine_replicate_style(dish_name, elements)
        
        # Собираем промпт частями
        prompt_parts = [
            # Основное описание
            f"Professional food photography of {dish_name}",
            
            # Детали
            elements if elements else "",
            
            # Качество и стиль
            style,
            "highly detailed, sharp focus",
            "appetizing, delicious looking",
            
            # Освещение и композиция
            "natural window lighting, soft shadows",
            "shallow depth of field, blurred background",
            "clean plate, food styling",
            
            # Технические требования
            "square aspect ratio 1:1",
            "1024x1024 resolution"
        ]
        
        # Фильтруем пустые части
        prompt = ", ".join(filter(None, prompt_parts))
        
        # Ограничиваем длину (Replicate обычно до 500 символов)
        max_length = 500
        if len(prompt) > max_length:
            # Сохраняем самое важное
            important_parts = [
                f"Professional food photography of {dish_name}",
                elements[:100] if elements else "",
                style,
                "appetizing, delicious looking"
            ]
            prompt = ", ".join(filter(None, important_parts))[:max_length]
        
        return prompt.strip()
    
    def _extract_key_elements(self, recipe_text: str = None, visual_desc: str = None) -> str:
        """
        Извлекает ключевые элементы для Replicate промпта
        
        Returns:
            str: Ключевые элементы через запятую
        """
        elements = []
        
        # Из визуального описания
        if visual_desc:
            # Упрощаем для Replicate
            simple_desc = visual_desc.lower()
            # Убираем технические термины
            for word in ["professional", "photography", "photo", "image", "picture"]:
                simple_desc = simple_desc.replace(word, "")
            elements.append(simple_desc.strip())
        
        # Из рецепта (первые упоминания ингредиентов)
        if recipe_text:
            lines = recipe_text.split('\n')
            for line in lines[:10]:  # Проверяем первые 10 строк
                line_lower = line.lower()
                # Ищем строки с ингредиентами
                if any(marker in line_lower for marker in ['-', '•', '*', '–']) and len(line.strip()) > 5:
                    clean_line = line.strip().lstrip('-•*– ').strip()
                    # Оставляем только существительные (грубая эвристика)
                    words = clean_line.split()
                    if words and len(words) <= 5:  # Короткие описания
                        elements.append(clean_line)
                        if len(elements) >= 3:  # Максимум 3 элемента
                            break
        
        # Дедупликация и форматирование
        if elements:
            unique_elements = []
            seen = set()
            for elem in elements:
                if elem not in seen and len(elem) > 2:
                    seen.add(elem)
                    unique_elements.append(elem)
            
            return ", ".join(unique_elements[:3])  # Максимум 3 элемента
        
        return "fresh ingredients, beautiful presentation"
    
    def _determine_replicate_style(self, dish_name: str, elements: str) -> str:
        """
        Определяет стиль для Replicate промпта
        
        Returns:
            str: Описание стиля
        """
        dish_lower = dish_name.lower()
        elements_lower = elements.lower()
        
        # Стиль в зависимости от типа блюда
        if any(word in dish_lower or word in elements_lower 
               for word in ["cake", "pie", "cookie", "dessert", "sweet", "chocolate", "торт", "десерт"]):
            return "food photography, dessert styling, studio lighting"
        
        elif any(word in dish_lower or word in elements_lower 
                 for word in ["salad", "vegetable", "fresh", "зелень", "овощ", "салат"]):
            return "fresh, vibrant, natural light, healthy food"
        
        elif any(word in dish_lower or word in elements_lower 
                 for word in ["meat", "steak", "chicken", "beef", "pork", "мясо", "куриц", "говядин"]):
            return "restaurant quality, gourmet, dramatic lighting"
        
        elif any(word in dish_lower or word in elements_lower 
                 for word in ["soup", "stew", "broth", "суп", "бульон", "похлебка"]):
            return "comfort food, rustic, warm lighting"
        
        elif any(word in dish_lower or word in elements_lower 
                 for word in ["pasta", "pizza", "italian", "итальянск", "паста", "пицца"]):
            return "Italian cuisine, rustic, wood-fired"
        
        elif any(word in dish_lower or word in elements_lower 
                 for word in ["sushi", "asian", "japanese", "chinese", "суши", "азиатск"]):
            return "Japanese minimalism, clean presentation"
        
        else:
            return "restaurant quality, professional food styling"
    
    def _prepare_parameters(self, prompt: str) -> Dict[str, Any]:
        """
        Подготавливает параметры для Replicate API
        
        Args:
            prompt: Текстовый промпт
            
        Returns:
            Dict: Параметры для API
        """
        params = {
            "prompt": prompt,
            "num_outputs": 1,
            **self.model_params  # Добавляем параметры модели
        }
        
        # Для flux моделей добавляем дополнительные параметры
        if "flux" in self.model_id:
            params.update({
                "output_format": "jpg",
                "output_quality": 90,
                "seed": None,  # Случайный seed
            })
        
        return params
    
    async def _run_generation(self, params: Dict[str, Any]) -> Optional[str]:
        """
        Запускает генерацию через Replicate API
        
        Args:
            params: Параметры генерации
            
        Returns:
            str: URL сгенерированного изображения или None
        """
        try:
            # Запускаем в отдельном потоке, так как replicate.run блокирующий
            output = await asyncio.to_thread(
                self.client.run,
                self.model_id,
                input=params
            )
            
            # Ожидаем завершения и получаем результат
            if isinstance(output, list) and len(output) > 0:
                return output[0]
            elif isinstance(output, str):
                return output
            
            return None
            
        except Exception as e:
            logger.error(f"Ошибка запуска генерации Replicate: {e}")
            return None
    
    async def _download_image(self, image_url: str) -> Optional[bytes]:
        """
        Скачивает изображение по URL
        
        Args:
            image_url: URL изображения
            
        Returns:
            bytes: Данные изображения или None
        """
        import aiohttp
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url, timeout=30) as response:
                    if response.status == 200:
                        return await response.read()
                    else:
                        logger.error(f"Ошибка скачивания изображения: {response.status}")
                        return None
                        
        except asyncio.TimeoutError:
            logger.error("Timeout при скачивании изображения")
            return None
        except Exception as e:
            logger.error(f"Ошибка скачивания изображения: {e}")
            return None
    
    async def _optimize_image(self, image_data: bytes) -> bytes:
        """
        Оптимизирует изображение для Telegram
        
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
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            
            # Изменяем размер если слишком большое (Telegram ограничение ~10MB)
            max_dimension = 2048
            if max(img.size) > max_dimension:
                ratio = max_dimension / max(img.size)
                new_size = tuple(int(dim * ratio) for dim in img.size)
                img = img.resize(new_size, Image.Resampling.LANCZOS)
            
            # Сохраняем с оптимизацией
            output = io.BytesIO()
            
            # Выбираем формат в зависимости от модели
            if "flux" in self.model_id:
                # Flux обычно возвращает JPG
                img.save(output, format='JPEG', quality=IMAGE_QUALITY, optimize=True)
            else:
                # Другие модели могут возвращать PNG
                if img.mode == 'RGB':
                    img.save(output, format='JPEG', quality=IMAGE_QUALITY, optimize=True)
                else:
                    img.save(output, format='PNG', optimize=True)
            
            return output.getvalue()
            
        except ImportError:
            logger.warning("PIL не установлен, пропускаем оптимизацию")
            return image_data
        except Exception as e:
            logger.error(f"Ошибка оптимизации изображения: {e}")
            return image_data
    
    async def get_remaining_credits(self) -> Optional[float]:
        """
        Получает оставшийся баланс кредитов
        
        Returns:
            float: Оставшийся баланс в долларах или None
        """
        try:
            # Replicate API для получения баланса
            # Это требует дополнительных прав, обычно через dashboard
            # Здесь реализация заглушка
            
            # В реальности нужно использовать Replicate billing API
            # или парсить HTML dashboard (не рекомендуется)
            
            logger.info("Получение баланса Replicate через API не реализовано")
            logger.info("Проверьте баланс в https://replicate.com/account/billing")
            return None
            
        except Exception as e:
            logger.error(f"Ошибка получения баланса Replicate: {e}")
            return None
    
    async def test_connection(self) -> bool:
        """
        Тестирует подключение к Replicate API
        
        Returns:
            bool: True если подключение успешно
        """
        try:
            # Простой тест - пытаемся получить список моделей
            models = await asyncio.to_thread(self.client.models.list)
            return models is not None
            
        except Exception as e:
            logger.error(f"Ошибка тестирования Replicate: {e}")
            return False

# Синглтон с основной моделью
replicate_service = ReplicateImageService(model="flux-1.1-pro")