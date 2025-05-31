import discord
from discord import ui
from typing import Optional, Callable
from locales import t

class LanguageSelectView(ui.View):
    def __init__(self, cog = None):
        super().__init__(timeout=600)  # 10 minuti
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

class GameIDModal(ui.Modal):
    def __init__(self, lang: str = "en", verify_callback: Optional[Callable] = None):
        super().__init__(title=t("verification.enter_id", lang))
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

class AllianceModal(ui.Modal):
    def __init__(self, lang: str = "en", submit_callback: Optional[Callable] = None):
        super().__init__(title=t("alliance.enter_name", lang))
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

class VerificationView(ui.View):
    def __init__(self, lang: str = "en", cog = None):
        super().__init__(timeout=600)  # 10 minuti
        self.lang = lang
        self.cog = cog
    
    @ui.button(label="Inserisci ID", style=discord.ButtonStyle.primary, emoji="🎮")
    async def verify_button(self, interaction: discord.Interaction, button: ui.Button):
        modal = GameIDModal(self.lang, self.cog.handle_id_verification if self.cog else None)
        await interaction.response.send_modal(modal)

class AllianceTypeView(ui.View):
    def __init__(self, lang: str = "en", cog = None):
        super().__init__(timeout=600)  # 10 minuti
        self.lang = lang
        self.cog = cog
    
    @ui.button(style=discord.ButtonStyle.success, emoji="✅")
    async def alliance_yes(self, interaction: discord.Interaction, button: ui.Button):
        button.label = t("alliance.type_yes", self.lang)
        await self.cog.handle_alliance_type_selection(interaction, "alliance")
    
    @ui.button(style=discord.ButtonStyle.danger, emoji="❌")
    async def alliance_no(self, interaction: discord.Interaction, button: ui.Button):
        button.label = t("alliance.type_no", self.lang)
        await self.cog.handle_alliance_type_selection(interaction, "no_alliance")
    
    @ui.button(style=discord.ButtonStyle.secondary, emoji="🌍")
    async def alliance_other(self, interaction: discord.Interaction, button: ui.Button):
        button.label = t("alliance.type_other", self.lang)
        await self.cog.handle_alliance_type_selection(interaction, "other_state")

class AllianceView(ui.View):
    def __init__(self, lang: str = "en", cog = None):
        super().__init__(timeout=600)  # 10 minuti
        self.lang = lang
        self.cog = cog
    
    @ui.button(label="Inserisci Alleanza", style=discord.ButtonStyle.success, emoji="⚔️")
    async def alliance_button(self, interaction: discord.Interaction, button: ui.Button):
        modal = AllianceModal(self.lang, self.cog.handle_alliance_submission if self.cog else None)
        await interaction.response.send_modal(modal)

class AllianceRoleView(ui.View):
    def __init__(self, lang: str = "en", cog = None):
        super().__init__(timeout=600)  # 10 minuti
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