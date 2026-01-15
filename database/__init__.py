"""
Фасад для работы с базой данных
"""
import logging
from typing import Optional
from database.connection import DatabaseConnection
from database.repositories.user_repository import UserRepository
from database.repositories.recipe_repository import RecipeRepository
from database.repositories.session_repository import SessionRepository
from database.repositories.image_repository import ImageRepository

logger = logging.getLogger(__name__)

class DatabaseFacade:
    """Фасад для работы со всеми репозиториями"""
    
    def __init__(self):
        self.users = UserRepository()
        self.recipes = RecipeRepository()
        self.sessions = SessionRepository()
        self.images = ImageRepository()
        self._initialized = False
    
    async def initialize(self):
        """Инициализация базы данных"""
        if not self._initialized:
            await DatabaseConnection.initialize()
            
            # Запускаем миграции
            try:
                from database.migrations.v1_initial import run_migration
                await run_migration()
                logger.info("✅ Миграции выполнены успешно")
            except Exception as e:
                logger.warning(f"⚠️  Ошибка при выполнении миграций: {e}")
                # Продолжаем работу, возможно таблицы уже созданы
            
            self._initialized = True
            logger.info("✅ DatabaseFacade инициализирован")
    
    async def close(self):
        """Закрытие соединений"""
        await DatabaseConnection.close()
        self._initialized = False
        logger.info("💤 DatabaseFacade закрыт")
    
    async def get_stats(self) -> dict:
        """Получение общей статистики"""
        try:
            # Количество пользователей
            users_count = await self.users._execute_query("SELECT COUNT(*) FROM users")
            users_count = users_count[0]['count'] if users_count else 0
            
            # Количество активных сессий
            active_sessions = await self.sessions._execute_query(
                "SELECT COUNT(*) FROM user_sessions WHERE expires_at > NOW()"
            )
            active_sessions = active_sessions[0]['count'] if active_sessions else 0
            
            # Количество сохраненных рецептов
            saved_recipes = await self.recipes._execute_query("SELECT COUNT(*) FROM recipes")
            saved_recipes = saved_recipes[0]['count'] if saved_recipes else 0
            
            # Количество изображений
            images_count = await self.images._execute_query("SELECT COUNT(*) FROM dish_images")
            images_count = images_count[0]['count'] if images_count else 0
            
            return {
                'users': users_count,
                'active_sessions': active_sessions,
                'saved_recipes': saved_recipes,
                'images_count': images_count
            }
        except Exception as e:
            logger.error(f"Ошибка получения статистики: {e}")
            return {
                'users': 0,
                'active_sessions': 0,
                'saved_recipes': 0,
                'images_count': 0
            }
    
    async def cleanup(self):
        """Очистка устаревших данных"""
        try:
            # Очищаем просроченные сессии
            expired_sessions = await self.sessions.cleanup_expired_sessions()
            
            # Можно добавить очистку временных изображений и т.д.
            
            return {
                'expired_sessions_cleaned': expired_sessions
            }
        except Exception as e:
            logger.error(f"Ошибка очистки данных: {e}")
            return {}

# Глобальный экземпляр фасада
db = DatabaseFacade()
