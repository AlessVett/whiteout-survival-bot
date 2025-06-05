# WhiteOut Survival Discord Bot - Deployment Guide

## 🚀 Production Deployment with Docker

### Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- A server with at least 2GB RAM
- Discord Bot Token
- API credentials for WhiteOut Survival

### Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/AlessVett/whiteout-survival-bot.git
   cd whiteout-survival-bot/packages/bots/discord/1375476122061508619
   ```

2. **Configure environment**
   ```bash
   cp .env.example .env.production
   nano .env.production  # Edit with your values
   ```

3. **Deploy**
   ```bash
   ./scripts/deploy.sh
   ```

### Manual Deployment

1. **Build the images**
   ```bash
   docker-compose -f docker-compose.prod.yml build
   ```

2. **Start the services**
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

3. **Check logs**
   ```bash
   docker-compose -f docker-compose.prod.yml logs -f
   ```

### Configuration

Edit `.env.production` with your values:

```env
# Discord Configuration
DISCORD_TOKEN=your_bot_token_here
GUILD_ID=your_server_id_here

# MongoDB Configuration
MONGO_ROOT_USERNAME=root
MONGO_ROOT_PASSWORD=secure_password_here
MONGO_USER=bot_user
MONGO_PASSWORD=secure_password_here
MONGO_DB=whiteout_survival_crm

# API Configuration
API_BASE_URL=https://wos-giftcode-api.centurygame.com/api/player
API_KEY=your_api_key_if_needed

# Bot Configuration
DEFAULT_LANGUAGE=en
EMBED_COLOR=0x5865F2
```

### Services

The deployment includes:

1. **discord-bot**: The main Discord bot application
2. **mongodb**: MongoDB database with authentication
3. **mongo-backup**: Automatic daily backups (keeps last 7 days)

### Maintenance

#### View Logs
```bash
# All services
docker-compose -f docker-compose.prod.yml logs -f

# Just the bot
docker-compose -f docker-compose.prod.yml logs -f discord-bot

# Just MongoDB
docker-compose -f docker-compose.prod.yml logs -f mongodb
```

#### Restart Services
```bash
# Restart everything
docker-compose -f docker-compose.prod.yml restart

# Restart just the bot
docker-compose -f docker-compose.prod.yml restart discord-bot
```

#### Stop Services
```bash
docker-compose -f docker-compose.prod.yml down
```

#### Update Bot
```bash
git pull
docker-compose -f docker-compose.prod.yml build discord-bot
docker-compose -f docker-compose.prod.yml up -d discord-bot
```

#### Manual Backup
```bash
docker-compose -f docker-compose.prod.yml exec mongodb mongodump \
  --username=$MONGO_USER \
  --password=$MONGO_PASSWORD \
  --authenticationDatabase=admin \
  --db=whiteout_survival_crm \
  --out=/backups/manual-$(date +%Y%m%d-%H%M%S)
```

### Monitoring

#### Health Checks
Both services include health checks:
- Bot: Checks Discord library is functional
- MongoDB: Checks database is responding

#### Check Status
```bash
docker-compose -f docker-compose.prod.yml ps
```

### Security Best Practices

1. **Environment Files**
   - Never commit `.env.production` to git
   - Use strong, unique passwords
   - Rotate credentials regularly

2. **Network Security**
   - MongoDB is not exposed to the internet
   - Only the bot can access MongoDB
   - Use firewall rules on your server

3. **Backups**
   - Automatic daily backups are enabled
   - Test restore procedures regularly
   - Consider off-site backup storage

4. **Updates**
   - Keep Docker images updated
   - Monitor Discord.py for security updates
   - Update MongoDB regularly

### Troubleshooting

#### Bot Won't Start
1. Check Discord token is valid
2. Verify MongoDB is running: `docker-compose -f docker-compose.prod.yml ps`
3. Check logs: `docker-compose -f docker-compose.prod.yml logs discord-bot`

#### MongoDB Connection Issues
1. Verify credentials in `.env.production`
2. Check MongoDB logs: `docker-compose -f docker-compose.prod.yml logs mongodb`
3. Ensure MongoDB is healthy: `docker-compose -f docker-compose.prod.yml ps`

#### Permission Errors
1. Bot needs appropriate Discord permissions
2. Check bot role position in Discord server
3. Verify GUILD_ID is correct

#### Required Bot Permissions
When inviting the bot, ensure these permissions:
- **Manage Roles** - For verification and alliance roles
- **Manage Channels** - To create alliance channels
- **Send Messages** - Basic messaging
- **Embed Links** - For rich embeds
- **Mention Everyone** - For moderator announcements
- **Manage Messages** - For moderation
- **Read Message History** - For event management
- **Add Reactions** - For UI interactions
- **View Channels** - To see all channels

#### Post-Deployment Setup
1. **Create first moderator**: Use `/add-moderator @user` as admin
2. **Sync commands**: Commands may take up to 1 hour to appear globally
3. **Test verification**: Ensure API connection works
4. **Check channel creation**: Verify bot can create categories/channels

### Resource Usage

Typical resource usage:
- **Bot**: 100-200MB RAM, minimal CPU
- **MongoDB**: 200-500MB RAM, varies with data
- **Disk**: 1-5GB depending on data and backups

### Scaling

For larger deployments:
1. Use external MongoDB cluster (MongoDB Atlas)
2. Run multiple bot instances with sharding
3. Use Redis for caching
4. Implement proper logging aggregation

## 📞 Support

For issues specific to deployment, check:
1. Docker logs
2. MongoDB connection
3. Network connectivity
4. Discord API status

For bot-specific issues, check the main documentation.