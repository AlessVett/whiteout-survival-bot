import discord
from functools import wraps
from src.config import Config

def guild_only():
    """Decorator per assicurarsi che i comandi funzionino solo nel server autorizzato"""
    def decorator(func):
        @wraps(func)
        async def wrapper(self, interaction: discord.Interaction, *args, **kwargs):
            if interaction.guild_id != Config.GUILD_ID:
                await interaction.response.send_message(
                    "❌ This bot is configured to work only in the authorized server.",
                    ephemeral=True
                )
                return
            return await func(self, interaction, *args, **kwargs)
        return wrapper
    return decorator

def is_authorized_guild(guild_id: int) -> bool:
    """Verifica se un guild ID è autorizzato"""
    return guild_id == Config.GUILD_ID