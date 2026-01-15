"""
Валидаторы данных
"""
import re
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class DataValidators:
    """Класс валидаторов данных"""
    
    # Паттерны для валидации
    DISH_NAME_PATTERN = r'^[a-zA-Zа-яА-ЯёЁ0-9\s\-.,!?]{3,100}$'
    PRODUCTS_PATTERN = r'^[a-zA-Zа-яА-ЯёЁ0-9\s\-,.!?]{3,500}$'
    URL_PATTERN = r'^https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+'
    
    @staticmethod
    def validate_dish_name(name: str) -> tuple[bool, Optional[str]]:
        """
        Валидация названия блюда
        
        Returns:
            (is_valid, error_message)
        """
        if not name or len(name.strip()) < 3:
            return False, "Название блюда слишком короткое (минимум 3 символа)"
        
        if len(name) > 100:
            return False, "Название блюда слишком длинное (максимум 100 символов)"
        
        # Проверка на специальные символы
        if re.search(r'[<>{}[\]\\|`~]', name):
            return False, "Название содержит запрещенные символы"
        
        return True, None
    
    @staticmethod
    def validate_products(products: str) -> tuple[bool, Optional[str]]:
        """
        Валидация списка продуктов
        
        Returns:
            (is_valid, error_message)
        """
        if not products or len(products.strip()) < 3:
            return False, "Список продуктов слишком короткий"
        
        if len(products) > 500:
            return False, "Список продуктов слишком длинный (максимум 500 символов)"
        
        # Проверка на минимальное количество продуктов
        items = [item.strip() for item in products.split(',') if item.strip()]
        if len(items) < 2:
            # Проверяем разделение пробелами
            items = [item.strip() for item in products.split() if item.strip()]
            if len(items) < 2:
                return False, "Укажите хотя бы 2 продукта"
        
        # Проверка на запрещенные слова
        forbidden_words = ["http://", "https://", "@", "script", "SELECT", "INSERT", "DELETE"]
        for word in forbidden_words:
            if word.lower() in products.lower():
                return False, "Список продуктов содержит запрещенные слова"
        
        return True, None
    
    @staticmethod
    def validate_category(category: str) -> tuple[bool, Optional[str]]:
        """
        Валидация категории
        
        Returns:
            (is_valid, error_message)
        """
        valid_categories = {
            "breakfast", "soup", "main", "salad", "snack", 
            "dessert", "drink", "sauce", "mix"
        }
        
        if category not in valid_categories:
            return False, f"Неизвестная категория. Допустимые: {', '.join(valid_categories)}"
        
        return True, None
    
    @staticmethod
    def validate_recipe_text(text: str) -> tuple[bool, Optional[str]]:
        """
        Валидация текста рецепта
        
        Returns:
            (is_valid, error_message)
        """
        if not text or len(text.strip()) < 10:
            return False, "Текст рецепта слишком короткий (минимум 10 символов)"
        
        if len(text) > 10000:
            return False, "Текст рецепта слишком длинный (максимум 10000 символов)"
        
        # Проверка на запрещенные HTML теги
        dangerous_tags = ["<script>", "<iframe>", "<object>", "<embed>"]
        for tag in dangerous_tags:
            if tag in text.lower():
                return False, "Текст содержит запрещенные HTML теги"
        
        return True, None
    
    @staticmethod
    def validate_url(url: str) -> tuple[bool, Optional[str]]:
        """
        Валидация URL
        
        Returns:
            (is_valid, error_message)
        """
        if not url:
            return False, "URL не может быть пустым"
        
        if not re.match(DataValidators.URL_PATTERN, url):
            return False, "Некорректный формат URL"
        
        # Проверка длины
        if len(url) > 500:
            return False, "URL слишком длинный (максимум 500 символов)"
        
        return True, None
    
    @staticmethod
    def validate_user_input(text: str, input_type: str = "general") -> tuple[bool, Optional[str]]:
        """
        Общая валидация пользовательского ввода
        
        Args:
            text: Текст для валидации
            input_type: Тип ввода ('general', 'dish_name', 'products')
        
        Returns:
            (is_valid, error_message)
        """
        if not text:
            return False, "Ввод не может быть пустым"
        
        # Проверка длины
        if len(text) > 1000:
            return False, "Сообщение слишком длинное (максимум 1000 символов)"
        
        # Проверка на спам/флуд
        if DataValidators._looks_like_spam(text):
            return False, "Сообщение выглядит как спам"
        
        # Специфичные проверки по типу
        if input_type == "dish_name":
            return DataValidators.validate_dish_name(text)
        elif input_type == "products":
            return DataValidators.validate_products(text)
        
        return True, None
    
    @staticmethod
    def _looks_like_spam(text: str) -> bool:
        """
        Эвристическая проверка на спам
        
        Returns:
            True если похоже на спам
        """
        # Много повторяющихся символов
        if re.search(r'(.)\1{5,}', text):
            return True
        
        # Много специальных символов
        special_chars = len(re.findall(r'[!@#$%^&*()_+=|<>?{}\[\]~]', text))
        if special_chars > len(text) * 0.3:  # Более 30% спецсимволов
            return True
        
        # Содержит URL (кроме разрешенных случаев)
        if re.search(r'https?://', text) and 'unsplash.com' not in text and 'replicate.com' not in text:
            return True
        
        # Слишком много заглавных букв
        upper_count = sum(1 for c in text if c.isupper())
        if upper_count > len(text) * 0.7:  # Более 70% заглавных
            return True
        
        return False
    
    @staticmethod
    def sanitize_input(text: str, max_length: int = 500) -> str:
        """
        Санитизация пользовательского ввода
        
        Args:
            text: Исходный текст
            max_length: Максимальная длина
            
        Returns:
            Очищенный текст
        """
        if not text:
            return ""
        
        # Убираем лишние пробелы
        text = ' '.join(text.split())
        
        # Заменяем опасные символы
        text = text.replace('<', '&lt;').replace('>', '&gt;')
        text = text.replace('"', "'").replace('`', "'")
        
        # Убираем управляющие символы
        text = re.sub(r'[\r\n\t]+', ' ', text)
        
        # Обрезаем если слишком длинный
        if len(text) > max_length:
            text = text[:max_length] + "..."
        
        return text.strip()
