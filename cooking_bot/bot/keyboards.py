"""
Клавиатуры для бота
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from typing import List, Dict, Optional

# --- СЛОВАРЬ КАТЕГОРИЙ ---
CATEGORY_MAP = {
    "breakfast": "🍳 Завтраки",
    "soup": "🍲 Супы",
    "main": "🍝 Вторые блюда",
    "salad": "🥗 Салаты",
    "snack": "🥪 Закуски",
    "dessert": "🍰 Десерты",
    "drink": "🥤 Напитки",
    "sauce": "🍾 Соусы",
    "mix": "🍱 Комплексный обед",
}

def get_confirmation_keyboard() -> InlineKeyboardMarkup:
    """Кнопки после ввода продуктов: Добавить еще или Готовить"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить продукты", callback_data="action_add_more")],
        [InlineKeyboardButton(text="👨‍🍳 Готовить (Категории)", callback_data="action_cook")]
    ])

def get_categories_keyboard(categories: list) -> InlineKeyboardMarkup:
    """Клавиатура выбора категорий"""
    builder = []
    row = []
    
    for cat_key in categories:
        text = CATEGORY_MAP.get(cat_key, cat_key.capitalize())
        row.append(InlineKeyboardButton(text=text, callback_data=f"cat_{cat_key}"))
        if len(row) == 2:
            builder.append(row)
            row = []
    
    if row:
        builder.append(row)
    
    builder.append([InlineKeyboardButton(text="🗑 Сброс", callback_data="restart")])
    return InlineKeyboardMarkup(inline_keyboard=builder)

def get_dishes_keyboard(dishes_list: list) -> InlineKeyboardMarkup:
    """Клавиатура выбора блюд из списка"""
    builder = []
    
    for i, dish in enumerate(dishes_list):
        btn_text = f"{dish['name'][:40]}"
        builder.append([InlineKeyboardButton(text=btn_text, callback_data=f"dish_{i}")])
    
    builder.append([InlineKeyboardButton(text="⬅️ Назад к категориям", callback_data="back_to_categories")])
    return InlineKeyboardMarkup(inline_keyboard=builder)

def get_recipe_back_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура после показа рецепта"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Другой вариант", callback_data="repeat_recipe")],
        [InlineKeyboardButton(text="❤️ В избранное", callback_data="add_to_favorites")],
        [InlineKeyboardButton(text="⬅️ Вернуться к категориям", callback_data="back_to_categories")]
    ])

def get_hide_keyboard() -> InlineKeyboardMarkup:
    """Кнопка скрытия сообщения"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗑 Скрыть", callback_data="delete_msg")]
    ])

def get_stats_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для статистики"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗑 Очистить мою историю", callback_data="clear_my_history")],
        [InlineKeyboardButton(text="📝 Мои рецепты", callback_data="my_recipes")],
        [InlineKeyboardButton(text="❌ Закрыть", callback_data="delete_msg")]
    ])

def get_favorites_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для избранного"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")],
        [InlineKeyboardButton(text="🗑 Очистить избранное", callback_data="clear_favorites")]
    ])

def get_recipe_list_keyboard(recipes: List[Dict], page: int = 0, per_page: int = 5) -> InlineKeyboardMarkup:
    """Клавиатура для списка рецептов с пагинацией"""
    builder = []
    
    start_idx = page * per_page
    end_idx = start_idx + per_page
    page_recipes = recipes[start_idx:end_idx]
    
    for i, recipe in enumerate(page_recipes):
        idx = start_idx + i
        dish_name = recipe.get('dish_name', 'Без названия')[:30]
        builder.append([
            InlineKeyboardButton(
                text=f"📖 {dish_name}", 
                callback_data=f"view_recipe_{recipe.get('id')}"
            )
        ])
    
    # Пагинация
    pagination_buttons = []
    total_pages = (len(recipes) + per_page - 1) // per_page
    
    if page > 0:
        pagination_buttons.append(InlineKeyboardButton(text="⬅️", callback_data=f"recipes_page_{page-1}"))
    
    pagination_buttons.append(InlineKeyboardButton(text=f"{page+1}/{total_pages}", callback_data="noop"))
    
    if page < total_pages - 1:
        pagination_buttons.append(InlineKeyboardButton(text="➡️", callback_data=f"recipes_page_{page+1}"))
    
    if pagination_buttons:
        builder.append(pagination_buttons)
    
    builder.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")])
    
    return InlineKeyboardMarkup(inline_keyboard=builder)

def get_recipe_view_keyboard(recipe_id: int, is_favorite: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура для просмотра рецепта"""
    favorite_text = "❌ Из избранного" if is_favorite else "❤️ В избранное"
    
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=favorite_text, callback_data=f"toggle_favorite_{recipe_id}"),
            InlineKeyboardButton(text="🗑 Удалить", callback_data=f"delete_recipe_{recipe_id}")
        ],
        [
            InlineKeyboardButton(text="🔄 Сгенерировать изображение", callback_data=f"gen_image_{recipe_id}")
        ],
        [
            InlineKeyboardButton(text="⬅️ Назад к списку", callback_data="back_to_recipes_list")
        ]
    ])

def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Главное меню бота"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🍳 Новые продукты", callback_data="new_products"),
            InlineKeyboardButton(text="📝 Мои рецепты", callback_data="my_recipes")
        ],
        [
            InlineKeyboardButton(text="❤️ Избранное", callback_data="favorites"),
            InlineKeyboardButton(text="📊 Статистика", callback_data="stats")
        ],
        [
            InlineKeyboardButton(text="👨‍💻 Автор", callback_data="author"),
            InlineKeyboardButton(text="ℹ️ Помощь", callback_data="help")
        ]
    ])
