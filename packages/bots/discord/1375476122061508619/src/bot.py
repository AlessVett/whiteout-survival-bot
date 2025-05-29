import discord
from discord.ext import commands
import asyncio
import os

from src.config import Config
from locales import get_localization
from src.database import get_database
from src.services.cron_manager import CronManager

class CRMBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        
        super().__init__(
            command_prefix='!',
            intents=intents,
            help_command=None
        )
        
        self.localization = get_localization()
        self.db = get_database()
        self.cron_manager = None
    
    async def setup_hook(self):
        """Carica i cogs e prepara il bot"""
        # Inizializza indici database
        await self.db.create_indexes()
        
        # Carica cogs
        cogs_dir = os.path.join(os.path.dirname(__file__), 'cogs')
        for filename in os.listdir(cogs_dir):
            if filename.endswith('.py') and not filename.startswith('_'):
                await self.load_extension(f'src.cogs.{filename[:-3]}')
                print(f"Caricato cog: {filename[:-3]}")
        
        # Carica server stats service come cog
        from src.services.server_stats import ServerStats
        await self.add_cog(ServerStats(self))
        print("Caricato cog: server_stats")
    
    async def on_ready(self):
        print(f'{self.user} è online!')
        print(f'ID Bot: {self.user.id}')
        
        # Imposta presenza
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="WhiteoutSurvival SvS"
            )
        )
        
        # Avvia il CronManager
        self.cron_manager = CronManager(self)
        await self.cron_manager.start()
        
        # Sincronizza i comandi slash
        try:
            synced = await self.tree.sync()
            print(f"Sincronizzati {len(synced)} comandi slash")
        except Exception as e:
            print(f"Errore sincronizzazione comandi: {e}")
    
    async def close(self):
        """Chiudi connessioni prima di spegnere il bot"""
        # Ferma il CronManager
        if self.cron_manager:
            await self.cron_manager.stop()
        
        await self.db.close()
        await super().close()

async def main():
    # Valida configurazione
    Config.validate()
    
    # Crea e avvia il bot
    bot = CRMBot()
    await bot.start(Config.DISCORD_TOKEN)

if __name__ == '__main__':
    asyncio.run(main())