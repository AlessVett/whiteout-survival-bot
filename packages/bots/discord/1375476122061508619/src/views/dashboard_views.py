import discord
from discord import ui
from typing import Optional, List
from locales import t
from .base import BaseView, BaseModal

class DashboardView(BaseView):
    def __init__(self, lang: str = "en", user_data: dict = None, cog = None):
        super().__init__(timeout=600, lang=lang, auto_defer=False)
        self.user_data = user_data
        self.cog = cog
        
        # Aggiungi bottone manage alliance se R4 o R5
        if user_data and user_data.get('alliance_role') in ['R4', 'R5']:
            self.add_item(ManageAllianceButton())
    
    @ui.button(label="🌍 Language", style=discord.ButtonStyle.primary, row=0)
    async def change_language(self, interaction: discord.Interaction, button: ui.Button):
        embed = discord.Embed(
            title="🌍 Language Selection",
            description="Select your preferred language:",
            color=0x3498DB
        )
        view = LanguageChangeView(self.cog)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @ui.button(label="⚔️ Alliance", style=discord.ButtonStyle.success, row=0)
    async def change_alliance(self, interaction: discord.Interaction, button: ui.Button):
        await self.cog.handle_alliance_change(interaction)
    
    @ui.button(label="🔒 Privacy", style=discord.ButtonStyle.gray, row=1) 
    async def privacy_settings(self, interaction: discord.Interaction, button: ui.Button):
        from src.views.privacy_views import PrivacyView
        from src.cogs.commands import CommandsCog
        
        embed = discord.Embed(
            title="🔒 Privacy & Data Management",
            description="Manage your personal data and privacy settings",
            color=0xE74C3C
        )
        
        commands_cog = interaction.client.get_cog('CommandsCog')
        if commands_cog:
            view = PrivacyView(self.lang, commands_cog)
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    

class ManageAllianceButton(ui.Button):
    def __init__(self):
        super().__init__(
            label="👥 Manage",
            style=discord.ButtonStyle.danger,  # Red for admin functions
            row=0
        )
    
    async def callback(self, interaction: discord.Interaction):
        await self.view.cog.handle_alliance_management(interaction)

class LanguageChangeView(BaseView):
    def __init__(self, cog = None):
        super().__init__(timeout=300, auto_defer=False)
        self.cog = cog
        
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
        
        for i, (emoji, label, code) in enumerate(languages):
            # Use different button styles for visual appeal
            if i < 4:
                style = discord.ButtonStyle.primary
            elif i < 8:
                style = discord.ButtonStyle.success
            else:
                style = discord.ButtonStyle.secondary
                
            button = ui.Button(
                label=f"{emoji} {label}",
                style=style,
                row=i // 4  # 4 buttons per row
            )
            button.callback = self.make_callback(code)
            self.add_item(button)
    
    def make_callback(self, lang_code: str):
        async def callback(interaction: discord.Interaction):
            await self.cog.handle_language_change(interaction, lang_code)
        return callback

class AllianceMemberSelect(ui.Select):
    def __init__(self, members: List[dict], lang: str, action: str, cog=None):
        self.lang = lang
        self.action = action
        self.cog = cog
        
        options = []
        for member in members[:25]:  # Discord limit
            nickname = member.get('game_nickname', member.get('discord_name', 'Unknown'))
            role = member.get('alliance_role', 'R1')
            options.append(
                discord.SelectOption(
                    label=f"{nickname} - {role}",
                    value=str(member['discord_id']),
                    description=f"ID: {member.get('game_id', 'N/A')}"
                )
            )
        
        placeholder = t("alliance_management.select_member", lang)
        if action == "transfer":
            placeholder = t("alliance_management.select_new_leader", lang)
            
        super().__init__(
            placeholder=placeholder,
            options=options,
            min_values=1,
            max_values=1
        )
    
    async def callback(self, interaction: discord.Interaction):
        selected_id = int(self.values[0])
        
        if self.action == "change_role":
            view = RoleSelectView(selected_id, self.lang, self.cog)
            await interaction.response.send_message(
                t("alliance_management.select_new_role", self.lang, member=self.values[0]),
                view=view,
                ephemeral=True
            )
        elif self.action == "transfer":
            await self.cog.handle_leadership_transfer(interaction, selected_id)

