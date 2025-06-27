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


API_BASE="http://localhost:8080"
USER_ADDRESS="0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC"
ORDER_ID="15"

echo "🔍 Тестирование API эндпоинтов Linkora DEX Order System"
echo "=================================================="
echo ""

echo "📊 1. Проверка статистики"
echo "curl $API_BASE/statistics"
curl -s "$API_BASE/statistics" | jq '.'
echo ""
echo "=================================================="

echo "🏥 2. Проверка здоровья системы"
echo "curl $API_BASE/health"
curl -s "$API_BASE/health" | jq '.'
echo ""
echo "=================================================="

echo "📋 3. PENDING ордера (без пагинации)"
echo "curl $API_BASE/orders/pending"
curl -s "$API_BASE/orders/pending" | jq '.'
echo ""
echo "=================================================="

echo "📋 4. PENDING ордера с пагинацией (limit=2, offset=0)"
echo "curl '$API_BASE/orders/pending?limit=2&offset=0'"
curl -s "$API_BASE/orders/pending?limit=2&offset=0" | jq '.'
echo ""
echo "=================================================="

echo "📋 5. EXECUTED ордера"
echo "curl $API_BASE/orders/executed"
curl -s "$API_BASE/orders/executed" | jq '.'
echo ""
echo "=================================================="

echo "📋 6. EXECUTED ордера с пагинацией (limit=5, offset=0)"
echo "curl '$API_BASE/orders/executed?limit=5&offset=0'"
curl -s "$API_BASE/orders/executed?limit=5&offset=0" | jq '.'
echo ""
echo "=================================================="

echo "📋 7. CANCELLED ордера"
echo "curl $API_BASE/orders/cancelled"
curl -s "$API_BASE/orders/cancelled" | jq '.'
echo ""
echo "=================================================="

echo "📋 8. CANCELLED ордера с пагинацией (limit=3, offset=0)"
echo "curl '$API_BASE/orders/cancelled?limit=3&offset=0'"
curl -s "$API_BASE/orders/cancelled?limit=3&offset=0" | jq '.'
echo ""
echo "=================================================="

echo "📋 9. Все ордера без фильтра"
echo "curl $API_BASE/orders/all"
curl -s "$API_BASE/orders/all" | jq '.'
echo ""
echo "=================================================="

echo "📋 10. Все ордера с фильтром по статусу PENDING"
echo "curl '$API_BASE/orders/all?status=pending'"
curl -s "$API_BASE/orders/all?status=pending" | jq '.'
echo ""
echo "=================================================="

echo "📋 11. Все ордера с фильтром по статусу EXECUTED и пагинацией"
echo "curl '$API_BASE/orders/all?status=executed&limit=10&offset=0'"
curl -s "$API_BASE/orders/all?status=executed&limit=10&offset=0" | jq '.'
echo ""
echo "=================================================="

echo "👤 12. Ордера пользователя (все статусы)"
echo "curl $API_BASE/users/$USER_ADDRESS/orders"
curl -s "$API_BASE/users/$USER_ADDRESS/orders" | jq '.'
echo ""
echo "=================================================="

echo "👤 13. Ордера пользователя с фильтром PENDING"
echo "curl '$API_BASE/users/$USER_ADDRESS/orders?status=pending'"
curl -s "$API_BASE/users/$USER_ADDRESS/orders?status=pending" | jq '.'
echo ""
echo "=================================================="

echo "👤 14. Ордера пользователя с фильтром EXECUTED и пагинацией"
echo "curl '$API_BASE/users/$USER_ADDRESS/orders?status=executed&limit=5&offset=0'"
curl -s "$API_BASE/users/$USER_ADDRESS/orders?status=executed&limit=5&offset=0" | jq '.'
echo ""
echo "=================================================="

echo "📄 15. Детали конкретного ордера"
echo "curl $API_BASE/orders/$ORDER_ID"
curl -s "$API_BASE/orders/$ORDER_ID" | jq '.'
echo ""
echo "=================================================="

echo "📝 16. События конкретного ордера"
echo "curl $API_BASE/orders/$ORDER_ID/events"
curl -s "$API_BASE/orders/$ORDER_ID/events" | jq '.'
echo ""
echo "=================================================="

echo "❌ 17. Тест несуществующего ордера (должен вернуть 404)"
echo "curl $API_BASE/orders/99999"
curl -s "$API_BASE/orders/99999" | jq '.'
echo ""
echo "=================================================="

echo "❌ 18. Тест невалидного статуса (должен вернуть 400)"
echo "curl '$API_BASE/orders/all?status=invalid_status'"
curl -s "$API_BASE/orders/all?status=invalid_status" | jq '.'
echo ""
echo "=================================================="

echo "❌ 19. Тест невалидного order_id (должен вернуть 400)"
echo "curl $API_BASE/orders/invalid_id"
curl -s "$API_BASE/orders/invalid_id" | jq '.'
echo ""
echo "=================================================="

echo "🔢 20. Тест граничных значений пагинации (limit=1001, должен ограничиться до 1000)"
echo "curl '$API_BASE/orders/pending?limit=1001&offset=0'"
curl -s "$API_BASE/orders/pending?limit=1001&offset=0" | jq '.limit'
echo ""
echo "=================================================="

echo "🔢 21. Тест отрицательного offset (должен стать 0)"
echo "curl '$API_BASE/orders/pending?limit=5&offset=-10'"
curl -s "$API_BASE/orders/pending?limit=5&offset=-10" | jq '.offset'
echo ""
echo "=================================================="

echo "📊 22. Проверка формата числовых значений (без научной нотации)"
echo "curl '$API_BASE/orders/pending?limit=1' | jq '.orders[0].min_amount_out'"
curl -s "$API_BASE/orders/pending?limit=1" | jq '.orders[0].min_amount_out // "no orders"'
echo ""
echo "=================================================="

echo "✅ Тестирование завершено!"
echo ""
echo "🔍 Дополнительные команды для ручной проверки:"
echo ""
echo "# Проверка производительности"
echo "time curl -s '$API_BASE/orders/all?limit=1000&offset=0' > /dev/null"
echo ""
echo "# Проверка headers ответа"
echo "curl -I '$API_BASE/health'"
echo ""
echo "# Красивый вывод JSON"
echo "curl -s '$API_BASE/statistics' | jq '.statistics'"
echo ""
echo "# Подсчет записей"
echo "curl -s '$API_BASE/orders/pending' | jq '.total'"
echo ""
echo "# Проверка пагинации has_more"
echo "curl -s '$API_BASE/orders/all?limit=1&offset=0' | jq '.has_more'"