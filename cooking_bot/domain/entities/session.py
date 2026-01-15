"""
Бизнес-сущность сессии
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import uuid

@dataclass
class UserSession:
    """Сессия пользователя"""
    id: Optional[int] = None
    user_id: int = 0
    session_id: str = ""
    products: Optional[str] = None
    state: Optional[str] = None
    categories: List[str] = field(default_factory=list)
    generated_dishes: List[Dict] = field(default_factory=list)
    current_dish: Optional[str] = None
    history: List[Dict] = field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    
    def __post_init__(self):
        if not self.session_id:
            self.session_id = str(uuid.uuid4())
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()
        if self.expires_at is None:
            self.expires_at = datetime.now() + timedelta(hours=1)
    
    @property
    def is_expired(self) -> bool:
        """Истекла ли сессия"""
        return datetime.now() > self.expires_at
    
    def renew(self, hours: int = 1):
        """Продление сессии"""
        self.expires_at = datetime.now() + timedelta(hours=hours)
        self.updated_at = datetime.now()
    
    def add_to_history(self, role: str, text: str):
        """Добавление сообщения в историю"""
        self.history.append({
            "role": role,
            "text": text,
            "timestamp": datetime.now().isoformat()
        })
        self.updated_at = datetime.now()
    
    def clear_history(self):
        """Очистка истории"""
        self.history.clear()
        self.updated_at = datetime.now()
    
    def set_products(self, products: str):
        """Установка продуктов"""
        self.products = products
        self.updated_at = datetime.now()
    
    def append_products(self, new_products: str):
        """Добавление продуктов"""
        if self.products:
            self.products = f"{self.products}, {new_products}"
        else:
            self.products = new_products
        self.updated_at = datetime.now()
    
    def to_dict(self) -> Dict:
        """Преобразование в словарь"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "products": self.products,
            "state": self.state,
            "categories": self.categories,
            "generated_dishes": self.generated_dishes,
            "current_dish": self.current_dish,
            "history": self.history,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None
        }