class RoleSelectView(BaseView):
    def __init__(self, member_id: int, lang: str, cog = None):
        super().__init__(timeout=300, lang=lang, auto_defer=False)
        self.member_id = member_id
        self.cog = cog
        
        roles = ["R1", "R2", "R3", "R4"]
        for role in roles:
            button = ui.Button(
                label=role,
                style=discord.ButtonStyle.primary
            )
            button.callback = self.make_callback(role)
            self.add_item(button)
    
    def make_callback(self, new_role: str):
        async def callback(interaction: discord.Interaction):
            await self.cog.handle_role_change(interaction, self.member_id, new_role)
        return callback

class AllianceManagementView(BaseView):
    def __init__(self, alliance_name: str, members: List[dict], user_role: str, lang: str, cog = None):
        super().__init__(timeout=600, lang=lang)
        self.alliance_name = alliance_name
        self.members = members
        self.user_role = user_role
        self.cog = cog
        
        # Filtra membri che possono essere gestiti
        manageable_members = []
        role_hierarchy = {"R5": 5, "R4": 4, "R3": 3, "R2": 2, "R1": 1}
        user_level = role_hierarchy.get(user_role, 0)
        
        # Ottieni l'ID dell'utente corrente dal cog
        current_user_id = None
        if hasattr(cog, 'current_interaction_user_id'):
            current_user_id = cog.current_interaction_user_id
            
        for member in members:
            member_level = role_hierarchy.get(member.get('alliance_role', 'R1'), 1)
            # Escludi se stesso dalla lista
            if member_level < user_level and member['discord_id'] != current_user_id:
                manageable_members.append(member)
        
        # Riga 0: Select per membri (se ci sono membri gestibili)
        if manageable_members:
            select = AllianceMemberSelect(manageable_members, lang, "change_role", cog)
            self.add_item(select)
        
        # Riga 1: Bottoni di gestione
        # Aggiungi bottone gestione eventi per R4 e R5
        if user_role in ['R4', 'R5']:
            self.add_item(ManageEventsButton(lang))
        
        # Solo R5 può trasferire leadership e sciogliere
        if user_role == "R5":
            self.add_item(TransferLeadershipButton(lang))
            self.add_item(DissolveAllianceButton(lang))

class ManageEventsButton(ui.Button):
    def __init__(self, lang: str):
        super().__init__(
            label=t("alliance_management.manage_events", lang),
            style=discord.ButtonStyle.primary,
            emoji="📅",
            row=1
        )
        self.lang = lang
    
    async def callback(self, interaction: discord.Interaction):
        from .event_views import EventListView
        view = EventListView(self.view.alliance_name, self.lang)
        await view.setup()
        await interaction.response.send_message(
            t("events.view_events", self.lang),
            view=view,
            ephemeral=True
        )

class TransferLeadershipButton(ui.Button):
    def __init__(self, lang: str):
        super().__init__(
            label=t("alliance_management.transfer_leadership", lang),
            style=discord.ButtonStyle.danger,
            emoji="👑",
            row=2
        )
        self.lang = lang
    
    async def callback(self, interaction: discord.Interaction):
        # Mostra selezione per nuovo leader
        eligible_members = [m for m in self.view.members if m.get('alliance_role') != 'R5']
        if eligible_members:
            select = AllianceMemberSelect(eligible_members, self.lang, "transfer", self.view.cog)
            view = BaseView(timeout=300, lang=self.lang, auto_defer=False)
            view.add_item(select)
            await interaction.response.send_message(
                t("alliance_management.select_new_leader", self.lang),
                view=view,
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "No eligible members for leadership transfer.",
                ephemeral=True
            )

class DissolveAllianceButton(ui.Button):
    def __init__(self, lang: str):
        super().__init__(
            label=t("alliance_management.dissolve", lang),
            style=discord.ButtonStyle.danger,
            emoji="💔",
            row=2
        )
        self.lang = lang
    
    async def callback(self, interaction: discord.Interaction):
        view = ConfirmDissolveView(self.lang, self.view.cog, self.view.alliance_name)
        await interaction.response.send_message(
            t("alliance_management.confirm_dissolve", self.lang),
            view=view,
            ephemeral=True
        )

class ConfirmDissolveView(BaseView):
    def __init__(self, lang: str, cog = None, alliance_name: str = None):
        super().__init__(timeout=60, lang=lang, auto_defer=False)
        self.cog = cog
        self.alliance_name = alliance_name
    
    @ui.button(label="✅ Confirm", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: ui.Button):
        await self.cog.handle_alliance_dissolution(interaction, self.alliance_name)
    
    @ui.button(label="❌ Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message("Dissolution cancelled.", ephemeral=True)