"""
Pydantic схемы для изображений
"""
from pydantic import BaseModel, Field, HttpUrl
from typing import Optional
from datetime import datetime

class ImageBase(BaseModel):
    """Базовая схема изображения"""
    image_url: str = Field(..., description="URL изображения")
    recipe_id: Optional[int] = Field(None, description="ID рецепта")

class ImageCreate(ImageBase):
    """Схема для создания изображения"""
    storage_type: str = Field("replicate", description="Тип хранилища")
    prompt_used: Optional[str] = Field(None, description="Промпт для генерации")
    model_name: Optional[str] = Field(None, description="Название модели")
    image_hash: Optional[str] = Field(None, description="Хеш изображения")
    width: Optional[int] = Field(None, description="Ширина изображения")
    height: Optional[int] = Field(None, description="Высота изображения")
    file_size_bytes: Optional[int] = Field(None, description="Размер файла в байтах")

class ImageUpdate(BaseModel):
    """Схема для обновления изображения"""
    is_primary: Optional[bool] = None
    prompt_used: Optional[str] = None

class ImageResponse(ImageBase):
    """Схема ответа с изображением"""
    id: int
    storage_type: str
    prompt_used: Optional[str]
    model_name: Optional[str]
    image_hash: Optional[str]
    width: Optional[int]
    height: Optional[int]
    file_size_bytes: Optional[int]
    is_primary: bool
    created_at: datetime
    
    class Config:
        from_attributes = True
