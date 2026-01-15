"""
Pydantic схемы для рецептов
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class RecipeBase(BaseModel):
    """Базовая схема рецепта"""
    dish_name: str = Field(..., min_length=1, max_length=255, description="Название блюда")
    recipe_text: str = Field(..., min_length=10, description="Текст рецепта")
    products_used: Optional[str] = Field(None, description="Использованные продукты")
    category: Optional[str] = Field(None, description="Категория блюда")

class RecipeCreate(RecipeBase):
    """Схема для создания рецепта"""
    user_id: int = Field(..., description="ID пользователя")
    language: str = Field("ru", description="Язык рецепта")
    cooking_time_minutes: Optional[int] = Field(None, ge=1, description="Время приготовления в минутах")
    difficulty_level: Optional[str] = Field(None, description="Уровень сложности")
    servings: Optional[int] = Field(None, ge=1, description="Количество порций")
    nutrition_info: Optional[dict] = Field(None, description="Пищевая ценность")

class RecipeUpdate(BaseModel):
    """Схема для обновления рецепта"""
    dish_name: Optional[str] = Field(None, min_length=1, max_length=255)
    recipe_text: Optional[str] = Field(None, min_length=10)
    products_used: Optional[str] = None
    category: Optional[str] = None
    is_favorite: Optional[bool] = None
    cooking_time_minutes: Optional[int] = Field(None, ge=1)
    difficulty_level: Optional[str] = None
    servings: Optional[int] = Field(None, ge=1)
    nutrition_info: Optional[dict] = None

class RecipeResponse(RecipeBase):
    """Схема ответа с рецептом"""
    id: int
    user_id: int
    language: str
    is_favorite: bool
    is_ai_generated: bool
    cooking_time_minutes: Optional[int]
    difficulty_level: Optional[str]
    servings: Optional[int]
    nutrition_info: Optional[dict]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class RecipeWithImages(RecipeResponse):
    """Схема рецепта с изображениями"""
    images: List[dict] = Field(default_factory=list, description="Изображения блюда")
