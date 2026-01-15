"""
SQLAlchemy модель рецепта
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from database.models.user import Base
from datetime import datetime

class Recipe(Base):
    """Модель рецепта"""
    __tablename__ = "recipes"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    dish_name = Column(String(255), nullable=False)
    recipe_text = Column(Text, nullable=False)
    products_used = Column(Text)
    category = Column(String(50))
    language = Column(String(10), default='ru')
    is_favorite = Column(Boolean, default=False)
    is_ai_generated = Column(Boolean, default=True)
    cooking_time_minutes = Column(Integer)
    difficulty_level = Column(String(20))
    servings = Column(Integer)
    nutrition_info = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Связи
    user = relationship("User", back_populates="recipes")
    images = relationship("DishImage", back_populates="recipe", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Recipe(id={self.id}, dish_name='{self.dish_name}', user_id={self.user_id})>"
