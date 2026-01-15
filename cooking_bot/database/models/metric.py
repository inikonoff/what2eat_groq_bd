"""
SQLAlchemy модель метрики
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON, ForeignKey, Numeric
from sqlalchemy.orm import relationship
from database.models.user import Base
from datetime import datetime

class UsageMetric(Base):
    """Модель метрики использования"""
    __tablename__ = "usage_metrics"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    metric_type = Column(String(50), nullable=False)
    service_name = Column(String(50))
    details = Column(JSON)
    tokens_used = Column(Integer)
    cost_units = Column(Numeric(10, 6))
    response_time_ms = Column(Integer)
    success = Column(Boolean, default=True)
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Связи
    user = relationship("User")
    
    def __repr__(self):
        return f"<UsageMetric(id={self.id}, type='{self.metric_type}', user_id={self.user_id})>"
