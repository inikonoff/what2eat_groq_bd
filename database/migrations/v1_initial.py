"""
Первоначальная миграция для создания всех таблиц
"""

MIGRATION_SQL = """
-- Пользователи
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    username VARCHAR(255),
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    language_code VARCHAR(10) DEFAULT 'ru',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_active TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_premium BOOLEAN DEFAULT FALSE,
    settings JSONB DEFAULT '{}'
);

-- Сессии пользователей
CREATE TABLE IF NOT EXISTS user_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_id VARCHAR(100) UNIQUE NOT NULL,
    products TEXT,
    state VARCHAR(50),
    categories JSONB,
    generated_dishes JSONB,
    current_dish VARCHAR(255),
    history JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() + INTERVAL '1 hour',
    CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Рецепты
CREATE TABLE IF NOT EXISTS recipes (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    dish_name VARCHAR(255) NOT NULL,
    recipe_text TEXT NOT NULL,
    products_used TEXT,
    category VARCHAR(50),
    language VARCHAR(10) DEFAULT 'ru',
    is_favorite BOOLEAN DEFAULT FALSE,
    is_ai_generated BOOLEAN DEFAULT TRUE,
    cooking_time_minutes INTEGER,
    difficulty_level VARCHAR(20),
    servings INTEGER,
    nutrition_info JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Изображения блюд
CREATE TABLE IF NOT EXISTS dish_images (
    id SERIAL PRIMARY KEY,
    recipe_id INTEGER REFERENCES recipes(id) ON DELETE CASCADE,
    image_url VARCHAR(500) NOT NULL,
    storage_type VARCHAR(20) DEFAULT 'replicate', -- replicate, unsplash, uploaded
    prompt_used TEXT,
    model_name VARCHAR(100),
    image_hash VARCHAR(64), -- для дедупликации
    width INTEGER,
    height INTEGER,
    file_size_bytes INTEGER,
    is_primary BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT fk_recipe FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
);

-- Избранные рецепты
CREATE TABLE IF NOT EXISTS favorite_recipes (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    recipe_id INTEGER NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, recipe_id),
    CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_recipe FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
);

-- Метрики использования
CREATE TABLE IF NOT EXISTS usage_metrics (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    metric_type VARCHAR(50) NOT NULL, -- 'groq_request', 'image_generation', 'recipe_view'
    service_name VARCHAR(50), -- 'groq', 'replicate', 'unsplash'
    details JSONB,
    tokens_used INTEGER,
    cost_units DECIMAL(10,6),
    response_time_ms INTEGER,
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- История поиска
CREATE TABLE IF NOT EXISTS search_history (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    search_query TEXT NOT NULL,
    search_type VARCHAR(50), -- 'ingredients', 'dish_name', 'category'
    results_count INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Индексы для производительности
CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id);
CREATE INDEX IF NOT EXISTS idx_users_last_active ON users(last_active);
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON user_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_expires_at ON user_sessions(expires_at);
CREATE INDEX IF NOT EXISTS idx_recipes_user_id ON recipes(user_id);
CREATE INDEX IF NOT EXISTS idx_recipes_created_at ON recipes(created_at);
CREATE INDEX IF NOT EXISTS idx_recipes_is_favorite ON recipes(is_favorite);
CREATE INDEX IF NOT EXISTS idx_favorites_user_id ON favorite_recipes(user_id);
CREATE INDEX IF NOT EXISTS idx_metrics_user_id ON usage_metrics(user_id);
CREATE INDEX IF NOT EXISTS idx_metrics_created_at ON usage_metrics(created_at);
CREATE INDEX IF NOT EXISTS idx_search_history_user_id ON search_history(user_id);

-- Триггер для обновления updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_user_sessions_updated_at 
    BEFORE UPDATE ON user_sessions 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_recipes_updated_at 
    BEFORE UPDATE ON recipes 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
"""

async def run_migration():
    """Запуск миграции"""
    from database.connection import DatabaseConnection
    
    async with DatabaseConnection.acquire_connection() as conn:
        # Разделяем SQL на отдельные выражения
        statements = MIGRATION_SQL.split(';')
        for statement in statements:
            statement = statement.strip()
            if statement:
                try:
                    await conn.execute(statement)
                except Exception as e:
                    print(f"Warning: Could not execute statement: {e}")
                    continue
    
    print("✅ Миграция v1 успешно выполнена")
