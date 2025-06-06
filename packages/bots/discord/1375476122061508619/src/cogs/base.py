"""
Base Cog class with common functionality for all cogs.

This module provides the foundational classes for all Discord cogs in the bot,
including standardized error handling, logging, database access, and user interaction management.

Classes:
    BaseCog: Base class for all Discord cogs with common functionality
    InteractionHandler: Mixin for managing Discord interaction states
"""

import discord
from discord.ext import commands
from typing import Optional, Dict, Any, Union
import logging
import traceback
from datetime import datetime

from src.database import get_database
from src.config import Config
from locales import t


class BaseCog(commands.Cog):
    """
    Base class for all cogs with common functionality.
    
    Provides standardized error handling, logging, database access, and utility methods
    that are commonly needed across all cogs in the bot.
    
    Attributes:
        bot: The Discord bot instance
        db: Database connection instance
        logger: Logger instance for this cog
        _error_cooldowns: Dictionary tracking error message cooldowns per user
    """
    
    def __init__(self, bot: commands.Bot) -> None:
        """
        Initialize the base cog.
        
        Args:
            bot: The Discord bot instance
        """
        self.bot = bot
        self.db = get_database()
        self.logger = logging.getLogger(f"cog.{self.__class__.__name__}")
        self._error_cooldowns: Dict[int, datetime] = {}
    
    def get_user_lang(self, user_data: Optional[Dict[str, Any]]) -> str:
        """
        Get user language from database or use default.
        
        Args:
            user_data: User data dictionary from database
            
        Returns:
            Language code (e.g., 'en', 'it')
        """
        return user_data.get('language', Config.DEFAULT_LANGUAGE) if user_data else Config.DEFAULT_LANGUAGE
    
    async def get_user_data(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Fetch user data from database with error handling.
        
        Args:
            user_id: Discord user ID
            
        Returns:
            User data dictionary or None if not found/error
        """
        try:
            return await self.db.get_user(user_id)
        except Exception as e:
            self.logger.error(f"Failed to fetch user {user_id}: {e}")
            return None
    
    async def ensure_user_exists(self, user_id: int, username: str) -> Dict[str, Any]:
        """
        Ensure user exists in database, create if not.
        
        Args:
            user_id: Discord user ID
            username: Discord username
            
        Returns:
            User data dictionary
        """
        user_data = await self.get_user_data(user_id)
        if not user_data:
            user_data = await self.db.create_user(user_id, username)
        return user_data
    
    async def send_error_message(
        self, 
        interaction: discord.Interaction, 
        message_key: str,
        lang: str = None,
        ephemeral: bool = True,
        **kwargs
    ):
        """Send a localized error message to the user."""
        if not lang:
            user_data = await self.get_user_data(interaction.user.id)
            lang = self.get_user_lang(user_data)
        
        error_message = t(message_key, lang, **kwargs)
        
        if interaction.response.is_done():
            await interaction.followup.send(error_message, ephemeral=ephemeral)
        else:
            await interaction.response.send_message(error_message, ephemeral=ephemeral)
    
    async def send_success_message(
        self,
        interaction: discord.Interaction,
        message_key: str,
        lang: str = None,
        ephemeral: bool = True,
        **kwargs
    ):
        """Send a localized success message to the user."""
        if not lang:
            user_data = await self.get_user_data(interaction.user.id)
            lang = self.get_user_lang(user_data)
        
        success_message = t(message_key, lang, **kwargs)
        
        if interaction.response.is_done():
            await interaction.followup.send(success_message, ephemeral=ephemeral)
        else:
            await interaction.response.send_message(success_message, ephemeral=ephemeral)
    
    async def handle_cog_error(
        self,
        interaction: discord.Interaction,
        error: Exception,
        custom_message: Optional[str] = None
    ):
        """Handle errors in a standardized way."""
        user_id = interaction.user.id
        
        # Rate limit error messages per user
        now = datetime.utcnow()
        if user_id in self._error_cooldowns:
            last_error = self._error_cooldowns[user_id]
            if (now - last_error).total_seconds() < 60:  # 1 minute cooldown
                return
        
        self._error_cooldowns[user_id] = now
        
        # Log the error
        self.logger.error(
            f"Error in {self.__class__.__name__} for user {user_id}: {error}",
            exc_info=True
        )
        
        # Get user language
        user_data = await self.get_user_data(user_id)
        lang = self.get_user_lang(user_data)
        
        # Send error message
        error_message = custom_message or t("errors.generic_error", lang)
        
        try:
            if interaction.response.is_done():
                await interaction.followup.send(error_message, ephemeral=True)
            else:
                await interaction.response.send_message(error_message, ephemeral=True)
        except discord.HTTPException:
            # If we can't send a message, just log it
            self.logger.error(f"Failed to send error message to user {user_id}")
    
    def cog_unload(self):
        """Cleanup when cog is unloaded."""
        self.logger.info(f"{self.__class__.__name__} unloaded")
    
    async def cog_command_error(self, ctx: commands.Context, error: commands.CommandError):
        """Handle command errors."""
        if isinstance(error, commands.CommandNotFound):
            return
        
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"Missing required argument: {error.param.name}")
        elif isinstance(error, commands.BadArgument):
            await ctx.send(f"Bad argument: {error}")
        elif isinstance(error, commands.CheckFailure):
            await ctx.send("You don't have permission to use this command.")
        else:
            self.logger.error(f"Unhandled command error: {error}", exc_info=True)
            await ctx.send("An error occurred while processing your command.")
    
    async def cog_app_command_error(
        self,
        interaction: discord.Interaction,
        error: discord.app_commands.AppCommandError
    ):
        """Handle application command errors."""
        await self.handle_cog_error(interaction, error)


class InteractionHandler:
    """Mixin for handling Discord interactions with proper state management."""
    
    def __init__(self):
        self._interaction_states: Dict[int, Dict[str, Any]] = {}
    
    def save_interaction_state(self, user_id: int, state: Dict[str, Any]):
        """Save interaction state for a user."""
        self._interaction_states[user_id] = state
    
    def get_interaction_state(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get saved interaction state for a user."""
        return self._interaction_states.get(user_id)
    
    def clear_interaction_state(self, user_id: int):
        """Clear interaction state for a user."""
        self._interaction_states.pop(user_id, None)
    
    async def defer_interaction(self, interaction: discord.Interaction, ephemeral: bool = False):
        """Safely defer an interaction."""
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=ephemeral)