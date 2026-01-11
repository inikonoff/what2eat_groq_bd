import os
import json
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Union
from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_KEY

logger = logging.getLogger(__name__)

class SupabaseService:
    """Сервис для работы с Supabase PostgreSQL"""
    
    def __init__(self):
        self.client: Optional[Client] = None
        self._connect()
    
    def _connect(self):
        """Подключение к Supabase"""
        try:
            if not SUPABASE_URL or not SUPABASE_KEY:
                raise ValueError("Supabase URL и KEY не настроены в .env")
            
            self.client = create_client(SUPABASE_URL, SUPABASE_KEY)
            logger.info("✅ Supabase подключен успешно")
            
            # Тестовый запрос для проверки соединения
            self.client.table('users').select('count', count='exact').limit(1).execute()
            
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к Supabase: {e}")
            self.client = None
    
    def _ensure_connection(self):
        """Проверяет и восстанавливает соединение при необходимости"""
        if self.client is None:
            self._connect()
    
    # --- USERS ---
    
    async def get_user(self, user_id: int) -> Optional[Dict]:
        """Получает пользователя по ID, создает если не существует"""
        self._ensure_connection()
        if not self.client:
            return None
        
        try:
            # Пытаемся получить существующего пользователя
            response = self.client.table('users') \
                .select('*') \
                .eq('user_id', user_id) \
                .limit(1) \
                .execute()
            
            if response.data and len(response.data) > 0:
                user = response.data[0]
                logger.debug(f"Найден пользователь: {user_id}")
                return user
            
            # Создаем нового пользователя
            return await self.create_user(user_id)
            
        except Exception as e:
            logger.error(f"Ошибка при получении пользователя {user_id}: {e}")
            return None
    
    async def create_user(self, user_id: int, username: str = None) -> Dict:
        """Создает нового пользователя"""
        self._ensure_connection()
        if not self.client:
            return self._get_default_user(user_id)
        
        try:
            user_data = {
                'user_id': user_id,
                'username': username,
                'products': None,
                'state': None,
                'session_json': {},
                'is_premium': False,
                'premium_ends_at': None,
                'is_banned': False,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'updated_at': datetime.now(timezone.utc).isoformat()
            }
            
            response = self.client.table('users') \
                .insert(user_data) \
                .execute()
            
            if response.data and len(response.data) > 0:
                logger.info(f"Создан новый пользователь: {user_id}")
                return response.data[0]
            
            return user_data
            
        except Exception as e:
            logger.error(f"Ошибка при создании пользователя {user_id}: {e}")
            return self._get_default_user(user_id)
    
    def _get_default_user(self, user_id: int) -> Dict:
        """Возвращает дефолтную структуру пользователя при ошибках БД"""
        return {
            'user_id': user_id,
            'products': None,
            'state': None,
            'session_json': {},
            'is_premium': False,
            'premium_ends_at': None
        }
    
    async def update_user_field(self, user_id: int, field: str, value: Any):
        """Обновляет поле пользователя"""
        self._ensure_connection()
        if not self.client:
            return
        
        try:
            update_data = {
                field: value,
                'updated_at': datetime.now(timezone.utc).isoformat()
            }
            
            self.client.table('users') \
                .update(update_data) \
                .eq('user_id', user_id) \
                .execute()
                
        except Exception as e:
            logger.error(f"Ошибка обновления поля {field} для пользователя {user_id}: {e}")
    
    async def update_user_session(self, user_id: int, session_data: Dict):
        """Обновляет сессионные данные пользователя"""
        await self.update_user_field(user_id, 'session_json', session_data)
    
    async def update_user_products(self, user_id: int, products: str):
        """Обновляет список продуктов пользователя"""
        await self.update_user_field(user_id, 'products', products)
    
    async def update_user_state(self, user_id: int, state: str):
        """Обновляет состояние пользователя"""
        await self.update_user_field(user_id, 'state', state)
    
    # --- FAVORITES ---
    
    async def add_favorite(
        self, 
        user_id: int, 
        dish_name: str, 
        recipe_text: str,
        products_snapshot: str,
        image_base64: str = None
    ) -> Optional[str]:
        """Добавляет рецепт в избранное, возвращает recipe_id"""
        self._ensure_connection()
        if not self.client:
            return None
        
        try:
            recipe_id = str(uuid.uuid4())
            current_time = datetime.now(timezone.utc).isoformat()
            
            favorite_data = {
                'recipe_id': recipe_id,
                'user_id': user_id,
                'dish_name': dish_name[:500],  # Ограничиваем длину
                'recipe_text': recipe_text[:10000],  # Ограничиваем длину
                'products_snapshot': products_snapshot[:2000],
                'image_base64': image_base64[:500000] if image_base64 else None,  # Ограничиваем base64
                'created_at': current_time
            }
            
            # Очищаем слишком большие значения для БД
            if image_base64 and len(image_base64) > 500000:
                logger.warning(f"Изображение для {dish_name} слишком большое, обрезаем")
                favorite_data['image_base64'] = None
            
            response = self.client.table('favorites') \
                .insert(favorite_data) \
                .execute()
            
            if response.data and len(response.data) > 0:
                logger.info(f"Добавлен в избранное: {dish_name} для пользователя {user_id}")
                return recipe_id
            
            return None
            
        except Exception as e:
            logger.error(f"Ошибка при добавлении в избранное: {e}")
            return None
    
    async def get_favorites(self, user_id: int, limit: int = 20) -> List[Dict]:
        """Получает список избранных рецептов"""
        self._ensure_connection()
        if not self.client:
            return []
        
        try:
            response = self.client.table('favorites') \
                .select('recipe_id, dish_name, created_at, image_base64') \
                .eq('user_id', user_id) \
                .order('created_at', desc=True) \
                .limit(limit) \
                .execute()
            
            return response.data if response.data else []
            
        except Exception as e:
            logger.error(f"Ошибка при получении избранного для пользователя {user_id}: {e}")
            return []
    
    async def get_favorite_by_id(self, user_id: int, recipe_id: str) -> Optional[Dict]:
        """Получает полную информацию о рецепте"""
        self._ensure_connection()
        if not self.client:
            return None
        
        try:
            response = self.client.table('favorites') \
                .select('*') \
                .eq('user_id', user_id) \
                .eq('recipe_id', recipe_id) \
                .limit(1) \
                .execute()
            
            if response.data and len(response.data) > 0:
                return response.data[0]
            return None
            
        except Exception as e:
            logger.error(f"Ошибка при получении рецепта {recipe_id}: {e}")
            return None
    
    async def delete_favorite(self, user_id: int, recipe_id: str) -> bool:
        """Удаляет рецепт из избранного"""
        self._ensure_connection()
        if not self.client:
            return False
        
        try:
            response = self.client.table('favorites') \
                .delete() \
                .eq('user_id', user_id) \
                .eq('recipe_id', recipe_id) \
                .execute()
            
            success = response.data is not None
            if success:
                logger.info(f"Удален рецепт {recipe_id} для пользователя {user_id}")
            return success
            
        except Exception as e:
            logger.error(f"Ошибка при удалении рецепта {recipe_id}: {e}")
            return False
    
    async def check_recipe_exists(self, user_id: int, dish_name: str) -> bool:
        """Проверяет, существует ли уже рецепт с таким названием"""
        self._ensure_connection()
        if not self.client:
            return False
        
        try:
            response = self.client.table('favorites') \
                .select('recipe_id') \
                .eq('user_id', user_id) \
                .eq('dish_name', dish_name) \
                .limit(1) \
                .execute()
            
            return bool(response.data and len(response.data) > 0)
            
        except Exception as e:
            logger.error(f"Ошибка при проверке существования рецепта: {e}")
            return False
    
    # --- PROMO CODES ---
    
    async def activate_promo(self, user_id: int, code_text: str) -> Dict[str, Any]:
        """Активирует промокод для пользователя"""
        self._ensure_connection()
        if not self.client:
            return {"status": "error", "message": "Database connection failed"}
        
        try:
            # Начинаем транзакцию
            # 1. Получаем промокод
            promo_response = self.client.table('promo_codes') \
                .select('*') \
                .eq('code', code_text.upper()) \
                .limit(1) \
                .execute()
            
            if not promo_response.data or len(promo_response.data) == 0:
                return {"status": "not_found", "message": "Промокод не найден"}
            
            promo = promo_response.data[0]
            
            # Проверяем лимиты
            usage_limit = promo.get('usage_limit', 1)
            usages_count = promo.get('usages_count', 0)
            
            if usages_count >= usage_limit:
                return {"status": "limit_reached", "message": "Лимит использований исчерпан"}
            
            # Проверяем, не активировал ли уже этот пользователь
            if promo.get('activated_by') == user_id:
                return {"status": "already_used", "message": "Вы уже использовали этот промокод"}
            
            # Рассчитываем новую дату окончания премиума
            days = promo.get('days_value', 7)
            current_time = datetime.now(timezone.utc)
            
            # Получаем текущую дату окончания премиума пользователя
            user_response = self.client.table('users') \
                .select('premium_ends_at') \
                .eq('user_id', user_id) \
                .limit(1) \
                .execute()
            
            current_end = None
            if user_response.data and len(user_response.data) > 0:
                current_end_str = user_response.data[0].get('premium_ends_at')
                if current_end_str:
                    current_end = datetime.fromisoformat(current_end_str.replace('Z', '+00:00'))
            
            # Вычисляем новую дату окончания
            if current_end and current_end > current_time:
                new_end = current_end + timedelta(days=days)
            else:
                new_end = current_time + timedelta(days=days)
            
            # Выполняем обновления
            # 1. Обновляем промокод
            self.client.table('promo_codes') \
                .update({
                    'usages_count': usages_count + 1,
                    'activated_by': user_id,
                    'activated_at': current_time.isoformat()
                }) \
                .eq('code', code_text.upper()) \
                .execute()
            
            # 2. Обновляем пользователя
            self.client.table('users') \
                .update({
                    'is_premium': True,
                    'premium_ends_at': new_end.isoformat(),
                    'updated_at': current_time.isoformat()
                }) \
                .eq('user_id', user_id) \
                .execute()
            
            logger.info(f"Промокод {code_text} активирован пользователем {user_id}")
            
            return {
                "status": "success",
                "message": f"Премиум активирован на {days} дней",
                "days": days,
                "expires_at": new_end.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Ошибка активации промокода {code_text} для пользователя {user_id}: {e}")
            return {"status": "error", "message": str(e)}
    
    async def create_promo_code(self, code: str, days: int, limit: int = 1) -> bool:
        """Создает новый промокод (админ функция)"""
        self._ensure_connection()
        if not self.client:
            return False
        
        try:
            promo_data = {
                'code': code.upper(),
                'days_value': days,
                'usage_limit': limit,
                'usages_count': 0,
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
            response = self.client.table('promo_codes') \
                .insert(promo_data) \
                .execute()
            
            success = response.data is not None
            if success:
                logger.info(f"Создан промокод: {code} на {days} дней")
            return success
            
        except Exception as e:
            logger.error(f"Ошибка создания промокода {code}: {e}")
            return False
    
    # --- ADMIN FUNCTIONS ---
    
    async def get_all_users(self, limit: int = 1000) -> List[Dict]:
        """Получает список всех пользователей (админ)"""
        self._ensure_connection()
        if not self.client:
            return []
        
        try:
            response = self.client.table('users') \
                .select('user_id, username, created_at, is_premium, premium_ends_at') \
                .order('created_at', desc=True) \
                .limit(limit) \
                .execute()
            
            return response.data if response.data else []
            
        except Exception as e:
            logger.error(f"Ошибка при получении списка пользователей: {e}")
            return []
    
    async def get_user_stats(self) -> Dict[str, Any]:
        """Получает статистику пользователей"""
        self._ensure_connection()
        if not self.client:
            return {}
        
        try:
            # Общее количество пользователей
            total_response = self.client.table('users') \
                .select('count', count='exact') \
                .execute()
            total_users = total_response.count or 0
            
            # Премиум пользователи
            premium_response = self.client.table('users') \
                .select('count', count='exact') \
                .eq('is_premium', True) \
                .execute()
            premium_users = premium_response.count or 0
            
            # Новые пользователи за последние 7 дней
            week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
            new_response = self.client.table('users') \
                .select('count', count='exact') \
                .gte('created_at', week_ago) \
                .execute()
            new_users = new_response.count or 0
            
            # Количество рецептов
            recipes_response = self.client.table('favorites') \
                .select('count', count='exact') \
                .execute()
            total_recipes = recipes_response.count or 0
            
            return {
                'total_users': total_users,
                'premium_users': premium_users,
                'new_users_7d': new_users,
                'total_recipes': total_recipes,
                'updated_at': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Ошибка при получении статистики: {e}")
            return {}
    
    async def search_users(self, query: str, limit: int = 50) -> List[Dict]:
        """Поиск пользователей (админ)"""
        self._ensure_connection()
        if not self.client:
            return []
        
        try:
            response = self.client.table('users') \
                .select('user_id, username, created_at, is_premium') \
                .or_(f'user_id.eq.{query},username.ilike.%{query}%') \
                .limit(limit) \
                .execute()
            
            return response.data if response.data else []
            
        except Exception as e:
            logger.error(f"Ошибка поиска пользователей по запросу {query}: {e}")
            return []
    
    # --- CLEANUP ---
    
    async def cleanup_old_data(self, days_old: int = 180):
        """Очищает старые данные (выполнять периодически)"""
        self._ensure_connection()
        if not self.client:
            return
        
        try:
            cutoff_date = (datetime.now(timezone.utc) - timedelta(days=days_old)).isoformat()
            
            # Удаляем старые сессии неактивных пользователей
            self.client.table('users') \
                .update({'session_json': {}}) \
                .lt('updated_at', cutoff_date) \
                .execute()
            
            logger.info(f"Очищены сессии старше {days_old} дней")
            
        except Exception as e:
            logger.error(f"Ошибка при очистке старых данных: {e}")

# Синглтон
supabase_service = SupabaseService()