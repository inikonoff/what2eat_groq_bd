import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from database.repositories.base import AsyncPGRepository

logger = logging.getLogger(__name__)

class RecipeRepository(AsyncPGRepository):
    """Репозиторий для работы с рецептами"""
    
    def __init__(self):
        super().__init__(table_name="recipes", pk_column="id")
    
    async def create_recipe(self, user_id: int, dish_name: str, recipe_text: str,
                           products_used: str = None, category: str = None, **kwargs) -> Dict[str, Any]:
        """Создание нового рецепта"""
        recipe_data = {
            'user_id': user_id,
            'dish_name': dish_name,
            'recipe_text': recipe_text,
            'products_used': products_used,
            'category': category,
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        }
        
        # Добавляем дополнительные поля
        recipe_data.update(kwargs)
        
        return await self.create(recipe_data)
    
    async def get_user_recipes(self, user_id: int, limit: int = 20, 
                              offset: int = 0) -> List[Dict[str, Any]]:
        """Получение рецептов пользователя"""
        filters = {'user_id': user_id}
        return await self.list(filters=filters, limit=limit, offset=offset, 
                               order_by='created_at DESC')
    
    async def get_favorite_recipes(self, user_id: int, limit: int = 20,
                                  offset: int = 0) -> List[Dict[str, Any]]:
        """Получение избранных рецептов пользователя"""
        query = """
            SELECT r.* FROM recipes r
            JOIN favorite_recipes f ON r.id = f.recipe_id
            WHERE f.user_id = $1
            ORDER BY f.created_at DESC
            LIMIT $2 OFFSET $3
        """
        
        result = await self._execute_query(query, user_id, limit, offset)
        return [self._map_row_to_entity(row) for row in result]
    
    async def add_to_favorites(self, user_id: int, recipe_id: int) -> bool:
        """Добавление рецепта в избранное"""
        # Проверяем, существует ли уже
        check_query = """
            SELECT 1 FROM favorite_recipes 
            WHERE user_id = $1 AND recipe_id = $2
        """
        
        exists = await self._execute_query(check_query, user_id, recipe_id)
        if exists:
            return True
        
        # Добавляем
        insert_query = """
            INSERT INTO favorite_recipes (user_id, recipe_id, created_at)
            VALUES ($1, $2, NOW())
        """
        
        try:
            await self._execute_query(insert_query, user_id, recipe_id)
            
            # Помечаем рецепт как избранный
            await self.update(recipe_id, {'is_favorite': True})
            return True
        except Exception as e:
            logger.error(f"Ошибка добавления в избранное: {e}")
            return False
    
    async def remove_from_favorites(self, user_id: int, recipe_id: int) -> bool:
        """Удаление рецепта из избранного"""
        delete_query = """
            DELETE FROM favorite_recipes 
            WHERE user_id = $1 AND recipe_id = $2
        """
        
        try:
            await self._execute_query(delete_query, user_id, recipe_id)
            
            # Проверяем, остались ли другие пользователи добавили рецепт в избранное
            check_others = """
                SELECT COUNT(*) FROM favorite_recipes 
                WHERE recipe_id = $1
            """
            
            others = await self._execute_query(check_others, recipe_id)
            count = others[0]['count'] if others else 0
            
            if count == 0:
                await self.update(recipe_id, {'is_favorite': False})
            
            return True
        except Exception as e:
            logger.error(f"Ошибка удаления из избранного: {e}")
            return False
    
    async def search_recipes(self, user_id: int, query: str, 
                            category: str = None) -> List[Dict[str, Any]]:
        """Поиск рецептов"""
        search_query = """
            SELECT * FROM recipes
            WHERE user_id = $1 
            AND (dish_name ILIKE $2 OR products_used ILIKE $2)
        """
        
        params = [user_id, f"%{query}%"]
        
        if category:
            search_query += " AND category = $3"
            params.append(category)
        
        search_query += " ORDER BY created_at DESC LIMIT 20"
        
        result = await self._execute_query(search_query, *params)
        return [self._map_row_to_entity(row) for row in result]
    
    async def get_recipe_with_images(self, recipe_id: int) -> Optional[Dict[str, Any]]:
        """Получение рецепта с изображениями"""
        recipe = await self.get_by_id(recipe_id)
        if not recipe:
            return None
        
        # Получаем изображения
        images_query = """
            SELECT * FROM dish_images
            WHERE recipe_id = $1
            ORDER BY is_primary DESC, created_at DESC
        """
        
        images = await self._execute_query(images_query, recipe_id)
        recipe['images'] = [dict(img) for img in images]
        
        return recipe
    
    async def delete_user_recipes(self, user_id: int) -> int:
        """Удаление всех рецептов пользователя"""
        # Сначала получаем ID рецептов для удаления связанных изображений
        recipes_query = "SELECT id FROM recipes WHERE user_id = $1"
        recipes = await self._execute_query(recipes_query, user_id)
        recipe_ids = [r['id'] for r in recipes]
        
        # Удаляем связанные изображения
        if recipe_ids:
            images_query = "DELETE FROM dish_images WHERE recipe_id = ANY($1)"
            await self._execute_query(images_query, recipe_ids)
        
        # Удаляем из избранного
        favorites_query = "DELETE FROM favorite_recipes WHERE user_id = $1"
        await self._execute_query(favorites_query, user_id)
        
        # Удаляем рецепты
        delete_query = "DELETE FROM recipes WHERE user_id = $1 RETURNING COUNT(*)"
        result = await self._execute_query(delete_query, user_id)
        
        return result[0]['count'] if result else 0
