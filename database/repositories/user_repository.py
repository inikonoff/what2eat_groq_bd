import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from database.repositories.base import AsyncPGRepository

logger = logging.getLogger(__name__)

class UserRepository(AsyncPGRepository):
    """Репозиторий для работы с пользователями"""
    
    def __init__(self):
        super().__init__(table_name="users", pk_column="id")
    
    async def get_by_telegram_id(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        """Получение пользователя по Telegram ID"""
        query = """
            SELECT * FROM users
            WHERE telegram_id = $1
        """
        
        result = await self._execute_query(query, telegram_id)
        return self._map_row_to_entity(result[0]) if result else None
    
    async def get_or_create(self, telegram_id: int, **user_data) -> Dict[str, Any]:
        """Получение или создание пользователя"""
        user = await self.get_by_telegram_id(telegram_id)
        
        if user:
            # Обновляем данные если нужно
            updates = {}
            for key, value in user_data.items():
                if value is not None and value != user.get(key):
                    updates[key] = value
            
            if updates:
                user = await self.update(user['id'], updates)
            
            return user
        else:
            # Создаем нового пользователя
            user_data['telegram_id'] = telegram_id
            return await self.create(user_data)
    
    async def update_last_active(self, telegram_id: int):
        """Обновление времени последней активности"""
        user = await self.get_by_telegram_id(telegram_id)
        if user:
            await self.update(user['id'], {'last_active': datetime.now()})
    
    async def update_language(self, telegram_id: int, language_code: str) -> bool:
        """Обновление языка пользователя"""
        user = await self.get_by_telegram_id(telegram_id)
        if user:
            await self.update(user['id'], {'language_code': language_code})
            return True
        return False
    
    async def get_active_users(self, days: int = 7) -> List[Dict[str, Any]]:
        """Получение активных пользователей за последние N дней"""
        query = """
            SELECT * FROM users
            WHERE last_active >= NOW() - INTERVAL '$1 days'
            ORDER BY last_active DESC
        """
        
        result = await self._execute_query(query, days)
        return [self._map_row_to_entity(row) for row in result]
    
    async def get_user_stats(self, telegram_id: int) -> Dict[str, Any]:
        """Получение статистики пользователя"""
        user = await self.get_by_telegram_id(telegram_id)
        if not user:
            return {}
        
        # Количество рецептов
        recipes_count = await self._execute_query(
            "SELECT COUNT(*) FROM recipes WHERE user_id = $1",
            user['id']
        )
        
        # Количество избранных
        favorites_count = await self._execute_query(
            "SELECT COUNT(*) FROM favorite_recipes WHERE user_id = $1",
            user['id']
        )
        
        # Последние активности
        last_recipes = await self._execute_query(
            "SELECT dish_name, created_at FROM recipes WHERE user_id = $1 ORDER BY created_at DESC LIMIT 5",
            user['id']
        )
        
        return {
            'user_id': user['id'],
            'telegram_id': user['telegram_id'],
            'recipes_count': recipes_count[0]['count'] if recipes_count else 0,
            'favorites_count': favorites_count[0]['count'] if favorites_count else 0,
            'last_recipes': [
                {'dish_name': r['dish_name'], 'created_at': r['created_at']}
                for r in last_recipes
            ],
            'created_at': user['created_at'],
            'last_active': user['last_active']
        }
