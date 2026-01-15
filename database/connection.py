import asyncpg
import logging
from typing import Optional
from contextlib import asynccontextmanager
from config import DB_CONFIG

logger = logging.getLogger(__name__)

class DatabaseConnection:
    """Управление подключением к базе данных"""
    
    _pool: Optional[asyncpg.Pool] = None
    
    @classmethod
    async def get_pool(cls) -> asyncpg.Pool:
        """Получение пула соединений (синглтон)"""
        if cls._pool is None:
            await cls.initialize()
        return cls._pool
    
    @classmethod
    async def initialize(cls):
        """Инициализация пула соединений"""
        try:
            cls._pool = await asyncpg.create_pool(
                dsn=DB_CONFIG.url,
                min_size=DB_CONFIG.min_connections,
                max_size=DB_CONFIG.max_connections,
                statement_cache_size=DB_CONFIG.statement_cache_size,
                command_timeout=60,
                max_queries=50000,
                max_inactive_connection_lifetime=300
            )
            logger.info("✅ Пул соединений с БД инициализирован")
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации пула БД: {e}")
            raise
    
    @classmethod
    async def close(cls):
        """Закрытие пула соединений"""
        if cls._pool:
            await cls._pool.close()
            cls._pool = None
            logger.info("💤 Пул соединений с БД закрыт")
    
    @classmethod
    @asynccontextmanager
    async def acquire_connection(self):
        """Контекстный менеджер для получения соединения"""
        pool = await self.get_pool()
        conn = await pool.acquire()
        try:
            yield conn
        finally:
            await pool.release(conn)
    
    @classmethod
    @asynccontextmanager
    async def transaction(self):
        """Контекстный менеджер для транзакции"""
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            async with conn.transaction():
                yield conn
