"""
Детектор намерений пользователя
"""
import re
from typing import Dict, Any, Tuple
import logging

logger = logging.getLogger(__name__)

class IntentDetector:
    """Класс для определения намерений пользователя"""
    
    # Паттерны запросов рецептов
    RECIPE_REQUEST_PATTERNS = [
        r'^дай\s+рецепт\s+(.+)$',
        r'^рецепт\s+(.+)$',
        r'^как\s+приготовить\s+(.+)$',
        r'^как\s+сделать\s+(.+)$',
        r'^хочу\s+приготовить\s+(.+)$',
        r'^хочу\s+сделать\s+(.+)$',
        r'^готовим\s+(.+)$',
        r'^приготовь\s+(.+)$',
        r'^сделай\s+(.+)$',
        r'^как\s+готовить\s+(.+)$',
        r'^научи\s+готовить\s+(.+)$',
        r'^рецептик\s+(.+)$',
        r'^recipe\s+for\s+(.+)$',
        r'^how\s+to\s+cook\s+(.+)$',
        r'^how\s+to\s+make\s+(.+)$',
        r'^i\s+want\s+to\s+cook\s+(.+)$',
        r'^i\s+want\s+to\s+make\s+(.+)$',
        r'^cook\s+(.+)$',
        r'^make\s+(.+)$'
    ]
    
    # Паттерны списка продуктов
    PRODUCTS_PATTERNS = [
        r'^у\s+меня\s+есть\s+(.+)$',
        r'^имеется\s+(.+)$',
        r'^в\s+наличии\s+(.+)$',
        r'^продукты\s*:\s*(.+)$',
        r'^ингредиенты\s*:\s*(.+)$',
        r'^i\s+have\s+(.+)$',
        r'^products?\s*:\s*(.+)$',
        r'^ingredients?\s*:\s*(.+)$'
    ]
    
    # Стоп-слова (не продукты)
    STOP_WORDS = {
        'привет', 'здравствуйте', 'здравствуй', 'добрый', 'вечер', 'утро', 'день',
        'пока', 'до свидания', 'спасибо', 'благодарю', 'пожалуйста',
        'помощь', 'help', 'start', 'старт', 'меню', 'что ты умеешь'
    }
    
    @staticmethod
    def detect(text: str) -> Dict[str, Any]:
        """
        Определяет намерение пользователя
        
        Returns:
            Dict с ключами:
            - intent: 'recipe_request', 'products_list', 'greeting', 'unknown'
            - dish_name: str (если это запрос рецепта)
            - products: str (если это список продуктов)
            - confidence: float (уверенность 0-1)
        """
        if not text or len(text.strip()) < 2:
            return {'intent': 'unknown', 'confidence': 0.0}
        
        text_lower = text.lower().strip()
        
        # 1. Проверка на стоп-слова (приветствия и т.д.)
        if any(stop_word in text_lower for stop_word in IntentDetector.STOP_WORDS):
            return {'intent': 'greeting', 'confidence': 0.9}
        
        # 2. Проверка на запрос рецепта
        dish_name = IntentDetector._extract_dish_name(text_lower)
        if dish_name:
            return {
                'intent': 'recipe_request',
                'dish_name': dish_name,
                'confidence': 0.85
            }
        
        # 3. Проверка на список продуктов
        if IntentDetector._is_products_list(text_lower):
            products = IntentDetector._clean_products_text(text_lower)
            return {
                'intent': 'products_list',
                'products': products,
                'confidence': 0.8
            }
        
        # 4. Проверка на указание продуктов в свободной форме
        if IntentDetector._looks_like_products(text_lower):
            return {
                'intent': 'products_list',
                'products': text_lower,
                'confidence': 0.7
            }
        
        return {'intent': 'unknown', 'confidence': 0.0}
    
    @staticmethod
    def _extract_dish_name(text: str) -> Optional[str]:
        """Извлекает название блюда из запроса"""
        for pattern in IntentDetector.RECIPE_REQUEST_PATTERNS:
            match = re.match(pattern, text, re.IGNORECASE)
            if match:
                dish_name = match.group(1).strip()
                return IntentDetector._clean_dish_name(dish_name)
        return None
    
    @staticmethod
    def _clean_dish_name(dish_name: str) -> str:
        """Очистка названия блюда"""
        # Убираем лишние слова
        words_to_remove = ['пожалуйста', 'please', 'мне', 'мог бы ты', 'could you']
        for word in words_to_remove:
            dish_name = re.sub(r'\b' + re.escape(word) + r'\b', '', dish_name, flags=re.IGNORECASE)
        
        # Убираем знаки препинания в начале/конце
        dish_name = re.sub(r'^[\s,:;\.\-!?]+', '', dish_name)
        dish_name = re.sub(r'[\s,:;\.\-!?]+$', '', dish_name)
        
        # Капитализируем первое слово
        if dish_name:
            dish_name = dish_name[0].upper() + dish_name[1:]
        
        return dish_name.strip()
    
    @staticmethod
    def _is_products_list(text: str) -> bool:
        """Проверяет, является ли текст списком продуктов"""
        # Проверка по паттернам
        for pattern in IntentDetector.PRODUCTS_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        # Эвристика: содержит много запятых или союзов
        comma_count = text.count(',')
        and_count = text.count(' и ') + text.count(' and ')
        
        if comma_count >= 2 or (comma_count >= 1 and and_count >= 1):
            return True
        
        # Эвристика: короткий текст без глаголов
        if len(text.split()) <= 10:
            action_verbs = ['дай', 'хочу', 'приготовь', 'сделай', 'научи', 'покажи', 'как']
            has_action_verb = any(verb in text for verb in action_verbs)
            
            if not has_action_verb:
                return True
        
        return False
    
    @staticmethod
    def _looks_like_products(text: str) -> bool:
        """Эвристическая проверка, похоже ли на продукты"""
        # Содержит типичные продукты
        common_products = [
            'яйц', 'молок', 'мук', 'сахар', 'соль', 'масл', 'картош', 'помидор',
            'огур', 'лук', 'чеснок', 'мяс', 'рыб', 'куриц', 'овощ', 'фрукт',
            'сыр', 'хлеб', 'макарон', 'рис', 'греч', 'специ', 'трав'
        ]
        
        text_words = set(text.split())
        product_matches = sum(1 for product in common_products 
                            if any(word.startswith(product) for word in text_words))
        
        return product_matches >= 2
    
    @staticmethod
    def _clean_products_text(text: str) -> str:
        """Очистка текста с продуктами"""
        # Убираем префиксы
        for pattern in IntentDetector.PRODUCTS_PATTERNS:
            match = re.match(pattern, text, re.IGNORECASE)
            if match:
                text = match.group(1)
                break
        
        # Убираем лишние пробелы и знаки препинания
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'[^\w\s,.-]', '', text)
        
        return text.strip()
