import logging
import uuid
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from database.repositories.base import AsyncPGRepository

logger = logging.getLogger(__name__)

class SessionRepository(AsyncPGRepository):
    """Репозиторий для работы с сессиями"""
    
    def __init__(self):
        super().__init__(table_name="user_sessions", pk_column="id")
    
    async def create_session(self, user_id: int, **session_data) -> Dict[str, Any]:
        """Создание новой сессии"""
        session_id = str(uuid.uuid4())
        expires_at = datetime.now() + timedelta(hours=1)
        
        session_data.update({
            'session_id': session_id,
            'user_id': user_id,
            'created_at': datetime.now(),
            'updated_at': datetime.now(),
            'expires_at': expires_at
        })
        
        return await self.create(session_data)
    
    async def get_active_session(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получение активной сессии пользователя"""
        query = """
            SELECT * FROM user_sessions
            WHERE user_id = $1 
            AND expires_at > NOW()
            ORDER BY updated_at DESC
            LIMIT 1
        """
        
        result = await self._execute_query(query, user_id)
        return self._map_row_to_entity(result[0]) if result else None
    
    async def update_session(self, user_id: int, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Обновление сессии пользователя"""
        session = await self.get_active_session(user_id)
        
        if not session:
            # Создаем новую сессию
            return await self.create_session(user_id, **updates)
        
        # Обновляем существующую сессию
        updates['updated_at'] = datetime.now()
        updates['expires_at'] = datetime.now() + timedelta(hours=1)
        
        return await self.update(session['id'], updates)
    
    async def clear_session(self, user_id: int) -> bool:
        """Очистка сессии пользователя"""
        session = await self.get_active_session(user_id)
        if not session:
            return True
        
        return await self.delete(session['id'])
    
    async def cleanup_expired_sessions(self) -> int:
        """Очистка просроченных сессий"""
        query = """
            DELETE FROM user_sessions
            WHERE expires_at <= NOW()
            RETURNING COUNT(*)
        """
        
        result = await self._execute_query(query)
        count = result[0]['count'] if result else 0
        
        if count > 0:
            logger.info(f"🧹 Очищено {count} просроченных сессий")
        
        return count
    
    async def get_session_products(self, user_id: int) -> Optional[str]:
        """Получение продуктов из активной сессии"""
        session = await self.get_active_session(user_id)
        return session.get('products') if session else None
    
    async def set_session_products(self, user_id: int, products: str) -> bool:
        """Установка продуктов в сессии"""
        session = await self.update_session(user_id, {'products': products})
        return session is not None
    
    async def append_session_products(self, user_id: int, new_products: str) -> bool:
        """Добавление продуктов к существующим в сессии"""
        current = await self.get_session_products(user_id)
        
        if current:
            products = f"{current}, {new_products}"
        else:
            products = new_products
        
        return await self.set_session_products(user_id, products)
