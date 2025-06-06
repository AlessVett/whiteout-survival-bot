"""
Improved verification views with better UX and error handling.
"""

import discord
from discord import ui
from typing import Optional, Callable, List, Dict, Any
import asyncio

from src.views.base import BaseView, BaseModal, ConfirmationView
from src.config import Config
from locales import t


class LanguageSelectionView(BaseView):
    """View for selecting user language with flag emojis and better layout."""
    
    LANGUAGES = [
        ("🇬🇧", "English", "en"),
        ("🇮🇹", "Italiano", "it"),
        ("🇰🇷", "한국어", "ko"),
        ("🇨🇳", "中文", "zh"),
        ("🇯🇵", "日本語", "ja"),
        ("🇸🇦", "العربية", "ar"),
        ("🇪🇸", "Español", "es"),
        ("🇩🇪", "Deutsch", "de"),
        ("🇫🇷", "Français", "fr"),
        ("🇷🇺", "Русский", "ru"),
        ("🇺🇦", "Українська", "uk")
    ]
    
    def __init__(
        self,
        *,
        callback: Optional[Callable] = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.callback = callback
        self._create_buttons()
    
    def _create_buttons(self):
        """Create language buttons in a grid layout with enhanced styling."""
        for i, (emoji, label, code) in enumerate(self.LANGUAGES):
            # Use different button styles for variety
            if i < 4:  # First row - primary colors
                style = discord.ButtonStyle.primary
            elif i < 8:  # Second row - secondary colors  
                style = discord.ButtonStyle.secondary
            else:  # Third row - success colors
                style = discord.ButtonStyle.success
                
            button = ui.Button(
                label=f"{emoji} {label}",
                style=style,
                custom_id=f"lang_{code}",
                row=i // 4  # 4 buttons per row for better layout
            )
            button.callback = self._make_callback(code)
            self.add_item(button)
    
    def _make_callback(self, lang_code: str):
        """Create callback for language button."""
        async def callback(interaction: discord.Interaction):
            # Update button states
            for item in self.children:
                if isinstance(item, ui.Button):
                    if item.custom_id == f"lang_{lang_code}":
                        item.style = discord.ButtonStyle.success
                        item.disabled = True
                    else:
                        item.disabled = True
            
            # Update message
            await interaction.response.edit_message(view=self)
            
            # Call the callback
            if self.callback:
                await self.callback(interaction, lang_code)
            
            self.stop()
        
        return callback


class GameIDModal(BaseModal):
    """Modal for entering game ID with validation."""
    
    def __init__(
        self,
        *,
        callback: Optional[Callable] = None,
        min_length: int = 6,
        max_length: int = 20,
        **kwargs
    ):
        super().__init__(
            title=t("verification.enter_id_title", kwargs.get('lang', 'en')),
            **kwargs
        )
        self.callback = callback
        
        # Game ID input
        self.game_id = ui.TextInput(
            label=t("verification.game_id_label", self.lang),
            placeholder=t("verification.game_id_placeholder", self.lang),
            min_length=min_length,
            max_length=max_length,
            required=True
        )
        self.add_item(self.game_id)
    
    async def handle_submit(self, interaction: discord.Interaction):
        """Handle modal submission."""
        if self.callback:
            await interaction.response.defer()
            await self.callback(interaction, self.game_id.value.strip())


class VerificationMethodView(BaseView):
    """View for selecting verification method."""
    
    def __init__(
        self,
        *,
        callback: Optional[Callable] = None,
        show_manual: bool = True,
        show_api: bool = True,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.callback = callback
        
        # Manual verification button
        if show_manual:
            manual_btn = ui.Button(
                label=t("verification.manual_method", self.lang),
                emoji="✍️",
                style=discord.ButtonStyle.primary,
                custom_id="manual"
            )
            manual_btn.callback = self._manual_callback
            self.add_item(manual_btn)
        
        # API verification button
        if show_api:
            api_btn = ui.Button(
                label=t("verification.api_method", self.lang),
                emoji="🔗",
                style=discord.ButtonStyle.secondary,
                custom_id="api"
            )
            api_btn.callback = self._api_callback
            self.add_item(api_btn)
        
        # Help button
        help_btn = ui.Button(
            label=t("buttons.help", self.lang),
            emoji="❓",
            style=discord.ButtonStyle.secondary,
            custom_id="help"
        )
        help_btn.callback = self._help_callback
        self.add_item(help_btn)
    
    async def _manual_callback(self, interaction: discord.Interaction):
        """Handle manual verification selection."""
        if self.callback:
            await self.callback(interaction, "manual")
    
    async def _api_callback(self, interaction: discord.Interaction):
        """Handle API verification selection."""
        if self.callback:
            await self.callback(interaction, "api")
    
    async def _help_callback(self, interaction: discord.Interaction):
        """Show help information."""
        embed = discord.Embed(
            title=t("verification.help_title", self.lang),
            description=t("verification.help_description", self.lang),
            color=Config.EMBED_COLOR
        )
        
        embed.add_field(
            name=t("verification.manual_help_title", self.lang),
            value=t("verification.manual_help_description", self.lang),
            inline=False
        )
        
        embed.add_field(
            name=t("verification.api_help_title", self.lang),
            value=t("verification.api_help_description", self.lang),
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


class GameIDVerificationView(BaseView):
    """View for game ID verification with retry functionality."""
    
    def __init__(
        self,
        *,
        callback: Optional[Callable] = None,
        max_retries: int = 3,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.callback = callback
        self.max_retries = max_retries
        self.retry_count = 0
        
        # Enter ID button - main action
        self.enter_id_btn = ui.Button(
            label=f"🎮 {t('verification.enter_id', self.lang)}",
            style=discord.ButtonStyle.success,  # Green for main action
            custom_id="enter_id",
            row=0
        )
        self.enter_id_btn.callback = self._enter_id_callback
        self.add_item(self.enter_id_btn)
        
        # Tutorial button - helpful secondary action
        tutorial_btn = ui.Button(
            label=f"📖 {t('verification.show_tutorial', self.lang)}",
            style=discord.ButtonStyle.primary,  # Blue for help
            custom_id="tutorial",
            row=0
        )
        tutorial_btn.callback = self._tutorial_callback
        self.add_item(tutorial_btn)
        
        # Skip button (if allowed) - less prominent
        if Config.ALLOW_SKIP_VERIFICATION:
            skip_btn = ui.Button(
                label=f"⏭️ {t('buttons.skip', self.lang)}",
                style=discord.ButtonStyle.gray,  # Gray for skip
                custom_id="skip",
                row=1
            )
            skip_btn.callback = self._skip_callback
            self.add_item(skip_btn)
    
    async def _enter_id_callback(self, interaction: discord.Interaction):
        """Handle enter ID button."""
        modal = GameIDModal(
            lang=self.lang,
            callback=self._handle_id_submission
        )
        await interaction.response.send_modal(modal)
    
    async def _handle_id_submission(self, interaction: discord.Interaction, game_id: str):
        """Handle game ID submission."""
        self.retry_count += 1
        
        if self.callback:
            await self.callback(interaction, game_id)
        
        # Check if max retries reached
        if self.retry_count >= self.max_retries:
            self.enter_id_btn.disabled = True
            self.enter_id_btn.label = t("verification.max_retries_reached", self.lang)
            await self.update_message(view=self)
    
    async def _skip_callback(self, interaction: discord.Interaction):
        """Handle skip button."""
        # Show confirmation
        confirm_embed = discord.Embed(
            title=t("verification.skip_confirm_title", self.lang),
            description=t("verification.skip_confirm_description", self.lang),
            color=discord.Color.orange()
        )
        
        confirm_view = ConfirmationView(
            lang=self.lang,
            user_id=self.user_id
        )
        
        await interaction.response.send_message(
            embed=confirm_embed,
            view=confirm_view,
            ephemeral=True
        )
        
        await confirm_view.wait()
        
        if confirm_view.value and self.callback:
            await self.callback(interaction, None)
    
    async def _tutorial_callback(self, interaction: discord.Interaction):
        """Show tutorial for finding game ID."""
        embed = discord.Embed(
            title=t("verification.tutorial_title", self.lang),
            description=t("verification.tutorial_description", self.lang),
            color=Config.EMBED_COLOR
        )
        
        # Add step-by-step instructions
        steps = [
            t("verification.tutorial_step1", self.lang),
            t("verification.tutorial_step2", self.lang),
            t("verification.tutorial_step3", self.lang),
            t("verification.tutorial_step4", self.lang)
        ]
        
        for i, step in enumerate(steps, 1):
            embed.add_field(
                name=f"{i}. {t('verification.step', self.lang)} {i}",
                value=step,
                inline=False
            )
        
        # Add tutorial image if available
        if Config.PLAYER_ID_TUTORIAL_IMAGE:
            embed.set_image(url=Config.PLAYER_ID_TUTORIAL_IMAGE)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


class AllianceTypeButton(ui.Button):
    """Custom button for alliance type selection."""
    
    def __init__(
        self,
        *,
        alliance_type: str,
        label: str,
        emoji: str,
        description: str,
        style: discord.ButtonStyle = discord.ButtonStyle.primary,
        callback: Optional[Callable] = None
    ):
        super().__init__(
            label=label,
            emoji=emoji,
            style=style,
            custom_id=f"alliance_{alliance_type}"
        )
        self.alliance_type = alliance_type
        self.description = description
        self._callback = callback
    
    async def callback(self, interaction: discord.Interaction):
        """Handle button click."""
        # Show description
        embed = discord.Embed(
            title=self.label,
            description=self.description,
            color=Config.EMBED_COLOR
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=5)
        
        # Call the callback
        if self._callback:
            await self._callback(interaction, self.alliance_type)


class AllianceSelectionView(BaseView):
    """View for selecting alliance type."""
    
    def __init__(
        self,
        *,
        callback: Optional[Callable] = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.callback = callback
        
        # Alliance member button - main option
        alliance_btn = AllianceTypeButton(
            alliance_type="alliance",
            label=f"🏰 {t('alliance.type_alliance', self.lang)}",
            emoji="⚔️",
            description=t("alliance.type_alliance_description", self.lang),
            style=discord.ButtonStyle.success,  # Green for recommended option
            callback=self._handle_selection
        )
        self.add_item(alliance_btn)
        
        # No alliance button - independent option
        no_alliance_btn = AllianceTypeButton(
            alliance_type="no_alliance",
            label=f"🚶‍♂️ {t('alliance.type_no_alliance', self.lang)}",
            emoji="🎯",
            description=t("alliance.type_no_alliance_description", self.lang),
            style=discord.ButtonStyle.primary,  # Blue for alternative
            callback=self._handle_selection
        )
        self.add_item(no_alliance_btn)
        
        # Other state button - special case
        other_state_btn = AllianceTypeButton(
            alliance_type="other_state",
            label=f"🌍 {t('alliance.type_other_state', self.lang)}",
            emoji="🗺️",
            description=t("alliance.type_other_state_description", self.lang),
            style=discord.ButtonStyle.gray,  # Gray for less common option
            callback=self._handle_selection
        )
        self.add_item(other_state_btn)
    
    async def _handle_selection(self, interaction: discord.Interaction, alliance_type: str):
        """Handle alliance type selection."""
        # Disable all buttons
        self.disable_all_items()
        
        # Update the selected button
        for item in self.children:
            if isinstance(item, AllianceTypeButton) and item.alliance_type == alliance_type:
                item.style = discord.ButtonStyle.success
        
        await self.update_message(view=self)
        
        if self.callback:
            await self.callback(interaction, alliance_type)
        
        self.stop()


class AllianceNameModal(BaseModal):
    """Modal for entering alliance name."""
    
    def __init__(
        self,
        *,
        callback: Optional[Callable] = None,
        suggestions: Optional[List[str]] = None,
        **kwargs
    ):
        super().__init__(
            title=t("alliance.enter_name_title", kwargs.get('lang', 'en')),
            **kwargs
        )
        self.callback = callback
        
        # Alliance name input
        placeholder = t("alliance.name_placeholder", self.lang)
        if suggestions:
            placeholder += f" ({', '.join(suggestions[:3])}...)"
        
        self.alliance_name = ui.TextInput(
            label=t("alliance.name_label", self.lang),
            placeholder=placeholder,
            min_length=2,
            max_length=50,
            required=True
        )
        self.add_item(self.alliance_name)
    
    async def handle_submit(self, interaction: discord.Interaction):
        """Handle modal submission."""
        if self.callback:
            await interaction.response.defer()
            await self.callback(interaction, self.alliance_name.value.strip())


class AllianceRoleSelectionView(BaseView):
    """View for selecting alliance role (R1-R5)."""
    
    ROLES = [
        ("R5", "👑", discord.ButtonStyle.danger, "Leader"),      # Leader - Red
        ("R4", "⚔️", discord.ButtonStyle.primary, "Officer"),    # Officer - Blue  
        ("R3", "🛡️", discord.ButtonStyle.success, "Elite"),     # Elite - Green
        ("R2", "⚡", discord.ButtonStyle.secondary, "Veteran"),  # Veteran - Gray
        ("R1", "🌱", discord.ButtonStyle.secondary, "Member")    # Member - Gray
    ]
    
    def __init__(
        self,
        *,
        callback: Optional[Callable] = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.callback = callback
        self._create_role_buttons()
    
    def _create_role_buttons(self):
        """Create role selection buttons with enhanced styling."""
        for role, emoji, style, title in self.ROLES:
            button = ui.Button(
                label=f"{emoji} {role} - {title}",
                style=style,
                custom_id=f"role_{role}",
                row=0 if role in ["R5", "R4"] else 1  # Leadership roles on top row
            )
            button.callback = self._make_callback(role)
            self.add_item(button)
    
    def _make_callback(self, role: str):
        """Create callback for role button."""
        async def callback(interaction: discord.Interaction):
            # Update button states
            for item in self.children:
                if isinstance(item, ui.Button):
                    if item.custom_id == f"role_{role}":
                        item.style = discord.ButtonStyle.success
                    item.disabled = True
            
            await interaction.response.edit_message(view=self)
            
            if self.callback:
                await self.callback(interaction, role)
            
            self.stop()
        
        return callback


class VerificationCompleteView(BaseView):
    """View shown when verification is complete."""
    
    def __init__(
        self,
        *,
        show_dashboard: bool = True,
        show_help: bool = True,
        **kwargs
    ):
        super().__init__(**kwargs)
        
        # Dashboard button - primary action
        if show_dashboard:
            dashboard_btn = ui.Button(
                label=f"🎛️ {t('buttons.open_dashboard', self.lang)}",
                style=discord.ButtonStyle.success,  # Green for main action
                custom_id="dashboard",
                row=0
            )
            dashboard_btn.callback = self._dashboard_callback
            self.add_item(dashboard_btn)
        
        # Help button - secondary action
        if show_help:
            help_btn = ui.Button(
                label=f"❓ {t('buttons.get_help', self.lang)}",
                style=discord.ButtonStyle.primary,  # Blue for help
                custom_id="help",
                row=0
            )
            help_btn.callback = self._help_callback
            self.add_item(help_btn)
        
        # Close button - dismiss action
        close_btn = ui.Button(
            label=f"✅ {t('buttons.close', self.lang)}",
            style=discord.ButtonStyle.gray,  # Gray for close
            custom_id="close",
            row=1
        )
        close_btn.callback = self._close_callback
        self.add_item(close_btn)
    
    async def _dashboard_callback(self, interaction: discord.Interaction):
        """Open user dashboard."""
        await interaction.response.send_message(
            t("verification.opening_dashboard", self.lang),
            ephemeral=True
        )
        # Trigger dashboard command
        dashboard_command = interaction.client.get_command("dashboard")
        if dashboard_command:
            await dashboard_command(interaction)
    
    async def _help_callback(self, interaction: discord.Interaction):
        """Show help information."""
        embed = discord.Embed(
            title=t("help.welcome_title", self.lang),
            description=t("help.welcome_description", self.lang),
            color=Config.EMBED_COLOR
        )
        
        # Add command list
        commands = [
            ("/dashboard", t("commands.dashboard_description", self.lang)),
            ("/events", t("commands.events_description", self.lang)),
            ("/alliance", t("commands.alliance_description", self.lang)),
            ("/profile", t("commands.profile_description", self.lang)),
            ("/help", t("commands.help_description", self.lang))
        ]
        
        for cmd, desc in commands:
            embed.add_field(
                name=cmd,
                value=desc,
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    async def _close_callback(self, interaction: discord.Interaction):
        """Close the verification complete message."""
        try:
            await interaction.message.delete()
        except discord.HTTPException:
            await interaction.response.send_message(
                t("errors.cannot_delete", self.lang),
                ephemeral=True
            )