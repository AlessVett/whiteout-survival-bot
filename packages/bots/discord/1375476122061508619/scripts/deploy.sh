#!/bin/bash

# WhiteOut Survival Discord Bot Deployment Script

set -e

echo "🚀 WhiteOut Survival Discord Bot Deployment"
echo "==========================================="

# Change to project root
cd "$(dirname "$0")/.."

# Check if .env.production exists
if [ ! -f .env.production ]; then
    echo "❌ Error: .env.production file not found!"
    echo "Please copy .env.example to .env.production and configure it."
    exit 1
fi

# Load environment variables
export $(cat .env.production | grep -v '^#' | xargs)

# Function to check required env vars
check_env_var() {
    if [ -z "${!1}" ]; then
        echo "❌ Error: $1 is not set in .env.production"
        exit 1
    fi
}

# Check required environment variables
echo "📋 Checking environment variables..."
check_env_var "DISCORD_TOKEN"
check_env_var "GUILD_ID"
check_env_var "MONGO_ROOT_PASSWORD"
check_env_var "MONGO_PASSWORD"

echo "✅ Environment variables verified"

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p logs backups

# Build and start services
echo "🔨 Building Docker images..."
docker-compose -f docker-compose.prod.yml build

echo "🚀 Starting services..."
docker-compose -f docker-compose.prod.yml up -d

# Wait for MongoDB to be ready
echo "⏳ Waiting for MongoDB to be ready..."
sleep 10

# Check service status
echo "📊 Checking service status..."
docker-compose -f docker-compose.prod.yml ps

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📌 Useful commands:"
echo "  - View logs: docker-compose -f docker-compose.prod.yml logs -f discord-bot"
echo "  - Stop services: docker-compose -f docker-compose.prod.yml down"
echo "  - Restart bot: docker-compose -f docker-compose.prod.yml restart discord-bot"
echo "  - View MongoDB logs: docker-compose -f docker-compose.prod.yml logs mongodb"
echo "  - Enter bot container: docker-compose -f docker-compose.prod.yml exec discord-bot bash"
echo ""
echo "🔒 Security reminder: Make sure to:"
echo "  - Use strong passwords in production"
echo "  - Keep .env.production file secure and never commit it to git"
echo "  - Regularly backup your MongoDB data"
echo "  - Monitor logs for any issues"