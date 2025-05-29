import discord
from discord import ui
from typing import Optional, Callable
from locales import t

class AllianceChangeTypeView(ui.View):
    def __init__(self, lang: str = "en", cog = None):
        super().__init__(timeout=600)
        self.lang = lang
        self.cog = cog
    
    @ui.button(style=discord.ButtonStyle.success, emoji="✅")
    async def alliance_yes(self, interaction: discord.Interaction, button: ui.Button):
        button.label = t("alliance.type_yes", self.lang)
        await self.cog.handle_alliance_change_type(interaction, "alliance")
    
    @ui.button(style=discord.ButtonStyle.danger, emoji="❌")
    async def alliance_no(self, interaction: discord.Interaction, button: ui.Button):
        button.label = t("alliance.type_no", self.lang)
        await self.cog.handle_alliance_change_type(interaction, "no_alliance")
    
    @ui.button(style=discord.ButtonStyle.secondary, emoji="🌍")
    async def alliance_other(self, interaction: discord.Interaction, button: ui.Button):
        button.label = t("alliance.type_other", self.lang)
        await self.cog.handle_alliance_change_type(interaction, "other_state")

class AllianceChangeNameModal(ui.Modal):
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

class AllianceChangeNameView(ui.View):
    def __init__(self, lang: str = "en", cog = None):
        super().__init__(timeout=600)
        self.lang = lang
        self.cog = cog
    
    @ui.button(label="Enter Alliance Name", style=discord.ButtonStyle.success, emoji="⚔️")
    async def alliance_button(self, interaction: discord.Interaction, button: ui.Button):
        modal = AllianceChangeNameModal(self.lang, self.cog.handle_alliance_change_name if self.cog else None)
        await interaction.response.send_modal(modal)

class AllianceChangeRoleView(ui.View):
    def __init__(self, lang: str = "en", cog = None):
        super().__init__(timeout=600)
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
            await self.cog.handle_alliance_change_role(interaction, role)
        return callback