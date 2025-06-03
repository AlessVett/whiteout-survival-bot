# Contributing to DWOS

First off, thank you for considering contributing to DWOS! It's people like you that make DWOS such a great tool for the WhiteOut Survival community.

## Code of Conduct

By participating in this project, you are expected to uphold our Code of Conduct:
- Be respectful and inclusive
- Welcome newcomers and help them get started
- Focus on what is best for the community
- Show empathy towards other community members

## Project Overview

DWOS is a distributed platform for WhiteOut Survival community management. While currently focused on Discord, we're building a multi-platform ecosystem including:
- Discord Bot (current)
- Telegram Bot (planned)
- KakaoTalk Bot (planned)
- WhatsApp Business Integration (planned)
- FastAPI Gateway (planned)
- Analytics Dashboard (planned)

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check existing issues to avoid duplicates. When you create a bug report, include:

- **Platform**: Which bot/service is affected (Discord, Telegram, API, etc.)
- **Clear title**: Descriptive summary of the issue
- **Steps to reproduce**: Exact steps to trigger the bug
- **Expected vs actual behavior**: What should happen vs what happens
- **Screenshots/logs**: Visual evidence or error messages
- **Environment**: OS, Python version, platform-specific details

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion:

- **Specify the platform(s)**: Which bots/services would benefit
- **Use a clear title**: Descriptive summary of the enhancement
- **Detailed description**: What, why, and how
- **User impact**: How this helps the community
- **Implementation ideas**: Technical suggestions (optional)

### Pull Requests

1. **Fork the repository** and create your branch from `main`
2. **Follow the setup instructions** for your target platform
3. **Make your changes** following our coding standards
4. **Test your changes** thoroughly
5. **Update documentation** if needed
6. **Submit a pull request** with a clear description

## Development Setup

### Prerequisites

- Python 3.11 or higher
- MongoDB instance
- Platform-specific developer accounts (Discord, Telegram, etc.)

### Project Structure

```
dwos/
├── packages/
│   ├── bots/
│   │   ├── discord/          # Discord bot implementation
│   │   ├── telegram/         # Telegram bot (future)
│   │   └── kakaotalk/        # KakaoTalk bot (future)
│   ├── api/                  # FastAPI gateway (future)
│   ├── shared/               # Shared libraries
│   └── analytics/            # Analytics service (future)
├── configs/                  # Shared configurations
└── docs/                     # Documentation
```

### Platform-Specific Setup

#### Discord Bot

```bash
cd packages/bots/discord/1375476122061508619
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Configure .env with Discord credentials
python main.py
```

#### Telegram Bot (Future)

```bash
cd packages/bots/telegram
# Setup instructions will be added
```

#### FastAPI Gateway (Future)

```bash
cd packages/api
# Setup instructions will be added
```

## Coding Standards

### General Guidelines

- **Language**: Python 3.11+ for backend services
- **Style**: Follow [PEP 8](https://pep8.org/)
- **Formatting**: Use Black for Python code
- **Type hints**: Required for all functions
- **Documentation**: Docstrings for all public functions
- **Testing**: Unit tests for business logic

### Platform-Specific Standards

#### Discord Bot
- Use discord.py 2.0+ features
- Implement commands as Cogs
- Use Views for UI components
- Support slash commands

#### Telegram Bot
- Use python-telegram-bot
- Implement inline keyboards
- Support both commands and conversations

#### API Development
- Use FastAPI with Pydantic models
- RESTful design principles
- OpenAPI documentation
- JWT authentication

### Commit Messages

Format:
```
<type>(<scope>): <subject>

<body>

<footer>
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Code style changes
- `refactor`: Code refactoring
- `test`: Test additions/changes
- `chore`: Maintenance tasks

Scopes:
- `discord`: Discord bot specific
- `telegram`: Telegram bot specific
- `api`: API gateway
- `shared`: Shared components
- `all`: Changes affecting multiple platforms

Example:
```
feat(discord): Add Korean language support

- Add ko.json translation file
- Update language selector with Korean option
- Test all commands with Korean locale

Closes #123
```

## Translation Guidelines

Translations are crucial for our multi-platform approach:

1. **Consistency**: Use same translations across all platforms
2. **Structure**: Maintain JSON structure from English files
3. **Placeholders**: Keep variables like `{username}` unchanged
4. **Context**: Consider platform-specific terminology
5. **Testing**: Verify on actual platform

### Adding a New Language

1. Create translation files in all platforms:
   - `/packages/bots/discord/*/locales/<lang>.json`
   - `/packages/bots/telegram/*/locales/<lang>.json`
   - `/packages/shared/locales/<lang>.json`

2. Update language selectors in each platform

3. Test thoroughly on each platform

## Testing

### Unit Tests
- Test business logic independently
- Mock external dependencies
- Aim for 80% coverage

### Integration Tests
- Test platform-specific features
- Verify database operations
- Check API integrations

### Platform Testing
- **Discord**: Test with different server permissions
- **Telegram**: Test in groups and private chats
- **API**: Test rate limiting and authentication

## Contributing New Platforms

Want to add support for a new platform? Here's how:

1. **Propose the platform**: Open an issue explaining:
   - Why this platform is valuable
   - User base in WhiteOut Survival community
   - Technical feasibility
   - Maintenance commitment

2. **Design the architecture**:
   - Follow existing bot structure
   - Reuse shared components
   - Plan for localization

3. **Implement core features**:
   - User verification
   - Alliance management
   - Event scheduling
   - Multi-language support

4. **Documentation**:
   - Setup instructions
   - Platform-specific features
   - API documentation

## Pull Request Process

1. **Ensure compatibility**: Changes shouldn't break other platforms
2. **Update documentation**: README, API docs, inline comments
3. **Add tests**: Unit and integration tests
4. **Pass CI/CD**: All checks must pass
5. **Request review**: From platform maintainers

### Review Criteria

- **Code quality**: Clean, maintainable code
- **Platform standards**: Follows platform best practices
- **Performance**: Efficient resource usage
- **Security**: No exposed credentials or vulnerabilities
- **User experience**: Intuitive and consistent

## Community

### Getting Help

- **Issues**: For bugs and features
- **Discussions**: For questions and ideas
- **Discord**: Join our development server
- **Email**: support@wos-2630.fun

### Platform Champions

We're looking for maintainers for each platform:
- **Discord**: Active maintainer
- **Telegram**: Looking for maintainer
- **KakaoTalk**: Looking for maintainer
- **WhatsApp**: Looking for maintainer

## Priority Areas

### High Priority
- Telegram bot implementation
- FastAPI gateway development
- Shared authentication system
- Cross-platform event synchronization

### Medium Priority
- Analytics dashboard
- Admin panel
- KakaoTalk integration
- Performance optimizations

### Future Exploration
- WhatsApp Business API
- WeChat integration
- Mobile app
- Voice assistants

## Recognition

Contributors are recognized through:
- Contributors list in README
- Credits in release notes
- Platform-specific champion roles
- Community highlights

Thank you for contributing to DWOS! Together we're building the future of gaming community management. 🎮🌍🚀