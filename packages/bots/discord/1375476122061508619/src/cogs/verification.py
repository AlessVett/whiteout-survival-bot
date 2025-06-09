"""
Improved Verification Cog with better error handling, state management, and user experience.

This module provides a comprehensive verification system for Discord users joining the server.
It handles multi-step verification including language selection, game ID verification,
alliance type selection, and final setup completion.

Classes:
    VerificationStep: Enum defining verification process steps
    VerificationCog: Main cog handling the verification process

Features:
    - Multi-step verification process with state management
    - Automatic user role assignment and channel creation
    - Support for alliance-based organization
    - Rate limiting and error handling
    - Localized user interface
"""

import discord
from discord.ext import commands
from discord import app_commands, ui
from typing import Optional, Dict, Any
import asyncio
from datetime import datetime, timedelta
from enum import Enum

from src.cogs.base import BaseCog, InteractionHandler
from src.views.verification_views import (
    LanguageSelectionView,
    VerificationMethodView,
    GameIDVerificationView,
    AllianceSelectionView,
    AllianceRoleSelectionView,
    VerificationCompleteView,
    AllianceNameModal
)
from src.views.base import BaseView, ConfirmationView
from src.utils.utils import verify_game_id, get_or_create_role, setup_member_channel
from src.config import Config
from locales import t


class VerificationStep(Enum):
    """Verification process steps."""
    LANGUAGE_SELECTION = "language_selection"
    ID_VERIFICATION = "id_verification"
    ALLIANCE_TYPE = "alliance_type"
    ALLIANCE_SELECTION = "alliance_selection"
    ALLIANCE_ROLE = "alliance_role"
    COMPLETE = "complete"


