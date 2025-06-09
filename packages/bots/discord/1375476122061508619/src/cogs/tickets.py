"""
Ticket System Cog for DWOS Discord Bot

This cog provides ticket support functionality, allowing users to create
support tickets that are managed through the admin panel.
"""

import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import json
import logging
from datetime import datetime
from typing import Optional

from src.config import Config
from locales import t
from src.cogs.base import BaseCog
from src.views.base import BaseView, BaseModal

logger = logging.getLogger(__name__)

class TicketModal(BaseModal):
    """Modal for ticket creation"""
    
    def __init__(self, cog, lang='en'):
        super().__init__(
            title=t("tickets.modal.title", lang=lang),
            lang=lang,
            custom_id="ticket_modal"
        )
        self.cog = cog
        
        # Title input
        self.title_input = discord.ui.TextInput(
            label=t("tickets.modal.title_label", lang=lang),
            placeholder=t("tickets.modal.title_placeholder", lang=lang),
            max_length=100,
            required=True
        )
        self.add_item(self.title_input)
        
        # Description input
        self.description_input = discord.ui.TextInput(
            label=t("tickets.modal.description_label", lang=lang),
            placeholder=t("tickets.modal.description_placeholder", lang=lang),
            style=discord.TextStyle.paragraph,
            max_length=1000,
            required=True
        )
        self.add_item(self.description_input)
        
        # Priority select
        self.priority_input = discord.ui.TextInput(
            label=t("tickets.modal.priority_label", lang=lang),
            placeholder=t("tickets.modal.priority_placeholder", lang=lang),
            default="medium",
            max_length=10,
            required=False
        )
        self.add_item(self.priority_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle modal submission"""
        try:
            await interaction.response.defer(ephemeral=True)
            
            # Validate priority
            priority = self.priority_input.value.lower()
            if priority not in ['low', 'medium', 'high', 'urgent']:
                priority = 'medium'
            
            # Create ticket via API
            ticket_data = {
                "user_id": str(interaction.user.id),
                "user_name": str(interaction.user),
                "guild_id": str(interaction.guild.id),
                "title": self.title_input.value,
                "description": self.description_input.value,
                "priority": priority,
                "category": "Discord Support"
            }
            
            ticket_result = await self.cog.create_ticket_api(ticket_data)
            
            if not ticket_result["success"]:
                await interaction.followup.send(
                    t("tickets.creation.error", lang=self.lang),
                    ephemeral=True
                )
                return
            
            ticket_id = ticket_result["ticket_id"]
            
            # Create private channel for the ticket
            channel = await self.cog.create_ticket_channel(
                interaction.guild,
                interaction.user,
                ticket_id,
                self.title_input.value
            )
            
            if not channel:
                await interaction.followup.send(
                    t("tickets.channel.creation_error", lang=self.lang),
                    ephemeral=True
                )
                return
            
            # Update ticket with channel ID
            await self.cog.update_ticket_channel(ticket_id, channel.id)
            
            # Send confirmation
            embed = discord.Embed(
                title=t("tickets.creation.success_title", lang=self.lang),
                description=t("tickets.creation.success_description", 
                           lang=self.lang, 
                           ticket_id=ticket_id, 
                           channel=channel.mention),
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            embed.add_field(
                name=t("tickets.creation.title_field", lang=self.lang),
                value=self.title_input.value,
                inline=False
            )
            embed.add_field(
                name=t("tickets.creation.priority_field", lang=self.lang),
                value=priority.title(),
                inline=True
            )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
            # Send initial message in ticket channel
            await self.cog.send_ticket_welcome_message(channel, interaction.user, ticket_id, ticket_data)
            
        except Exception as e:
            logger.error(f"Error creating ticket: {e}")
            await interaction.followup.send(
                t("tickets.creation.error", lang=self.lang),
                ephemeral=True
            )

class TicketsCog(BaseCog):
    """Tickets cog for support system"""
    
    def __init__(self, bot):
        super().__init__(bot)
        self.api_base_url = Config.API_GATEWAY_URL or "http://api-gateway:8000"
        self.api_key = Config.DISCORD_BOT_API_KEY or "discord-bot-api-key-change-me"
    
    @commands.Cog.listener()
    async def on_message(self, message):
        """Listen for messages in ticket channels"""
        # Ignore bot messages
        if message.author.bot:
            return
        
        # Check if message is in a ticket channel
        if not message.channel.name.startswith("ticket-"):
            return
        
        # Extract ticket ID from channel name
        try:
            # Extract the ticket part and convert to proper format
            raw_ticket_id = message.channel.name.replace("ticket-", "", 1)  # Only replace first occurrence
            
            # If it still contains "ticket-", it means the format was "ticket-ticket-00003"
            if raw_ticket_id.startswith("ticket-"):
                ticket_id = raw_ticket_id.upper()
            else:
                # If it's just numbers, format it properly
                if raw_ticket_id.isdigit():
                    ticket_id = f"TICKET-{raw_ticket_id.zfill(5)}"
                else:
                    # Try to extract the number part
                    numbers = ''.join(filter(str.isdigit, raw_ticket_id))
                    if numbers:
                        ticket_id = f"TICKET-{numbers.zfill(5)}"
                    else:
                        ticket_id = raw_ticket_id.upper()
            
            logger.info(f"Processing message in channel '{message.channel.name}' -> extracted: '{raw_ticket_id}' -> ticket_id: '{ticket_id}'")
            
            # Add message to ticket
            success = await self.add_message_to_ticket(
                ticket_id=ticket_id,
                user_id=str(message.author.id),
                user_name=str(message.author),
                content=message.content,
                is_admin=self.is_admin_user(message.author)
            )
            
            if success:
                logger.info(f"Successfully added message to ticket {ticket_id}")
            else:
                logger.warning(f"Failed to add message to ticket {ticket_id}")
            
        except Exception as e:
            logger.error(f"Error adding message to ticket: {e}")
    
    def is_admin_user(self, user) -> bool:
        """Check if user is an admin or moderator"""
        admin_roles = ["Admin", "Moderator", "Support", "Staff"]
        user_roles = [role.name for role in user.roles]
        return any(role in admin_roles for role in user_roles)
        
    async def create_ticket_api(self, ticket_data: dict) -> dict:
        """Create ticket via API Gateway"""
        try:
            headers = {
                "Content-Type": "application/json",
                "X-API-Key": self.api_key
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.api_base_url}/api/discord/tickets/create",
                    json=ticket_data,
                    headers=headers
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        logger.error(f"API error: {response.status} - {await response.text()}")
                        return {"success": False, "error": f"API error: {response.status}"}
                        
        except Exception as e:
            logger.error(f"Error calling API: {e}")
            return {"success": False, "error": str(e)}
    
    async def update_ticket_channel(self, ticket_id: str, channel_id: int) -> bool:
        """Update ticket with channel ID"""
        try:
            headers = {
                "Content-Type": "application/json",
                "X-API-Key": self.api_key
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.put(
                    f"{self.api_base_url}/api/discord/tickets/{ticket_id}/channel",
                    json={"channel_id": str(channel_id)},
                    headers=headers
                ) as response:
                    return response.status == 200
                    
        except Exception as e:
            logger.error(f"Error updating ticket channel: {e}")
            return False
    
    async def close_ticket_api(self, ticket_id: str) -> bool:
        """Close ticket via API"""
        try:
            headers = {
                "Content-Type": "application/json",
                "X-API-Key": self.api_key
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.put(
                    f"{self.api_base_url}/api/discord/tickets/{ticket_id}/close",
                    headers=headers
                ) as response:
                    return response.status == 200
                    
        except Exception as e:
            logger.error(f"Error closing ticket: {e}")
            return False
    
    async def add_message_to_ticket(self, ticket_id: str, user_id: str, user_name: str, content: str, is_admin: bool = False) -> bool:
        """Add a message to an existing ticket"""
        try:
            headers = {
                "Content-Type": "application/json",
                "X-API-Key": self.api_key
            }
            
            message_data = {
                "user_id": user_id,
                "user_name": user_name,
                "content": content,
                "is_admin": is_admin
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.api_base_url}/api/discord/tickets/{ticket_id}/message",
                    json=message_data,
                    headers=headers
                ) as response:
                    if response.status == 200:
                        logger.debug(f"Added message to ticket {ticket_id} from {user_name}")
                        return True
                    else:
                        logger.error(f"Failed to add message to ticket: {response.status} - {await response.text()}")
                        return False
                    
        except Exception as e:
            logger.error(f"Error adding message to ticket: {e}")
            return False
    
    async def create_ticket_channel(self, guild: discord.Guild, user: discord.Member, ticket_id: str, title: str) -> Optional[discord.TextChannel]:
        """Create a private ticket channel"""
        try:
            # Find or create tickets category
            category = discord.utils.get(guild.categories, name="🎫 Support Tickets")
            if not category:
                category = await guild.create_category(
                    "🎫 Support Tickets",
                    reason=f"Ticket system category"
                )
            
            # Create channel with specific permissions
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                user: discord.PermissionOverwrite(
                    read_messages=True, 
                    send_messages=True, 
                    read_message_history=True
                ),
                guild.me: discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    manage_messages=True,
                    read_message_history=True
                )
            }
            
            # Add admin/mod roles if they exist
            admin_role = discord.utils.get(guild.roles, name="Admin")
            if admin_role:
                overwrites[admin_role] = discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    manage_messages=True,
                    read_message_history=True
                )
            
            mod_role = discord.utils.get(guild.roles, name="Moderator")
            if mod_role:
                overwrites[mod_role] = discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    read_message_history=True
                )
            
            # Create channel
            channel_name = f"ticket-{ticket_id.lower()}"
            channel = await guild.create_text_channel(
                channel_name,
                category=category,
                overwrites=overwrites,
                topic=f"Support ticket: {title} | User: {user} | ID: {ticket_id}",
                reason=f"Support ticket created by {user}"
            )
            
            return channel
            
        except Exception as e:
            logger.error(f"Error creating ticket channel: {e}")
            return None
    
    async def send_ticket_welcome_message(self, channel: discord.TextChannel, user: discord.Member, ticket_id: str, ticket_data: dict):
        """Send welcome message in ticket channel"""
        try:
            embed = discord.Embed(
                title="🎫 Support Ticket Created",
                description=f"Welcome {user.mention}! Your support ticket has been created.",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            
            embed.add_field(
                name="Ticket ID",
                value=f"`{ticket_id}`",
                inline=True
            )
            embed.add_field(
                name="Priority",
                value=ticket_data["priority"].title(),
                inline=True
            )
            embed.add_field(
                name="Category",
                value=ticket_data["category"],
                inline=True
            )
            embed.add_field(
                name="Title",
                value=ticket_data["title"],
                inline=False
            )
            embed.add_field(
                name="Description",
                value=ticket_data["description"],
                inline=False
            )
            
            embed.set_footer(text="Our team will respond as soon as possible. You can close this ticket by using /close-ticket.")
            
            # Add close button
            view = TicketControlView(self, ticket_id)
            
            await channel.send(embed=embed, view=view)
            
        except Exception as e:
            logger.error(f"Error sending welcome message: {e}")
    
    @app_commands.command(name="ticket", description="Create a new support ticket")
    async def ticket_command(self, interaction: discord.Interaction):
        """Create a new support ticket"""
        try:
            # Get user data for language
            user_data = await self.ensure_user_exists(interaction.user.id, interaction.user.name)
            lang = self.get_user_lang(user_data)
            
            # Check if user already has an open ticket
            existing_ticket = await self.check_existing_ticket(interaction.user.id, interaction.guild.id)
            if existing_ticket:
                await interaction.response.send_message(
                    t("tickets.already_exists", lang=lang, ticket_id=existing_ticket),
                    ephemeral=True
                )
                return
            
            # Show modal
            modal = TicketModal(self, lang)
            await interaction.response.send_modal(modal)
            
        except Exception as e:
            logger.error(f"Error in ticket command: {e}")
            await self.send_error_message(
                interaction,
                "tickets.creation.error",
                ephemeral=True
            )
    
    @app_commands.command(name="close-ticket", description="Close the current support ticket")
    async def close_ticket_command(self, interaction: discord.Interaction):
        """Close the current support ticket"""
        try:
            # Check if we're in a ticket channel
            if not interaction.channel.name.startswith("ticket-"):
                await interaction.response.send_message(
                    "❌ This command can only be used in ticket channels.",
                    ephemeral=True
                )
                return
            
            # Extract ticket ID from channel name
            raw_ticket_id = interaction.channel.name.replace("ticket-", "", 1)  # Only replace first occurrence
            
            # If it still contains "ticket-", it means the format was "ticket-ticket-00003"
            if raw_ticket_id.startswith("ticket-"):
                ticket_id = raw_ticket_id.upper()
            else:
                # If it's just numbers, format it properly
                if raw_ticket_id.isdigit():
                    ticket_id = f"TICKET-{raw_ticket_id.zfill(5)}"
                else:
                    # Try to extract the number part
                    numbers = ''.join(filter(str.isdigit, raw_ticket_id))
                    if numbers:
                        ticket_id = f"TICKET-{numbers.zfill(5)}"
                    else:
                        ticket_id = raw_ticket_id.upper()
            
            logger.info(f"Close ticket command in channel '{interaction.channel.name}' -> ticket_id: '{ticket_id}'")
            
            # Close ticket via API
            success = await self.close_ticket_api(ticket_id)
            
            if success:
                embed = discord.Embed(
                    title="🔒 Ticket Closed",
                    description=f"Ticket `{ticket_id}` has been closed.\nThis channel will be deleted in 10 seconds.",
                    color=discord.Color.red(),
                    timestamp=datetime.utcnow()
                )
                embed.set_footer(text=f"Closed by {interaction.user}")
                
                await interaction.response.send_message(embed=embed)
                
                # Delete channel after delay
                import asyncio
                await asyncio.sleep(10)
                await interaction.channel.delete(reason=f"Ticket {ticket_id} closed by {interaction.user}")
                
            else:
                await interaction.response.send_message(
                    "❌ Failed to close ticket. Please try again or contact an administrator.",
                    ephemeral=True
                )
                
        except Exception as e:
            logger.error(f"Error closing ticket: {e}")
            await interaction.response.send_message(
                "❌ An error occurred while closing the ticket.",
                ephemeral=True
            )
    
    async def check_existing_ticket(self, user_id: int, guild_id: int) -> Optional[str]:
        """Check if user has an existing open ticket"""
        try:
            # Look for existing ticket channels
            guild = self.bot.get_guild(guild_id)
            if not guild:
                return None
            
            for channel in guild.text_channels:
                if (channel.name.startswith("ticket-") and 
                    channel.topic and 
                    f"User: <@{user_id}>" in channel.topic):
                    # Extract ticket ID from channel name
                    return channel.name.replace("ticket-", "").upper()
            
            return None
            
        except Exception as e:
            logger.error(f"Error checking existing tickets: {e}")
            return None

class TicketControlView(BaseView):
    """View with controls for ticket management"""
    
    def __init__(self, cog, ticket_id: str):
        super().__init__(
            timeout=None,  # Persistent view
            auto_defer=False
        )
        self.cog = cog
        self.ticket_id = ticket_id
    
    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.danger, emoji="🔒")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Close ticket button"""
        try:
            # Close ticket via API
            success = await self.cog.close_ticket_api(self.ticket_id)
            
            if success:
                embed = discord.Embed(
                    title="🔒 Ticket Closed",
                    description=f"Ticket `{self.ticket_id}` has been closed.\nThis channel will be deleted in 10 seconds.",
                    color=discord.Color.red(),
                    timestamp=datetime.utcnow()
                )
                embed.set_footer(text=f"Closed by {interaction.user}")
                
                await interaction.response.send_message(embed=embed)
                
                # Disable all buttons
                for item in self.children:
                    item.disabled = True
                await interaction.edit_original_response(view=self)
                
                # Delete channel after delay
                import asyncio
                await asyncio.sleep(10)
                await interaction.channel.delete(reason=f"Ticket {self.ticket_id} closed by {interaction.user}")
                
            else:
                await interaction.response.send_message(
                    "❌ Failed to close ticket. Please try again or contact an administrator.",
                    ephemeral=True
                )
                
        except Exception as e:
            await interaction.response.send_message(
                "❌ An error occurred while closing the ticket.",
                ephemeral=True
            )

async def setup(bot):
    """Setup function for the cog"""
    await bot.add_cog(TicketsCog(bot))