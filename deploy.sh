#!/bin/bash

# Build and deploy DWOS platform with Docker Swarm

set -e

echo "🚀 DWOS Platform Deployment Script"
echo "================================="

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Parse arguments
ENVIRONMENT=${1:-development}
ACTION=${2:-deploy}

echo "📦 Environment: $ENVIRONMENT"
echo "🔧 Action: $ACTION"

# Build images
build_images() {
    echo ""
    echo "🏗️  Building Docker images..."
    
    # Build API Gateway
    echo "  - Building API Gateway..."
    docker build -t dwos/api-gateway:latest .
    
    # Build Discord Bot
    echo "  - Building Discord Bot..."
    docker build -t dwos/discord-bot:latest ./packages/bots/discord/1375476122061508619/
    
    echo "✅ Images built successfully!"
}

# Initialize Swarm
init_swarm() {
    if ! docker info | grep -q "Swarm: active"; then
        echo ""
        echo "🐝 Initializing Docker Swarm..."
        docker swarm init
    else
        echo "✅ Docker Swarm already initialized"
    fi
}

# Deploy stack
deploy_stack() {
    echo ""
    echo "🚀 Deploying DWOS stack..."
    
    if [ "$ENVIRONMENT" == "development" ]; then
        docker stack deploy -c docker-compose.yml dwos
    else
        docker stack deploy -c docker-stack.yml dwos
    fi
    
    echo "✅ Stack deployed successfully!"
    echo ""
    echo "📊 Services:"
    docker service ls | grep dwos
}

# Remove stack
remove_stack() {
    echo ""
    echo "🗑️  Removing DWOS stack..."
    docker stack rm dwos
    echo "✅ Stack removed"
}

# Show logs
show_logs() {
    SERVICE=${3:-api-gateway}
    echo ""
    echo "📜 Showing logs for $SERVICE..."
    
    if [ "$ENVIRONMENT" == "development" ]; then
        docker compose logs -f $SERVICE
    else
        docker service logs -f dwos_$SERVICE
    fi
}

# Scale service
scale_service() {
    SERVICE=$3
    REPLICAS=$4
    
    if [ -z "$SERVICE" ] || [ -z "$REPLICAS" ]; then
        echo "❌ Usage: ./deploy.sh $ENVIRONMENT scale <service> <replicas>"
        exit 1
    fi
    
    echo ""
    echo "⚖️  Scaling dwos_$SERVICE to $REPLICAS replicas..."
    docker service scale dwos_$SERVICE=$REPLICAS
}

# Main execution
case $ACTION in
    deploy)
        build_images
        init_swarm
        deploy_stack
        echo ""
        echo "🎉 Deployment complete!"
        echo ""
        echo "📍 Access points:"
        echo "  - API Gateway: http://localhost:8000"
        echo "  - API Docs: http://localhost:8000/api/docs"
        echo "  - Prometheus: http://localhost:9090"
        echo "  - Grafana: http://localhost:3000 (admin/admin)"
        echo "  - RabbitMQ: http://localhost:15672 (admin/admin)"
        echo "  - Consul: http://localhost:8500"
        echo "  - Traefik: http://localhost:8080"
        ;;
    
    build)
        build_images
        ;;
    
    remove)
        remove_stack
        ;;
    
    logs)
        show_logs $@
        ;;
    
    scale)
        scale_service $@
        ;;
    
    restart)
        SERVICE=$3
        echo "🔄 Restarting service dwos_$SERVICE..."
        docker service update --force dwos_$SERVICE
        ;;
    
    status)
        echo ""
        echo "📊 Stack status:"
        docker stack ps dwos
        ;;
    
    *)
        echo "❌ Unknown action: $ACTION"
        echo ""
        echo "Usage: ./deploy.sh [environment] [action] [options]"
        echo ""
        echo "Environments:"
        echo "  - development (default)"
        echo "  - production"
        echo ""
        echo "Actions:"
        echo "  - deploy: Build and deploy the stack"
        echo "  - build: Build Docker images only"
        echo "  - remove: Remove the stack"
        echo "  - logs [service]: Show service logs"
        echo "  - scale <service> <replicas>: Scale a service"
        echo "  - restart <service>: Restart a service"
        echo "  - status: Show stack status"
        exit 1
        ;;
esac