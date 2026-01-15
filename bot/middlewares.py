"""
Middleware для бота
"""
import logging
import time
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from database import db

logger = logging.getLogger(__name__)

class UserRegistrationMiddleware(BaseMiddleware):
    """Middleware для автоматической регистрации пользователя"""
    
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        user = event.from_user
        
        # Регистрируем/обновляем пользователя в БД
        try:
            await db.users.get_or_create(
                telegram_id=user.id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name
            )
            
            # Обновляем время последней активности
            await db.users.update_last_active(user.id)
            
        except Exception as e:
            logger.error(f"Ошибка регистрации пользователя: {e}")
        
        return await handler(event, data)

class LoggingMiddleware(BaseMiddleware):
    """Middleware для логирования всех событий"""
    
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        start_time = time.time()
        
        user = event.from_user
        logger.info(f"📨 Сообщение от @{user.username} (ID: {user.id}): {event.text}")
        
        try:
            result = await handler(event, data)
        except Exception as e:
            logger.error(f"❌ Ошибка обработки сообщения: {e}")
            raise
        
        end_time = time.time()
        logger.info(f"✅ Сообщение обработано за {end_time - start_time:.2f} сек")
        
        return result

class CallbackLoggingMiddleware(BaseMiddleware):
    """Middleware для логирования callback запросов"""
    
    async def __call__(
        self,
        handler: Callable[[CallbackQuery, Dict[str, Any]], Awaitable[Any]],
        event: CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        user = event.from_user
        logger.info(f"🖱️ Callback от @{user.username}: {event.data}")
        
        return await handler(event, data)
