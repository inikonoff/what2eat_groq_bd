"""
Redis кэш (опционально)
"""
import logging
from typing import Optional, Any, Dict
import json
import pickle

logger = logging.getLogger(__name__)

class RedisCache:
    """Redis кэш (заглушка, требует настройки Redis)"""
    
    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0):
        self.host = host
        self.port = port
        self.db = db
        self._client = None
        self._connected = False
    
    async def connect(self):
        """Подключение к Redis"""
        try:
            # Раскомментировать для использования реального Redis
            # import redis.asyncio as redis
            # self._client = redis.Redis(host=self.host, port=self.port, db=self.db)
            # await self._client.ping()
            # self._connected = True
            # logger.info("✅ Подключение к Redis установлено")
            
            logger.warning("⚠️  Redis не настроен, используется заглушка")
            self._connected = False
            
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к Redis: {e}")
            self._connected = False
    
    async def disconnect(self):
        """Отключение от Redis"""
        if self._client and self._connected:
            await self._client.close()
            self._connected = False
            logger.info("💤 Отключение от Redis")
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Сохранение значения в кэш"""
        if not self._connected:
            return False
        
        try:
            # Сериализуем значение
            if isinstance(value, (dict, list)):
                serialized = json.dumps(value)
            else:
                serialized = str(value)
            
            if ttl:
                await self._client.setex(key, ttl, serialized)
            else:
                await self._client.set(key, serialized)
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка сохранения в Redis: {e}")
            return False
    
    async def get(self, key: str, default: Any = None) -> Any:
        """Получение значения из кэша"""
        if not self._connected:
            return default
        
        try:
            value = await self._client.get(key)
            if value is None:
                return default
            
            # Пытаемся десериализовать JSON
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value.decode()
                
        except Exception as e:
            logger.error(f"Ошибка получения из Redis: {e}")
            return default
    
    async def delete(self, key: str) -> bool:
        """Удаление значения из кэша"""
        if not self._connected:
            return False
        
        try:
            result = await self._client.delete(key)
            return result > 0
        except Exception as e:
            logger.error(f"Ошибка удаления из Redis: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Проверка существования ключа"""
        if not self._connected:
            return False
        
        try:
            return await self._client.exists(key) > 0
        except Exception as e:
            logger.error(f"Ошибка проверки ключа в Redis: {e}")
            return False
    
    async def incr(self, key: str, amount: int = 1) -> Optional[int]:
        """Инкремент значения"""
        if not self._connected:
            return None
        
        try:
            return await self._client.incrby(key, amount)
        except Exception as e:
            logger.error(f"Ошибка инкремента в Redis: {e}")
            return None
    
    async def hset(self, key: str, field: str, value: Any) -> bool:
        """Сохранение в хэш"""
        if not self._connected:
            return False
        
        try:
            if isinstance(value, (dict, list)):
                serialized = json.dumps(value)
            else:
                serialized = str(value)
            
            await self._client.hset
