import logging
import hashlib
from typing import Optional, List, Dict, Any
from datetime import datetime
from database.repositories.base import AsyncPGRepository

logger = logging.getLogger(__name__)

class ImageRepository(AsyncPGRepository):
    """Репозиторий для работы с изображениями"""
    
    def __init__(self):
        super().__init__(table_name="dish_images", pk_column="id")
    
    def _calculate_image_hash(self, image_url: str) -> str:
        """Вычисление хеша изображения для дедупликации"""
        return hashlib.sha256(image_url.encode()).hexdigest()
    
    async def create_image(self, recipe_id: int, image_url: str, 
                          storage_type: str = 'replicate', **kwargs) -> Dict[str, Any]:
        """Создание записи об изображении"""
        image_hash = self._calculate_image_hash(image_url)
        
        # Проверяем, не существует ли уже такое изображение
        existing = await self._execute_query(
            "SELECT id FROM dish_images WHERE image_hash = $1",
            image_hash
        )
        
        if existing:
            logger.info(f"Изображение уже существует: {image_hash}")
            return await self.get_by_id(existing[0]['id'])
        
        image_data = {
            'recipe_id': recipe_id,
            'image_url': image_url,
            'storage_type': storage_type,
            'image_hash': image_hash,
            'created_at': datetime.now(),
            'is_primary': True
        }
        
        # Если для рецепта уже есть изображения, новое не будет основным
        existing_images = await self.get_recipe_images(recipe_id)
        if existing_images:
            image_data['is_primary'] = False
        
        image_data.update(kwargs)
        
        return await self.create(image_data)
    
    async def get_recipe_images(self, recipe_id: int) -> List[Dict[str, Any]]:
        """Получение всех изображений рецепта"""
        filters = {'recipe_id': recipe_id}
        return await self.list(filters=filters, order_by='is_primary DESC, created_at DESC')
    
    async def get_primary_image(self, recipe_id: int) -> Optional[Dict[str, Any]]:
        """Получение основного изображения рецепта"""
        query = """
            SELECT * FROM dish_images
            WHERE recipe_id = $1 AND is_primary = TRUE
            LIMIT 1
        """
        
        result = await self._execute_query(query, recipe_id)
        return self._map_row_to_entity(result[0]) if result else None
    
    async def set_primary_image(self, image_id: int) -> bool:
        """Установка изображения как основного"""
        # Получаем информацию об изображении
        image = await self.get_by_id(image_id)
        if not image:
            return False
        
        recipe_id = image['recipe_id']
        
        # Сбрасываем флаг is_primary у всех изображений рецепта
        reset_query = """
            UPDATE dish_images 
            SET is_primary = FALSE 
            WHERE recipe_id = $1
        """
        await self._execute_query(reset_query, recipe_id)
        
        # Устанавливаем выбранное изображение как основное
        update_query = """
            UPDATE dish_images 
            SET is_primary = TRUE 
            WHERE id = $1
        """
        await self._execute_query(update_query, image_id)
        
        return True
    
    async def delete_recipe_images(self, recipe_id: int) -> int:
        """Удаление всех изображений рецепта"""
        query = """
            DELETE FROM dish_images
            WHERE recipe_id = $1
            RETURNING COUNT(*)
        """
        
        result = await self._execute_query(query, recipe_id)
        return result[0]['count'] if result else 0
