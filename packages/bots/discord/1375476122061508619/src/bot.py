import discord
from discord.ext import commands
import asyncio
import os

from src.config import Config
from locales import get_localization
from src.database import get_database
from src.services.cron_manager import CronManager
from src.services.admin_message_handler import AdminMessageHandler

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
        self.admin_message_handler = None
    
    async def setup_hook(self):
        """Carica i cogs e prepara il bot"""
        # Inizializza indici database
        await self.db.create_indexes()
        
        # Carica cogs
        cogs_dir = os.path.join(os.path.dirname(__file__), 'cogs')
        for filename in os.listdir(cogs_dir):
            if filename.endswith('.py') and not filename.startswith('_') and filename != 'base.py':
                await self.load_extension(f'src.cogs.{filename[:-3]}')
                print(f"Caricato cog: {filename[:-3]}")
        
        # Carica server stats service come cog
        from src.services.server_stats import ServerStats
        await self.add_cog(ServerStats(self))
        print("Caricato cog: server_stats")
    
    async def on_ready(self):
        print(f'{self.user} è online!')
        print(f'ID Bot: {self.user.id}')
        
        # Verifica che il bot sia nel server autorizzato
        authorized_guild = self.get_guild(Config.GUILD_ID)
        if not authorized_guild:
            print(f"❌ ERRORE: Il bot non è nel server autorizzato (ID: {Config.GUILD_ID})")
            print("❌ Il bot si spegnerà per motivi di sicurezza.")
            await self.close()
            return
        
        print(f"✅ Bot autorizzato per il server: {authorized_guild.name} (ID: {authorized_guild.id})")
        
        # Lascia tutti i server non autorizzati
        for guild in self.guilds:
            if guild.id != Config.GUILD_ID:
                print(f"⚠️ Uscendo dal server non autorizzato: {guild.name} (ID: {guild.id})")
                await guild.leave()
        
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
        
        # Avvia l'Admin Message Handler
        self.admin_message_handler = AdminMessageHandler(self)
        await self.admin_message_handler.start()
        
        # Sincronizza i comandi slash solo per il guild autorizzato
        try:
            synced = await self.tree.sync(guild=authorized_guild)
            print(f"Sincronizzati {len(synced)} comandi slash per {authorized_guild.name}")
        except Exception as e:
            print(f"Errore sincronizzazione comandi: {e}")
    
    async def on_guild_join(self, guild):
        """Quando il bot viene aggiunto a un nuovo server"""
        if guild.id != Config.GUILD_ID:
            print(f"⚠️ Tentativo di aggiunta a server non autorizzato: {guild.name} (ID: {guild.id})")
            print(f"⚠️ Uscendo dal server...")
            await guild.leave()
        else:
            print(f"✅ Aggiunto al server autorizzato: {guild.name}")
    
    async def close(self):
        """Chiudi connessioni prima di spegnere il bot"""
        # Ferma il CronManager
        if self.cron_manager:
            await self.cron_manager.stop()
            
        # Ferma l'Admin Message Handler
        if self.admin_message_handler:
            await self.admin_message_handler.stop()
        
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