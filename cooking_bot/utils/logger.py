"""
Настройка логгирования
"""
import logging
import sys
from typing import Optional
import colorlog

def setup_logging(level: int = logging.INFO, log_file: Optional[str] = None):
    """
    Настройка логгирования с цветным выводом
    
    Args:
        level: Уровень логгирования
        log_file: Путь к файлу логов (опционально)
    """
    # Форматтер с цветами для консоли
    console_formatter = colorlog.ColoredFormatter(
        '%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        }
    )
    
    # Форматтер для файла (без цветов)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Обработчик для консоли
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(level)
    
    # Настройка корневого логгера
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.addHandler(console_handler)
    
    # Обработчик для файла (если указан)
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(file_formatter)
        file_handler.setLevel(level)
        root_logger.addHandler(file_handler)
    
    # Настройка логгеров для сторонних библиотек
    logging.getLogger('aiogram').setLevel(logging.WARNING)
    logging.getLogger('asyncio').setLevel(logging.WARNING)
    logging.getLogger('aiohttp').setLevel(logging.WARNING)
    
    # Информационное сообщение
    logging.info(f"Логгирование настроено (уровень: {logging.getLevelName(level)})")

def get_logger(name: str) -> logging.Logger:
    """
    Получение именованного логгера
    
    Args:
        name: Имя логгера
        
    Returns:
        Настроенный логгер
    """
    return logging.getLogger(name)

class LoggerMixin:
    """Миксин для добавления логгера в классы"""
    
    @property
    def logger(self) -> logging.Logger:
        """Логгер экземпляра класса"""
        if not hasattr(self, '_logger'):
            self._logger = logging.getLogger(self.__class__.__name__)
        return self._logger
