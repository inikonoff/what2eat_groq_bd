"""
Доменный сервис для работы с сессиями
"""
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from domain.entities.session import UserSession
from domain.entities.user import User

logger = logging.getLogger(__name__)

class SessionService:
    """Сервис для бизнес-логики сессий"""
    
    @staticmethod
    def create_session(user: User) -> UserSession:
        """Создание новой сессии для пользователя"""
        session = UserSession(user_id=user.id if user.id else 0)
        logger.debug(f"Создана сессия для пользователя {user.telegram_id}")
        return session
    
    @staticmethod
    def restore_session(session_data: Dict[str, Any]) -> Optional[UserSession]:
        """Восстановление сессии из данных"""
        try:
            session = UserSession()
            
            # Восстанавливаем основные поля
            for key, value in session_data.items():
                if hasattr(session, key):
                    setattr(session, key, value)
            
            # Проверяем, не истекла ли сессия
            if session.is_expired:
                logger.debug(f"Сессия истекла: {session.session_id}")
                return None
            
            # Продлеваем сессию
            session.renew()
            
            logger.debug(f"Сессия восстановлена: {session.session_id}")
            return session
            
        except Exception as e:
            logger.error(f"Ошибка восстановления сессии: {e}")
            return None
    
    @staticmethod
    def validate_products(products: str) -> bool:
        """Валидация списка продуктов"""
        if not products or len(products.strip()) < 3:
            return False
        
        # Проверка на минимальную длину
        if len(products.split(',')) < 2 and len(products.split()) < 3:
            return False
        
        # Проверка на стоп-слова
        stop_words = {"привет", "пока", "спасибо", "помощь", "help", "start"}
        products_lower = products.lower()
        
        if any(word in products_lower for word in stop_words):
            return False
        
        return True
    
    @staticmethod
    def extract_categories_from_products(products: str) -> List[str]:
        """Извлечение возможных категорий из продуктов"""
        categories = []
        products_lower = products.lower()
        
        # Эвристики для определения категорий
        if any(word in products_lower for word in ["яйцо", "молоко", "блин", "омлет", "каша"]):
            categories.append("breakfast")
        
        if any(word in products_lower for word in ["бульон", "суп", "борщ", "солянка"]):
            categories.append("soup")
        
        if any(word in products_lower for word in ["мясо", "рыба", "курица", "гарнир", "паста"]):
            categories.append("main")
        
        if any(word in products_lower for word in ["салат", "овощ", "зелень", "помидор", "огурец"]):
            categories.append("salad")
        
        if any(word in products_lower for word in ["десерт", "торт", "пирог", "печенье", "сладк"]):
            categories.append("dessert")
        
        if any(word in products_lower for word in ["напиток", "чай", "кофе", "сок", "компот"]):
            categories.append("drink")
        
        # Если продуктов много, добавляем комплексный обед
        if len(products.split(',')) >= 5:
            categories.insert(0, "mix")
        
        # Убираем дубликаты
        return list(dict.fromkeys(categories))
    
    @staticmethod
    def format_products_for_display(products: str, max_length: int = 100) -> str:
        """Форматирование продуктов для отображения"""
        if not products:
            return ""
        
        # Обрезаем если слишком длинный
        if len(products) > max_length:
            products = products[:max_length] + "..."
        
        # Добавляем эмодзи
        return f"🛒 {products}"
    
    @staticmethod
    def merge_products(existing: Optional[str], new: str) -> str:
        """Объединение списков продуктов"""
        if not existing:
            return new
        
        # Убираем дубликаты
        existing_items = set(item.strip().lower() for item in existing.split(','))
        new_items = set(item.strip().lower() for item in new.split(','))
        
        # Объединяем
        all_items = existing_items.union(new_items)
        
        # Сортируем для удобства
        sorted_items = sorted(all_items, key=lambda x: x)
        
        return ', '.join(sorted_items)
    
    @staticmethod
    def analyze_session_activity(session: UserSession) -> Dict[str, Any]:
        """Анализ активности в сессии"""
        if not session.history:
            return {
                "messages_count": 0,
                "last_activity": None,
                "has_products": bool(session.products),
                "has_generated_dishes": bool(session.generated_dishes)
            }
        
        # Подсчет сообщений по ролям
        user_messages = sum(1 for msg in session.history if msg.get("role") == "user")
        bot_messages = sum(1 for msg in session.history if msg.get("role") == "bot")
        
        # Время последней активности
        last_activity = None
        for msg in reversed(session.history):
            if "timestamp" in msg:
                try:
                    last_activity = datetime.fromisoformat(msg["timestamp"])
                    break
                except (ValueError, TypeError):
                    pass
        
        return {
            "messages_count": len(session.history),
            "user_messages": user_messages,
            "bot_messages": bot_messages,
            "last_activity": last_activity,
            "has_products": bool(session.products),
            "has_generated_dishes": bool(session.generated_dishes),
            "categories_count": len(session.categories),
            "session_age_minutes": (datetime.now() - session.created_at).total_seconds() / 60 if session.created_at else 0
        }
