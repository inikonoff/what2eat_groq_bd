"""
SQLAlchemy модель рецепта
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from database.models.user import Base
from datetime import datetime

class Recipe(Base
