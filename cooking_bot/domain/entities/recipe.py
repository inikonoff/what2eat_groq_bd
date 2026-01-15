"""
Бизнес-сущность рецепта
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict
from .user import User

@dataclass
class Recipe:
    """Рецепт"""
    id: Optional[int] = None
    user_id: int = 0
    dish_name: str = ""
    recipe_text: str = ""
    products_used: Optional[str] = None
    category: Optional[str] = None
    language: str = "ru"
    is_favorite: bool = False
    is_ai_generated: bool = True
    cooking_time_minutes: Optional[int] = None
    difficulty_level: Optional[str] = None
    servings: Optional[int] = None
    nutrition_info: Optional[Dict] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    images: List[Dict] = field(default_factory=list)
    user: Optional[User] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()
        if self.nutrition_info is None:
            self.nutrition_info = {}
    
    @property
    def is_quick_recipe(self) -> bool:
        """Быстрый ли рецепт (<30 минут)"""
        return self.cooking_time_minutes is not None and self.cooking_time_minutes < 30
    
    @property
    def is_easy_recipe(self) -> bool:
        """Простой ли рецепт"""
        return self.difficulty_level in ["easy", "легко", "простой"]
    
    def update_timestamp(self):
        """Обновление времени изменения"""
        self.updated_at = datetime.now()
    
    def toggle_favorite(self):
        """Переключение статуса избранного"""
        self.is_favorite = not self.is_favorite
        self.update_timestamp()
    
    def add_image(self, image_url: str, storage_type: str = "replicate", **kwargs):
        """Добавление изображения"""
        image_data = {
            "image_url": image_url,
            "storage_type": storage_type,
            "created_at": datetime.now(),
            **kwargs
        }
        self.images.append(image_data)
    
    def to_dict(self) -> Dict:
        """Преобразование в словарь"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "dish_name": self.dish_name,
            "recipe_text": self.recipe_text,
            "products_used": self.products_used,
            "category": self.category,
            "language": self.language,
            "is_favorite": self.is_favorite,
            "is_ai_generated": self.is_ai_generated,
            "cooking_time_minutes": self.cooking_time_minutes,
            "difficulty_level": self.difficulty_level,
            "servings": self.servings,
            "nutrition_info": self.nutrition_info,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "images": self.images
        }
