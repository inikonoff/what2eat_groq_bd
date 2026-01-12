import os
import sys
import asyncio
import logging
from datetime import datetime
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from aiogram.fsm.storage.memory import MemoryStorage
from aiohttp import web

from config import (
    TELEGRAM_TOKEN, LOG_LEVEL, LOG_TO_FILE, LOG_FILE_PATH,
    IMAGE_CACHE_CLEANUP_ENABLED, CACHE_CLEANUP_INTERVAL_HOURS
)
from handlers import register_handlers
from groq_service import GroqService
from supabase_service import supabase_service
from image_service import image_service

# Настройка логирования
def setup_logging():
    """Настраивает систему логирования"""
    log_level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)
    
    # Формат логов
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    
    # Базовые настройки
    logging.basicConfig(
        level=log_level,
        format=log_format,
        datefmt=date_format,
        handlers=[]
    )
    
    # Хендлер для stdout
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(log_level)
    stdout_handler.setFormatter(logging.Formatter(log_format, date_format))
    
    # Получаем корневой логгер
    root_logger = logging.getLogger()
    root_logger.addHandler(stdout_handler)
    
    # Хендлер для файла если нужно
    if LOG_TO_FILE:
        # Создаем директорию для логов
        log_dir = Path(LOG_FILE_PATH).parent
        log_dir.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(LOG_FILE_PATH, encoding='utf-8')
        file_handler.setLevel(log_level)
        file_handler.setFormatter(logging.Formatter(log_format, date_format))
        root_logger.addHandler(file_handler)
    
    # Устанавливаем уровень для наших логгеров
    logging.getLogger('aiogram').setLevel(logging.WARNING)
    logging.getLogger('aiohttp').setLevel(logging.WARNING)
    logging.getLogger('asyncio').setLevel(logging.WARNING)
    
    logger = logging.getLogger(__name__)
    logger.info(f"✅ Логирование настроено. Уровень: {LOG_LEVEL}")
    
    return logger

# Веб-сервер для health checks (Render/Heroku)
async def health_check(request):
    """Endpoint для проверки работоспособности"""
    return web.Response(text="Bot is running OK")

async def stats_check(request):
    """Endpoint для получения статистики"""
    try:
        stats = image_service.get_stats()
        return web.json_response(stats)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

async def start_web_server():
    """Запускает веб-сервер для health checks"""
    try:
        app = web.Application()
        app.router.add_get('/', health_check)
        app.router.add_get('/health', health_check)
        app.router.add_get('/stats', stats_check)
        
        runner = web.AppRunner(app)
        await runner.setup()
        
        port = int(os.environ.get("PORT", 8080))
        site = web.TCPSite(runner, '0.0.0.0', port)
        await site.start()
        
        logging.info(f"✅ Веб-сервер запущен на порту {port}")
        
    except Exception as e:
        logging.error(f"❌ Ошибка запуска веб-сервера: {e}")
        raise

async def setup_bot_commands(bot: Bot):
    """Настраивает команды бота"""
    commands = [
        BotCommand(command="start", description="🔄 Рестарт / новые продукты"),
        BotCommand(command="my_recipes", description="📂 Сохраненные рецепты"),
        BotCommand(command="author", description="👨‍💻 Автор бота"),
    ]
    
    try:
        await bot.set_my_commands(commands)
        logging.info("✅ Команды бота настроены")
    except Exception as e:
        logging.error(f"❌ Ошибка настройки команд: {e}")

