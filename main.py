import asyncio
import os
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from config import API_CONFIG
from bot.handlers import register_handlers
from state.manager import state_manager
from aiohttp import web
from database import db
from utils.logger import setup_logging

# Настройка логирования
setup_logging()
logger = logging.getLogger(__name__)

# Инициализация
bot = Bot(token=API_CONFIG.telegram_token)
dp = Dispatcher()

# --- Веб-сервер для Render ---
async def health_check(request):
    """Health check endpoint для Render"""
    return web.Response(text="Cooking Bot is running OK")

async def db_health_check(request):
    """Проверка здоровья БД"""
    try:
        stats = await db.get_stats()
        return web.json_response({
            "status": "healthy",
            "database": "connected",
            "stats": stats
        })
    except Exception as e:
        return web.json_response({
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e)
        }, status=500)

async def start_web_server():
    """Запуск веб-сервера для Render"""
    try:
        app = web.Application()
        app.router.add_get('/', health_check)
        app.router.add_get('/health', health_check)
        app.router.add_get('/db-health', db_health_check)
        
        runner = web.AppRunner(app)
        await runner.setup()
        
        port = int(os.environ.get("PORT", 8080))
        site = web.TCPSite(runner, '0.0.0.0', port)
        await site.start()
        
        logger.info(f"✅ WEB SERVER STARTED ON PORT {port}")
        
        # Запускаем периодические задачи
        asyncio.create_task(periodic_cleanup())
        
    except Exception as e:
        logger.error(f"❌ Error starting web server: {e}")

async def periodic_cleanup():
    """Периодическая очистка устаревших данных"""
    import time
    while True:
        try:
            # Ожидаем 1 час
            await asyncio.sleep(3600)
            
            # Очищаем устаревшие сессии
            cleanup_result = await db.cleanup()
            logger.info(f"🧹 Периодическая очистка: {cleanup_result}")
            
        except Exception as e:
            logger.error(f"Ошибка периодической очистки: {e}")
            await asyncio.sleep(300)  # Ждем 5 минут при ошибке

# --- НАСТРОЙКА МЕНЮ БОТА ---
async def setup_bot_commands(bot: Bot):
    """Настройка команд бота"""
    commands = [
        BotCommand(command="/start", description="🔄 Рестарт / новые продукты"),
        BotCommand(command="/author", description="👨‍💻 Автор бота"),
        BotCommand(command="/stats", description="📊 Статистика и история"),
        BotCommand(command="/favorites", description="❤️ Мои избранные рецепты"),
        BotCommand(command="/history", description="📝 История моих рецептов")
    ]
    try:
        await bot.set_my_commands(commands)
        logger.info("✅ Команды бота настроены")
    except Exception as e:
        logger.error(f"❌ Не удалось установить команды: {e}")

# --- ГЛАВНАЯ ФУНКЦИЯ ---
async def main():
    logger.info("🤖 Инициализация кулинарного бота с улучшенной архитектурой...")
    
    try:
        # 1. Инициализация базы данных
        await db.initialize()
        logger.info("✅ База данных инициализирована")
        
        # 2. Инициализация StateManager
        await state_manager.initialize()
        logger.info("✅ StateManager инициализирован")
        
        # 3. Запуск веб-сервера для Render
        await start_web_server()
        
        # 4. Регистрация обработчиков
        register_handlers(dp)
        logger.info("✅ Обработчики зарегистрированы")
        
        # 5. Настройка команд бота
        await setup_bot_commands(bot)
        
        logger.info("🚀 Запуск бота...")
        
        # 6. Удаляем вебхук и запускаем polling
        await bot.delete_webhook(drop_pending_updates=True)
        
        # 7. Запускаем polling
        await dp.start_polling(bot)
        
    except Exception as e:
        logger.error(f"❌ Критическая ошибка при запуске: {e}")
        raise
    finally:
        # Graceful shutdown
        logger.info("🔄 Завершение работы бота...")
        await state_manager.shutdown()
        logger.info("👋 Бот завершил работу")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("⏹ Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"💥 Критическая ошибка: {e}")
        sys.exit(1)
