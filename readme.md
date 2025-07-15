# Linkora DEX Backend Platform

High-performance platform for collecting, storing and providing cryptocurrency market data in real-time with DEX orders support, multiple timeframes and WebSocket connections.

## Platform Architecture

### Core Components
- **📊 Data Collector** - Asynchronous data collection from Binance API (candles, orderbook)
- **🚀 API Server** - REST API and WebSocket server with real-time aggregation
- **📋 Order System** - Microservice system for DEX orders processing
- **🗄️ TimescaleDB** - Optimized time series database
- **⚡ Redis** - Pub/sub broker for real-time notifications

### Technology Stack
- **Backend**: Python 3.11+ with asyncio
- **API Framework**: Starlette (ASGI)
- **Database**: TimescaleDB (PostgreSQL) + asyncpg
- **Cache & Pub/Sub**: Redis
- **Blockchain**: Web3.py for Ethereum/Hardhat
- **Containerization**: Docker & Docker Compose

### Architectural Diagram
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Data Collector│    │   API Server    │    │  Order System   │
│                 │    │                 │    │                 │
│ ┌─────────────┐ │    │ ┌─────────────┐ │    │ ┌─────────────┐ │
│ │   Source    │ │    │ │    REST     │ │    │ │   Event     │ │
│ │     API     │ │    │ │     API     │ │    │ │ Processor   │ │
│ └─────────────┘ │    │ └─────────────┘ │    │ └─────────────┘ │
│ ┌─────────────┐ │    │ ┌─────────────┐ │    │ ┌─────────────┐ │
│ │ OrderBook   │ │    │ │  WebSocket  │ │    │ │   Order     │ │
│ │ Collector   │ │    │ │   Manager   │ │    │ │     API     │ │
│ └─────────────┘ │    │ └─────────────┘ │    │ └─────────────┘ │
└─────────────────┘    └─────────────────┘    └─────────────────┘
        │                        │                        │
        └────────────────────────┼────────────────────────┘
                                 │
            ┌─────────────────────┼─────────────────────┐
            │                    │                     │
    ┌───────▼────────┐   ┌───────▼────────┐   ┌───────▼────────┐
    │  TimescaleDB   │   │     Redis      │   │   Blockchain   │
    │   (Primary)    │   │   (Pub/Sub)    │   │   (Hardhat)    │
    └────────────────┘   └────────────────┘   └────────────────┘
```

## Quick Start

### Requirements
- Docker & Docker Compose
- 4GB+ RAM
- 10GB+ free space

### Installation and Launch
```bash
# Repository cloning
git clone <repository-url>
cd Linkora-Dex-Backend

# Start all services
docker-compose up -d

# Check status
docker-compose ps

# Check system health
curl http://localhost:8022/health  # API Server
curl http://localhost:8080/health  # Order System
```

### Quick Functionality Check
```bash
# Crypto Data API
curl "http://localhost:8022/symbols"                    # Available symbols
curl "http://localhost:8022/candles?symbol=BTCUSDT"     # Candle data
curl "http://localhost:8022/orderbook?symbol=BTCUSDT"   # OrderBook data

# Order System API  
curl "http://localhost:8080/orders/pending"             # Pending orders
curl "http://localhost:8080/statistics"                 # Orders statistics
```

## Platform Services

### 📊 Data Collector Service
> **Port**: Internal service  
> **Purpose**: Data collection from Binance API  
> **Documentation**: [data-collector/readme.md](data-collector/readme.md)

**Main Functions**
- Asynchronous klines/candles data collection
- Parallel orderbook data collection
- Automatic state recovery
- Scientific notation normalization (5E-8 → 0.00000005)
- Real-time publishing to Redis

**Configuration**
```python
SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'BNBUSDT']
START_DATE = datetime(2025, 1, 1)
REALTIME_INTERVAL = 0.5  # seconds
ORDERBOOK_LEVELS = 20
```

**Working Algorithm**
1. **Historical mode** Data collection from START_DATE to current moment
2. **Real-time mode** Updates every 0.5 seconds
3. **Publishing** Redis channels `candles:all`, `orderbook:all`

---

### 🚀 API Server
> **Port**: 8022  
> **Purpose**: REST API + WebSocket server  
> **Documentation**: [api-server/readme.md](api-server/readme.md)

**REST API Endpoints**
```http
GET /health                              # System status
GET /symbols                             # Trading pairs list  
GET /candles?symbol=BTCUSDT&timeframe=1H # Candle data with aggregation
GET /orderbook?symbol=BTCUSDT&levels=10  # OrderBook data
GET /price?symbol=BTCUSDT&timeframe=1H   # Current price with analytics
```

**WebSocket API**
```javascript
// Real-time candles with timeframe aggregation
ws://localhost:8022/ws?symbol=BTCUSDT&timeframe=5&type=candles

