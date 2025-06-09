import discord
from discord import ui
from typing import Optional, Callable
from locales import t
from .base import BaseView, BaseModal

class LanguageSelectView(BaseView):
    def __init__(self, cog = None, **kwargs):
        kwargs['auto_defer'] = False  # Disable auto_defer since buttons edit messages
        super().__init__(timeout=600, **kwargs)  # 10 minuti
        self.cog = cog
        
        # Add language buttons
        languages = [
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
        
        for emoji, label, code in languages:
            button = ui.Button(
                label=label,
                emoji=emoji,
                style=discord.ButtonStyle.primary,
                custom_id=code
            )
            button.callback = self.make_callback(code)
            self.add_item(button)
    
    def make_callback(self, lang_code: str):
        async def callback(interaction: discord.Interaction):
            await self.cog.handle_language_selection(interaction, lang_code)
        return callback
    
    async def on_timeout(self):
        """Chiamato quando la view scade"""
        for item in self.children:
            item.disabled = True

class GameIDModal(BaseModal):
    def __init__(self, lang: str = "en", verify_callback: Optional[Callable] = None):
        super().__init__(title=t("verification.enter_id", lang), lang=lang, custom_id="legacy_game_id_modal")
        self.lang = lang
        self.verify_callback = verify_callback
        
        self.game_id = ui.TextInput(
            label="Game ID",
            placeholder="123456789",
            min_length=6,
            max_length=20,
            required=True
        )
        self.add_item(self.game_id)
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        if self.verify_callback:
            await self.verify_callback(interaction, self.game_id.value)

class AllianceModal(BaseModal):
    def __init__(self, lang: str = "en", submit_callback: Optional[Callable] = None):
        super().__init__(title=t("alliance.enter_name", lang), lang=lang, custom_id="legacy_alliance_modal")
        self.lang = lang
        self.submit_callback = submit_callback
        
        self.alliance_name = ui.TextInput(
            label="Alliance Name",
            placeholder="MyAlliance",
            min_length=2,
            max_length=50,
            required=True
        )
        self.add_item(self.alliance_name)
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        if self.submit_callback:
            await self.submit_callback(interaction, self.alliance_name.value)

class VerificationView(BaseView):
    def __init__(self, lang: str = "en", cog = None, **kwargs):
        kwargs['auto_defer'] = False  # Disable auto_defer since buttons send modals
        super().__init__(timeout=600, lang=lang, **kwargs)  # 10 minuti
        self.lang = lang
        self.cog = cog
    
    @ui.button(label="🎮 Inserisci ID", style=discord.ButtonStyle.success)
    async def verify_button(self, interaction: discord.Interaction, button: ui.Button):
        modal = GameIDModal(self.lang, self.cog.handle_id_verification if self.cog else None)
        await interaction.response.send_modal(modal)

class AllianceTypeView(BaseView):
    def __init__(self, lang: str = "en", cog = None, **kwargs):
        super().__init__(timeout=600, lang=lang, **kwargs)  # 10 minuti
        self.lang = lang
        self.cog = cog
    
    @ui.button(label="Yes, I'm in an alliance", style=discord.ButtonStyle.success, emoji="✅")
    async def alliance_yes(self, interaction: discord.Interaction, button: ui.Button):
        await self.cog.handle_alliance_type_selection(interaction, "alliance")
    
    @ui.button(label="No alliance", style=discord.ButtonStyle.danger, emoji="❌")
    async def alliance_no(self, interaction: discord.Interaction, button: ui.Button):
        await self.cog.handle_alliance_type_selection(interaction, "no_alliance")
    
    @ui.button(label="Other state", style=discord.ButtonStyle.secondary, emoji="🌍")
    async def alliance_other(self, interaction: discord.Interaction, button: ui.Button):
        await self.cog.handle_alliance_type_selection(interaction, "other_state")

class AllianceView(BaseView):
    def __init__(self, lang: str = "en", cog = None, **kwargs):
        kwargs['auto_defer'] = False  # Disable auto_defer since buttons send modals
        super().__init__(timeout=600, lang=lang, **kwargs)  # 10 minuti
        self.lang = lang
        self.cog = cog
    
    @ui.button(label="Inserisci Alleanza", style=discord.ButtonStyle.success, emoji="⚔️")
    async def alliance_button(self, interaction: discord.Interaction, button: ui.Button):
        modal = AllianceModal(self.lang, self.cog.handle_alliance_submission if self.cog else None)
        await interaction.response.send_modal(modal)

class AllianceRoleView(BaseView):
    def __init__(self, lang: str = "en", cog = None, **kwargs):
        super().__init__(timeout=600, lang=lang, **kwargs)  # 10 minuti
        self.lang = lang
        self.cog = cog
        
        # Aggiungi bottoni per ogni ruolo
        roles = ["R5", "R4", "R3", "R2", "R1"]
        for role in roles:
            button = ui.Button(
                label=t(f"alliance.role_{role.lower()}", lang),
                style=discord.ButtonStyle.primary,
                custom_id=role
            )
            button.callback = self.make_callback(role)
            self.add_item(button)
    
    def make_callback(self, role: str):
        async def callback(interaction: discord.Interaction):
            await self.cog.handle_alliance_role_selection(interaction, role)
        return callback