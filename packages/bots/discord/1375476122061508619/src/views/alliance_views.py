import discord
from discord import ui
from typing import Optional, Callable
from locales import t
from .base import BaseView, BaseModal

class AllianceChangeTypeView(BaseView):
    def __init__(self, lang: str = "en", cog = None, **kwargs):
        kwargs['auto_defer'] = False  # Disable auto_defer since buttons send responses
        super().__init__(timeout=600, lang=lang, **kwargs)
        self.lang = lang
        self.cog = cog
    
    @ui.button(label="🏰 Join Alliance", style=discord.ButtonStyle.success, row=0)
    async def alliance_yes(self, interaction: discord.Interaction, button: ui.Button):
        await self.cog.handle_alliance_change_type(interaction, "alliance")
    
    @ui.button(label="🚶‍♂️ No Alliance", style=discord.ButtonStyle.primary, row=0)
    async def alliance_no(self, interaction: discord.Interaction, button: ui.Button):
        await self.cog.handle_alliance_change_type(interaction, "no_alliance")
    
    @ui.button(label="🌍 Other State", style=discord.ButtonStyle.gray, row=1)
    async def alliance_other(self, interaction: discord.Interaction, button: ui.Button):
        await self.cog.handle_alliance_change_type(interaction, "other_state")

class AllianceChangeNameModal(BaseModal):
    def __init__(self, lang: str = "en", submit_callback: Optional[Callable] = None):
        super().__init__(title=t("alliance.enter_name", lang), lang=lang, custom_id="alliance_change_name_modal")
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

class AllianceChangeNameView(BaseView):
    def __init__(self, lang: str = "en", cog = None, **kwargs):
        kwargs['auto_defer'] = False  # Disable auto_defer since buttons send modals
        super().__init__(timeout=600, lang=lang, **kwargs)
        self.lang = lang
        self.cog = cog
    
    @ui.button(label="✏️ Enter Alliance Name", style=discord.ButtonStyle.success, row=0)
    async def alliance_button(self, interaction: discord.Interaction, button: ui.Button):
        modal = AllianceChangeNameModal(self.lang, self.cog.handle_alliance_change_name if self.cog else None)
        await interaction.response.send_modal(modal)

class AllianceChangeRoleView(BaseView):
    def __init__(self, lang: str = "en", cog = None, **kwargs):
        kwargs['auto_defer'] = False  # Disable auto_defer since buttons send responses
        super().__init__(timeout=600, lang=lang, **kwargs)
        self.lang = lang
        self.cog = cog
        
        # Add buttons for each role with enhanced styling
        roles_info = [
            ("R5", "👑", discord.ButtonStyle.danger, "Leader"),      # Red for leader
            ("R4", "⚔️", discord.ButtonStyle.primary, "Officer"),    # Blue for officer  
            ("R3", "🛡️", discord.ButtonStyle.success, "Elite"),     # Green for elite
            ("R2", "⚡", discord.ButtonStyle.secondary, "Veteran"),  # Gray for veteran
            ("R1", "🌱", discord.ButtonStyle.secondary, "Member")    # Gray for member
        ]
        
        for role, emoji, style, title in roles_info:
            button = ui.Button(
                label=f"{emoji} {role} - {title}",
                style=style,
                custom_id=role,
                row=0 if role in ["R5", "R4"] else 1  # Leadership roles on top
            )
            button.callback = self.make_callback(role)
            self.add_item(button)
    
    def make_callback(self, role: str):
        async def callback(interaction: discord.Interaction):
            await self.cog.handle_alliance_change_role(interaction, role)
        return callback