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

# setup_monitoring.sh - Создание всех диагностических скриптов

echo "Создание диагностических скриптов..."

# 1. Быстрая проверка
cat > quick_check.sh << 'EOF'
#!/bin/bash
echo "=== БЫСТРАЯ ДИАГНОСТИКА ==="
echo "1. Статус контейнеров:"
docker-compose ps
echo "2. Подключение к БД:"
docker exec crypto_timescaledb pg_isready -U crypto_user -d crypto_data
echo "3. Таблицы в БД:"
docker exec crypto_timescaledb psql -U crypto_user -d crypto_data -c "\dt"
echo "4. API health check:"
curl -s "http://localhost:8022/health" | jq . 2>/dev/null || curl -s "http://localhost:8022/health"
echo "=== КОНЕЦ БЫСТРОЙ ДИАГНОСТИКИ ==="
EOF

# 2. Проверка соединений
cat > db_connections_check.sh << 'EOF'
#!/bin/bash
echo "=== ДИАГНОСТИКА СОЕДИНЕНИЙ БД ==="
echo "1. Активные соединения:"
docker exec crypto_timescaledb psql -U crypto_user -d crypto_data -c "
SELECT pid, state, query_start, application_name,
       CASE WHEN length(query) > 50 THEN substring(query, 1, 50) || '...' ELSE query END as query_short
FROM pg_stat_activity
WHERE datname = 'crypto_data'
ORDER BY state, query_start;
"
echo "2. Зависшие транзакции:"
docker exec crypto_timescaledb psql -U crypto_user -d crypto_data -c "
SELECT pid, state, query_start, now() - query_start as duration
FROM pg_stat_activity
WHERE datname = 'crypto_data' AND state = 'idle in transaction'
ORDER BY query_start;
"
echo "=== КОНЕЦ ДИАГНОСТИКИ СОЕДИНЕНИЙ ==="
EOF

# 3. Проверка данных
cat > data_check.sh << 'EOF'
#!/bin/bash
echo "=== ДИАГНОСТИКА ДАННЫХ ==="
echo "1. Количество записей в таблицах:"
docker exec crypto_timescaledb psql -U crypto_user -d crypto_data -c "
SELECT
    'candles' as table_name, COUNT(*) as records,
    MIN(timestamp) as min_timestamp, MAX(timestamp) as max_timestamp
FROM candles
UNION ALL
SELECT
    'orderbook_data' as table_name, COUNT(*) as records,
    MIN(timestamp) as min_timestamp, MAX(timestamp) as max_timestamp
FROM orderbook_data
UNION ALL
SELECT
    'collector_state' as table_name, COUNT(*) as records,
    NULL as min_timestamp, NULL as max_timestamp
FROM collector_state;
"
echo "2. Последние записи orderbook по символам:"
docker exec crypto_timescaledb psql -U crypto_user -d crypto_data -c "
SELECT symbol, COUNT(*) as records, MAX(timestamp) as last_update,
       EXTRACT(epoch FROM (NOW() - to_timestamp(MAX(timestamp)/1000))) as seconds_ago
FROM orderbook_data
GROUP BY symbol
ORDER BY symbol;
"
echo "=== КОНЕЦ ДИАГНОСТИКИ ДАННЫХ ==="
EOF

# 4. Проверка API
cat > api_check.sh << 'EOF'
#!/bin/bash
echo "=== ДИАГНОСТИКА API ==="
echo "1. Health check:"
curl -s "http://localhost:8022/health" | jq . 2>/dev/null || curl -s "http://localhost:8022/health"
echo "2. Symbols endpoint:"
curl -s "http://localhost:8022/symbols" | jq '.symbols | length' 2>/dev/null || echo "API error"
echo "3. Orderbook для всех символов:"
for symbol in BTCUSDT ETHUSDT SOLUSDT XRPUSDT BNBUSDT; do
    echo -n "$symbol: "
    response=$(curl -s "http://localhost:8022/orderbook?symbol=$symbol&levels=5")
    if echo "$response" | jq -e '.symbol' >/dev/null 2>&1; then
        echo "✅ OK"
    else
        echo "❌ $(echo "$response" | jq -r '.error' 2>/dev/null || echo 'API Error')"
    fi
done
echo "=== КОНЕЦ ДИАГНОСТИКИ API ==="
EOF

# 5. Мониторинг роста данных
cat > monitor_growth.sh << 'EOF'
#!/bin/bash
echo "Мониторинг роста данных каждые 30 секунд..."
while true; do
    echo "=== $(date) ==="
    docker exec crypto_timescaledb psql -U crypto_user -d crypto_data -c "
    SELECT 'orderbook' as type, COUNT(*) as records FROM orderbook_data
    UNION ALL
    SELECT 'candles' as type, COUNT(*) as records FROM candles;
    "
    sleep 30
done
EOF

# 6. Скрипт экстренного восстановления
cat > emergency_fix.sh << 'EOF'
#!/bin/bash
echo "=== ЭКСТРЕННОЕ ВОССТАНОВЛЕНИЕ ==="

echo "1. Завершение зависших транзакций..."
docker exec crypto_timescaledb psql -U crypto_user -d crypto_data -c "
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = 'crypto_data' AND state LIKE '%transaction%';
"

echo "2. Перезапуск data-collector..."
docker-compose restart data-collector

echo "3. Ожидание 30 секунд..."
sleep 30

echo "4. Проверка восстановления..."
./quick_check.sh

echo "=== КОНЕЦ ЭКСТРЕННОГО ВОССТАНОВЛЕНИЯ ==="
EOF

# 7. Полная диагностика
cat > full_diagnostics.sh << 'EOF'
#!/bin/bash
echo "=================================================================================="
echo "ПОЛНАЯ ДИАГНОСТИКА СИСТЕМЫ - $(date)"
echo "=================================================================================="

./quick_check.sh
echo ""
./db_connections_check.sh
echo ""
./data_check.sh
echo ""
./api_check.sh

echo ""
echo "=================================================================================="
echo "ДИАГНОСТИКА ЗАВЕРШЕНА - $(date)"
echo "=================================================================================="
EOF

# Установка прав на выполнение
chmod +x *.sh

echo "✅ Созданы диагностические скрипты:"
echo "   - quick_check.sh (быстрая проверка)"
echo "   - db_connections_check.sh (соединения БД)"
echo "   - data_check.sh (проверка данных)"
echo "   - api_check.sh (проверка API)"
echo "   - monitor_growth.sh (мониторинг роста)"
echo "   - emergency_fix.sh (экстренное восстановление)"
echo "   - full_diagnostics.sh (полная диагностика)"
echo ""
echo "Использование:"
echo "   ./quick_check.sh              # Быстрая проверка"
echo "   ./full_diagnostics.sh         # Полная диагностика"
echo "   ./emergency_fix.sh            # При проблемах"
echo "   ./monitor_growth.sh           # Мониторинг в реальном времени"