// Real-time orderbook
ws://localhost:8022/ws?symbol=BTCUSDT&type=orderbook
```

**Supported Timeframes**
`1`, `3`, `5`, `15`, `30`, `45`, `1H`, `2H`, `3H`, `4H`, `1D`, `1W`, `1M`

**Key Features**
- Real-time aggregation of minute candles into larger timeframes
- WebSocket heartbeat protocol (30 sec)
- Automatic inactive connections cleanup
- TimescaleDB integration with connection pooling

---

### 📋 Order System  
> **Port**: 8080  
> **Purpose**: DEX orders processing  
> **Documentation**: [order_system/readme.md](order_system/readme.md)

**Microservices**
- **Order API** (port 8080) - REST API for orders
- **Event Processor** (internal) - Blockchain events scanner

**Order API Endpoints**
```http
GET /orders/pending?limit=100&offset=0                    # PENDING orders
GET /orders/executed?limit=100&offset=0                   # EXECUTED orders  
GET /orders/cancelled?limit=100&offset=0                  # CANCELLED orders
GET /users/{address}/orders?status=executed               # User orders
GET /orders/{id}                                          # Order details
GET /orders/{id}/events                                   # Order events
GET /statistics                                           # Orders statistics
```

**Event Processor Functions**
- Blockchain events scanning (OrderCreated, OrderExecuted, OrderCancelled)
- Parallel block processing during recovery
- Automatic recovery after failures (recovery mode)
- 100% event duplication prevention

**Order Schema**
```json
{
  "id": 5,
  "user_address": "0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC",
  "token_in": "0x0000000000000000000000000000000000000000",
  "token_out": "0xA51c1fc2f0D1a1b8494Ed1FE312d7C3a78Ed91C0",
  "amount_in": "0.05",
  "target_price": "0.8944299",
  "order_type": "LIMIT",
  "status": "EXECUTED",
  "created_at": "2025-06-07T09:38:39+00:00",
  "executed_at": "2025-06-07T09:35:52.244466+00:00"
}
```

## Database Schema

### TimescaleDB Tables

**Crypto Market Data**
```sql
-- Candle data (hypertable, compression 7 days)
candles (symbol, timestamp, OHLCV, trades, taker_buy_*)

-- OrderBook data (hypertable, compression 1 day)  
orderbook_data (symbol, timestamp, last_update_id, bids JSONB, asks JSONB)

-- Data collector state
collector_state (symbol, last_timestamp, is_realtime, last_updated)
```

**Order System Data**
```sql
-- Main order data
orders (id, user_address, token_in, token_out, amount_in, target_price, 
        order_type, status, created_at, executed_at, ...)

-- Order events history (hypertable)
order_events (order_id, event_type, old_status, new_status, timestamp, ...)

-- Blockchain scanner state
system_state (component_name, last_processed_block, status, updated_at)

-- Processed events (duplication prevention)
processed_events (tx_hash, log_index, event_type, processed_at)
```

## Configuration

### Environment Variables
```bash
# Database
DB_HOST=timescaledb
DB_PORT=5432
DB_NAME=crypto_data
DB_USER=crypto_user
DB_PASSWORD=crypto_password

# Redis
REDIS_HOST=redis
REDIS_PORT=6379

# API Servers
API_HOST=0.0.0.0
API_PORT=8000        # API Server
ORDER_API_PORT=8080  # Order System API

# Binance Data Collection
BINANCE_BASE_URL=https://api.binance.com
SYMBOLS=BTCUSDT,ETHUSDT,SOLUSDT,XRPUSDT,BNBUSDT
START_DATE=2025-01-01
REALTIME_INTERVAL=0.5

