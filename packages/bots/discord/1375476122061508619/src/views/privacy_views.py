import discord
from discord import ui
from typing import Optional
from locales import t
import json
from datetime import datetime

class PrivacyView(ui.View):
    def __init__(self, lang: str = "en", cog = None):
        super().__init__(timeout=300)
        self.lang = lang
        self.cog = cog
    
    @ui.button(label="📄 View My Data", style=discord.ButtonStyle.primary, row=0)
    async def view_data(self, interaction: discord.Interaction, button: ui.Button):
        button.label = t("privacy.view_data", self.lang)
        await self.cog.handle_view_data(interaction, self.lang)
    
    
    @ui.button(label="🗑️ Delete My Data", style=discord.ButtonStyle.danger, row=0)
    async def delete_data(self, interaction: discord.Interaction, button: ui.Button):
        button.label = t("privacy.delete_data", self.lang)
        view = DeleteConfirmationView(self.lang, self.cog)
        
        embed = discord.Embed(
            title=t("privacy.delete_confirmation", self.lang),
            description=t("privacy.delete_warning", self.lang),
            color=discord.Color.red()
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @ui.button(label="📋 Privacy Policy", style=discord.ButtonStyle.secondary, row=1)
    async def privacy_policy(self, interaction: discord.Interaction, button: ui.Button):
        button.label = t("privacy.privacy_policy", self.lang)
        
        embed = discord.Embed(
            title=t("privacy.policy_links", self.lang),
            description=t("privacy.policy_description", self.lang),
            color=discord.Color.blue()
        )
        
        # Replace with your actual URLs
        privacy_url = "https://wos-2630.fun/discord/privacy-policy/"
        terms_url = "https://wos-2630.fun/discord/terms-of-service/"
        
        embed.add_field(
            name=t("privacy.privacy_policy", self.lang),
            value=f"[View Privacy Policy]({privacy_url})",
            inline=True
        )
        embed.add_field(
            name=t("privacy.terms_service", self.lang),
            value=f"[View Terms of Service]({terms_url})",
            inline=True
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

class DeleteConfirmationView(ui.View):
    def __init__(self, lang: str = "en", cog = None):
        super().__init__(timeout=60)
        self.lang = lang
        self.cog = cog
    
    @ui.button(label="🗑️ Yes, Delete Everything", style=discord.ButtonStyle.danger)
    async def confirm_delete(self, interaction: discord.Interaction, button: ui.Button):
        button.label = t("privacy.delete_confirm", self.lang)
        await self.cog.handle_delete_data(interaction, self.lang)
    
    @ui.button(label="❌ Cancel", style=discord.ButtonStyle.secondary)
    async def cancel_delete(self, interaction: discord.Interaction, button: ui.Button):
        button.label = t("privacy.delete_cancel", self.lang)
        await interaction.response.send_message(
            "❌ Deletion cancelled.",
            ephemeral=True
        )
        
        # Disable all buttons
        for item in self.children:
            item.disabled = True
        await interaction.edit_original_response(view=self)