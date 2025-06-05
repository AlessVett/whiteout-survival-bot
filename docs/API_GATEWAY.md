# 🌐 DWOS API Gateway Documentation

## 📋 **Overview**

The DWOS API Gateway is the central hub of the distributed platform, built with FastAPI. It provides service discovery, health monitoring, load balancing, and unified API access to all microservices.

**Status**: ✅ **PRODUCTION READY**  
**Base URL**: `http://localhost:8000`  
**Documentation**: `http://localhost:8000/api/docs`  

## 🔗 **Core Endpoints**

### **Root & Information**
```http
GET /
```
Returns platform information and status.

**Response**:
```json
{
  "name": "DWOS Platform",
  "version": "0.1.0", 
  "status": "running",
  "docs": "/api/docs"
}
```

### **Health Monitoring**

#### Gateway Health Check
```http
GET /api/v1/health
```
Returns API Gateway health status.

**Response**:
```json
{
  "status": "healthy",
  "timestamp": "2025-06-05T10:42:33.180537",
  "service": "api-gateway"
}
```

#### Service Discovery
```http
GET /api/v1/health/services
```
Returns health status of all registered microservices.

**Response**:
```json
{
  "timestamp": "2025-06-05T10:42:40.774586",
  "services": {
    "api-gateway": {
      "healthy_instances": 1,
      "instances": [
        {
          "id": "api-gateway-1",
          "address": "api-gateway",
          "port": 8000,
          "tags": ["gateway", "api", "v1"]
        }
      ]
    },
    "discord-bot": {
      "healthy_instances": 1,
      "instances": [
        {
          "id": "discord-bot-1", 
          "address": "discord-bot",
          "port": 8001,
          "tags": ["bot", "discord", "v1"]
        }
      ]
    }
  }
}
```

## 🔧 **Service Management**

### **Restart Service**
```http
POST /api/v1/services/{service_name}/reload
```
Triggers a zero-downtime restart of the specified microservice.

**Parameters**:
- `service_name`: Name of the service (e.g., "discord-bot")

**Response**:
```json
{
  "status": "success",
  "service": "discord-bot",
  "message": "Service discord-bot reloaded successfully"
}
```

### **Service Status**
```http
GET /api/v1/services/{service_name}/status
```
Gets detailed status information for a specific service.

**Response**:
```json
{
  "service": "discord-bot",
  "running": true,
  "pid": 8,
  "health": "healthy"
}
```

### **Service Proxy**
```http
{METHOD} /api/v1/services/{service_name}/{path}
```
Proxies requests directly to microservices. Supports all HTTP methods.

**Example**:
```bash
# Get Discord bot admin status
GET /api/v1/services/discord-bot/admin/status

# Reload Discord bot directly
POST /api/v1/services/discord-bot/admin/reload
```

## 🔄 **Service Discovery**

### **Consul Integration**

The API Gateway automatically discovers and routes to healthy service instances using Consul:

- **Auto-Registration**: Services register themselves on startup
- **Health Monitoring**: Continuous health checks every 10 seconds
- **Load Balancing**: Automatic routing to healthy instances
- **Failure Detection**: Unhealthy services removed from routing

### **Service Registration**

Services auto-register with the following information:
```json
{
  "ID": "service-instance-id",
  "Name": "service-name", 
  "Address": "container-name",
  "Port": 8001,
  "Tags": ["bot", "discord", "v1"],
  "Check": {
    "HTTP": "http://container:port/health",
    "Interval": "10s"
  }
}
```

## 📊 **Monitoring & Observability**

### **Metrics Endpoint**
```http
GET /metrics
```
Prometheus-compatible metrics for monitoring and alerting.

### **Structured Logging**

All logs are structured JSON with correlation IDs:
```json
{
  "event": "Service registered: discord-bot (discord-bot-1)",
  "logger": "applications.v1.core.service_discovery", 
  "level": "info",
  "timestamp": "2025-06-05T10:13:27.369613Z"
}
```

### **Health Check Intervals**

- **Service Registration**: On startup
- **Health Checks**: Every 10 seconds
- **Service Discovery**: Real-time updates
- **Consul Watch**: 30-second intervals

## 🔐 **Security & Configuration**

### **Environment Variables**

```bash
# Core Configuration
APP_NAME=DWOS Platform
APP_VERSION=0.1.0
APP_ENV=development
DEBUG=True

# API Settings
API_V1_STR=/api/v1
API_HOST=0.0.0.0
API_PORT=8000

# Service Discovery
CONSUL_HOST=consul
CONSUL_PORT=8500

# Message Queue
RABBITMQ_URL=amqp://admin:admin@rabbitmq:5672

# Caching
REDIS_URL=redis://redis:6379

# Rate Limiting
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_PERIOD=60
```

### **CORS Configuration**

Default allowed origins:
- `http://localhost:3000` (Frontend development)
- `http://localhost:8000` (API Gateway)

### **Rate Limiting**

- **Default**: 100 requests per 60 seconds per IP
- **Customizable**: Per endpoint rate limiting available
- **Headers**: `X-RateLimit-Limit`, `X-RateLimit-Remaining`

## 🚀 **Deployment**

### **Development**
```bash
# Start all services
docker compose up -d

# Check status
curl http://localhost:8000/api/v1/health/services
```

### **Production (Docker Swarm)**
```bash
# Deploy stack
./deploy.sh production deploy

# Scale services
./deploy.sh production scale discord-bot 3

# Check service status
./deploy.sh production status
```

## 🛠️ **Development**

### **Adding New Endpoints**

1. Create router in `applications/v1/routers/`
2. Register in `main.py`
3. Add health endpoint to service
4. Update service discovery tags

### **Error Handling**

All endpoints return consistent error responses:
```json
{
  "detail": "Error description",
  "status_code": 400,
  "timestamp": "2025-06-05T10:42:33.180537"
}
```

### **Testing**

```bash
# Run health checks
curl http://localhost:8000/api/v1/health

# Test service discovery
curl http://localhost:8000/api/v1/health/services

# Test service management
curl -X POST http://localhost:8000/api/v1/services/discord-bot/reload
```

## 📚 **API Reference**

For complete API documentation with interactive examples:
👉 **[Visit API Docs](http://localhost:8000/api/docs)**

The documentation includes:
- Interactive request/response examples
- Schema definitions
- Authentication details
- Rate limiting information
- Error response formats