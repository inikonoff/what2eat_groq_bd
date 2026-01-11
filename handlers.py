import os
import io
import base64
import logging
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any

from aiogram import Dispatcher, F, html, Bot
from aiogram.types import (
    Message, InlineKeyboardMarkup, InlineKeyboardButton, 
    CallbackQuery, BufferedInputFile, BotCommand, BotCommandScopeChat
)
from aiogram.filters import Command

from groq_service import GroqService
from utils import VoiceProcessor
from supabase_service import supabase_service
from image_service import image_service
from config import ADMIN_ID, MAX_PRODUCTS_LENGTH

# Настройка логирования
logger = logging.getLogger(__name__)

# Инициализация сервисов
groq_service = GroqService()
voice_processor = VoiceProcessor()

# --- КОНСТАНТЫ И СЛОВАРИ ---

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

# --- КЛАВИАТУРЫ ---

def get_confirmation_keyboard():
    """Кнопки после ввода продуктов"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить продукты", callback_data="action_add_more")],
        [InlineKeyboardButton(text="👨‍🍳 Готовить (Категории)", callback_data="action_cook")]
    ])

def get_categories_keyboard(categories: list):
    """Клавиатура для выбора категории"""
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

def get_dishes_keyboard(dishes_list: list):
    """Клавиатура для выбора блюда из списка"""
    builder = []
    for i, dish in enumerate(dishes_list):
        btn_text = f"{dish['name'][:40]}"
        builder.append([InlineKeyboardButton(text=btn_text, callback_data=f"dish_{i}")])
    builder.append([InlineKeyboardButton(text="⬅️ Назад к категориям", callback_data="back_to_categories")])
    return InlineKeyboardMarkup(inline_keyboard=builder)

def get_recipe_keyboard(show_save: bool = True, delete_id: str = None, dish_name: str = None):
    """Клавиатура для рецепта"""
    buttons = []
    
    # Кнопка генерации фото (только если есть название блюда)
    if dish_name and not delete_id:
        buttons.append([InlineKeyboardButton(text="🎨 Сгенерировать фото", callback_data="gen_photo")])
    
    # Кнопка сохранения рецепта
    if show_save:
        buttons.append([InlineKeyboardButton(text="❤️ Сохранить рецепт", callback_data="save_recipe")])
    
    # Кнопки навигации
    if delete_id:
        buttons.append([InlineKeyboardButton(text="❌ Удалить рецепт", callback_data=f"delete_fav_{delete_id}")])
        buttons.append([InlineKeyboardButton(text="⬅️ К списку", callback_data="my_recipes_list")])
    else:
        buttons.append([InlineKeyboardButton(text="⬅️ Вернуться к категориям", callback_data="back_to_categories")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_favorites_keyboard(fav_list):
    """Клавиатура для списка избранных рецептов"""
    builder = []
    for fav in fav_list:
        btn_text = f"📜 {fav['dish_name'][:35]}"
        if len(fav['dish_name']) > 35:
            btn_text += "..."
        builder.append([InlineKeyboardButton(text=btn_text, callback_data=f"fav_{fav['recipe_id']}")])
    builder.append([InlineKeyboardButton(text="⬅️ Закрыть", callback_data="delete_msg")])
    return InlineKeyboardMarkup(inline_keyboard=builder)

def get_hide_keyboard():
    """Кнопка скрытия сообщения"""
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🗑 Скрыть", callback_data="delete_msg")
    ]])

# --- НАСТРОЙКА МЕНЮ БОТА ---

async def set_main_menu(bot: Bot, user_id: int):
    """Устанавливает меню команд для пользователя"""
    commands = [
        BotCommand(command="start", description="🔄 Рестарт / Начать заново"),
        BotCommand(command="my_recipes", description="📂 Сохраненные рецепты"),
        BotCommand(command="author", description="👨‍💻 Связь с автором"),
    ]
    
    # Добавляем админские команды
    if user_id == ADMIN_ID:
        commands.append(BotCommand(command="admin", description="🛠 Панель администратора"))
        commands.append(BotCommand(command="stats", description="📊 Статистика"))
    
    try:
        await bot.set_my_commands(commands, scope=BotCommandScopeChat(chat_id=user_id))
    except Exception as e:
        logger.error(f"Ошибка установки меню для {user_id}: {e}")

# --- ОСНОВНЫЕ ХЭНДЛЕРЫ ---

async def cmd_start(message: Message):
    """Обработчик команды /start"""
    user_id = message.from_user.id
    
    # Настраиваем меню
    await set_main_menu(message.bot, user_id)
    
    # Сбрасываем сессию пользователя
    await supabase_service.update_user_state(user_id, None)
    await supabase_service.update_user_products(user_id, None)
    
    # Приветственное сообщение
    welcome_text = (
        "👋 <b>Здравствуйте!</b>\n\n"
        "Я — ваш персональный шеф-повар с искусственным интеллектом.\n\n"
        "🍏 <b>Как это работает:</b>\n"
        "1. Напишите или продиктуйте мне список продуктов\n"
        "2. Я подберу подходящие блюда и категории\n"
        "3. Выберите блюдо и получите подробный рецепт\n"
        "4. Я могу сгенерировать фото блюда!\n\n"
        "🌍 <b>Поддерживаю:</b> русский и английский языки\n"
        "🎤 <b>Голосовые сообщения:</b> говорите продукты, я распознаю\n"
        "📸 <b>Генерация фото:</b> кнопка '🎨 Сгенерировать фото'\n\n"
        "🍽 <b>Начнем? Просто напишите или продиктуйте продукты!</b>"
    )
    
    await message.answer(welcome_text, parse_mode="HTML")

async def cmd_author(message: Message):
    """Обработчик команды /author"""
    await message.answer(
        "👨‍💻 <b>Автор бота:</b> @inikonoff\n\n"
        "💡 <b>Идеи и предложения:</b> @inikonoff\n"
        "🐛 <b>Сообщить об ошибке:</b> @inikonoff\n\n"
        "🌟 <b>Бот с открытым исходным кодом</b>\n"
        "GitHub: https://github.com/inikonoff/chef-ai-bot",
        parse_mode="HTML"
    )

async def cmd_my_recipes(message: Message):
    """Обработчик команды /my_recipes - список сохраненных рецептов"""
    user_id = message.from_user.id
    
    # Получаем избранное
    favorites = await supabase_service.get_favorites(user_id)
    
    if not favorites:
        await message.answer(
            "📂 <b>Сохраненные рецепты отсутствуют.</b>\n\n"
            "Чтобы сохранить рецепт:\n"
            "1. Сгенерируйте рецепт блюда\n"
            "2. Нажмите кнопку '❤️ Сохранить рецепт'\n"
            "3. Рецепт появится здесь!",
            parse_mode="HTML"
        )
        return
    
    # Формируем сообщение со списком
    recipes_text = "📂 <b>Ваши сохраненные рецепты:</b>\n\n"
    for i, fav in enumerate(favorites[:20], 1):
        date_str = ""
        if fav.get('created_at'):
            try:
                date = datetime.fromisoformat(fav['created_at'].replace('Z', '+00:00'))
                date_str = date.strftime("%d.%m.%Y")
            except:
                pass
        
        recipe_line = f"{i}. <b>{html.quote(fav['dish_name'])}</b>"
        if date_str:
            recipe_line += f" ({date_str})"
        recipes_text += recipe_line + "\n"
    
    if len(favorites) > 20:
        recipes_text += f"\n📝 <i>Показано 20 из {len(favorites)} рецептов</i>"
    
    await message.answer(recipes_text, 
                        reply_markup=get_favorites_keyboard(favorites[:20]), 
                        parse_mode="HTML")

async def cmd_stats(message: Message):
    """Показывает статистику (админ)"""
    if message.from_user.id != ADMIN_ID:
        return
    
    try:
        # Статистика пользователей
        user_stats = await supabase_service.get_user_stats()
        
        # Статистика генерации изображений
        image_stats = image_service.get_stats()
        
        # Формируем сообщение
        stats_text = "📊 <b>СТАТИСТИКА СИСТЕМЫ</b>\n\n"
        
        stats_text += "👥 <b>Пользователи:</b>\n"
        stats_text += f"• Всего: {user_stats.get('total_users', 0)}\n"
        stats_text += f"• Премиум: {user_stats.get('premium_users', 0)}\n"
        stats_text += f"• Новые (7д): {user_stats.get('new_users_7d', 0)}\n"
        stats_text += f"• Рецептов сохранено: {user_stats.get('total_recipes', 0)}\n\n"
        
        stats_text += "🖼 <b>Генерация изображений:</b>\n"
        stats_text += f"• Всего запросов: {image_stats.get('total_requests', 0)}\n"
        stats_text += f"• Попаданий в кэш: {image_stats.get('cache_hits', 0)}\n"
        stats_text += f"• Эффективность кэша: {image_stats.get('cache_hit_rate', 0):.1f}%\n"
        stats_text += f"• Gemini использовано сегодня: {image_stats['gemini']['daily_used']}/{image_stats['gemini']['daily_limit']}\n\n"
        
        stats_text += "⚙️ <b>Настройки:</b>\n"
        stats_text += f"• Приоритет: {image_stats.get('provider_priority', 'gemini_first')}\n"
        stats_text += f"• Fallback Replicate: {'✅' if image_stats.get('replicate_fallback') else '❌'}\n"
        
        # Добавляем информацию о кэше
        cache_stats = image_stats.get('cache', {})
        if cache_stats:
            stats_text += f"\n💾 <b>Кэш изображений:</b>\n"
            stats_text += f"• Файлов: {cache_stats.get('file_count', 0)}\n"
            stats_text += f"• Размер: {cache_stats.get('total_size_mb', 0):.1f}MB / {cache_stats.get('max_size_mb', 0)}MB\n"
            if cache_stats.get('last_cleanup'):
                stats_text += f"• Последняя очистка: {cache_stats.get('last_cleanup', 'никогда')}\n"
        
        await message.answer(stats_text, parse_mode="HTML")
        
    except Exception as e:
        logger.error(f"Ошибка получения статистики: {e}")
        await message.answer(f"❌ Ошибка получения статистики: {e}")

# --- ОБРАБОТКА ГОЛОСОВЫХ СООБЩЕНИЙ ---

async def handle_voice(message: Message):
    """Обработчик голосовых сообщений"""
    user_id = message.from_user.id
    
    # Сообщение о начале обработки
    processing_msg = await message.answer("🎧 <i>Слушаю...</i>", parse_mode="HTML")
    
    try:
        # Создаем временный файл
        temp_file = f"temp/voice_{user_id}_{message.voice.file_id}.ogg"
        
        # Скачиваем голосовое сообщение
        await message.bot.download(message.voice, destination=temp_file)
        
        # Распознаем речь
        text = await voice_processor.process_voice(temp_file)
        
        # Удаляем сообщение обработки
        await processing_msg.delete()
        
        # Удаляем голосовое сообщение (опционально)
        try:
            await message.delete()
        except:
            pass
        
        if text:
            # Обрабатываем распознанный текст
            await process_products_input(message, user_id, text)
        else:
            await message.answer("😕 <b>Не удалось распознать речь.</b>\nПопробуйте говорить четче или напишите текстом.", 
                               parse_mode="HTML")
            
    except Exception as e:
        await processing_msg.delete()
        logger.error(f"Ошибка обработки голосового сообщения: {e}")
        await message.answer("❌ <b>Ошибка обработки голосового сообщения.</b>\nПопробуйте написать текстом.", 
                           parse_mode="HTML")
    
    finally:
        # Очистка временного файла
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except:
                pass

# --- ОБРАБОТКА ТЕКСТОВЫХ СООБЩЕНИЙ ---

async def handle_text(message: Message):
    """Обработчик текстовых сообщений"""
    user_id = message.from_user.id
    text = message.text.strip()
    
    # Проверяем, не является ли сообщение командой
    if text.startswith('/'):
        return
    
    await process_products_input(message, user_id, text)

async def handle_direct_recipe(message: Message):
    """Обработчик прямого запроса рецепта (дай рецепт ...)"""
    user_id = message.from_user.id
    text = message.text.strip()
    
    # Извлекаем название блюда
    dish_name = text.lower().replace("дай рецепт", "", 1).strip()
    
    if len(dish_name) < 3:
        await message.answer("📝 <b>Укажите название блюда.</b>\nПример: <i>Дай рецепт паста карбонара</i>", 
                           parse_mode="HTML")
        return
    
    # Сообщение о начале генерации
    wait_msg = await message.answer(f"⚡️ <i>Ищу рецепт: <b>{html.quote(dish_name)}</b>...</i>", 
                                  parse_mode="HTML")
    
    try:
        # Генерируем рецепт через Groq
        recipe = await groq_service.generate_freestyle_recipe(dish_name)
        
        # Сохраняем во временные данные пользователя
        session_data = {
            'temp_recipe': {
                'name': dish_name,
                'text': recipe,
                'products': "",
                'visual': dish_name
            }
        }
        await supabase_service.update_user_session(user_id, session_data)
        await supabase_service.update_user_state(user_id, "recipe_sent")
        
        # Удаляем сообщение ожидания и отправляем рецепт
        await wait_msg.delete()
        await message.answer(recipe, 
                           reply_markup=get_recipe_keyboard(show_save=False, dish_name=dish_name), 
                           parse_mode="HTML")
        
    except Exception as e:
        await wait_msg.delete()
        logger.error(f"Ошибка генерации рецепта '{dish_name}': {e}")
        await message.answer("❌ <b>Не удалось сгенерировать рецепт.</b>\nПопробуйте еще раз или измените название блюда.", 
                           parse_mode="HTML")

# --- ОСНОВНАЯ ЛОГИКА ОБРАБОТКИ ПРОДУКТОВ ---

async def process_products_input(message: Message, user_id: int, text: str):
    """
    Основная логика обработки ввода продуктов
    
    Args:
        message: Объект сообщения
        user_id: ID пользователя
        text: Введенный текст
    """
    # Проверяем пасхалку (благодарность)
    if text.lower().strip(" .!") in ["спасибо", "спс", "благодарю", "thanks", "thank you"]:
        user_data = await supabase_service.get_user(user_id)
        if user_data.get('state') == "recipe_sent":
            await message.answer("🥰 <b>На здоровье! Приятного аппетита!</b> 👨‍🍳", parse_mode="HTML")
            await supabase_service.update_user_state(user_id, None)
        return
    
    # Получаем текущего пользователя
    user_data = await supabase_service.get_user(user_id)
    current_products = user_data.get('products')
    
    # Если это первый ввод продуктов
    if not current_products:
        # Валидируем ввод
        is_valid = await groq_service.validate_ingredients(text)
        if not is_valid:
            await message.answer(
                f"🤨 <b>\"{html.quote(text[:100])}\"</b> — не похоже на список продуктов.\n\n"
                "📝 <b>Пример правильного ввода:</b>\n"
                "<i>курица, помидоры, лук, сыр, сметана</i>\n"
                "или\n"
                "<i>яйца молоко мука сахар</i>",
                parse_mode="HTML"
            )
            return
        
        # Сохраняем продукты
        await supabase_service.update_user_products(user_id, text)
        response_text = f"✅ <b>Принято:</b> {html.quote(text)}"
        
    else:
        # Добавляем к существующим продуктам
        new_products = f"{current_products}, {text}"
        
        # Проверяем длину (ограничение от перегрузки)
        if len(new_products) > MAX_PRODUCTS_LENGTH:
            await message.answer(
                f"⚠️ <b>Слишком много продуктов!</b>\n"
                f"Текущий список: {len(current_products)} символов\n"
                f"Максимум: {MAX_PRODUCTS_LENGTH} символов\n\n"
                "Рекомендуется начать новый список командой /start",
                parse_mode="HTML"
            )
            return
        
        await supabase_service.update_user_products(user_id, new_products)
        response_text = (
            f"➕ <b>Добавлено:</b> {html.quote(text)}\n"
            f"🛒 <b>Всего продуктов:</b> {html.quote(new_products[:200])}"
            f"{'...' if len(new_products) > 200 else ''}"
        )
    
    # Предлагаем добавить еще или начать готовить
    await message.answer(response_text, 
                        reply_markup=get_confirmation_keyboard(), 
                        parse_mode="HTML")

# --- ЛОГИКА КАТЕГОРИЙ И БЛЮД ---

async def start_category_flow(message: Message, user_id: int):
    """Запускает процесс выбора категорий на основе продуктов"""
    user_data = await supabase_service.get_user(user_id)
    products = user_data.get('products')
    
    if not products:
        await message.answer("🛒 <b>Список продуктов пуст.</b>\nНачните заново с команды /start", 
                           parse_mode="HTML")
        return
    
    # Сообщение о начале анализа
    wait_msg = await message.answer("👨‍🍳 <i>Анализирую продукты и подбираю категории...</i>", 
                                  parse_mode="HTML")
    
    try:
        # Анализируем категории через Groq
        categories = await groq_service.analyze_categories(products)
        
        await wait_msg.delete()
        
        if not categories:
            await message.answer(
                "🤔 <b>Не удалось определить подходящие категории.</b>\n\n"
                "Возможно, в списке продуктов есть опечатки или неясные названия.\n"
                "Попробуйте уточнить список продуктов.",
                parse_mode="HTML"
            )
            return
        
        # Сохраняем категории в сессии
        session_data = user_data.get('session_json', {})
        session_data['categories'] = categories
        await supabase_service.update_user_session(user_id, session_data)
        
        # Если категория только одна - сразу показываем блюда
        if len(categories) == 1:
            await show_dishes_for_category(message, user_id, products, categories[0])
        else:
            # Показываем выбор категорий
            await message.answer(
                "📂 <b>Выберите категорию блюд:</b>\n\n"
                f"<i>На основе ваших продуктов: {html.quote(products[:100])}{'...' if len(products) > 100 else ''}</i>",
                reply_markup=get_categories_keyboard(categories),
                parse_mode="HTML"
            )
            
    except Exception as e:
        await wait_msg.delete()
        logger.error(f"Ошибка анализа категорий: {e}")
        await message.answer(
            "❌ <b>Ошибка при анализе продуктов.</b>\n"
            "Попробуйте еще раз или уточните список продуктов.",
            parse_mode="HTML"
        )

async def show_dishes_for_category(message: Message, user_id: int, products: str, category: str):
    """Показывает список блюд для выбранной категории"""
    cat_name = CATEGORY_MAP.get(category, category.capitalize())
    
    # Сообщение о подборе блюд
    wait_msg = await message.answer(f"🍳 <i>Подбираю {cat_name.lower()}...</i>", parse_mode="HTML")
    
    try:
        # Генерируем список блюд через Groq
        dishes_list = await groq_service.generate_dishes_list(products, category)
        
        await wait_msg.delete()
        
        if not dishes_list:
            await message.answer(
                f"😔 <b>Не удалось придумать {cat_name.lower()} из ваших продуктов.</b>\n\n"
                "Попробуйте другую категорию или дополните список продуктов.",
                parse_mode="HTML"
            )
            return
        
        # Сохраняем блюда в сессии
        user_data = await supabase_service.get_user(user_id)
        session_data = user_data.get('session_json', {})
        session_data['generated_dishes'] = dishes_list
        await supabase_service.update_user_session(user_id, session_data)
        
        # Формируем сообщение со списком блюд
        response_text = f"🍽 <b>Меню: {cat_name}</b>\n\n"
        
        for i, dish in enumerate(dishes_list, 1):
            response_text += f"{i}. <b>{html.quote(dish['name'])}</b>\n"
            response_text += f"<i>{html.quote(dish['desc'])}</i>\n\n"
        
        response_text += "👇 <b>Выберите блюдо для получения рецепта:</b>"
        
        # Отправляем сообщение с клавиатурой
        await message.answer(response_text, 
                           reply_markup=get_dishes_keyboard(dishes_list), 
                           parse_mode="HTML")
        
    except Exception as e:
        await wait_msg.delete()
        logger.error(f"Ошибка генерации списка блюд для категории {category}: {e}")
        await message.answer(
            f"❌ <b>Ошибка при подборе {cat_name.lower()}.</b>\n"
            "Попробуйте другую категорию.",
            parse_mode="HTML"
        )

async def generate_and_send_recipe(message: Message, user_id: int, dish_name: str):
    """Генерирует и отправляет рецепт выбранного блюда"""
    # Сообщение о начале генерации
    wait_msg = await message.answer(f"👨‍🍳 <i>Пишу рецепт: <b>{html.quote(dish_name)}</b>...</i>", 
                                  parse_mode="HTML")
    
    try:
        # Получаем продукты пользователя
        user_data = await supabase_service.get_user(user_id)
        products = user_data.get('products', '')
        
        # Генерируем рецепт через Groq
        recipe = await groq_service.generate_recipe(dish_name, products)
        
        await wait_msg.delete()
        
        # Сохраняем рецепт во временные данные
        session_data = user_data.get('session_json', {})
        session_data['temp_recipe'] = {
            'name': dish_name,
            'text': recipe,
            'products': products,
            'visual': dish_name  # Для генерации изображений
        }
        await supabase_service.update_user_session(user_id, session_data)
        await supabase_service.update_user_state(user_id, "recipe_sent")
        
        # Отправляем рецепт
        await message.answer(recipe, 
                           reply_markup=get_recipe_keyboard(show_save=True, dish_name=dish_name), 
                           parse_mode="HTML")
        
    except Exception as e:
        await wait_msg.delete()
        logger.error(f"Ошибка генерации рецепта для '{dish_name}': {e}")
        await message.answer(
            "❌ <b>Не удалось сгенерировать рецепт.</b>\n"
            "Попробуйте выбрать другое блюдо.",
            parse_mode="HTML"
        )

# --- ГЕНЕРАЦИЯ ИЗОБРАЖЕНИЙ ---

async def handle_generate_image(callback: CallbackQuery):
    """Обработчик генерации изображения для блюда"""
    user_id = callback.from_user.id
    
    # Получаем данные пользователя
    user_data = await supabase_service.get_user(user_id)
    session_data = user_data.get('session_json', {})
    temp_recipe = session_data.get('temp_recipe')
    
    if not temp_recipe:
        await callback.answer("❌ Нет данных о рецепте. Сначала получите рецепт.", show_alert=True)
        return
    
    dish_name = temp_recipe.get('name')
    recipe_text = temp_recipe.get('text', '')
    visual_desc = temp_recipe.get('visual', dish_name)
    
    # Уведомляем пользователя о начале генерации
    await callback.answer("🎨 Начинаю генерацию изображения... (это займет 15-30 секунд)")
    
    # Сообщение о процессе генерации
    wait_msg = await callback.message.answer(f"🎨 <i>Генерирую изображение для: <b>{html.quote(dish_name)}</b>...</i>\n\n"
                                           f"<i>Используется AI: Gemini + Replicate</i>\n"
                                           f"<i>Время ожидания: 15-30 секунд</i>", 
                                           parse_mode="HTML")
    
    try:
        # Генерируем изображение через наш сервис
        image_bytes = await image_service.generate_dish_image(
            dish_name=dish_name,
            recipe_text=recipe_text,
            visual_desc=visual_desc
        )
        
        await wait_msg.delete()
        
        if image_bytes:
            # Сохраняем base64 изображения в сессии для будущего сохранения
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            session_data['temp_recipe']['image_base64'] = image_base64
            await supabase_service.update_user_session(user_id, session_data)
            
            # Отправляем изображение
            await callback.message.reply_photo(
                BufferedInputFile(image_bytes, filename=f"{dish_name[:50]}.jpg"),
                caption=f"📸 <b>{html.quote(dish_name)}</b>\n\n"
                       f"<i>Сгенерировано искусственным интеллектом</i>",
                parse_mode="HTML"
            )
            
            logger.info(f"✅ Изображение сгенерировано для: {dish_name}")
            
        else:
            await callback.message.answer(
                "😔 <b>Не удалось сгенерировать изображение.</b>\n\n"
                "Возможные причины:\n"
                "• Ограничение дневного лимита генерации\n"
                "• Слишком сложное описание блюда\n"
                "• Технические проблемы с сервисами генерации\n\n"
                "Попробуйте еще раз позже или выберите другое блюдо.",
                parse_mode="HTML"
            )
            
    except Exception as e:
        await wait_msg.delete()
        logger.error(f"Ошибка генерации изображения для '{dish_name}': {e}")
        await callback.message.answer(
            "❌ <b>Ошибка при генерации изображения.</b>\n"
            "Попробуйте еще раз или выберите другое блюдо.",
            parse_mode="HTML"
        )

# --- СОХРАНЕНИЕ РЕЦЕПТОВ ---

async def handle_save_recipe(callback: CallbackQuery):
    """Обработчик сохранения рецепта в избранное"""
    user_id = callback.from_user.id
    
    # Получаем данные пользователя
    user_data = await supabase_service.get_user(user_id)
    session_data = user_data.get('session_json', {})
    temp_recipe = session_data.get('temp_recipe')
    
    if not temp_recipe:
        await callback.answer("❌ Нет данных о рецепте.", show_alert=True)
        return
    
    dish_name = temp_recipe.get('name')
    recipe_text = temp_recipe.get('text', '')
    products = temp_recipe.get('products', '')
    image_base64 = temp_recipe.get('image_base64')
    
    # Проверяем, не сохранен ли уже этот рецепт
    exists = await supabase_service.check_recipe_exists(user_id, dish_name)
    if exists:
        await callback.answer("⚠️ Этот рецепт уже сохранен!", show_alert=True)
        return
    
    # Сохраняем рецепт
    recipe_id = await supabase_service.add_favorite(
        user_id=user_id,
        dish_name=dish_name,
        recipe_text=recipe_text,
        products_snapshot=products,
        image_base64=image_base64
    )
    
    if recipe_id:
        await callback.answer("✅ Рецепт сохранен в избранное!")
        
        # Обновляем клавиатуру (убираем кнопку сохранения)
        await callback.message.edit_reply_markup(
            reply_markup=get_recipe_keyboard(show_save=False, dish_name=dish_name)
        )
    else:
        await callback.answer("❌ Ошибка сохранения рецепта", show_alert=True)

# --- РАБОТА С ИЗБРАННЫМ ---

async def handle_show_favorite(callback: CallbackQuery):
    """Показывает сохраненный рецепт из избранного"""
    user_id = callback.from_user.id
    recipe_id = callback.data.split("_")[1]
    
    # Получаем рецепт из БД
    favorite = await supabase_service.get_favorite_by_id(user_id, recipe_id)
    
    if not favorite:
        await callback.answer("❌ Рецепт не найден.", show_alert=True)
        return
    
    dish_name = favorite.get('dish_name')
    recipe_text = favorite.get('recipe_text')
    image_base64 = favorite.get('image_base64')
    
    # Если есть изображение - отправляем с ним
    if image_base64:
        try:
            image_bytes = base64.b64decode(image_base64)
            
            # Разбиваем длинный рецепт на части
            if len(recipe_text) > 1024:
                caption = f"📂 <b>{html.quote(dish_name)}</b>\n\n{recipe_text[:1000]}..."
                recipe_rest = recipe_text[1000:]
                
                # Отправляем фото с первой частью рецепта
                await callback.message.answer_photo(
                    BufferedInputFile(image_bytes, filename="saved_dish.jpg"),
                    caption=caption,
                    parse_mode="HTML",
                    reply_markup=get_recipe_keyboard(show_save=False, delete_id=recipe_id, dish_name=dish_name)
                )
                
                # Отправляем остаток рецепта отдельным сообщением
                if recipe_rest:
                    await callback.message.answer(
                        recipe_rest,
                        parse_mode="HTML"
                    )
            else:
                # Весь рецепт помещается в caption
                await callback.message.answer_photo(
                    BufferedInputFile(image_bytes, filename="saved_dish.jpg"),
                    caption=f"📂 <b>{html.quote(dish_name)}</b>\n\n{recipe_text}",
                    parse_mode="HTML",
                    reply_markup=get_recipe_keyboard(show_save=False, delete_id=recipe_id, dish_name=dish_name)
                )
                
        except Exception as e:
            logger.error(f"Ошибка отправки изображения из избранного: {e}")
            # Если ошибка с изображением - отправляем только текст
            await callback.message.answer(
                f"📂 <b>{html.quote(dish_name)}</b>\n\n{recipe_text}",
                parse_mode="HTML",
                reply_markup=get_recipe_keyboard(show_save=False, delete_id=recipe_id, dish_name=dish_name)
            )
    else:
        # Без изображения
        await callback.message.answer(
            f"📂 <b>{html.quote(dish_name)}</b>\n\n{recipe_text}",
            parse_mode="HTML",
            reply_markup=get_recipe_keyboard(show_save=False, delete_id=recipe_id, dish_name=dish_name)
        )

async def handle_delete_favorite(callback: CallbackQuery):
    """Удаляет рецепт из избранного"""
    user_id = callback.from_user.id
    recipe_id = callback.data.split("_")[2]  # delete_fav_{id}
    
    # Удаляем рецепт
    success = await supabase_service.delete_favorite(user_id, recipe_id)
    
    if success:
        await callback.answer("✅ Рецепт удален из избранного")
        
        # Возвращаемся к списку избранного
        favorites = await supabase_service.get_favorites(user_id)
        
        if favorites:
            await callback.message.edit_text(
                "📂 <b>Ваши сохраненные рецепты:</b>",
                reply_markup=get_favorites_keyboard(favorites),
                parse_mode="HTML"
            )
        else:
            await callback.message.edit_text(
                "📂 <b>Сохраненные рецепты отсутствуют.</b>",
                parse_mode="HTML"
            )
    else:
        await callback.answer("❌ Ошибка удаления рецепта", show_alert=True)

# --- ОБРАБОТКА CALLBACK-ЗАПРОСОВ ---

async def handle_callback(callback: CallbackQuery):
    """Главный обработчик callback-запросов"""
    user_id = callback.from_user.id
    data = callback.data
    
    try:
        # 1. Удаление сообщения
        if data == "delete_msg":
            await callback.message.delete()
            return
        
        # 2. Сброс сессии
        if data == "restart":
            await supabase_service.update_user_state(user_id, None)
            await supabase_service.update_user_products(user_id, None)
            await callback.message.answer("🔄 <b>Сессия сброшена.</b>\nЖду список продуктов! 🍏", 
                                        parse_mode="HTML")
            await callback.answer()
            return
        
        # 3. Добавить больше продуктов
        if data == "action_add_more":
            await callback.message.answer("➕ <b>Напишите или продиктуйте, что добавить:</b>", 
                                        parse_mode="HTML")
            await callback.answer()
            return
        
        # 4. Начать готовить (переход к категориям)
        if data == "action_cook":
            await callback.message.delete()
            await start_category_flow(callback.message, user_id)
            await callback.answer()
            return
        
        # 5. Выбор категории
        if data.startswith("cat_"):
            category = data.split("_")[1]
            user_data = await supabase_service.get_user(user_id)
            products = user_data.get('products')
            
            if not products:
                await callback.answer("❌ Сначала введите продукты.", show_alert=True)
                return
            
            await callback.answer(f"Выбрано: {CATEGORY_MAP.get(category, category)}")
            await callback.message.delete()
            await show_dishes_for_category(callback.message, user_id, products, category)
            return
        
        # 6. Назад к категориям
        if data == "back_to_categories":
            user_data = await supabase_service.get_user(user_id)
            session_data = user_data.get('session_json', {})
            categories = session_data.get('categories', [])
            
            if categories:
                await callback.message.delete()
                await callback.message.answer(
                    "📂 <b>Выберите категорию:</b>",
                    reply_markup=get_categories_keyboard(categories),
                    parse_mode="HTML"
                )
            await callback.answer()
            return
        
        # 7. Выбор блюда из списка
        if data.startswith("dish_"):
            try:
                index = int(data.split("_")[1])
                user_data = await supabase_service.get_user(user_id)
                session_data = user_data.get('session_json', {})
                dishes = session_data.get('generated_dishes', [])
                
                if 0 <= index < len(dishes):
                    dish_name = dishes[index]['name']
                    await callback.answer(f"Выбрано: {dish_name[:30]}...")
                    await generate_and_send_recipe(callback.message, user_id, dish_name)
                else:
                    await callback.answer("❌ Блюдо не найдено.", show_alert=True)
                    
            except (ValueError, IndexError) as e:
                await callback.answer("❌ Ошибка выбора блюда.", show_alert=True)
                logger.error(f"Ошибка выбора блюда: {e}")
            return
        
        # 8. Генерация изображения
        if data == "gen_photo":
            await handle_generate_image(callback)
            return
        
        # 9. Сохранение рецепта
        if data == "save_recipe":
            await handle_save_recipe(callback)
            return
        
        # 10. Показать список избранного
        if data == "my_recipes_list":
            await callback.message.delete()
            await cmd_my_recipes(callback.message)
            await callback.answer()
            return
        
        # 11. Показать конкретный рецепт из избранного
        if data.startswith("fav_"):
            await handle_show_favorite(callback)
            return
        
        # 12. Удаление рецепта из избранного
        if data.startswith("delete_fav_"):
            await handle_delete_favorite(callback)
            return
        
        # Неизвестный callback
        logger.warning(f"Неизвестный callback: {data}")
        await callback.answer("❌ Неизвестная команда")
        
    except Exception as e:
        logger.error(f"Ошибка обработки callback {data}: {e}", exc_info=True)
        await callback.answer("❌ Произошла ошибка. Попробуйте еще раз.", show_alert=True)

# --- РЕГИСТРАЦИЯ ХЭНДЛЕРОВ ---

def register_handlers(dp: Dispatcher):
    """Регистрирует все обработчики"""
    
    # Команды
    dp.message.register(cmd_start, Command("start"))
    dp.message.register(cmd_author, Command("author"))
    dp.message.register(cmd_my_recipes, Command("my_recipes"))
    dp.message.register(cmd_stats, Command("stats"))
    
    # Текстовые сообщения
    dp.message.register(handle_direct_recipe, F.text.lower().startswith("дай рецепт"))
    dp.message.register(handle_voice, F.voice)
    dp.message.register(handle_text, F.text)
    
    # Callback-запросы
    dp.callback_query.register(handle_callback)