class VerificationCog(BaseCog, InteractionHandler):
    """Handles user verification process with improved state management."""
    
    def __init__(self, bot: commands.Bot):
        BaseCog.__init__(self, bot)
        InteractionHandler.__init__(self)
        
        # Verification session tracking
        self._active_verifications: Dict[int, Dict[str, Any]] = {}
        
        # Rate limiting for verification attempts
        self._verification_attempts: Dict[int, List[datetime]] = {}
        self._max_attempts = 5
        self._attempt_window = timedelta(minutes=30)
    
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Handle new member joining the server."""
        if member.bot:
            return
        
        try:
            # Check if user is already verified
            user_data = await self.ensure_user_exists(member.id, member.name)
            
            if user_data.get('verified'):
                await self._restore_verified_user(member, user_data)
            else:
                await self._setup_new_user(member, user_data)
                
        except Exception as e:
            self.logger.error(f"Error handling member join for {member.id}: {e}")
    
    async def _restore_verified_user(self, member: discord.Member, user_data: Dict[str, Any]):
        """Restore roles and settings for a verified user."""
        guild = member.guild
        lang = self.get_user_lang(user_data)
        
        try:
            # Add verified role
            verified_role = await get_or_create_role(guild, t("roles.verified", lang))
            await member.add_roles(verified_role)
            
            # Restore alliance roles
            alliance_type = user_data.get('alliance_type', 'no_alliance')
            
            if alliance_type == 'alliance' and user_data.get('alliance'):
                # Add alliance role
                alliance_role = await get_or_create_role(guild, user_data['alliance'])
                await member.add_roles(alliance_role)
                
                # Add rank role if present
                if user_data.get('alliance_role'):
                    rank_role_name = f"{user_data['alliance']} - {user_data['alliance_role']}"
                    rank_role = await get_or_create_role(guild, rank_role_name)
                    await member.add_roles(rank_role)
            
            elif alliance_type == 'no_alliance':
                role = await get_or_create_role(guild, t("roles.no_alliance", lang))
                await member.add_roles(role)
            
            elif alliance_type == 'other_state':
                role = await get_or_create_role(guild, t("roles.other_state", lang))
                await member.add_roles(role)
            
            # Restore nickname
            if user_data.get('game_nickname'):
                nickname = self._format_nickname(user_data)
                try:
                    await member.edit(nick=nickname)
                except discord.Forbidden:
                    self.logger.warning(f"Cannot edit nickname for {member.id}")
            
            # Send welcome back message
            try:
                embed = discord.Embed(
                    title=t("welcome.welcome_back_title", lang),
                    description=t("welcome.welcome_back_description", lang, username=member.mention),
                    color=Config.EMBED_COLOR
                )
                await member.send(embed=embed)
            except discord.Forbidden:
                pass
                
        except Exception as e:
            self.logger.error(f"Error restoring verified user {member.id}: {e}")
    
    async def _setup_new_user(self, member: discord.Member, user_data: Dict[str, Any]):
        """Setup verification process for new users."""
        guild = member.guild
        
        try:
            # Add unverified role
            unverified_role = await get_or_create_role(guild, "Unverified")
            await member.add_roles(unverified_role)
            
            # Create verification channel
            channel_name = f"verify-{member.name}"
            verification_channel = await setup_member_channel(
                guild,
                member,
                "Welcome",
                channel_name
            )
            
            # Update database with channel info
            await self.db.update_user_channels(
                member.id,
                verification_channel_id=verification_channel.id
            )
            
            # Start verification session
            self._active_verifications[member.id] = {
                'channel_id': verification_channel.id,
                'started_at': datetime.utcnow(),
                'current_step': VerificationStep.LANGUAGE_SELECTION
            }
            
            # Send language selection with enhanced design
            embed = discord.Embed(
                title="🌟 Welcome to Dawn of Ashes",
                color=0x5865F2  # Discord blurple
            )
            embed.set_author(
                name="🌍 Language Selection",
                icon_url="https://cdn.discordapp.com/emojis/1234567890.gif"  # Optional: add server icon
            )
            embed.description = (
                "┌─────────────────────────────────────┐\n"
                "│  **Please select your language**   │\n"
                "│  *Seleziona la tua lingua*          │\n"
                "└─────────────────────────────────────┘\n\n"
                "🔹 Choose your preferred language to continue with the verification process\n"
                "🔹 Scegli la tua lingua preferita per continuare con la verifica"
            )
            embed.set_footer(
                text="⏱️ This menu will timeout in 10 minutes • Made with ❤️ by DoW Team",
                icon_url="https://cdn.discordapp.com/emojis/clock.gif"
            )
            embed.set_thumbnail(
                url="https://cdn.discordapp.com/attachments/123/flags_world.png"  # World flags icon
            )
            
            view = LanguageSelectionView(
                callback=self._handle_language_selection,
                user_id=member.id
            )
            
            message = await verification_channel.send(embed=embed, view=view)
            view.message = message
            
        except Exception as e:
            self.logger.error(f"Error setting up new user {member.id}: {e}")
    
    @app_commands.command(
        name="verify",
        description="Start or resume the verification process"
    )
    async def verify_command(self, interaction: discord.Interaction):
        """Command to start or resume verification."""
        user_id = interaction.user.id
        
        # Check rate limiting
        if not await self._check_rate_limit(user_id):
            await self.send_error_message(
                interaction,
                "verification.too_many_attempts",
                ephemeral=True
            )
            return
        
        # Get user data
        user_data = await self.ensure_user_exists(user_id, interaction.user.name)
        lang = self.get_user_lang(user_data)
        
        # Check if already verified
        if user_data.get('verified'):
            await self.send_success_message(
                interaction,
                "verification.already_verified",
                lang=lang,
                ephemeral=True
            )
            return
        
        # Resume or start verification
        await self._resume_verification(interaction, user_data)
    
    @app_commands.command(
        name="reverify",
        description="Redo the verification process"
    )
    async def reverify_command(self, interaction: discord.Interaction):
        """Command to redo verification."""
        user_id = interaction.user.id
        user_data = await self.get_user_data(user_id)
        
        if not user_data:
            await self.send_error_message(
                interaction,
                "errors.user_not_found",
                ephemeral=True
            )
            return
        
        lang = self.get_user_lang(user_data)
        
        # Show confirmation
        embed = discord.Embed(
            title=t("verification.reverify_title", lang),
            description=t("verification.reverify_confirm", lang),
            color=discord.Color.orange()
        )
        
        view = ConfirmationView(
            lang=lang,
            user_id=user_id
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        
        # Wait for confirmation
        await view.wait()
        
        if view.value:
            # Reset verification
            await self.db.reset_user_verification(user_id)
            await self._resume_verification(interaction, user_data)
        else:
            await interaction.followup.send(
                t("verification.reverify_cancelled", lang),
                ephemeral=True
            )
    
    async def _resume_verification(self, interaction: discord.Interaction, user_data: Dict[str, Any]):
        """Resume verification from the last step."""
        user_id = interaction.user.id
        lang = self.get_user_lang(user_data)
        
        # Determine the current step
        step = VerificationStep(user_data.get('verification_step', 'language_selection'))
        
        # Get or create verification channel
        channel_id = user_data.get('verification_channel_id')
        if channel_id:
            channel = self.bot.get_channel(channel_id)
            if not channel:
                # Channel was deleted, create a new one
                channel = await self._create_verification_channel(interaction.guild, interaction.user)
                await self.db.update_user_channels(user_id, verification_channel_id=channel.id)
        else:
            channel = interaction.channel
        
        # Send appropriate view based on step
        if step == VerificationStep.LANGUAGE_SELECTION:
            await self._send_language_selection(channel, user_id)
        elif step == VerificationStep.ID_VERIFICATION:
            await self._send_id_verification(channel, user_id, lang)
        elif step == VerificationStep.ALLIANCE_TYPE:
            await self._send_alliance_type_selection(channel, user_id, lang)
        elif step == VerificationStep.ALLIANCE_SELECTION:
            await self._send_alliance_selection(channel, user_id, lang)
        elif step == VerificationStep.ALLIANCE_ROLE:
            await self._send_alliance_role_selection(channel, user_id, lang)
        
        await interaction.response.send_message(
            t("verification.resuming", lang),
            ephemeral=True
        )
    
    async def _check_rate_limit(self, user_id: int) -> bool:
        """Check if user has exceeded verification attempt limit."""
        now = datetime.utcnow()
        
        # Clean old attempts
        if user_id in self._verification_attempts:
            self._verification_attempts[user_id] = [
                attempt for attempt in self._verification_attempts[user_id]
                if now - attempt < self._attempt_window
            ]
        
        # Check limit
        attempts = self._verification_attempts.get(user_id, [])
        if len(attempts) >= self._max_attempts:
            return False
        
        # Record new attempt
        if user_id not in self._verification_attempts:
            self._verification_attempts[user_id] = []
        self._verification_attempts[user_id].append(now)
        
        return True
    
    def _format_nickname(self, user_data: Dict[str, Any]) -> str:
        """Format user nickname based on alliance status."""
        nickname = user_data.get('game_nickname', '')
        alliance_type = user_data.get('alliance_type', 'no_alliance')
        
        prefix = ""
        if alliance_type == 'alliance' and user_data.get('alliance'):
            prefix = f"[{user_data['alliance']}]"
        elif alliance_type == 'other_state':
            prefix = "[OS]"
        
        return f"{prefix} {nickname}".strip()
    
    # Callback methods for views
    async def _handle_language_selection(self, interaction: discord.Interaction, language: str):
        """Handle language selection."""
        user_id = interaction.user.id
        
        # Update user language
        await self.db.update_user(user_id, {'language': language})
        
        # Update session
        if user_id in self._active_verifications:
            self._active_verifications[user_id]['language'] = language
        
        # Send next step
        await self._send_id_verification(interaction.channel, user_id, language)
    
    async def _handle_alliance_name_submission(self, interaction: discord.Interaction, alliance_name: str):
        """Handle alliance name submission."""
        user_id = interaction.user.id
        user_data = await self.get_user_data(user_id)
        lang = self.get_user_lang(user_data)
        
        # Validate alliance name
        if len(alliance_name.strip()) < 2:
            await self.send_error_message(
                interaction,
                "alliance.name_too_short",
                lang=lang,
                ephemeral=True
            )
            return
        
        alliance_name = alliance_name.strip()
        
        # Update user data
        await self.db.update_user(user_id, {
            'alliance': alliance_name,
            'verification_step': VerificationStep.ALLIANCE_ROLE.value
        })
        
        # Check if alliance exists or create placeholder
        try:
            alliance_data = await self.db.get_alliance(alliance_name)
            if not alliance_data:
                await self.db.create_alliance_placeholder(
                    alliance_name, 
                    interaction.guild.id, 
                    lang
                )
                self.logger.info(f"Created alliance placeholder: {alliance_name}")
        except Exception as e:
            self.logger.error(f"Error handling alliance: {e}")
        
        # Send success response to complete the deferred interaction
        await interaction.followup.send(
            f"✅ Alliance name set to: **{alliance_name}**",
            ephemeral=True
        )
        
        # Send next step
        await self._send_alliance_role_selection(interaction.channel, user_id, lang)
    
    async def _handle_alliance_role_selection(self, interaction: discord.Interaction, role: str):
        """Handle alliance role selection."""
        user_id = interaction.user.id
        user_data = await self.get_user_data(user_id)
        lang = self.get_user_lang(user_data)
        
        # Update user data
        await self.db.update_user(user_id, {
            'alliance_role': role,
            'verification_step': VerificationStep.COMPLETE.value
        })
        
        # Complete verification
        await self._complete_verification(interaction, user_id)
    
    async def _send_language_selection(self, channel: discord.TextChannel, user_id: int):
        """Send language selection view."""
        embed = discord.Embed(
            title="🌍 Language Selection / Selezione Lingua",
            description=(
                "Please select your preferred language:\n"
                "Seleziona la tua lingua preferita:"
            ),
            color=Config.EMBED_COLOR
        )
        
        view = LanguageSelectionView(
            callback=self._handle_language_selection,
            user_id=user_id
        )
        
        message = await channel.send(embed=embed, view=view)
        view.message = message
    
    async def _send_id_verification(self, channel: discord.TextChannel, user_id: int, lang: str):
        """Send ID verification view with enhanced design."""
        embed = discord.Embed(
            title="🎮 " + t("verification.id_title", lang),
            color=0x00D166  # Green success color
        )
        embed.set_author(
            name="Step 2/4 • Game ID Verification",
            icon_url="https://cdn.discordapp.com/emojis/game_controller.gif"
        )
        
        embed.description = (
            f"┌───────────────────────────────────────┐\n"
            f"│  **{t('verification.id_description', lang)}**  │\n"
            f"└───────────────────────────────────────┘\n\n"
            f"🎯 {t('verification.id_description', lang)}\n\n"
            f"📍 **{t('verification.id_help', lang)}:**\n"
            f"└─ {t('verification.id_location', lang)}"
        )
        
        # Add helpful tips section
        embed.add_field(
            name="💡 Tips",
            value=(
                "• Make sure your Game ID is exactly as shown in-game\n"
                "• Double-check for typos before submitting\n"
                "• Contact support if you have issues finding your ID"
            ),
            inline=False
        )
        
        embed.set_footer(
            text="🔐 Your Game ID is used for verification only • Secure & Private",
            icon_url="https://cdn.discordapp.com/emojis/shield.gif"
        )
        
        # Add tutorial image if configured
        if Config.PLAYER_ID_TUTORIAL_IMAGE:
            embed.set_image(url=Config.PLAYER_ID_TUTORIAL_IMAGE)
        
        view = GameIDVerificationView(
            callback=self._handle_id_verification,
            user_id=user_id,
            lang=lang
        )
        
        message = await channel.send(embed=embed, view=view)
        view.message = message
    
    async def _handle_id_verification(self, interaction: discord.Interaction, game_id: str):
        """Handle game ID verification."""
        user_id = interaction.user.id
        user_data = await self.get_user_data(user_id)
        lang = self.get_user_lang(user_data)
        
        try:
            # Verify game ID using API
            is_valid, player_info = await verify_game_id(game_id)
            
            if not is_valid or not player_info:
                await self.send_error_message(
                    interaction,
                    "verification.invalid_id",
                    lang=lang,
                    ephemeral=True
                )
                return
            
            # Update user data
            await self.db.update_user(user_id, {
                'game_id': game_id,
                'game_nickname': player_info.get('nickname', 'Unknown'),
                'stove_lv': player_info.get('stove_lv'),
                'verification_step': VerificationStep.ALLIANCE_TYPE.value
            })
            
            # Send success message
            success_embed = discord.Embed(
                title="✅ " + t("verification.id_verified_title", lang),
                description=t("verification.id_verified_description", lang),
                color=0x27AE60  # Green success color
            )
            success_embed.add_field(
                name="🎮 Game ID",
                value=f"`{game_id}`",
                inline=True
            )
            success_embed.add_field(
                name="👤 Nickname", 
                value=player_info.get('nickname', 'Unknown'),
                inline=True
            )
            if player_info.get('stove_lv'):
                success_embed.add_field(
                    name="⭐ Level",
                    value=f"Lv. {player_info['stove_lv']}",
                    inline=True
                )
            
            await interaction.followup.send(embed=success_embed, ephemeral=True)
            
            # Send next step - alliance type selection
            await self._send_alliance_type_selection(interaction.channel, user_id, lang)
            
        except Exception as e:
            self.logger.error(f"Error in ID verification for user {user_id}: {e}")
            await self.send_error_message(
                interaction,
                "verification.id_verification_error",
                lang=lang,
                ephemeral=True
            )
    
    async def handle_id_verification(self, interaction: discord.Interaction, game_id: str):
        """Public method for handling ID verification from views."""
        await self._handle_id_verification(interaction, game_id)
    
    async def handle_language_selection(self, interaction: discord.Interaction, lang_code: str):
        """Public method for handling language selection from views."""
        await self._handle_language_selection(interaction, lang_code)
    
    async def handle_alliance_type_selection(self, interaction: discord.Interaction, alliance_type: str):
        """Public method for handling alliance type selection from views."""
        await self._handle_alliance_type_selection(interaction, alliance_type)
    
    async def handle_alliance_submission(self, interaction: discord.Interaction, alliance_name: str):
        """Public method for handling alliance name submission from views."""
        await self._handle_alliance_name_submission(interaction, alliance_name)
    
    async def handle_alliance_role_selection(self, interaction: discord.Interaction, role: str):
        """Public method for handling alliance role selection from views."""
        await self._handle_alliance_role_selection(interaction, role)
    
    async def _send_alliance_type_selection(self, channel: discord.TextChannel, user_id: int, lang: str):
        """Send alliance type selection view with enhanced design."""
        embed = discord.Embed(
            title="⚔️ " + t("alliance.type_title", lang),
            color=0xFF6B35  # Orange/red alliance color
        )
        embed.set_author(
            name="Step 3/4 • Alliance Configuration",
            icon_url="https://cdn.discordapp.com/emojis/crossed_swords.gif"
        )
        
        embed.description = (
            f"┌─────────────────────────────────────────┐\n"
            f"│  **{t('alliance.type_description', lang)}**  │\n"
            f"└─────────────────────────────────────────┘\n\n"
            f"🏰 Choose your alliance status to configure your server access\n\n"
            f"**Available Options:**\n"
            f"🔹 **Alliance Member** - Join or create an alliance\n"
            f"🔹 **No Alliance** - Play independently\n"
            f"🔹 **Other State** - From a different game state"
        )
        
        embed.set_footer(
            text="💡 You can change this later in your dashboard • Step 3 of 4",
            icon_url="https://cdn.discordapp.com/emojis/info.gif"
        )
        
        view = AllianceSelectionView(
            callback=self._handle_alliance_type_selection,
            user_id=user_id,
            lang=lang
        )
        
        message = await channel.send(embed=embed, view=view)
        view.message = message
    
    async def _handle_alliance_type_selection(self, interaction: discord.Interaction, alliance_type: str):
        """Handle alliance type selection."""
        user_id = interaction.user.id
        user_data = await self.get_user_data(user_id)
        lang = self.get_user_lang(user_data)
        
        try:
            # Update user data
            await self.db.update_user(user_id, {
                'alliance_type': alliance_type,
                'verification_step': VerificationStep.COMPLETE.value if alliance_type != 'alliance' else VerificationStep.ALLIANCE_SELECTION.value
            })
            
            if alliance_type == 'alliance':
                # Need to select specific alliance
                await self._send_alliance_selection(interaction.channel, user_id, lang)
            else:
                # Complete verification
                await self._complete_verification(interaction, user_id)
                
        except Exception as e:
            self.logger.error(f"Error in alliance type selection for user {user_id}: {e}")
            # The view already handles the response, so we don't need to respond here
    
    async def _send_alliance_selection(self, channel: discord.TextChannel, user_id: int, lang: str):
        """Send alliance name selection."""
        embed = discord.Embed(
            title=t("alliance.enter_name_title", lang),
            description=t("alliance.enter_name_description", lang),
            color=Config.EMBED_COLOR
        )
        
        # Add helpful information
        embed.add_field(
            name=t("alliance.name_requirements", lang),
            value=t("alliance.name_requirements_text", lang),
            inline=False
        )
        
        # Get alliance suggestions from database
        try:
            existing_alliances = await self.db.get_popular_alliances(limit=5)
            if existing_alliances:
                suggestions = [alliance.get('name', '') for alliance in existing_alliances]
                embed.add_field(
                    name=t("alliance.suggestions", lang),
                    value=", ".join(suggestions),
                    inline=False
                )
        except Exception as e:
            self.logger.warning(f"Could not get alliance suggestions: {e}")
        
        view = AllianceNameModal(
            callback=self._handle_alliance_name_submission,
            lang=lang
        )
        
        # Create button to open modal
        enter_btn = ui.Button(
            label=t("alliance.enter_name_button", lang),
            emoji="✏️",
            style=discord.ButtonStyle.primary,
            custom_id="enter_alliance_name"
        )
        
        async def open_modal(interaction: discord.Interaction):
            if interaction.response.is_done():
                return  # Interaction already handled
            
            modal = AllianceNameModal(
                callback=self._handle_alliance_name_submission,
                lang=lang
            )
            await interaction.response.send_modal(modal)
        
        enter_btn.callback = open_modal
        
        view = BaseView(user_id=user_id, lang=lang, auto_defer=False)
        view.add_item(enter_btn)
        
        message = await channel.send(embed=embed, view=view)
        view.message = message
    
    async def _send_alliance_role_selection(self, channel: discord.TextChannel, user_id: int, lang: str):
        """Send alliance role selection."""
        user_data = await self.get_user_data(user_id)
        if not user_data:
            return
        
        alliance_name = user_data.get('alliance', 'Unknown')
        
        embed = discord.Embed(
            title=f"👑 {alliance_name} - {t('alliance.role_selection_title', lang)}",
            color=0x9B59B6  # Purple for royalty/hierarchy
        )
        embed.set_author(
            name="Step 4/4 • Role Selection",
            icon_url="https://cdn.discordapp.com/emojis/crown.gif"
        )
        
        embed.description = (
            f"┌──────────────────────────────────────────┐\n"
            f"│  **Select your role in {alliance_name}**  │\n"
            f"└──────────────────────────────────────────┘\n\n"
            f"🎭 {t('alliance.role_selection_description', lang)}\n\n"
            f"**Alliance Hierarchy:**"
        )
        
        # Add role descriptions with better formatting
        roles_info = [
            ("👑 R5", "Leader", t("alliance.role_r5_description", lang), "🔴"),
            ("⚔️ R4", "Officer", t("alliance.role_r4_description", lang), "🟠"),
            ("🛡️ R3", "Elite", t("alliance.role_r3_description", lang), "🟡"),
            ("⚡ R2", "Veteran", t("alliance.role_r2_description", lang), "🟢"),
            ("🌱 R1", "Member", t("alliance.role_r1_description", lang), "🔵")
        ]
        
        role_text = ""
        for emoji_role, title, description, dot in roles_info:
            role_text += f"\n{dot} **{emoji_role} {title}**\n└─ {description}\n"
        
        embed.add_field(
            name="📋 Available Roles",
            value=role_text,
            inline=False
        )
        
        embed.set_footer(
            text="⚠️ Choose carefully - This affects your permissions • Final Step!",
            icon_url="https://cdn.discordapp.com/emojis/warning.gif"
        )
        
        view = AllianceRoleSelectionView(
            callback=self._handle_alliance_role_selection,
            user_id=user_id,
            lang=lang
        )
        
        message = await channel.send(embed=embed, view=view)
        view.message = message
    
    async def _complete_verification(self, interaction: discord.Interaction, user_id: int):
        """Complete the verification process."""
        user_data = await self.get_user_data(user_id)
        lang = self.get_user_lang(user_data)
        member = interaction.guild.get_member(user_id)
        guild = interaction.guild
        
        if not member:
            return
        
        try:
            # Import here to avoid circular imports
            from src.services.alliance_channels import AllianceChannels
            
            # Remove unverified role
            unverified_role = discord.utils.get(guild.roles, name="Unverified")
            if unverified_role:
                await member.remove_roles(unverified_role)
            
            # Add verified role
            verified_role = await get_or_create_role(guild, "Verified")
            await member.add_roles(verified_role)
            
            # Handle roles based on alliance type
            alliance_type = user_data.get('alliance_type', 'no_alliance')
            game_nickname = user_data.get('game_nickname', member.name)
            prefix = ""
            
            if alliance_type == 'alliance' and user_data.get('alliance'):
                alliance = user_data['alliance']
                alliance_role = user_data.get('alliance_role')
                
                # Add alliance role
                alliance_role_obj = await get_or_create_role(guild, alliance)
                await member.add_roles(alliance_role_obj)
                
                # Add R1-R5 role if specified
                if alliance_role:
                    role_name = f"{alliance} - {alliance_role}"
                    role_obj = await get_or_create_role(guild, role_name)
                    await member.add_roles(role_obj)
                
                # Handle alliance channels for R5
                if alliance_role == "R5":
                    try:
                        alliance_channels = AllianceChannels()
                        created_channels = await alliance_channels.create_all_alliance_channels(
                            guild, alliance, alliance_role_obj, lang
                        )
                        
                        # Update alliance in database
                        general_channel = created_channels.get("general")
                        if general_channel:
                            await self.db.create_alliance(
                                alliance, guild.id, general_channel.id, member.id, lang
                            )
                    except Exception as e:
                        self.logger.error(f"Error creating alliance channels: {e}")
                
                prefix = f"[{alliance}]"
                
            elif alliance_type == 'no_alliance':
                role = await get_or_create_role(guild, "No Alliance")
                await member.add_roles(role)
                
            elif alliance_type == 'other_state':
                role = await get_or_create_role(guild, "Other State")
                await member.add_roles(role)
                prefix = "[OS]"
            
            # Update nickname
            try:
                nick = f"{prefix} {game_nickname}" if prefix else game_nickname
                await member.edit(nick=nick)
            except discord.Forbidden:
                pass
            
            # Create personal channel
            try:
                personal_channel_name = f"private-{game_nickname}"
                personal_channel = await setup_member_channel(
                    guild, member, "Personal Channels", personal_channel_name
                )
                await self.db.update_user_channels(
                    member.id, personal_channel_id=personal_channel.id
                )
                
                # Send welcome message to personal channel
                welcome_embed = discord.Embed(
                    title="Welcome to your personal channel!",
                    description="This is your private space where you can manage your settings and receive important notifications.",
                    color=Config.EMBED_COLOR
                )
                welcome_embed.add_field(
                    name="Use `/dashboard` to open your control panel where you can:",
                    value="• Change your language\n• Change your alliance\n• Manage alliance members (if you're R4 or R5)",
                    inline=False
                )
                await personal_channel.send(embed=welcome_embed)
                
            except Exception as e:
                self.logger.error(f"Error creating personal channel: {e}")
            
            # Mark as verified
            await self.db.update_user(user_id, {
                'verified': True,
                'verified_at': datetime.utcnow()
            })
            
            # Send completion message with celebration design
            embed = discord.Embed(
                title="🎉 " + t("verification.complete_title", lang),
                color=0x00FF00  # Bright green for success
            )
            embed.set_author(
                name="✅ Verification Complete!",
                icon_url="https://cdn.discordapp.com/emojis/party.gif"
            )
            
            embed.description = (
                f"┌─────────────────────────────────────────┐\n"
                f"│  **🎊 Welcome to Dawn of Ashes! 🎊**   │\n"
                f"└─────────────────────────────────────────┘\n\n"
                f"🌟 {t('verification.complete_description', lang, username=member.mention)}\n\n"
                f"**🔸 Your Profile Summary:**"
            )
            
            # Add verification details with enhanced formatting
            profile_info = f"```yaml\n"
            profile_info += f"Game ID: {user_data.get('game_id', 'N/A')}\n"
            profile_info += f"Nickname: {game_nickname}\n"
            
            if alliance_type == 'alliance':
                profile_info += f"Alliance: {user_data.get('alliance', 'N/A')}\n"
                if user_data.get('alliance_role'):
                    profile_info += f"Role: {user_data['alliance_role']}\n"
            elif alliance_type == 'no_alliance':
                profile_info += f"Status: Independent Player\n"
            elif alliance_type == 'other_state':
                profile_info += f"Status: Other State Player\n"
            
            profile_info += "```"
            
            embed.add_field(
                name="📄 Your Information",
                value=profile_info,
                inline=False
            )
            
            # Add next steps
            embed.add_field(
                name="🚀 What's Next?",
                value=(
                    "• 📱 Check your **personal channel** for settings\n"
                    "• 🎛️ Use `/dashboard` to manage your profile\n"
                    "• 🏰 Join your alliance channels (if applicable)\n"
                    "• 📅 Stay updated with server events"
                ),
                inline=False
            )
            
            embed.set_footer(
                text="🎈 Thank you for joining our community! • Enjoy your stay",
                icon_url="https://cdn.discordapp.com/emojis/heart.gif"
            )
            embed.set_thumbnail(
                url="https://cdn.discordapp.com/attachments/success_checkmark.png"
            )
            
            view = VerificationCompleteView(
                lang=lang,
                user_id=user_id
            )
            
            await interaction.channel.send(embed=embed, view=view)
            
            # Clean up verification channel after delay
            await asyncio.sleep(30)
            verification_channel_id = user_data.get('verification_channel_id')
            if verification_channel_id:
                try:
                    await interaction.channel.delete()
                    await self.db.update_user_channels(member.id, verification_channel_id=None)
                except discord.HTTPException:
                    pass
            
            # Clean up session
            self._active_verifications.pop(user_id, None)
            
        except Exception as e:
            self.logger.error(f"Error completing verification for {user_id}: {e}")
            await self.handle_cog_error(interaction, e)


async def setup(bot: commands.Bot):
    """Load the cog."""
    await bot.add_cog(VerificationCog(bot))