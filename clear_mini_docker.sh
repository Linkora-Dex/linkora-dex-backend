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


PROJECT_NAME="linkora-dex-backend"
COMPOSE_FILE="docker-compose.yml"

echo "Stopping and removing containers..."
docker-compose -f $COMPOSE_FILE down --remove-orphans

echo "Removing project containers (if any remain)..."
docker ps -a --filter "name=crypto_" --format "{{.ID}}" | xargs -r docker rm -f

echo "Removing project images..."
docker images --filter "reference=${PROJECT_NAME}*" --format "{{.ID}}" | xargs -r docker rmi -f

echo "Removing project volumes..."
docker volume ls --filter "name=${PROJECT_NAME}" --format "{{.Name}}" | xargs -r docker volume rm

echo "Removing project network..."
docker network ls --filter "name=${PROJECT_NAME}" --format "{{.Name}}" | xargs -r docker network rm

echo "Cleaning up unused Docker resources..."
docker system prune -f --volumes

echo "Cleanup completed"