#!/bin/bash

# Copyright (C) 2025 Linkora DEX
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
#
# For commercial licensing, contact: licensing@linkora.info


# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функция для выполнения SQL запросов
execute_sql() {
    local query="$1"
    local description="$2"

    echo -e "${BLUE}=== $description ===${NC}"
    docker exec -it crypto_timescaledb psql -U crypto_user -d crypto_data -c "$query"
    echo ""
}

# Функция для выполнения тихих SQL запросов (только результат)
execute_sql_quiet() {
    local query="$1"
    docker exec -it crypto_timescaledb psql -U crypto_user -d crypto_data -t -c "$query" 2>/dev/null | tr -d ' '
}

echo -e "${GREEN}🔍 Проверка схемы базы данных${NC}"
echo "========================================"

# 1. Проверка структуры таблицы orders
execute_sql "
SELECT
    column_name,
    data_type,
    column_default,
    is_nullable,
    character_maximum_length
FROM information_schema.columns
WHERE table_name = 'orders'
ORDER BY ordinal_position;
" "Структура таблицы orders"

# 2. Проверка ограничений CHECK
execute_sql "
SELECT
    constraint_name,
    check_clause
FROM information_schema.check_constraints
WHERE constraint_name LIKE '%order%' OR constraint_name LIKE '%status%';
" "Ограничения CHECK для orders"

# 3. Проверка индексов
execute_sql "
SELECT
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'orders';
" "Индексы таблицы orders"

# 4. Проверка данных - типы ордеров
execute_sql "
SELECT
    order_type,
    COUNT(*) as count
FROM orders
GROUP BY order_type
ORDER BY count DESC;
" "Распределение типов ордеров"

# 5. Проверка данных - статусы ордеров
execute_sql "
SELECT
    status,
    COUNT(*) as count
FROM orders
GROUP BY status
ORDER BY count DESC;
" "Распределение статусов ордеров"

# 6. Проверка научной нотации в числах
execute_sql "
SELECT
    id,
    amount_in,
    amount_in::text as amount_text,
    target_price,
    target_price::text as price_text,
    min_amount_out,
    min_amount_out::text as min_out_text
FROM orders
LIMIT 3;
" "Примеры числовых полей (научная нотация)"

# 7. Проверка NULL значений
execute_sql "
SELECT
    COUNT(*) as total_orders,
    COUNT(executed_at) as with_executed_at,
    COUNT(*) - COUNT(executed_at) as null_executed_at
FROM orders;
" "Статистика NULL значений"

# 8. Проверка размеров данных
execute_sql "
SELECT
    pg_size_pretty(pg_total_relation_size('orders')) as table_size,
    COUNT(*) as total_rows
FROM orders;
" "Размер таблицы orders"

# 9. Проверка последних записей
execute_sql "
SELECT
    id,
    user_address,
    order_type,
    status,
    created_at
FROM orders
ORDER BY created_at DESC
LIMIT 5;
" "Последние 5 ордеров"

# 10. Проверка проблемных данных
echo -e "${YELLOW}🔍 Поиск потенциальных проблем...${NC}"

# Проверяем есть ли STOP_LOSS вместо STOP
STOP_LOSS_COUNT=$(execute_sql_quiet "SELECT COUNT(*) FROM orders WHERE order_type = 'STOP_LOSS';")
if [ "$STOP_LOSS_COUNT" -gt 0 ]; then
    echo -e "${RED}⚠️  Найдено $STOP_LOSS_COUNT ордеров с типом 'STOP_LOSS' (должно быть 'STOP')${NC}"

    echo -e "${YELLOW}Хотите исправить? (y/n):${NC}"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        execute_sql "UPDATE orders SET order_type = 'STOP' WHERE order_type = 'STOP_LOSS';" "Исправление STOP_LOSS → STOP"
        echo -e "${GREEN}✅ Исправлено!${NC}"
    fi
else
    echo -e "${GREEN}✅ Типы ордеров корректны${NC}"
fi

# Проверяем есть ли неизвестные статусы
execute_sql "
SELECT DISTINCT status
FROM orders
WHERE status NOT IN ('PENDING', 'EXECUTED', 'CANCELLED', 'FAILED');
" "Неизвестные статусы (если есть)"

echo -e "${GREEN}🏁 Проверка завершена${NC}"