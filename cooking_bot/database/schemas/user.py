"""
Pydantic схемы для пользователей
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    """Базовая схема пользователя"""
    telegram_id: int = Field(..., description="ID пользователя в Telegram")
    username: Optional[str] = Field(None, description="Username в Telegram")
    first_name: Optional[str] = Field(None, description="Имя пользователя")
    last_name: Optional[str] = Field(None, description="Фамилия пользователя")

class UserCreate(UserBase):
    """Схема для создания пользователя"""
    language_code: str = Field("ru", description="Код языка")
    settings: dict = Field(default_factory=dict, description="Настройки пользователя")

class UserUpdate(BaseModel):
    """Схема для обновления пользователя"""
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    language_code: Optional[str] = None
    is_premium: Optional[bool] = None
    settings: Optional[dict] = None

class UserResponse(UserBase):
    """Схема ответа с пользователем"""
    id: int
    language_code: str
    is_premium: bool
    settings: dict
    created_at: datetime
    last_active: datetime
    
    class Config:
        from_attributes = True

class UserStats(BaseModel):
    """Статистика пользователя"""
    user_id: int
    telegram_id: int
    recipes_count: int = 0
    favorites_count: int = 0
    images_count: int = 0
    created_at: datetime
    last_active: datetime
