# 🏗️ DWOS Microservices Architecture

## 📋 **Architecture Overview**

DWOS (Distributed WhiteOut Survival) is built as a modern microservices platform designed for scalability, reliability, and maintainability. The architecture follows cloud-native principles with containerization, service discovery, and event-driven communication.

```
┌─────────────────────────────────────────────────────────────────┐
│                        Load Balancer                            │
│                     (Traefik - Optional)                        │
└─────────────────────────┬───────────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────────┐
│                   FastAPI API Gateway                           │
│              Service Discovery | Load Balancing                 │
│                Health Monitoring | Routing                      │
└─────────────────┬─────────────────────┬─────────────────────────┘
                  │                     │
         ┌────────▼──────┐     ┌────────▼──────┐
         │ Discord Bot   │     │ Future Bots   │
         │ Microservice  │     │ (Telegram,    │
         │ Port 8001     │     │  WhatsApp)    │
         └───────┬───────┘     └───────────────┘
                 │
    ┌────────────┼────────────────────────────────────┐
    │            │                                    │
┌───▼───┐   ┌────▼────┐   ┌─────────┐   ┌─────────┐   │
│MongoDB│   │RabbitMQ │   │ Consul  │   │ Redis   │   │
│Primary│   │Messages │   │Discovery│   │ Cache   │   │
│  DB   │   │ Queue   │   │Service  │   │         │   │
└───────┘   └─────────┘   └─────────┘   └─────────┘   │
                                                      │
            ┌─────────────────────────────────────────┘
            │
    ┌───────▼──────┐   ┌──────────┐
    │ Prometheus   │   │ Grafana  │
    │  Metrics     │   │Dashboard │
    └──────────────┘   └──────────┘
```

## 🔧 **Core Components**

### **1. API Gateway (FastAPI)**
**Status**: ✅ **PRODUCTION READY**  
**Port**: `8000`  
**Repository**: `/main.py`, `/applications/v1/`

#### **Responsibilities**:
- **Service Discovery**: Auto-discovery and routing to healthy services
- **Load Balancing**: Distribute traffic across service instances
- **Health Monitoring**: Continuous health checks and status reporting
- **API Documentation**: Auto-generated OpenAPI/Swagger documentation
- **Rate Limiting**: Protect services from abuse
- **Request Proxying**: Route requests to appropriate microservices

#### **Key Features**:
- Service registry integration with Consul
- Real-time health monitoring
- API versioning (`/api/v1/`)
- Structured logging with correlation IDs
- Prometheus metrics export
- CORS and security middleware

#### **Endpoints**:
```
GET  /                           # Platform info
GET  /api/v1/health             # Gateway health
GET  /api/v1/health/services    # All services status
POST /api/v1/services/{name}/reload  # Restart service
GET  /api/v1/services/{name}/status  # Service status
ANY  /api/v1/services/{name}/*  # Proxy to service
```

### **2. Discord Bot Microservice**
**Status**: ✅ **ONLINE & OPERATIONAL**  
**Port**: `8001`  
**Repository**: `/packages/bots/discord/1375476122061508619/`

#### **Responsibilities**:
- Discord bot logic and command handling
- Player verification and alliance management
- Event scheduling and notifications
- Multi-language support (11 languages)
- Database operations for user data

#### **Architecture**:
```
┌─────────────────────────────────────┐
│         FastAPI Wrapper             │ ← Health endpoints, admin API
├─────────────────────────────────────┤
│         Discord Bot Process         │ ← Main bot logic
├─────────────────────────────────────┤
│         Database Layer              │ ← MongoDB operations
└─────────────────────────────────────┘
```

#### **Endpoints**:
```
GET  /health              # Health check
GET  /admin/status        # Process status
POST /admin/reload        # Restart bot process
```

### **3. Service Discovery (Consul)**
**Status**: ✅ **ACTIVE**  
**Port**: `8500`  
**UI**: `http://localhost:8500`

#### **Responsibilities**:
- Service registration and discovery
- Health check coordination
- Configuration management
- Service catalog maintenance

#### **Service Registration**:
Services automatically register with:
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

### **4. Message Queue (RabbitMQ)**
**Status**: ✅ **CONFIGURED**  
**Port**: `5672` (AMQP), `15672` (Management UI)  
**Management**: `http://localhost:15672` (admin/admin)

#### **Responsibilities**:
- Inter-service communication
- Event-driven messaging
- Async task processing
- Notification delivery

#### **Message Patterns**:
- **Event Bus**: Pub/sub for system events
- **Task Queue**: Background job processing
- **RPC**: Request/response between services

### **5. Database Layer**

#### **MongoDB (Primary Database)**
**Status**: ✅ **OPERATIONAL**  
**Port**: `27017`  
**Database**: `dwos`

**Collections**:
- `users` - Discord user data and verification
- `alliances` - Alliance information and members
- `events` - Scheduled events and reminders
- `config` - Bot configuration and settings

#### **Redis (Cache & Sessions)**
**Status**: ✅ **OPERATIONAL**  
**Port**: `6379`

**Usage**:
- Session storage
- Rate limiting counters
- Temporary data caching
- Inter-service communication

### **6. Monitoring Stack**

#### **Prometheus (Metrics)**
**Status**: ✅ **COLLECTING**  
**Port**: `9090`  
**Metrics**: `http://localhost:8000/metrics`

**Collected Metrics**:
- HTTP request latency and count
- Service health status
- Resource utilization
- Custom business metrics

#### **Grafana (Dashboards)**
**Status**: ✅ **CONFIGURED**  
**Port**: `3000`  
**Login**: admin/admin

**Dashboards**:
- Service overview and health
- Performance metrics
- Resource utilization
- Alert management

## 🔄 **Communication Patterns**

