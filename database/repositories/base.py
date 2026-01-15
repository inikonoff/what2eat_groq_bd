from abc import ABC, abstractmethod
from typing import Generic, TypeVar, List, Optional, Dict, Any
from datetime import datetime
import logging

T = TypeVar('T')
logger = logging.getLogger(__name__)

class BaseRepository(ABC, Generic[T]):
    """Базовый класс репозитория"""
    
    @abstractmethod
    async def create(self, entity: T) -> T:
        pass
    
    @abstractmethod
    async def get_by_id(self, entity_id: int) -> Optional[T]:
        pass
    
    @abstractmethod
    async def update(self, entity_id: int, updates: Dict[str, Any]) -> Optional[T]:
        pass
    
    @abstractmethod
    async def delete(self, entity_id: int) -> bool:
        pass
    
    @abstractmethod
    async def list(self, filters: Optional[Dict[str, Any]] = None, 
                   limit: int = 100, offset: int = 0) -> List[T]:
        pass

class AsyncPGRepository(BaseRepository[T]):
    """Реализация репозитория для asyncpg"""
    
    def __init__(self, table_name: str, pk_column: str = 'id'):
        self.table_name = table_name
        self.pk_column = pk_column
    
    def _map_row_to_entity(self, row) -> T:
        """Преобразование строки БД в сущность (должен быть переопределен)"""
        return dict(row) if row else None
    
    def _build_where_clause(self, filters: Dict[str, Any]) -> tuple:
        """Построение WHERE условия"""
        if not filters:
            return "", []
        
        conditions = []
        values = []
        param_idx = 1
        
        for key, value in filters.items():
            if value is None:
                conditions.append(f"{key} IS NULL")
            elif isinstance(value, (list, tuple)):
                placeholders = ', '.join([f"${i}" for i in range(param_idx, param_idx + len(value))])
                conditions.append(f"{key} IN ({placeholders})")
                values.extend(value)
                param_idx += len(value)
            else:
                conditions.append(f"{key} = ${param_idx}")
                values.append(value)
                param_idx += 1
        
        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
        return where_clause, values
    
    async def _execute_query(self, query: str, *args):
        """Выполнение запроса"""
        from database.connection import DatabaseConnection
        pool = await DatabaseConnection.get_pool()
        
        try:
            return await pool.fetch(query, *args)
        except Exception as e:
            logger.error(f"Ошибка выполнения запроса {query}: {e}")
            raise
    
    async def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Создание записи"""
        columns = ', '.join(data.keys())
        placeholders = ', '.join([f"${i+1}" for i in range(len(data))])
        
        query = f"""
            INSERT INTO {self.table_name} ({columns})
            VALUES ({placeholders})
            RETURNING *
        """
        
        result = await self._execute_query(query, *data.values())
        return self._map_row_to_entity(result[0]) if result else None
    
    async def get_by_id(self, entity_id: int) -> Optional[Dict[str, Any]]:
        """Получение записи по ID"""
        query = f"""
            SELECT * FROM {self.table_name}
            WHERE {self.pk_column} = $1
        """
        
        result = await self._execute_query(query, entity_id)
        return self._map_row_to_entity(result[0]) if result else None
    
    async def update(self, entity_id: int, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Обновление записи"""
        if not updates:
            return await self.get_by_id(entity_id)
        
        set_clauses = []
        values = []
        param_idx = 1
        
        for key, value in updates.items():
            set_clauses.append(f"{key} = ${param_idx}")
            values.append(value)
            param_idx += 1
        
        values.append(entity_id)
        
        query = f"""
            UPDATE {self.table_name}
            SET {', '.join(set_clauses)}
            WHERE {self.pk_column} = ${param_idx}
            RETURNING *
        """
        
        result = await self._execute_query(query, *values)
        return self._map_row_to_entity(result[0]) if result else None
    
    async def delete(self, entity_id: int) -> bool:
        """Удаление записи"""
        query = f"""
            DELETE FROM {self.table_name}
            WHERE {self.pk_column} = $1
        """
        
        try:
            result = await self._execute_query(query, entity_id)
            return True
        except Exception as e:
            logger.error(f"Ошибка удаления записи: {e}")
            return False
    
    async def list(self, filters: Optional[Dict[str, Any]] = None, 
                   limit: int = 100, offset: int = 0,
                   order_by: str = None) -> List[Dict[str, Any]]:
        """Получение списка записей"""
        where_clause, where_values = self._build_where_clause(filters or {})
        
        query = f"""
            SELECT * FROM {self.table_name}
            {where_clause}
        """
        
        if order_by:
            query += f" ORDER BY {order_by}"
        
        query += f" LIMIT {limit} OFFSET {offset}"
        
        result = await self._execute_query(query, *where_values)
        return [self._map_row_to_entity(row) for row in result]
