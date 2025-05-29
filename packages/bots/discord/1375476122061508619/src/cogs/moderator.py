import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional

from src.config import Config
from locales import t
from src.database import get_database
from src.utils.utils import get_or_create_role
from src.views.moderator_views import NewsModal, GiftCodeModal


class ModeratorCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = get_database()
        
    def get_user_lang(self, user_data: dict) -> str:
        """Get user language from database or use default"""
        return user_data.get('language', Config.DEFAULT_LANGUAGE) if user_data else Config.DEFAULT_LANGUAGE
    
    async def check_moderator_role(self, interaction: discord.Interaction) -> bool:
        """Check if user has moderator role and create it if needed"""
        # Get or create Moderator role
        moderator_role = discord.utils.get(interaction.guild.roles, name="Moderator")
        if not moderator_role:
            # Create Moderator role with appropriate permissions
            moderator_role = await interaction.guild.create_role(
                name="Moderator",
                color=discord.Color.green(),
                permissions=discord.Permissions(
                    send_messages=True,
                    manage_messages=True,
                    embed_links=True,
                    attach_files=True,
                    read_message_history=True,
                    mention_everyone=True,
                    use_external_emojis=True,
                    add_reactions=True,
                    view_channel=True
                ),
                reason="Created Moderator role for bot commands"
            )
        
        # Check if user has the role or is an administrator
        return moderator_role in interaction.user.roles or interaction.user.guild_permissions.administrator
    
    @app_commands.command(name="send-news", description="Send a news announcement to a channel")
    async def send_news(self, interaction: discord.Interaction):
        """Send news to a selected channel"""
        # Check permissions
        if not await self.check_moderator_role(interaction):
            user_data = await self.db.get_user(interaction.user.id)
            lang = self.get_user_lang(user_data)
            await interaction.response.send_message(
                t("moderator.no_permission", lang),
                ephemeral=True
            )
            return
        
        # Get user language
        user_data = await self.db.get_user(interaction.user.id)
        lang = self.get_user_lang(user_data)
        
        # Show news modal
        modal = NewsModal(lang)
        await interaction.response.send_modal(modal)
    
    @app_commands.command(name="notify-gift-code", description="Send a gift code to all alliance gift-code channels")
    async def notify_gift_code(self, interaction: discord.Interaction):
        """Send gift code to all alliance gift-code channels"""
        try:
            # Check permissions
            if not await self.check_moderator_role(interaction):
                user_data = await self.db.get_user(interaction.user.id)
                lang = self.get_user_lang(user_data)
                await interaction.response.send_message(
                    t("moderator.no_permission", lang),
                    ephemeral=True
                )
                return

            # Get user language
            user_data = await self.db.get_user(interaction.user.id)
            lang = self.get_user_lang(user_data)

            # Show gift code modal
            modal = GiftCodeModal(lang)
            await interaction.response.send_modal(modal)
        except Exception as e:
            await interaction.response.send_message(
                str(e),
                ephemeral=True
            )
    
    @app_commands.command(name="add-moderator", description="[Admin] Add moderator role to a user")
    @app_commands.describe(member="The member to add as moderator")
    @app_commands.default_permissions(administrator=True)
    async def add_moderator(self, interaction: discord.Interaction, member: discord.Member):
        """Add moderator role to a user"""
        # Get or create Moderator role
        moderator_role = discord.utils.get(interaction.guild.roles, name="Moderator")
        if not moderator_role:
            moderator_role = await interaction.guild.create_role(
                name="Moderator",
                color=discord.Color.green(),
                permissions=discord.Permissions(
                    send_messages=True,
                    manage_messages=True,
                    embed_links=True,
                    attach_files=True,
                    read_message_history=True,
                    mention_everyone=True,
                    use_external_emojis=True,
                    add_reactions=True,
                    view_channel=True
                ),
                reason="Created Moderator role for bot commands"
            )
        
        # Add role to member
        if moderator_role not in member.roles:
            await member.add_roles(moderator_role)
            await interaction.response.send_message(
                f"✅ Added Moderator role to {member.mention}",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"ℹ️ {member.mention} already has the Moderator role",
                ephemeral=True
            )
    
    @app_commands.command(name="remove-moderator", description="[Admin] Remove moderator role from a user")
    @app_commands.describe(member="The member to remove as moderator")
    @app_commands.default_permissions(administrator=True)
    async def remove_moderator(self, interaction: discord.Interaction, member: discord.Member):
        """Remove moderator role from a user"""
        moderator_role = discord.utils.get(interaction.guild.roles, name="Moderator")
        
        if not moderator_role:
            await interaction.response.send_message(
                "❌ Moderator role doesn't exist",
                ephemeral=True
            )
            return
        
        if moderator_role in member.roles:
            await member.remove_roles(moderator_role)
            await interaction.response.send_message(
                f"✅ Removed Moderator role from {member.mention}",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"ℹ️ {member.mention} doesn't have the Moderator role",
                ephemeral=True
            )


async def setup(bot):
    await bot.add_cog(ModeratorCog(bot))