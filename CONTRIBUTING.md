# 🤝 Contributing to DWOS Platform

Welcome to the DWOS (Distributed WhiteOut Survival) Platform! We're excited to have you contribute to this modern microservices platform for gaming community management.

## 📋 **Overview**

DWOS is a production-ready microservices platform built with FastAPI, Docker, and modern DevOps practices. Your contributions help build the future of gaming community management tools.

### **Current Architecture**
- **FastAPI API Gateway** - Central service discovery and routing ✅ **LIVE**
- **Discord Bot Microservice** - Community management for Discord ✅ **OPERATIONAL**
- **Service Discovery** - Consul-based health monitoring ✅ **ACTIVE**
- **Message Queue** - RabbitMQ for inter-service communication ✅ **CONFIGURED**
- **Monitoring Stack** - Prometheus & Grafana ✅ **COLLECTING**

## 🚀 **Getting Started**

### **1. Environment Setup**

#### **Prerequisites**
- **Docker & Docker Compose** (20.10+)
- **Python 3.11+** (for local development)
- **Git** with GitHub account
- **IDE** (VS Code recommended)

#### **Repository Setup**
```bash
# Fork and clone the repository
git clone https://github.com/AlessVett/whiteout-survival-bot.git
cd whiteout-survival-bot

# Create environment file
cp .env.example .env
# Edit .env with your Discord bot credentials (optional for testing)

# Start the development environment
docker compose up -d

# Verify everything is running
curl http://localhost:8000/api/v1/health/services
```

### **2. Development Workflow**

#### **Branch Strategy**
```bash
# Create feature branch from main
git checkout main
git pull origin main
git checkout -b feature/your-feature-name

# Work on your changes
# ...

# Push and create PR
git push origin feature/your-feature-name
```

#### **Local Development**
```bash
# View real-time logs
./deploy.sh development logs api-gateway

# Restart services after changes
docker compose restart service-name

# Rebuild after dependency changes
docker compose build
```

## 🏗️ **Contributing to Different Components**

### **API Gateway (FastAPI)**
**Location**: `/main.py`, `/applications/v1/`, `/configs/`

#### **Adding New Endpoints**
1. Create router in `applications/v1/routers/`
2. Add business logic
3. Include router in `main.py`
4. Update API documentation

**Example**: Adding a new service endpoint
```python
# applications/v1/routers/new_feature.py
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/new-feature", tags=["new-feature"])

@router.get("/")
async def get_feature():
    return {"status": "active"}
```

```python
# main.py - Add to imports and include router
from applications.v1.routers import new_feature
app.include_router(new_feature.router, prefix=settings.api_v1_str)
```

#### **Modifying Service Discovery**
- Update `applications/v1/core/service_discovery.py`
- Add health checks and service registration
- Test with multiple service instances

### **Discord Bot Microservice**
**Location**: `/packages/bots/discord/1375476122061508619/`

#### **Adding Bot Features**
1. Create new cog in `src/cogs/`
2. Add to `src/bot.py`
3. Update microservice health checks
4. Test both bot functionality and HTTP endpoints

**Example**: Adding a new command
```python
# src/cogs/new_feature.py
from discord.ext import commands

class NewFeatureCog(commands.Cog):
    @commands.slash_command(description="New feature command")
    async def new_command(self, ctx):
        await ctx.respond("New feature working!")

def setup(bot):
    bot.add_cog(NewFeatureCog(bot))
```

#### **Microservice API Endpoints**
The Discord bot runs as a microservice with:
- `GET /health` - Health check
- `GET /admin/status` - Process status
- `POST /admin/reload` - Restart bot process

### **Adding New Microservices**

#### **1. Service Structure**
```
packages/services/new-service/
├── main.py                 # Service entry point
├── Dockerfile             # Container definition
├── requirements.txt       # Python dependencies
├── microservice.py        # FastAPI wrapper (if needed)
├── src/                   # Business logic
│   ├── __init__.py
│   ├── service.py         # Main service logic
│   └── config.py         # Configuration
└── tests/                 # Service tests
    └── test_service.py
```

#### **2. Implementation Checklist**
- [ ] Implement health endpoint (`/health`)
- [ ] Add Consul service registration
- [ ] Configure Docker networking
- [ ] Add to docker-compose.yml
- [ ] Add to docker-stack.yml (production)
- [ ] Update API Gateway routing
- [ ] Add monitoring and logging
- [ ] Write tests

#### **3. Service Template**
```python
# main.py - Microservice template
from fastapi import FastAPI
from contextlib import asynccontextmanager
import consul

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Register with Consul
    consul_client = consul.Consul(host="consul", port=8500)
    consul_client.agent.service.register(
        name="new-service",
        service_id="new-service-1",
        address="new-service",
        port=8002,
        tags=["new-service", "v1"],
        check=consul.Check.http("http://new-service:8002/health", interval="10s")
    )
    
    yield
    
    # Cleanup
    consul_client.agent.service.deregister("new-service-1")

app = FastAPI(lifespan=lifespan)

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "new-service"}

@app.get("/")
async def root():
    return {"service": "new-service", "status": "running"}
```

## 🧪 **Testing Guidelines**