# Blockchain (Order System)
WEB3_PROVIDER=http://127.0.0.1:8545
TRADING_ADDRESS=0x...
ROUTER_ADDRESS=0x...
```

### Docker Compose Services
```yaml
services:
  timescaledb:       # Main database
  redis:             # Pub/sub and caching
  data-collector:    # Data collection from Binance  
  api-server:        # REST API + WebSocket (port 8022)
  order-api:         # Order System API (port 8080)
  order-events:      # Blockchain events processor
```

## Data Flow Architecture

### 1. Market Data Pipeline
```
Binance API → Data Collector → TimescaleDB → Redis pub/sub → API Server → WebSocket clients
```

### 2. Order Processing Pipeline  
```
Blockchain → Event Processor → TimescaleDB → Order API → REST clients
```

### 3. Real-time Aggregation
```
1m candles → CandleAggregator → 5m/1H/1D candles → WebSocket broadcast
```

## Monitoring & Diagnostics

### Health Checks
```bash
# All services
curl http://localhost:8022/health  # API Server
curl http://localhost:8080/health  # Order System

# Data check
docker exec crypto_timescaledb psql -U crypto_user -d crypto_data -c "
SELECT 'candles' as table_name, COUNT(*) FROM candles
UNION ALL  
SELECT 'orderbook_data', COUNT(*) FROM orderbook_data
UNION ALL
SELECT 'orders', COUNT(*) FROM orders;"
```

### Diagnostic Utilities
```bash
# Create monitoring scripts
./monitoring/setup_monitoring.sh

# Quick diagnostics
./quick_check.sh

# Full diagnostics
./full_diagnostics.sh

# For critical issues
./emergency_fix.sh
```

### Service Logs
```bash
# Real-time monitoring
docker-compose logs -f data-collector  # Data collection
docker-compose logs -f api-server      # API server
docker-compose logs -f order-events    # Blockchain scanner

# Error filtering
docker-compose logs data-collector | grep -E "(ERROR|WARN|orderbook)"
```

## Performance Features

### Database Optimization
- **TimescaleDB hypertables** with automatic partitioning
- **Connection pooling** (2-10 connections per service)
- **Data compression** 7 days (candles), 1 day (orderbook)
- **Indexes** by symbol, timestamp for fast queries

### Real-time Processing
- **Asynchronous architecture** with parallel processing
- **Redis pub/sub** for real-time notifications
- **WebSocket throttling** (5 sec update interval)
- **Batch operations** up to 1000 records per query

### Scalability
- **Horizontal scaling** through additional symbols
- **Microservice architecture** with independent components
- **Docker containers** for easy deployment
- **Load balancing** support for API endpoints

## API Examples

### Market Data API
```bash
# Get symbols
curl "http://localhost:8022/symbols"

# Hourly BTC candles
curl "http://localhost:8022/candles?symbol=BTCUSDT&timeframe=1H&limit=24"

# OrderBook with 10 levels
curl "http://localhost:8022/orderbook?symbol=ETHUSDT&levels=10"

# Current price with trend
curl "http://localhost:8022/price?symbol=BTCUSDT&timeframe=1H"
```

### Order System API
```bash
# Orders statistics
curl "http://localhost:8080/statistics"

# Executed orders with pagination
curl "http://localhost:8080/orders/executed?limit=10&offset=0"

# User orders
curl "http://localhost:8080/users/0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC/orders"

# Order events
curl "http://localhost:8080/orders/5/events"
```

### WebSocket Examples
```javascript
// Real-time 5-minute BTCUSDT candles
const ws1 = new WebSocket('ws://localhost:8022/ws?symbol=BTCUSDT&timeframe=5&type=candles');

// Real-time ETHUSDT orderbook
const ws2 = new WebSocket('ws://localhost:8022/ws?symbol=ETHUSDT&type=orderbook');

