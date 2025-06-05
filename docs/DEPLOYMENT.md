# 🚀 DWOS Deployment Guide

## 📋 **Prerequisites**

### **System Requirements**
- **Docker**: 20.10+ with Docker Compose
- **Docker Swarm**: For production deployment
- **RAM**: Minimum 2GB, Recommended 4GB+
- **CPU**: 2+ cores recommended
- **Storage**: 10GB+ available space

### **Network Ports**
- `8000` - API Gateway (FastAPI)
- `8001` - Discord Bot Microservice
- `8500` - Consul (Service Discovery)
- `5672` - RabbitMQ (Message Queue)
- `15672` - RabbitMQ Management UI
- `27017` - MongoDB
- `6379` - Redis
- `9090` - Prometheus
- `3000` - Grafana

## 🔧 **Environment Setup**

### **1. Clone Repository**
```bash
git clone https://github.com/AlessVett/whiteout-survival-bot.git
cd whiteout-survival-bot
```

### **2. Environment Configuration**
```bash
# Copy example environment file
cp .env.example .env

# Edit with your configurations
nano .env
```

**Required Environment Variables**:
```bash
# Discord Bot (Required if using Discord bot)
DISCORD_TOKEN=your_discord_bot_token
GUILD_ID=your_discord_guild_id
API_KEY=your_game_api_key_if_needed

# Database
MONGODB_URI=mongodb://mongodb:27017/
MONGODB_DB=dwos

# Infrastructure (Auto-configured for Docker)
RABBITMQ_URL=amqp://admin:admin@rabbitmq:5672
CONSUL_HOST=consul
CONSUL_PORT=8500
```

## 🔄 **Development Deployment**

### **Quick Start (5 minutes)**
```bash
# Start all services
docker compose up -d

# Verify deployment
curl http://localhost:8000/api/v1/health/services

# View logs
./deploy.sh development logs api-gateway
```

### **Individual Service Management**
```bash
# Start specific services
docker compose up -d api-gateway discord-bot

# Restart a service
docker compose restart discord-bot

# View service logs
./deploy.sh development logs discord-bot

# Scale a service (development)
docker compose up -d --scale discord-bot=2
```

### **Development Workflow**
```bash
# Code changes auto-reload (volumes mounted)
# API Gateway: Changes in ./ directory
# Discord Bot: Changes in ./packages/bots/discord/*/

# Rebuild after dependency changes
docker compose build

# Clean restart
docker compose down && docker compose up -d
```

## 🏭 **Production Deployment (Docker Swarm)**

### **1. Initialize Swarm**
```bash
# Initialize Docker Swarm (manager node)
docker swarm init

# Get join token for worker nodes
docker swarm join-token worker
```

### **2. Deploy Stack**
```bash
# Build and deploy with automation script
./deploy.sh production deploy

# Manual deployment
docker stack deploy -c docker-stack.yml dwos
```

### **3. Verify Deployment**
```bash
# Check stack status
./deploy.sh production status

# Check service status
docker service ls

# View service logs
./deploy.sh production logs api-gateway
```

## ⚖️ **Scaling & Load Balancing**

### **Horizontal Scaling**
```bash
# Scale Discord bot instances
./deploy.sh production scale discord-bot 3

# Scale API Gateway
./deploy.sh production scale api-gateway 2

# Manual scaling
docker service scale dwos_discord-bot=3
```

### **Auto-Scaling Configuration**
```yaml
# In docker-stack.yml
deploy:
  replicas: 2
  update_config:
    parallelism: 1
    delay: 10s
  restart_policy:
    condition: on-failure
    delay: 5s
    max_attempts: 3
```

### **Load Balancer (Traefik)**
```bash
# Access Traefik dashboard
open http://localhost:8080

# Check service discovery
curl http://localhost:8500/v1/catalog/services
```

## 📊 **Monitoring & Health Checks**

### **Health Monitoring**
```bash
# API Gateway health
curl http://localhost:8000/api/v1/health

# All services health
curl http://localhost:8000/api/v1/health/services

# Individual service health
curl http://localhost:8001/health
```

### **Metrics & Dashboards**
```bash
# Prometheus metrics
open http://localhost:9090

# Grafana dashboards
open http://localhost:3000
# Login: admin/admin

# RabbitMQ management
open http://localhost:15672
# Login: admin/admin

# Consul UI
open http://localhost:8500
```

### **Log Management**
```bash
# Development logs
./deploy.sh development logs api-gateway

# Production logs
./deploy.sh production logs api-gateway

# Export logs for analysis
docker service logs dwos_api-gateway > gateway.log
```

## 🔐 **Security & Best Practices**