async def test_services():
    """Тестирует подключение ко всем сервисам"""
    logger = logging.getLogger(__name__)
    
    logger.info("🧪 Тестирование подключения к сервисам...")
    
    results = {}
    
    # Тест Supabase
    try:
        test_user = await supabase_service.get_user(999999999)
        results['supabase'] = test_user is not None
        logger.info(f"Supabase: {'✅' if results['supabase'] else '❌'}")
    except Exception as e:
        results['supabase'] = False
        logger.error(f"Supabase error: {e}")
    
    # Тест Groq
    try:
        groq = GroqService()
        test_response = await groq.validate_ingredients("test")
        results['groq'] = True
        logger.info(f"Groq: ✅")
    except Exception as e:
        results['groq'] = False
        logger.error(f"Groq error: {e}")
    
    # Тест Image Services
    try:
        image_results = await image_service.test_services()
        results.update(image_results)
    except Exception as e:
        logger.error(f"Image services error: {e}")
        results['image_services'] = False
    
    # Сводка
    all_ok = all(results.values())
    if all_ok:
        logger.info("✅ Все сервисы подключены успешно!")
    else:
        failed = [k for k, v in results.items() if not v]
        logger.warning(f"⚠️ Некоторые сервисы не подключены: {failed}")
    
    return results

async def periodic_tasks(bot: Bot):
    """Фоновые периодические задачи"""
    logger = logging.getLogger(__name__)
    
    while True:
        try:
            # Ожидаем 1 час между задачами
            await asyncio.sleep(3600)
            
            # Очистка кэша изображений
            if IMAGE_CACHE_CLEANUP_ENABLED:
                logger.info("🔄 Запуск периодической очистки кэша изображений...")
                cache_stats = await image_service.cache_manager.cleanup_cache()
                logger.info(f"✅ Очистка кэша завершена: {cache_stats}")
            
            # Проверка статистики (логируем раз в час)
            stats = image_service.get_stats()
            logger.info(f"📊 Статистика за час: {stats['total_requests']} запросов, "
                       f"{stats['cache_hits']} попаданий в кэш ({stats['cache_hit_rate']:.1f}%)")
            
            # Можно добавить другие периодические задачи:
            # - Очистка старых сессий в БД
            # - Отправка статистики админу
            # - Проверка обновлений
            
        except Exception as e:
            logger.error(f"Ошибка в фоновых задачах: {e}")

async def on_startup(bot: Bot):
    """Действия при запуске бота"""
    logger = logging.getLogger(__name__)
    
    logger.info("🚀 Запуск бота...")
    
    # 1. Запускаем фоновые задачи сервиса изображений (ДОБАВИТЬ ЭТУ СТРОКУ)
    await image_service.start()
    
    # 2. Тестируем сервисы
    await test_services()
    
    # 3. Настраиваем команды
    await setup_bot_commands(bot)
    
    # 4. Запускаем фоновые задачи (это ваша старая функция periodic_tasks)
    asyncio.create_task(periodic_tasks(bot))
    
    logger.info("✅ Бот запущен и готов к работе!")

async def on_shutdown(bot: Bot):
    """Действия при остановке бота"""
    logger = logging.getLogger(__name__)
    
    logger.info("🛑 Остановка бота...")
    
    # Очистка ресурсов
    try:
        await image_service.cleanup()
        logger.info("✅ Ресурсы очищены")
    except Exception as e:
        logger.error(f"❌ Ошибка очистки ресурсов: {e}")
    
    logger.info("👋 Бот остановлен")

async def main():
    """Главная функция"""
    
    # Настройка логирования
    logger = setup_logging()
    
    try:
        # 1. Запускаем веб-сервер (для Render/Heroku)
        await start_web_server()
        
        # 2. Инициализируем бота
        bot = Bot(token=TELEGRAM_TOKEN)
        storage = MemoryStorage()
        dp = Dispatcher(storage=storage)
        
        # 3. Настраиваем обработчики запуска/остановки
        dp.startup.register(on_startup)
        dp.shutdown.register(on_shutdown)
        
        # 4. Регистрируем хендлеры
        register_handlers(dp)
        
        # 5. Запускаем бота
        logger.info("🤖 Бот запускается...")
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
        
    except KeyboardInterrupt:
        logger.info("⏹ Остановка по запросу пользователя")
    except Exception as e:
        logger.error(f"💥 Критическая ошибка: {e}", exc_info=True)
        raise
    finally:
        await on_shutdown(bot)

if __name__ == "__main__":
    # Запуск главной функции

    asyncio.run(main())