### **1. Synchronous Communication**
```
Client → API Gateway → Service Discovery → Microservice
                    ↓
               Load Balancer
```

**Used for**:
- Real-time API requests
- Health checks
- Admin operations
- Direct service communication

### **2. Asynchronous Communication**
```
Service A → RabbitMQ → Service B
         ↓
    Event Bus → Multiple Subscribers
```

**Used for**:
- Event notifications
- Background tasks
- Cross-service updates
- Decoupled operations

### **3. Service Discovery Flow**
```
1. Service starts → Registers with Consul
2. Health checks → Continuous monitoring
3. API Gateway → Discovers healthy instances
4. Request routing → Load balanced distribution
5. Service failure → Auto-removal from registry
```

## 🛡️ **Security Architecture**

### **Network Security**
```
External Traffic → Traefik (TLS termination)
                → API Gateway (Rate limiting)
                → Internal Services (Network isolation)
```

### **Authentication & Authorization**
- **Service-to-Service**: Internal network trust
- **External APIs**: Rate limiting and validation
- **Admin Endpoints**: Restricted access
- **Database**: Network isolation

### **Data Protection**
- **Secrets**: Docker secrets management
- **Environment Variables**: Secure configuration
- **Network Isolation**: Container networks
- **Encryption**: TLS for external traffic

## 📊 **Scalability Design**

### **Horizontal Scaling**
```bash
# Scale services independently
docker service scale dwos_discord-bot=3
docker service scale dwos_api-gateway=2
```

### **Resource Management**
```yaml
# Example resource constraints
deploy:
  resources:
    limits:
      memory: 512M
      cpus: '0.5'
    reservations:
      memory: 256M
      cpus: '0.25'
```

### **Auto-Scaling Triggers**
- CPU utilization > 70%
- Memory usage > 80%
- Request latency > 200ms
- Queue depth > 100 messages

## 🔍 **Health Monitoring**

### **Health Check Hierarchy**
```
1. Container Health → Docker health checks
2. Service Health → HTTP /health endpoints  
3. Application Health → Business logic checks
4. Infrastructure Health → Database, queue connectivity
```

### **Health Check Intervals**
- **Consul Health Checks**: 10 seconds
- **Service Discovery Updates**: Real-time
- **Prometheus Scraping**: 15 seconds
- **Gateway Health Aggregation**: 30 seconds

### **Failure Detection & Recovery**
```
Service Failure → Consul marks unhealthy
             → API Gateway stops routing
             → Auto-restart (Docker policy)
             → Re-registration on recovery
```

## 🚀 **Deployment Architecture**

### **Development Environment**
```
Docker Compose → Single host deployment
              → Volume mounts for live reload
              → Local networking
              → Simplified configuration
```

### **Production Environment**
```
Docker Swarm → Multi-host clustering
            → Service replication
            → Rolling updates
            → Load balancing
            → Health monitoring
```

### **CI/CD Pipeline** (Planned)
```
Code Push → GitHub Actions → Build Images
        → Run Tests → Push to Registry
        → Deploy to Staging → Run E2E Tests
        → Deploy to Production → Health Verification
```

## 📈 **Performance Characteristics**

### **Current Metrics**
- **API Gateway Response Time**: <50ms average
- **Service Discovery Latency**: <10ms
- **Database Query Time**: <100ms average
- **Memory Usage**: ~512MB per service
- **CPU Usage**: <25% per service

### **Scaling Targets**
- **1,000 Discord Users**: 2-3 bot instances
- **10,000 Discord Users**: 5-10 bot instances
- **Multiple Guilds**: Horizontal service scaling
- **High Availability**: Multi-node deployment

## 🔮 **Future Architecture Plans**

### **Phase 3: Multi-Platform** (Next)
```
API Gateway
    ├── Discord Bot (Current)
    ├── Telegram Bot (Planned)
    ├── WhatsApp Bot (Planned)
    └── Web Dashboard (Planned)
```

### **Phase 4: Advanced Features**
- **Event Sourcing**: Audit trail and replay
- **CQRS**: Command/Query separation
- **Distributed Cache**: Multi-tier caching
- **Machine Learning**: Analytics and insights

### **Phase 5: Enterprise Features**
- **Multi-Tenancy**: Isolated customer environments
- **Advanced Security**: OAuth2, JWT, RBAC
- **SLA Monitoring**: Performance guarantees
- **Disaster Recovery**: Multi-region deployment

## 🛠️ **Development Guidelines**

### **Adding New Microservices**
1. **Create Service Structure**:
   ```
   packages/services/new-service/
   ├── main.py                 # Service entry point
   ├── Dockerfile             # Container definition
   ├── requirements.txt       # Dependencies
   ├── src/                   # Business logic
   └── tests/                 # Service tests
   ```

2. **Implement Health Endpoints**:
   ```python
   @app.get("/health")
   async def health():
       return {"status": "healthy", "service": "new-service"}
   ```

3. **Service Registration**:
   - Auto-register with Consul on startup
   - Implement health checks
   - Tag with service metadata

4. **Update Configuration**:
   - Add to docker-compose.yml
   - Add to docker-stack.yml
   - Update API Gateway routing

### **Service Communication Best Practices**
- **Use async/await** for non-blocking operations
- **Implement circuit breakers** for external calls
- **Add correlation IDs** for request tracing
- **Use structured logging** for observability
- **Handle failures gracefully** with retries and fallbacks

## 📚 **Related Documentation**

- **[API Gateway Documentation](API_GATEWAY.md)** - Detailed API reference
- **[Deployment Guide](DEPLOYMENT.md)** - Step-by-step deployment
- **[Discord Bot README](../packages/bots/discord/1375476122061508619/README.md)** - Bot-specific docs
- **[Main README](../README.md)** - Project overview and quick start