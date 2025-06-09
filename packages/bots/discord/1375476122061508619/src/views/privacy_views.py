import discord
from discord import ui
from typing import Optional
from locales import t
import json
from datetime import datetime
from .base import BaseView

class PrivacyView(BaseView):
    def __init__(self, lang: str = "en", cog = None):
        super().__init__(
            lang=lang,
            timeout=300,
            auto_defer=False,
            custom_id="privacy_view"
        )
        self.cog = cog
    
    @ui.button(label="🔍 View Data", style=discord.ButtonStyle.primary, row=0)
    async def view_data(self, interaction: discord.Interaction, button: ui.Button):
        await self.cog.handle_view_data(interaction, self.lang)
    
    @ui.button(label="📥 Export Data", style=discord.ButtonStyle.secondary, row=0)
    async def export_data(self, interaction: discord.Interaction, button: ui.Button):
        await self.cog.handle_export_data(interaction, self.lang)
    
    @ui.button(label="🗑️ Delete Data", style=discord.ButtonStyle.danger, row=1)
    async def delete_data(self, interaction: discord.Interaction, button: ui.Button):
        view = DeleteConfirmationView(self.lang, self.cog)
        
        embed = discord.Embed(
            title="⚠️ " + t("privacy.delete_confirmation", self.lang),
            color=0xE74C3C  # Red for danger
        )
        embed.set_author(
            name="Data Deletion Warning",
            icon_url="https://cdn.discordapp.com/emojis/warning.gif"
        )
        
        embed.description = (
            f"┌─────────────────────────────────────────┐\n"
            f"│  **⚠️ PERMANENT ACTION WARNING**       │\n"
            f"└─────────────────────────────────────────┘\n\n"
            f"🚨 {t('privacy.delete_warning', self.lang)}\n\n"
            f"**❗ What will be deleted:**\n"
            f"🔹 Your Discord account data\n"
            f"🔹 Game ID and verification info\n"
            f"🔹 Alliance membership and role\n"
            f"🔹 All personal settings and preferences\n"
            f"🔹 Event history and participation\n\n"
            f"**⚡ This action is IRREVERSIBLE!**"
        )
        
        embed.set_footer(
            text="💭 Think carefully before proceeding • You can always contact support",
            icon_url="https://cdn.discordapp.com/emojis/thinking.gif"
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @ui.button(label="📋 Policies", style=discord.ButtonStyle.gray, row=1)
    async def privacy_policy(self, interaction: discord.Interaction, button: ui.Button):
        embed = discord.Embed(
            title="📋 Legal Documents",
            color=0x95A5A6  # Gray for info
        )
        embed.set_author(
            name="Privacy & Terms",
            icon_url="https://cdn.discordapp.com/emojis/document.gif"
        )
        
        embed.description = (
            f"┌────────────────────────────────────┐\n"
            f"│  **Legal Information & Policies** │\n"
            f"└────────────────────────────────────┘\n\n"
            f"📖 {t('privacy.policy_description', self.lang)}"
        )
        
        # Enhanced policy links with descriptions
        privacy_url = "https://wos-2630.fun/discord/privacy-policy/"
        terms_url = "https://wos-2630.fun/discord/terms-of-service/"
        
        embed.add_field(
            name="🔒 Privacy Policy",
            value=f"[📄 Read Privacy Policy]({privacy_url})\n└─ How we handle your data",
            inline=True
        )
        embed.add_field(
            name="📜 Terms of Service", 
            value=f"[📄 Read Terms of Service]({terms_url})\n└─ Rules and conditions of use",
            inline=True
        )
        embed.add_field(
            name="📧 Contact",
            value="support@wos-2630.fun\n└─ Questions about privacy",
            inline=True
        )
        
        embed.set_footer(
            text="🔗 Links open in your browser • Updated regularly",
            icon_url="https://cdn.discordapp.com/emojis/link.gif"
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

class DeleteConfirmationView(BaseView):
    def __init__(self, lang: str = "en", cog = None):
        super().__init__(
            lang=lang,
            timeout=60,
            auto_defer=False,
            custom_id="delete_confirmation_view"
        )
        self.cog = cog
    
    @ui.button(label="🗑️ DELETE EVERYTHING", style=discord.ButtonStyle.danger, row=0)
    async def confirm_delete(self, interaction: discord.Interaction, button: ui.Button):
        await self.cog.handle_delete_data(interaction, self.lang)
        
        # Disable all buttons after confirmation
        for item in self.children:
            item.disabled = True
        await interaction.edit_original_response(view=self)
    
    @ui.button(label="🛡️ Keep My Data", style=discord.ButtonStyle.success, row=0) 
    async def cancel_delete(self, interaction: discord.Interaction, button: ui.Button):
        embed = discord.Embed(
            title="✅ Data Deletion Cancelled",
            description=(
                "🛡️ Your data is safe and remains intact.\n"
                "You can access this menu anytime to manage your privacy settings."
            ),
            color=0x27AE60  # Green for safety
        )
        embed.set_footer(
            text="💚 Thank you for staying with us!",
            icon_url="https://cdn.discordapp.com/emojis/heart_green.gif"
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
        # Disable all buttons
        for item in self.children:
            item.disabled = True
        await interaction.edit_original_response(view=self)