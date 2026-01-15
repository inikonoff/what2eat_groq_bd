"""
Finite State Machine для управления диалогами
"""
from enum import Enum
from typing import Dict, Any, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

class UserState(str, Enum):
    """Состояния пользователя"""
    MAIN_MENU = "main_menu"
    ENTERING_PRODUCTS = "entering_products"
    SELECTING_CATEGORY = "selecting_category"
    SELECTING_DISH = "selecting_dish"
    VIEWING_RECIPE = "viewing_recipe"
    GENERATING_RECIPE = "generating_recipe"
    VIEWING_HISTORY = "viewing_history"
    VIEWING_FAVORITES = "viewing_favorites"
    GENERATING_IMAGE = "generating_image"

@dataclass
class FSMContext:
    """Контекст FSM"""
    state: UserState
    data: Dict[str, Any]
    
    def __init__(self, state: UserState = UserState.MAIN_MENU, **kwargs):
        self.state = state
        self.data = kwargs

class FSM:
    """Конечный автомат для управления состояниями"""
    
    def __init__(self):
        self._states: Dict[int, FSMContext] = {}
    
    async def set_state(self, user_id: int, state: UserState, **data):
        """Установка состояния пользователя"""
        if user_id not in self._states:
            self._states[user_id] = FSMContext(state=state, **data)
        else:
            self._states[user_id].state = state
            self._states[user_id].data.update(data)
        
        logger.debug(f"Пользователь {user_id} переведен в состояние {state}")
    
    async def get_state(self, user_id: int) -> Optional[UserState]:
        """Получение состояния пользователя"""
        if user_id in self._states:
            return self._states[user_id].state
        return None
    
    async def get_data(self, user_id: int, key: str = None, default=None):
        """Получение данных состояния"""
        if user_id not in self._states:
            return default
        
        if key is None:
            return self._states[user_id].data
        
        return self._states[user_id].data.get(key, default)
    
    async def update_data(self, user_id: int, **kwargs):
        """Обновление данных состояния"""
        if user_id not in self._states:
            self._states[user_id] = FSMContext(state=UserState.MAIN_MENU, **kwargs)
        else:
            self._states[user_id].data.update(kwargs)
    
    async def clear_state(self, user_id: int):
        """Очистка состояния пользователя"""
        if user_id in self._states:
            del self._states[user_id]
            logger.debug(f"Состояние пользователя {user_id} очищено")
    
    async def reset_to_main(self, user_id: int):
        """Сброс к главному меню"""
        await self.set_state(user_id, UserState.MAIN_MENU)
        logger.debug(f"Пользователь {user_id} возвращен в главное меню")

# Глобальный экземпляр FSM
fsm = FSM()