### **Production Security**
1. **Change Default Passwords**:
   ```bash
   # RabbitMQ
   RABBITMQ_DEFAULT_USER=your_secure_user
   RABBITMQ_DEFAULT_PASS=your_secure_password
   
   # Grafana
   GF_SECURITY_ADMIN_PASSWORD=your_secure_password
   ```

2. **Network Security**:
   ```bash
   # Use custom networks
   docker network create --driver overlay --encrypted dwos-secure
   ```

3. **Secrets Management**:
   ```bash
   # Use Docker secrets for sensitive data
   echo "your_discord_token" | docker secret create discord_token -
   ```

### **SSL/TLS Configuration**
```yaml
# Add to docker-stack.yml for Traefik
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.api.rule=Host(\`your-domain.com\`)"
  - "traefik.http.routers.api.tls.certresolver=letsencrypt"
```

## 🛠️ **Maintenance & Updates**

### **Rolling Updates**
```bash
# Update with zero downtime
./deploy.sh production deploy

# Manual rolling update
docker service update --image dwos/api-gateway:latest dwos_api-gateway
```

### **Backup Procedures**
```bash
# Backup MongoDB
docker exec dwos_mongodb_1 mongodump --out /backup

# Backup configuration
cp -r configs/ backups/configs-$(date +%Y%m%d)

# Backup Docker volumes
docker run --rm -v dwos_mongodb_data:/data -v $(pwd):/backup alpine tar czf /backup/mongodb_backup.tar.gz /data
```

### **Service Recovery**
```bash
# Restart failed service
./deploy.sh production restart discord-bot

# Force service update
docker service update --force dwos_discord-bot

# Remove and redeploy service
docker service rm dwos_discord-bot
docker stack deploy -c docker-stack.yml dwos
```

## 🚨 **Troubleshooting**

### **Common Issues**

1. **Service Not Starting**:
   ```bash
   # Check logs
   ./deploy.sh development logs service-name
   
   # Check resource constraints
   docker stats
   
   # Verify environment variables
   docker compose exec service-name env
   ```

2. **Service Discovery Issues**:
   ```bash
   # Check Consul status
   curl http://localhost:8500/v1/status/leader
   
   # Verify service registration
   curl http://localhost:8500/v1/catalog/services
   ```

3. **Database Connection Issues**:
   ```bash
   # Test MongoDB connection
   docker compose exec mongodb mongo --eval "db.stats()"
   
   # Check network connectivity
   docker compose exec api-gateway ping mongodb
   ```

### **Performance Optimization**
```bash
# Monitor resource usage
docker stats

# Check service performance
curl http://localhost:8000/metrics

# Optimize container resources
docker service update --limit-memory 512m dwos_discord-bot
```

### **Debug Mode**
```bash
# Enable debug logging
export DEBUG=True
docker compose up -d

# Access container for debugging
docker compose exec api-gateway bash

# Check service health
curl -v http://localhost:8001/health
```

## 📈 **Scaling Examples**

### **High Load Configuration**
```bash
# Scale for 1000+ Discord users
./deploy.sh production scale discord-bot 5
./deploy.sh production scale api-gateway 3

# Add resource limits
docker service update --limit-memory 1g --limit-cpus 1 dwos_discord-bot
```

### **Multi-Node Setup**
```bash
# Add worker nodes
docker swarm join --token <worker-token> <manager-ip>:2377

# Deploy with placement constraints
# Services will distribute across nodes automatically
```

## 📋 **Deployment Checklist**

### **Pre-Deployment**
- [ ] Environment variables configured
- [ ] Docker and Docker Compose installed
- [ ] Network ports available
- [ ] Sufficient system resources
- [ ] DNS/Domain configured (production)

### **Post-Deployment**
- [ ] All services healthy (`/api/v1/health/services`)
- [ ] Discord bot online and responding
- [ ] Monitoring dashboards accessible
- [ ] Logs being collected properly
- [ ] Backup procedures tested
- [ ] SSL certificates valid (production)

### **Maintenance Schedule**
- **Daily**: Health check monitoring
- **Weekly**: Log rotation and cleanup
- **Monthly**: Security updates and patches
- **Quarterly**: Backup restoration testing

## 🔗 **Useful Commands**

```bash
# One-liner status check
curl -s http://localhost:8000/api/v1/health/services | jq '.services | to_entries[] | {service: .key, healthy: .value.healthy_instances}'

# Quick restart all services
docker stack rm dwos && ./deploy.sh production deploy

# Check service discovery
watch -n 5 'curl -s http://localhost:8500/v1/catalog/services | jq'

# Development workflow
./deploy.sh development logs api-gateway
```