import os
from dotenv import load_dotenv
from typing import List, Dict, Any

load_dotenv()

class Config:
    """Enhanced configuration with better organization and validation."""
    
    # Discord Configuration
    DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
    GUILD_ID = int(os.getenv('GUILD_ID', '0'))
    
    # API Configuration
    GAME_API_URL = os.getenv('API_BASE_URL', 'https://wos-giftcode-api.centurygame.com/api/player')
    API_KEY = os.getenv('API_KEY', '')
    API_TIMEOUT = int(os.getenv('API_TIMEOUT', '30'))
    
    # Database Configuration
    MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
    MONGODB_DB = os.getenv('MONGODB_DB', 'whiteout_survival_crm')
    MONGODB_MAX_CONNECTIONS = int(os.getenv('MONGODB_MAX_CONNECTIONS', '10'))
    MONGODB_MIN_CONNECTIONS = int(os.getenv('MONGODB_MIN_CONNECTIONS', '1'))
    
    # Bot Settings
    DEFAULT_LANGUAGE = os.getenv('DEFAULT_LANGUAGE', 'it')
    COMMAND_PREFIX = os.getenv('COMMAND_PREFIX', '!')
    
    # UI Configuration
    embed_color_env = os.getenv('EMBED_COLOR', '0x5865F2')
    EMBED_COLOR = int(embed_color_env, 16) if embed_color_env.startswith('0x') else int(embed_color_env)
    
    # Timeouts (in seconds)
    VERIFICATION_TIMEOUT = int(os.getenv('VERIFICATION_TIMEOUT', '600'))  # 10 minutes
    INTERACTION_TIMEOUT = int(os.getenv('INTERACTION_TIMEOUT', '300'))   # 5 minutes
    SESSION_TIMEOUT = int(os.getenv('SESSION_TIMEOUT', '3600'))         # 1 hour
    
    # Rate Limiting
    RATE_LIMIT_COMMANDS = int(os.getenv('RATE_LIMIT_COMMANDS', '10'))   # commands per minute
    RATE_LIMIT_VERIFICATIONS = int(os.getenv('RATE_LIMIT_VERIFICATIONS', '5'))  # attempts per 30 min
    
    # Feature Flags
    ALLOW_SKIP_VERIFICATION = os.getenv('ALLOW_SKIP_VERIFICATION', 'false').lower() == 'true'
    ENABLE_API_VERIFICATION = os.getenv('ENABLE_API_VERIFICATION', 'true').lower() == 'true'
    ENABLE_AUTO_ROLES = os.getenv('ENABLE_AUTO_ROLES', 'true').lower() == 'true'
    ENABLE_WELCOME_DM = os.getenv('ENABLE_WELCOME_DM', 'true').lower() == 'true'
    
    # Tutorial and Help
    PLAYER_ID_TUTORIAL_IMAGE = os.getenv('PLAYER_ID_TUTORIAL_IMAGE', 
        'https://i.imgur.com/example.png')
    SUPPORT_SERVER_INVITE = os.getenv('SUPPORT_SERVER_INVITE', '')
    
    # Logging Configuration
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FORMAT = os.getenv('LOG_FORMAT', 'json')  # 'json' or 'text'
    
    # Channel Names and Categories
    VERIFICATION_CATEGORY = os.getenv('VERIFICATION_CATEGORY', 'Welcome')
    ALLIANCE_CATEGORY = os.getenv('ALLIANCE_CATEGORY', 'Alliances')
    ADMIN_CATEGORY = os.getenv('ADMIN_CATEGORY', 'Administration')
    
    # Role Names (defaults, can be localized)
    ROLE_VERIFIED = os.getenv('ROLE_VERIFIED', 'Verified')
    ROLE_UNVERIFIED = os.getenv('ROLE_UNVERIFIED', 'Unverified')
    ROLE_MODERATOR = os.getenv('ROLE_MODERATOR', 'Moderator')
    ROLE_ADMIN = os.getenv('ROLE_ADMIN', 'Admin')
    
    # Alliance Settings
    MAX_ALLIANCE_NAME_LENGTH = int(os.getenv('MAX_ALLIANCE_NAME_LENGTH', '50'))
    MIN_ALLIANCE_NAME_LENGTH = int(os.getenv('MIN_ALLIANCE_NAME_LENGTH', '2'))
    ALLIANCE_ROLES = ['R1', 'R2', 'R3', 'R4', 'R5']
    
    # Pagination Settings
    ITEMS_PER_PAGE = int(os.getenv('ITEMS_PER_PAGE', '10'))
    MAX_PAGES = int(os.getenv('MAX_PAGES', '100'))
    
    # Cache Settings
    CACHE_TTL = int(os.getenv('CACHE_TTL', '300'))  # 5 minutes
    CACHE_MAX_SIZE = int(os.getenv('CACHE_MAX_SIZE', '1000'))
    
    # Security
    ENABLE_COMMAND_LOGS = os.getenv('ENABLE_COMMAND_LOGS', 'true').lower() == 'true'
    ENABLE_ERROR_REPORTING = os.getenv('ENABLE_ERROR_REPORTING', 'true').lower() == 'true'
    MAX_ERROR_REPORTS_PER_USER = int(os.getenv('MAX_ERROR_REPORTS_PER_USER', '10'))
    
    @classmethod
    def validate(cls) -> bool:
        """Validate required configuration values."""
        errors = []
        
        if not cls.DISCORD_TOKEN:
            errors.append("DISCORD_TOKEN not configured")
        
        if cls.GUILD_ID == 0:
            errors.append("GUILD_ID not configured")
        
        if not cls.MONGODB_URI:
            errors.append("MONGODB_URI not configured")
        
        if errors:
            raise ValueError(f"Configuration errors: {', '.join(errors)}")
        
        return True
    
    @classmethod
    def get_feature_flags(cls) -> Dict[str, bool]:
        """Get all feature flags."""
        return {
            'skip_verification': cls.ALLOW_SKIP_VERIFICATION,
            'api_verification': cls.ENABLE_API_VERIFICATION,
            'auto_roles': cls.ENABLE_AUTO_ROLES,
            'welcome_dm': cls.ENABLE_WELCOME_DM,
            'command_logs': cls.ENABLE_COMMAND_LOGS,
            'error_reporting': cls.ENABLE_ERROR_REPORTING
        }
    
    @classmethod
    def get_timeout_settings(cls) -> Dict[str, int]:
        """Get all timeout settings."""
        return {
            'verification': cls.VERIFICATION_TIMEOUT,
            'interaction': cls.INTERACTION_TIMEOUT,
            'session': cls.SESSION_TIMEOUT
        }