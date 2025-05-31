# 🏔️ WhiteOut Survival Discord Bot

> A comprehensive Discord bot designed for WhiteOut Survival alliances, featuring automated player verification, alliance management, event scheduling, and cross-alliance coordination.

[![Discord.py](https://img.shields.io/badge/discord.py-2.3.2-blue.svg)](https://github.com/Rapptz/discord.py)
[![Python](https://img.shields.io/badge/python-3.11+-yellow.svg)](https://www.python.org)
[![MongoDB](https://img.shields.io/badge/mongodb-7.0-green.svg)](https://www.mongodb.com)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://www.docker.com)

## 🎯 Introduction

This bot transforms your Discord server into a powerful management hub for WhiteOut Survival alliances. It automates player verification through the game's API, creates organized alliance channels, manages events with reminders, and facilitates state-wide coordination between R5 leaders.

### Key Features

- 🔐 **Automated Player Verification** - Validates game IDs via official API
- 🏛️ **Alliance Management** - Hierarchical roles (R1-R5) with dedicated channels
- 📅 **Event System** - Schedule SvS, KE, Trap events with automatic reminders
- 🌐 **Multi-language Support** - English and Italian interfaces
- 👑 **R5 Council** - State-wide leadership coordination channel
- 📊 **Server Statistics** - Real-time member and alliance tracking
- 🎁 **Gift Code Sharing** - Dedicated channels for alliance gift codes
- 📰 **Moderator Tools** - News announcements and gift code broadcasting

## 📁 Project Structure

```
whiteout-survival-bot/
├── main.py                      # Entry point
├── requirements.txt             # Python dependencies
├── .env.example                 # Environment template
├── docker-compose.yml           # Development stack
├── docker-compose.prod.yml      # Production stack
├── README.md                    # This file
│
├── src/                         # Source code
│   ├── bot.py                  # Discord bot client
│   ├── config.py               # Configuration
│   ├── database.py             # MongoDB connection
│   │
│   ├── cogs/                   # Command modules
│   │   ├── verification.py     # Player verification
│   │   ├── events.py          # Event management
│   │   ├── commands.py        # Admin commands
│   │   ├── alliance_change.py # Alliance switching
│   │   └── moderator.py       # Moderator commands
│   │
│   ├── views/                  # UI components
│   │   ├── views.py           # Base verification UI
│   │   ├── dashboard_views.py # User dashboard
│   │   ├── event_views.py     # Event UI
│   │   ├── alliance_views.py  # Alliance UI
│   │   └── moderator_views.py # Moderator UI
│   │
│   ├── services/               # Business logic
│   │   ├── alliance_channels.py # Channel management
│   │   ├── cron_manager.py     # Event scheduler
│   │   └── server_stats.py     # Statistics
│   │
│   └── utils/                  # Utilities
│       └── utils.py           # Helper functions
│
├── locales/                    # Translations
│   ├── en.json                # English
│   └── it.json                # Italian
│
├── docker/                     # Docker files
│   ├── Dockerfile             # Container config
│   └── mongo-init.js          # DB initialization
│
├── scripts/                    # Utility scripts
│   └── deploy.sh              # Deployment script
│
└── docs/                       # Documentation
    └── DEPLOYMENT.md          # Deployment guide
```

### Core Components

#### 🤖 **Bot Core** (`src/bot.py`)
The main Discord bot client that loads all cogs and initializes services.

#### 🗄️ **Database** (`src/database.py`)
MongoDB integration using Motor for async operations. Manages:
- User profiles and verification status
- Alliance information and channels
- Events and reminders
- Communication channels

#### ✅ **Verification System** (`src/cogs/verification.py`)
Handles the player verification flow:
1. User clicks verification button
2. Enters game ID and nickname
3. API validates the player exists
4. User selects alliance and role
5. Bot assigns roles and creates channels

#### 📅 **Event Management** (`src/cogs/events.py`, `src/views/event_views.py`)
Complete event system with:
- Multiple event types (SvS, KE, Trap, Bear Trap, Custom)
- Recurring events (daily, 2-day, weekly, monthly)
- Reminders (15min, 30min, 1h, 2h, 24h before)
- Automatic cleanup of past events

#### 🏛️ **Alliance Channels** (`src/services/alliance_channels.py`)
Automatically creates when R5 joins:
- `{alliance}-general` - Main alliance chat
- `{alliance}-reminders` - Event notifications
- `{alliance}-gift-codes` - Code sharing
- `{alliance}-r4-r5-only` - Leadership channel
- `{alliance}-university` - Tips and guides
- `r5-council` - State-wide R5 coordination

#### ⏰ **Cron Manager** (`src/services/cron_manager.py`)
Background task scheduler that:
- Monitors upcoming events
- Sends reminders at configured times
- Handles recurring event scheduling
- Tracks reminder delivery status

#### 📊 **Server Statistics** (`src/services/server_stats.py`)
Updates voice channels with live stats:
- Total members
- Verified members
- Number of alliances
- Alliance member counts

#### 🌍 **Localization** (`locales/`)
Full multi-language support:
- User-specific language preferences
- All UI elements translated
- Commands work in both languages
- Alliance infrastructure in English

#### 📰 **Moderator System** (`src/cogs/moderator.py`)
Server-wide moderation tools:
- `/send-news` - Send formatted news to any channel
- `/notify-gift-code` - Broadcast codes to all alliance gift channels
- `/add-moderator` - Grant moderator permissions
- `/remove-moderator` - Revoke moderator permissions
- Automatic Moderator role creation with appropriate permissions

## 🛡️ Roles & Permissions

### Discord Roles Created by Bot
- **Verified** - Players who completed verification
- **Unverified** - New members awaiting verification
- **No Alliance** - Verified players without an alliance
- **Other State** - Players from different states
- **{Alliance}** - Alliance membership role
- **{Alliance} - R1/R2/R3/R4/R5** - Rank within alliance
- **Moderator** - Server moderators with special commands

### Permission Levels
1. **Regular Users** - Access to verification and dashboard
2. **R4/R5** - Can manage alliance events and members
3. **Moderators** - Can send news and gift codes server-wide
4. **Administrators** - Full bot management and debug commands

## 🚀 Deployment

For production deployment instructions, see [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

## 🔮 Future Development

### Planned Features

#### 📈 **Analytics Dashboard**
- Alliance growth tracking
- Event participation statistics
- Member activity reports
- Resource donation tracking

#### ⚔️ **Battle Management**
- SvS matchup coordination
- Battle formation templates
- Rally organization tools
- Defense alert system

#### 🏆 **Achievement System**
- Player milestones tracking
- Alliance achievements
- Leaderboards
- Reward distribution

#### 🤝 **Diplomacy Tools**
- NAP (Non-Aggression Pact) management
- Alliance relationship tracking
- Cross-state communication
- Treaty notifications

#### 📱 **Mobile Companion**
- Web dashboard for mobile access
- Push notifications for events
- Quick actions via web interface
- Real-time alliance chat bridge

#### 🧮 **Game Calculators**
- Troop training calculators
- Resource calculators
- Building upgrade planners
- Research path optimization

#### 🎮 **Mini-Games**
- Alliance trivia contests
- Prediction games for SvS
- Member engagement activities
- Reward point system

### Technical Improvements

- **Sharding Support** - Scale to multiple Discord servers
- **Redis Caching** - Improved performance for large alliances
- **API Rate Limiting** - Better handling of Discord limits
- **Webhook Integration** - External service notifications
- **Custom Commands** - Alliance-specific command creation

## 💝 Support Development

If you find this bot helpful for your alliance, consider supporting its development!

<a href="https://ko-fi.com/faltehd" target="_blank">
  <img height="36" style="border:0px;height:36px;" src="https://cdn.ko-fi.com/cdn/kofi2.png?v=3" border="0" alt="Buy Me a Coffee at ko-fi.com" />
</a>

Your support helps:
- 🖥️ Server hosting costs
- 🔧 Continuous development
- 🆕 New feature implementation
- 🐛 Bug fixes and maintenance
- 📚 Documentation improvements

## 🤝 Contributing

We welcome contributions! Areas where you can help:

1. **Translations** - Add support for more languages
2. **Features** - Implement items from the roadmap
3. **Bug Reports** - Help identify and fix issues
4. **Documentation** - Improve guides and examples
5. **Testing** - Test new features and provide feedback

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- WhiteOut Survival community for feedback and suggestions
- Discord.py team for the excellent library
- All alliance leaders who helped shape the features
- Contributors who helped improve the bot

---

<div align="center">
  <p>Built with ❄️ for the WhiteOut Survival community</p>
  <p>
    <a href="https://discord.gg/yourserver">Discord</a> •
    <a href="https://github.com/yourusername/repo/issues">Issues</a> •
    <a href="DEPLOYMENT.md">Deploy</a>
  </p>
</div>