"""
Base View classes with common functionality for all Discord UI components.

This module provides foundational classes for Discord UI components including views,
modals, and specialized components like paginated views and confirmation dialogs.

Classes:
    BaseView: Base class for all Discord views with timeout and error handling
    PaginatedView: Generic paginated view for displaying lists of items
    ConfirmationView: Simple yes/no confirmation dialog
    BaseModal: Base class for Discord modals with error handling

Functions:
    Provides timeout handling, error management, and interaction tracking.
"""

import discord
from discord import ui
from typing import Optional, Dict, Any, List, Callable, TypeVar, Generic
import asyncio
from datetime import datetime, timedelta
import logging

from src.config import Config
from locales import t

T = TypeVar('T')


class BaseView(ui.View):
    """
    Base class for all Discord views with common functionality.
    
    Provides standardized timeout handling, error management, interaction tracking,
    and user permission checking for Discord UI views.
    
    Attributes:
        user_id: Optional user ID to restrict interactions to specific user
        lang: Language code for localized messages
        auto_defer: Whether to automatically defer interactions
        delete_on_timeout: Whether to delete the message on timeout
        message: The Discord message containing this view
        logger: Logger instance for this view
        _interaction_count: Number of interactions processed
        _last_interaction: Timestamp of last interaction
    """
    
    def __init__(
        self,
        *,
        timeout: float = 600,  # 10 minutes default
        user_id: Optional[int] = None,
        lang: str = "en",
        auto_defer: bool = True,
        delete_on_timeout: bool = False
    ) -> None:
        super().__init__(timeout=timeout)
        self.user_id = user_id
        self.lang = lang
        self.auto_defer = auto_defer
        self.delete_on_timeout = delete_on_timeout
        self.message: Optional[discord.Message] = None
        self.logger = logging.getLogger(f"view.{self.__class__.__name__}")
        self._interaction_count = 0
        self._last_interaction: Optional[datetime] = None
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Check if the interaction is valid."""
        # If user_id is set, only that user can interact
        if self.user_id and interaction.user.id != self.user_id:
            await interaction.response.send_message(
                t("errors.not_your_interaction", self.lang),
                ephemeral=True
            )
            return False
        
        # Update interaction tracking
        self._interaction_count += 1
        self._last_interaction = datetime.utcnow()
        
        # Auto-defer if enabled and not already done
        if self.auto_defer and not interaction.response.is_done():
            await interaction.response.defer()
        
        return True
    
    async def on_timeout(self):
        """Handle view timeout."""
        self.logger.info(f"View timed out after {self._interaction_count} interactions")
        
        # Disable all items
        for item in self.children:
            if isinstance(item, (ui.Button, ui.Select)):
                item.disabled = True
        
        # Update or delete message
        if self.message:
            try:
                if self.delete_on_timeout:
                    await self.message.delete()
                else:
                    await self.message.edit(view=self)
            except discord.HTTPException:
                pass
    
    async def on_error(
        self,
        interaction: discord.Interaction,
        error: Exception,
        item: ui.Item
    ):
        """Handle errors in view interactions."""
        self.logger.error(
            f"Error in {item.__class__.__name__} for user {interaction.user.id}: {error}",
            exc_info=True
        )
        
        error_message = t("errors.interaction_error", self.lang)
        
        try:
            if interaction.response.is_done():
                await interaction.followup.send(error_message, ephemeral=True)
            else:
                await interaction.response.send_message(error_message, ephemeral=True)
        except discord.HTTPException:
            pass
    
    def disable_all_items(self):
        """Disable all items in the view."""
        for item in self.children:
            if hasattr(item, 'disabled'):
                item.disabled = True
    
    def enable_all_items(self):
        """Enable all items in the view."""
        for item in self.children:
            if hasattr(item, 'disabled'):
                item.disabled = False
    
    async def update_message(self, **kwargs):
        """Update the message with new content."""
        if self.message:
            try:
                await self.message.edit(**kwargs)
            except discord.HTTPException as e:
                self.logger.error(f"Failed to update message: {e}")


class PaginatedView(BaseView, Generic[T]):
    """Base class for paginated views."""
    
    def __init__(
        self,
        items: List[T],
        *,
        items_per_page: int = 10,
        format_item: Optional[Callable[[T, int], str]] = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.items = items
        self.items_per_page = items_per_page
        self.format_item = format_item or (lambda item, idx: str(item))
        self.current_page = 0
        self.total_pages = max(1, (len(items) + items_per_page - 1) // items_per_page)
        
        # Add navigation buttons
        self._add_navigation_buttons()
    
    def _add_navigation_buttons(self):
        """Add navigation buttons to the view."""
        # First page button
        self.first_button = ui.Button(
            emoji="⏮️",
            style=discord.ButtonStyle.secondary,
            disabled=True
        )
        self.first_button.callback = self.go_to_first
        self.add_item(self.first_button)
        
        # Previous button
        self.prev_button = ui.Button(
            emoji="◀️",
            style=discord.ButtonStyle.secondary,
            disabled=True
        )
        self.prev_button.callback = self.go_to_previous
        self.add_item(self.prev_button)
        
        # Page indicator
        self.page_button = ui.Button(
            label=f"1/{self.total_pages}",
            style=discord.ButtonStyle.secondary,
            disabled=True
        )
        self.add_item(self.page_button)
        
        # Next button
        self.next_button = ui.Button(
            emoji="▶️",
            style=discord.ButtonStyle.secondary,
            disabled=self.total_pages <= 1
        )
        self.next_button.callback = self.go_to_next
        self.add_item(self.next_button)
        
        # Last page button
        self.last_button = ui.Button(
            emoji="⏭️",
            style=discord.ButtonStyle.secondary,
            disabled=self.total_pages <= 1
        )
        self.last_button.callback = self.go_to_last
        self.add_item(self.last_button)
    
    def get_page_items(self) -> List[T]:
        """Get items for the current page."""
        start = self.current_page * self.items_per_page
        end = start + self.items_per_page
        return self.items[start:end]
    
    def format_page(self) -> discord.Embed:
        """Format the current page as an embed."""
        embed = discord.Embed(
            title=f"Page {self.current_page + 1}/{self.total_pages}",
            color=Config.EMBED_COLOR
        )
        
        items = self.get_page_items()
        if items:
            description = []
            start_idx = self.current_page * self.items_per_page
            
            for idx, item in enumerate(items):
                description.append(self.format_item(item, start_idx + idx))
            
            embed.description = "\n".join(description)
        else:
            embed.description = t("pagination.no_items", self.lang)
        
        return embed
    
    def update_buttons(self):
        """Update navigation button states."""
        self.first_button.disabled = self.current_page == 0
        self.prev_button.disabled = self.current_page == 0
        self.next_button.disabled = self.current_page >= self.total_pages - 1
        self.last_button.disabled = self.current_page >= self.total_pages - 1
        self.page_button.label = f"{self.current_page + 1}/{self.total_pages}"
    
    async def go_to_first(self, interaction: discord.Interaction):
        """Go to the first page."""
        self.current_page = 0
        await self.update_page(interaction)
    
    async def go_to_previous(self, interaction: discord.Interaction):
        """Go to the previous page."""
        self.current_page = max(0, self.current_page - 1)
        await self.update_page(interaction)
    
    async def go_to_next(self, interaction: discord.Interaction):
        """Go to the next page."""
        self.current_page = min(self.total_pages - 1, self.current_page + 1)
        await self.update_page(interaction)
    
    async def go_to_last(self, interaction: discord.Interaction):
        """Go to the last page."""
        self.current_page = self.total_pages - 1
        await self.update_page(interaction)
    
    async def update_page(self, interaction: discord.Interaction):
        """Update the message with the current page."""
        self.update_buttons()
        embed = self.format_page()
        await interaction.response.edit_message(embed=embed, view=self)


class ConfirmationView(BaseView):
    """Simple confirmation view with Yes/No buttons."""
    
    def __init__(
        self,
        *,
        confirm_label: Optional[str] = None,
        cancel_label: Optional[str] = None,
        confirm_style: discord.ButtonStyle = discord.ButtonStyle.success,
        cancel_style: discord.ButtonStyle = discord.ButtonStyle.danger,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.value: Optional[bool] = None
        
        # Confirm button
        confirm_btn = ui.Button(
            label=confirm_label or t("buttons.confirm", self.lang),
            style=confirm_style,
            emoji="✅"
        )
        confirm_btn.callback = self.confirm
        self.add_item(confirm_btn)
        
        # Cancel button
        cancel_btn = ui.Button(
            label=cancel_label or t("buttons.cancel", self.lang),
            style=cancel_style,
            emoji="❌"
        )
        cancel_btn.callback = self.cancel
        self.add_item(cancel_btn)
    
    async def confirm(self, interaction: discord.Interaction):
        """Handle confirmation."""
        self.value = True
        self.disable_all_items()
        await interaction.response.edit_message(view=self)
        self.stop()
    
    async def cancel(self, interaction: discord.Interaction):
        """Handle cancellation."""
        self.value = False
        self.disable_all_items()
        await interaction.response.edit_message(view=self)
        self.stop()


class BaseModal(ui.Modal):
    """Base class for all modals with common functionality."""
    
    def __init__(
        self,
        *,
        title: str,
        lang: str = "en",
        custom_id: Optional[str] = None
    ):
        super().__init__(title=title, custom_id=custom_id)
        self.lang = lang
        self.logger = logging.getLogger(f"modal.{self.__class__.__name__}")
        self._submitted = False
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle modal submission."""
        self._submitted = True
        await self.handle_submit(interaction)
    
    async def handle_submit(self, interaction: discord.Interaction):
        """Override this method to handle submission."""
        await interaction.response.send_message(
            t("modal.submitted", self.lang),
            ephemeral=True
        )
    
    async def on_error(
        self,
        interaction: discord.Interaction,
        error: Exception
    ):
        """Handle modal errors."""
        self.logger.error(
            f"Error in modal for user {interaction.user.id}: {error}",
            exc_info=True
        )
        
        error_message = t("errors.modal_error", self.lang)
        
        try:
            if interaction.response.is_done():
                await interaction.followup.send(error_message, ephemeral=True)
            else:
                await interaction.response.send_message(error_message, ephemeral=True)
        except discord.HTTPException:
            pass