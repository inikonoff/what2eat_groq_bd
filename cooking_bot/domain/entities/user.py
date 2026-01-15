"""
Бизнес-сущность пользователя
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict

@dataclass
class User:
    """Пользователь"""
    id: Optional[int] = None
    telegram_id: int = 0
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    language_code: str = "ru"
    is_premium: bool = False
    settings: Dict = None
    created_at: Optional[datetime] = None
    last_active: Optional[datetime] = None
    
    def __post_init__(self):
        if self.settings is None:
            self.settings = {}
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.last_active is None:
            self.last_active = datetime.now()
    
    @property
    def full_name(self) -> str:
        """Полное имя пользователя"""
        parts = []
        if self.first_name:
            parts.append(self.first_name)
        if self.last_name:
            parts.append(self.last_name)
        return " ".join(parts) if parts else str(self.telegram_id)
    
    def update_last_active(self):
        """Обновление времени последней активности"""
        self.last_active = datetime.now()
    
    def update_settings(self, **kwargs):
        """Обновление настроек"""
        self.settings.update(kwargs)
    
    def to_dict(self) -> Dict:
        """Преобразование в словарь"""
        return {
            "id": self.id,
            "telegram_id": self.telegram_id,
            "username": self.username,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "language_code": self.language_code,
            "is_premium": self.is_premium,
            "settings": self.settings,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_active": self.last_active.isoformat() if self.last_active else None
        }