// Message handling
ws1.onmessage = function(event) {
    const data = JSON.parse(event.data);
    if (data.type === 'heartbeat') {
        ws1.send(JSON.stringify({type: 'pong'}));
    } else {
        console.log(`${data.symbol} Price: ${data.close}`);
    }
};
```

## Demo Clients

### Functionality Testing
```bash
# Market Data Demo
cd demo
python orderbook_demo.py    # OrderBook WebSocket demo
python websocket_demo.py    # Candles WebSocket demo  
python api_test.py          # Comprehensive API testing

# Order System Demo
cd order_system
./test_api.sh              # Order API testing script
```

## Troubleshooting

### Common Issues

**1. "Database connection failed"**
```bash
docker-compose ps timescaledb           # Check status
docker-compose logs timescaledb         # DB logs
docker-compose restart timescaledb      # Restart
```

**2. "No orderbook data available"**
```bash
docker-compose logs data-collector | grep orderbook  # Check collection
docker exec crypto_timescaledb psql -U crypto_user -d crypto_data -c "SELECT COUNT(*) FROM orderbook_data;"
```

**3. "WebSocket connection failed"**
```bash
docker-compose logs api-server | grep WebSocket     # Check WebSocket manager
curl http://localhost:8022/health                   # API health check
```

**4. "Events not processing"** 
```bash
docker-compose logs order-events                    # Event processor logs
curl http://localhost:8080/statistics               # Check Order API
```

### Diagnostic Commands
```bash
# Full system
./full_diagnostics.sh

# Specific issues
./db_connections_check.sh    # Database
./api_check.sh              # API endpoints  
./monitor_growth.sh         # Data growth

# Recovery
./emergency_fix.sh          # Emergency recovery
```

## Development

### Local Development
```bash
# Install dependencies
pip install -r data-collector/requirements.txt
pip install -r api-server/requirements.txt  
pip install -r order_system/requirements.txt

# Run individual services
cd data-collector && python main.py
cd api-server && python main.py
cd order_system && python main.py
```

### Testing
```bash
# API testing
python demo/api_test.py

# Order System testing  
cd order_system && ./test_api.sh

# Load testing
ab -n 1000 -c 10 http://localhost:8022/health
```

## Production Deployment

### Docker Production
```yaml
# docker-compose.prod.yml
services:
  timescaledb:
    restart: unless-stopped
    volumes:
      - timescale_data:/var/lib/postgresql/data
    environment:
      POSTGRES_PASSWORD: ${STRONG_PASSWORD}

  api-server:
    restart: unless-stopped
    deploy:
      replicas: 2
    environment:
      LOG_LEVEL: WARNING
```

### Scaling
```bash
# Horizontal API scaling
docker-compose up -d --scale api-server=3

# Load balancer (nginx)
upstream backend {
    server api-server:8000;
    server api-server:8000;
    server api-server:8000;
}
```

## Security

### Best Practices
- Environment variables for all secret data
- Firewall rules to restrict DB port access
- CORS settings for production
- Rate limiting for API endpoints
- SSL/TLS for external connections

### Monitoring
- Health check endpoints for all services
- Logging of all critical operations  
- Metrics collection through TimescaleDB
- Alert system for critical errors

## Licensing

Linkora DEX Backend uses dual licensing model

- **Open Source**: GNU Affero General Public License v3.0 (AGPL v3)
- **Commercial**: Proprietary license for commercial use

Details see in [LICENSING.md](./LICENSING.md)

### Quick License Selection

**Use AGPL v3 if**
- Your project is also open source
- Ready to share all changes
- Comply with copyleft requirements

**Need Commercial License if**
- Developing proprietary software
- Providing closed SaaS services
- Enterprise support required

**Contact**: licensing@linkora.info

## Contact Me  

📫 Reach out on [LinkedIn](https://www.linkedin.com/in/yuri-kachanyuk/) or [Email](mailto:wku@ukr.net)  or [Telegram](https://t.me/trimbler)  

---

## Useful Links

- **Data Collector**: [data-collector/readme.md](data-collector/readme.md) - Detailed data collection documentation
- **API Server**: [api-server/readme.md](api-server/readme.md) - REST API and WebSocket documentation  
- **Order System**: [order_system/readme.md](order_system/readme.md) - DEX orders and blockchain integration
- **Demo Clients**: [demo/](demo/) - Client examples and testing
- **Monitoring**: [monitoring/](monitoring/) - Diagnostic utilities
