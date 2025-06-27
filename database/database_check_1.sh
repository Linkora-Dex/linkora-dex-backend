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


echo "🔍 Проверка событий ордеров в БД"

# Проверяем структуру таблицы order_events
echo "=== Структура таблицы order_events ==="
docker exec -it crypto_timescaledb psql -U crypto_user -d crypto_data -c "\d order_events"

# Проверяем есть ли события для конкретного ордера
echo "=== События для ордера 15 ==="
docker exec -it crypto_timescaledb psql -U crypto_user -d crypto_data -c "
SELECT * FROM order_events WHERE order_id = 15;
"

# Проверяем все события
echo "=== Все события в БД ==="
docker exec -it crypto_timescaledb psql -U crypto_user -d crypto_data -c "
SELECT order_id, event_type, old_status, new_status, timestamp
FROM order_events
ORDER BY timestamp DESC;
"

# Добавляем тестовое событие для проверки API
echo "=== Добавление тестового события ==="
docker exec -it crypto_timescaledb psql -U crypto_user -d crypto_data -c "
INSERT INTO order_events (order_id, event_type, old_status, new_status, event_data)
VALUES (15, 'ORDER_CREATED', NULL, 'PENDING', '{\"test\": \"data\"}');
"

echo "=== Проверка добавленного события ==="
docker exec -it crypto_timescaledb psql -U crypto_user -d crypto_data -c "
SELECT * FROM order_events WHERE order_id = 15;
"