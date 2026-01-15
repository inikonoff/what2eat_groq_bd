import logging
import json
from typing import Dict, List, Optional
from datetime import datetime
from config import APP_CONFIG
from database import db

logger = logging.getLogger(__name__)

class StateManager:
    """Менеджер состояния с интеграцией в БД"""
    
    def __init__(self):
        self._cache = {}
        self._user_db_ids = {}  # telegram_id -> db_user_id
        
    async def initialize(self):
        """Инициализация менеджера состояния"""
        await db.initialize()
        logger.info("✅ StateManager инициализирован с БД")
    
    async def shutdown(self):
        """Завершение работы"""
        await db.close()
        logger.info("💤 StateManager завершил работу")
    
    async def _get_user_db_id(self, telegram_id: int) -> Optional[int]:
        """Получение ID пользователя в БД"""
        if telegram_id not in self._user_db_ids:
            user = await db.users.get_by_telegram_id(telegram_id)
            if user:
                self._user_db_ids[telegram_id] = user['id']
            else:
                return None
        
        return self._user_db_ids.get(telegram_id)
    
    async def load_user_session(self, telegram_id: int) -> bool:
        """Загрузка сессии пользователя из БД"""
        try:
            # Получаем пользователя
            user = await db.users.get_by_telegram_id(telegram_id)
            if not user:
                return False
            
            self._user_db_ids[telegram_id] = user['id']
            
            # Получаем активную сессию
            session = await db.sessions.get_active_session(user['id'])
            if not session:
                return False
            
            # Загружаем данные в кеш
            cache_key = f"user_{telegram_id}"
            self._cache[cache_key] = {
                'products': session.get('products', ''),
                'state': session.get('state', ''),
                'categories': session.get('categories', []),
                'generated_dishes': session.get('generated_dishes', []),
                'current_dish': session.get('current_dish', ''),
                'history': session.get('history', [])
            }
            
            logger.debug(f"📥 Сессия загружена из БД для user_id={telegram_id}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка загрузки сессии из БД: {e}")
            return False
    
    async def _save_session_to_db(self, telegram_id: int, session_data: dict):
        """Сохранение сессии в БД"""
        try:
            user_id = await self._get_user_db_id(telegram_id)
            if not user_id:
                return
            
            await db.sessions.update_session(user_id, session_data)
            
        except Exception as e:
            logger.error(f"Ошибка сохранения сессии в БД: {e}")
    
    def _get_cache(self, telegram_id: int, key: str, default=None):
        """Получение значения из кеша"""
        cache_key = f"user_{telegram_id}"
        if cache_key not in self._cache:
            self._cache[cache_key] = {}
        
        return self._cache[cache_key].get(key, default)
    
    def _set_cache(self, telegram_id: int, key: str, value):
        """Установка значения в кеш"""
        cache_key = f"user_{telegram_id}"
        if cache_key not in self._cache:
            self._cache[cache_key] = {}
        
        self._cache[cache_key][key] = value
    
    # === Продукты ===
    def get_products(self, telegram_id: int) -> Optional[str]:
        return self._get_cache(telegram_id, 'products')
    
    async def set_products(self, telegram_id: int, products: str):
        self._set_cache(telegram_id, 'products', products)
        await self._save_session_to_db(telegram_id, {'products': products})
    
    async def append_products(self, telegram_id: int, new_products: str):
        current = self.get_products(telegram_id)
        if current:
            products = f"{current}, {new_products}"
        else:
            products = new_products
        
        await self.set_products(telegram_id, products)
    
    # === Состояние ===
    def get_state(self, telegram_id: int) -> Optional[str]:
        return self._get_cache(telegram_id, 'state')
    
    async def set_state(self, telegram_id: int, state: str):
        self._set_cache(telegram_id, 'state', state)
        await self._save_session_to_db(telegram_id, {'state': state})
    
    async def clear_state(self, telegram_id: int):
        if self.get_state(telegram_id):
            self._set_cache(telegram_id, 'state', None)
            await self._save_session_to_db(telegram_id, {'state': None})
    
    # === Категории ===
    async def set_categories(self, telegram_id: int, categories: List[str]):
        self._set_cache(telegram_id, 'categories', categories)
        await self._save_session_to_db(telegram_id, {'categories': categories})
    
    def get_categories(self, telegram_id: int) -> List[str]:
        return self._get_cache(telegram_id, 'categories', [])
    
    # === Блюда ===
    async def set_generated_dishes(self, telegram_id: int, dishes: List[Dict]):
        self._set_cache(telegram_id, 'generated_dishes', dishes)
        await self._save_session_to_db(telegram_id, {'generated_dishes': dishes})
    
    def get_generated_dishes(self, telegram_id: int) -> List[Dict]:
        return self._get_cache(telegram_id, 'generated_dishes', [])
    
    def get_generated_dish(self, telegram_id: int, index: int) -> Optional[str]:
        dishes = self.get_generated_dishes(telegram_id)
        if 0 <= index < len(dishes):
            return dishes[index].get('name')
        return None
    
    # === Текущее блюдо ===
    async def set_current_dish(self, telegram_id: int, dish_name: str):
        self._set_cache(telegram_id, 'current_dish', dish_name)
        await self._save_session_to_db(telegram_id, {'current_dish': dish_name})
    
    def get_current_dish(self, telegram_id: int) -> Optional[str]:
        return self._get_cache(telegram_id, 'current_dish')
    
    # === История сообщений ===
    async def add_message(self, telegram_id: int, role: str, text: str):
        history = self._get_cache(telegram_id, 'history', [])
        
        history.append({
            "role": role,
            "text": text,
            "timestamp": datetime.now().isoformat()
        })
        
        # Ограничиваем историю
        if len(history) > APP_CONFIG.max_history_messages:
            history = history[-APP_CONFIG.max_history_messages:]
        
        self._set_cache(telegram_id, 'history', history)
        await self._save_session_to_db(telegram_id, {'history': history})
    
    def get_history(self, telegram_id: int) -> List[Dict]:
        return self._get_cache(telegram_id, 'history', [])
    
    def get_last_bot_message(self, telegram_id: int) -> Optional[str]:
        history = self.get_history(telegram_id)
        for msg in reversed(history):
            if msg.get("role") == "bot":
                return msg.get("text")
        return None
    
    # === Рецепты (сохранение в БД) ===
    async def save_recipe_to_history(self, telegram_id: int, dish_name: str, recipe_text: str):
        """Сохранение рецепта в историю БД"""
        try:
            user_id = await self._get_user_db_id(telegram_id)
            if not user_id:
                # Создаем пользователя если не существует
                from bot.handlers import get_user_info_from_message
                # Нужно имплементировать получение информации о пользователе
                return
            
            products = self.get_products(telegram_id)
            
            recipe = await db.recipes.create_recipe(
                user_id=user_id,
                dish_name=dish_name,
                recipe_text=recipe_text,
                products_used=products,
                is_ai_generated=True
            )
            
            logger.info(f"📝 Рецепт сохранён в историю: {dish_name} (ID: {recipe['id']})")
            
            # === "ОКНО" ДЛЯ ГЕНЕРАЦИИ ИЗОБРАЖЕНИЯ ===
            # TODO: Раскомментировать и настроить когда будет готов сервис генерации изображений
            """
            try:
                from services.replicate_service import ReplicateService
                replicate = ReplicateService()
                
                # Генерируем изображение для рецепта
                image_url = await replicate.generate_dish_image(dish_name, recipe_text)
                
                if image_url:
                    # Сохраняем изображение в БД
                    await db.images.create_image(
                        recipe_id=recipe['id'],
                        image_url=image_url,
                        storage_type='replicate',
                        prompt_used=f"Изображение блюда: {dish_name}",
                        model_name="stability-ai/stable-diffusion"
                    )
                    logger.info(f"🖼️ Изображение сохранено для рецепта: {dish_name}")
            except Exception as img_error:
                logger.error(f"Ошибка генерации изображения: {img_error}")
                # Продолжаем работу без изображения
            """
            
        except Exception as e:
            logger.error(f"Ошибка сохранения рецепта: {e}")
    
    # === Очистка сессии ===
    async def clear_session(self, telegram_id: int):
        """Полная очистка сессии"""
        # Очищаем кеш
        cache_key = f"user_{telegram_id}"
        if cache_key in self._cache:
            del self._cache[cache_key]
        
        # Очищаем сессию в БД
        try:
            user_id = await self._get_user_db_id(telegram_id)
            if user_id:
                await db.sessions.clear_session(user_id)
                logger.info(f"🧹 Сессия очищена для user_id={telegram_id}")
        except Exception as e:
            logger.error(f"Ошибка очистки сессии в БД: {e}")

# Глобальный экземпляр
state_manager = StateManager()
