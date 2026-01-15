"""
Доменный сервис для работы с рецептами
"""
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from domain.entities.recipe import Recipe
from domain.entities.user import User

logger = logging.getLogger(__name__)

class RecipeService:
    """Сервис для бизнес-логики рецептов"""
    
    @staticmethod
    def create_recipe_from_ai(
        user: User,
        dish_name: str,
        recipe_text: str,
        products_used: Optional[str] = None,
        category: Optional[str] = None,
        **kwargs
    ) -> Recipe:
        """Создание рецепта из AI генерации"""
        recipe = Recipe(
            user_id=user.id if user.id else 0,
            dish_name=dish_name.strip(),
            recipe_text=recipe_text.strip(),
            products_used=products_used,
            category=category,
            is_ai_generated=True,
            **kwargs
        )
        
        # Извлекаем метаданные из текста рецепта
        RecipeService._extract_metadata(recipe)
        
        logger.info(f"Создан рецепт: {dish_name} для пользователя {user.telegram_id}")
        return recipe
    
    @staticmethod
    def _extract_metadata(recipe: Recipe):
        """Извлечение метаданных из текста рецепта"""
        text_lower = recipe.recipe_text.lower()
        
        # Определение уровня сложности
        if any(word in text_lower for word in ["просто", "легко", "быстро", "easy"]):
            recipe.difficulty_level = "легко"
        elif any(word in text_lower for word in ["средней", "умеренно", "medium"]):
            recipe.difficulty_level = "средне"
        elif any(word in text_lower for word in ["сложно", "трудно", "hard", "difficult"]):
            recipe.difficulty_level = "сложно"
        
        # Определение времени приготовления
        time_patterns = [
            (r"(\d+)\s*минут", 1),
            (r"(\d+)\s*мин", 1),
            (r"(\d+)\s*часа?", 60),
            (r"(\d+)\s*ч", 60),
            (r"(\d+)\s*час", 60)
        ]
        
        for pattern, multiplier in time_patterns:
            import re
            match = re.search(pattern, text_lower)
            if match:
                try:
                    recipe.cooking_time_minutes = int(match.group(1)) * multiplier
                    break
                except ValueError:
                    pass
        
        # Определение количества порций
        portion_patterns = [
            r"(\d+)\s*порци",
            r"(\d+)\s*персон",
            r"(\d+)\s*человек",
            r"(\d+)\s*servings",
            r"(\d+)\s*people"
        ]
        
        for pattern in portion_patterns:
            match = re.search(pattern, text_lower)
            if match:
                try:
                    recipe.servings = int(match.group(1))
                    break
                except ValueError:
                    pass
    
    @staticmethod
    def format_recipe_for_display(recipe: Recipe) -> str:
        """Форматирование рецепта для отображения"""
        lines = []
        
        # Заголовок
        lines.append(f"<b>{recipe.dish_name}</b>")
        lines.append("")
        
        # Метаданные
        if recipe.cooking_time_minutes:
            lines.append(f"⏱ <b>Время:</b> {recipe.cooking_time_minutes} мин")
        
        if recipe.difficulty_level:
            lines.append(f"🪦 <b>Сложность:</b> {recipe.difficulty_level}")
        
        if recipe.servings:
            lines.append(f"👥 <b>Порции:</b> {recipe.servings}")
        
        if recipe.nutrition_info:
            lines.append("📊 <b>Пищевая ценность:</b>")
            for key, value in recipe.nutrition_info.items():
                lines.append(f"  • {key}: {value}")
        
        # Продукты
        if recipe.products_used:
            lines.append("")
            lines.append("📦 <b>Продукты:</b>")
            products = recipe.products_used.split(',')
            for product in products[:10]:  # Ограничиваем количество
                lines.append(f"🔸 {product.strip()}")
        
        # Рецепт
        lines.append("")
        lines.append("🔪 <b>Приготовление:</b>")
        
        # Разделяем текст на абзацы
        recipe_text = recipe.recipe_text.strip()
        paragraphs = recipe.text.split('\n\n')
        
        for i, paragraph in enumerate(paragraphs[:5]):  # Ограничиваем количество абзацев
            if paragraph.strip():
                lines.append(f"{i+1}. {paragraph.strip()}")
        
        # Добавляем информацию об AI
        if recipe.is_ai_generated:
            lines.append("")
            lines.append("<i>✨ Рецепт сгенерирован искусственным интеллектом</i>")
        
        return "\n".join(lines)
    
    @staticmethod
    def search_recipes(recipes: List[Recipe], query: str, 
                      category: Optional[str] = None) -> List[Recipe]:
        """Поиск рецептов по запросу"""
        query_lower = query.lower()
        results = []
        
        for recipe in recipes:
            # Поиск в названии
            if query_lower in recipe.dish_name.lower():
                results.append(recipe)
                continue
            
            # Поиск в продуктах
            if recipe.products_used and query_lower in recipe.products_used.lower():
                results.append(recipe)
                continue
            
            # Поиск в тексте рецепта
            if query_lower in recipe.recipe_text.lower():
                results.append(recipe)
                continue
        
        # Фильтрация по категории
        if category:
            results = [r for r in results if r.category and r.category.lower() == category.lower()]
        
        return results
    
    @staticmethod
    def group_recipes_by_category(recipes: List[Recipe]) -> Dict[str, List[Recipe]]:
        """Группировка рецептов по категориям"""
        grouped = {}
        
        for recipe in recipes:
            category = recipe.category or "без категории"
            if category not in grouped:
                grouped[category] = []
            grouped[category].append(recipe)
        
        return grouped
    
    @staticmethod
    def calculate_statistics(recipes: List[Recipe]) -> Dict[str, Any]:
        """Расчет статистики по рецептам"""
        if not recipes:
            return {
                "total": 0,
                "favorites": 0,
                "average_cooking_time": 0,
                "categories": {},
                "difficulty_levels": {}
            }
        
        total = len(recipes)
        favorites = sum(1 for r in recipes if r.is_favorite)
        
        # Среднее время приготовления
        cooking_times = [r.cooking_time_minutes for r in recipes if r.cooking_time_minutes]
        avg_cooking_time = sum(cooking_times) / len(cooking_times) if cooking_times else 0
        
        # Категории
        categories = {}
        for recipe in recipes:
            category = recipe.category or "без категории"
            categories[category] = categories.get(category, 0) + 1
        
        # Уровни сложности
        difficulty_levels = {}
        for recipe in recipes:
            difficulty = recipe.difficulty_level or "не указано"
            difficulty_levels[difficulty] = difficulty_levels.get(difficulty, 0) + 1
        
        return {
            "total": total,
            "favorites": favorites,
            "average_cooking_time": round(avg_cooking_time, 1),
            "categories": categories,
            "difficulty_levels": difficulty_levels
        }