### **Unit Tests**
```bash
# Run tests for specific service
docker compose exec api-gateway python -m pytest tests/

# Run with coverage
docker compose exec api-gateway python -m pytest --cov=applications tests/
```

### **Integration Tests**
```bash
# Test service discovery
curl http://localhost:8000/api/v1/health/services

# Test service communication
curl http://localhost:8000/api/v1/services/discord-bot/health

# Test bot functionality (if Discord token configured)
# Use Discord test server
```

### **Load Testing**
```bash
# Install load testing tools
pip install locust

# Run load tests
locust -f tests/load_test.py --host=http://localhost:8000
```

## 📊 **Monitoring & Observability**

### **Adding Metrics**
```python
# Add Prometheus metrics
from prometheus_client import Counter, Histogram

REQUEST_COUNT = Counter('requests_total', 'Total requests', ['method', 'endpoint'])
REQUEST_LATENCY = Histogram('request_duration_seconds', 'Request latency')

@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    
    REQUEST_COUNT.labels(method=request.method, endpoint=request.url.path).inc()
    REQUEST_LATENCY.observe(time.time() - start_time)
    
    return response
```

### **Structured Logging**
```python
import structlog

logger = structlog.get_logger()

@app.post("/api/v1/example")
async def example_endpoint():
    logger.info("Processing request", endpoint="example", user_id="123")
    # ... business logic
    logger.info("Request completed", duration_ms=50)
```

## 🔧 **Code Quality Standards**

### **Code Style**
- **Python**: Follow PEP 8, use Black formatter
- **FastAPI**: Use async/await, proper type hints
- **Docker**: Multi-stage builds, security best practices
- **Git**: Conventional commits format

### **Pre-commit Setup**
```bash
# Install pre-commit hooks
pip install pre-commit
pre-commit install

# Run manually
pre-commit run --all-files
```

### **Code Review Checklist**
- [ ] Code follows style guidelines
- [ ] Tests pass and cover new functionality
- [ ] Health endpoints implemented for new services
- [ ] Documentation updated
- [ ] No secrets or credentials in code
- [ ] Performance impact considered
- [ ] Backwards compatibility maintained

## 🚀 **Deployment & Release**

### **Development Deployment**
```bash
# Test your changes
./deploy.sh development deploy

# Verify functionality
curl http://localhost:8000/api/v1/health/services
```

### **Production Considerations**
- Resource limits and scaling
- Security configurations
- Monitoring and alerting
- Backup and recovery procedures
- Rolling update strategies

## 📝 **Documentation**

### **Required Documentation**
- **API Changes**: Update OpenAPI schemas
- **New Services**: Add to ARCHITECTURE.md
- **Configuration**: Update .env.example
- **Deployment**: Update DEPLOYMENT.md if needed

### **Documentation Standards**
- Clear, concise explanations
- Code examples with comments
- Architecture diagrams for complex changes
- Migration guides for breaking changes

## 🐛 **Bug Reports & Feature Requests**

### **Bug Report Template**
```markdown
**Description**: Clear description of the bug

**Steps to Reproduce**:
1. Start services with `docker compose up -d`
2. Make request to `curl http://localhost:8000/api/endpoint`
3. Observe error

**Expected Behavior**: What should happen

**Actual Behavior**: What actually happens

**Environment**:
- OS: macOS/Linux/Windows
- Docker version: 
- Service versions: (from `curl http://localhost:8000/`)

**Logs**: Include relevant log output
```

### **Feature Request Template**
```markdown
**Feature Description**: Clear description of the requested feature

**Use Case**: Why is this feature needed?

**Proposed Implementation**: How should it work?

**Additional Context**: Any other relevant information
```

## 🏆 **Recognition**

### **Contributor Types**
- **Code Contributors**: New features, bug fixes, improvements
- **Documentation Contributors**: Guides, examples, translations
- **Community Contributors**: Issues, discussions, testing
- **Infrastructure Contributors**: DevOps, monitoring, security

### **Recognition Methods**
- GitHub contributor graphs
- Release notes mentions
- Community Discord recognition
- Annual contributor awards

## 🤔 **Getting Help**

### **Communication Channels**
- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: General questions and ideas
- **Discord Server**: Real-time chat and support
- **Documentation**: Comprehensive guides and references

### **Mentorship Program**
New contributors can request mentorship for:
- Understanding the codebase architecture
- Learning microservices patterns
- Docker and containerization
- FastAPI and Python async programming

## 🔄 **Release Process**

### **Versioning**
- **Semantic Versioning**: MAJOR.MINOR.PATCH
- **Release Branches**: `release/v1.2.0`
- **Hotfix Process**: Direct patches to main

### **Release Checklist**
- [ ] All tests pass
- [ ] Documentation updated
- [ ] Version numbers bumped
- [ ] Migration guides created
- [ ] Security review completed
- [ ] Performance testing passed

---

## 🎯 **Quick Start Summary**

1. **Fork & Clone** the repository
2. **Copy .env.example** to .env with your settings
3. **Run `docker compose up -d`** to start services
4. **Create feature branch** and make changes
5. **Test thoroughly** with provided commands
6. **Update documentation** as needed
7. **Submit pull request** with clear description

Thank you for contributing to DWOS! Your work helps build better tools for gaming communities worldwide. 🎮✨