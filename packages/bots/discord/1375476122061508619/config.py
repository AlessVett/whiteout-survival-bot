import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
    GAME_API_URL = os.getenv('GAME_API_URL', 'https://wos-giftcode-api.centurygame.com/api/player')
    GUILD_ID = int(os.getenv('GUILD_ID', '0'))
    
    MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
    MONGODB_DB = os.getenv('MONGODB_DB', 'whiteout_survival_crm')
    
    DEFAULT_LANGUAGE = os.getenv('DEFAULT_LANGUAGE', 'it')
    
    EMBED_COLOR = 0x5865F2
    VERIFICATION_TIMEOUT = 600  # 10 minuti
    
    # URL dell'immagine che mostra dove trovare l'ID del giocatore
    PLAYER_ID_TUTORIAL_IMAGE = os.getenv('PLAYER_ID_TUTORIAL_IMAGE', 
        'https://i.imgur.com/example.png')  # Sostituire con URL reale
    
    @classmethod
    def validate(cls):
        if not cls.DISCORD_TOKEN:
            raise ValueError("DISCORD_TOKEN non configurato")
        if cls.GUILD_ID == 0:
            raise ValueError("GUILD_ID non configurato")
        return True