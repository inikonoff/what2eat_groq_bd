"""
SQLAlchemy модель изображения блюда
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from database.models.user import Base
from datetime import datetime

class DishImage(Base):
    """Модель изображения блюда"""
    __tablename__ = "dish_images"
    
    id = Column(Integer, primary_key=True)
    recipe_id = Column(Integer, ForeignKey('recipes.id'))
    image_url = Column(String(500), nullable=False)
    storage_type = Column(String(20), default='replicate')
    prompt_used = Column(Text)
    model_name = Column(String(100))
    image_hash = Column(String(64))
    width = Column(Integer)
    height = Column(Integer)
    file_size_bytes = Column(Integer)
    is_primary = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Связи
    recipe = relationship("Recipe", back_populates="images")
    
    def __repr__(self):
        return f"<DishImage(id={self.id}, recipe_id={self.recipe_id}, url='{self.image_url[:30]}...')>"
