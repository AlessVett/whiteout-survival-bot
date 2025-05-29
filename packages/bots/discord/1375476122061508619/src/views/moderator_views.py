import discord
from discord import ui
from typing import Optional, List
from locales import t
from src.database import Database
from datetime import datetime


class NewsModal(ui.Modal):
    def __init__(self, lang: str):
        super().__init__(title="Send News", timeout=300)
        self.lang = lang
        
        # Title input
        self.title_input = ui.TextInput(
            label=t("moderator.news.title_label", lang),
            placeholder=t("moderator.news.title_placeholder", lang),
            max_length=100,
            required=True
        )
        self.add_item(self.title_input)
        
        # Description input
        self.description = ui.TextInput(
            label=t("moderator.news.description_label", lang),
            placeholder=t("moderator.news.description_placeholder", lang),
            style=discord.TextStyle.paragraph,
            max_length=2000,
            required=True
        )
        self.add_item(self.description)
        
        # Category input
        self.category = ui.TextInput(
            label=t("moderator.news.category_label", lang),
            placeholder=t("moderator.news.category_placeholder", lang),
            max_length=50,
            required=True
        )
        self.add_item(self.category)
    
    async def on_submit(self, interaction: discord.Interaction):
        # Create news embed
        embed = discord.Embed(
            title=f"📰 {self.title_input.value}",
            description=self.description.value,
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        embed.add_field(name="Category", value=self.category.value, inline=True)
        embed.set_footer(text=f"Posted by {interaction.user.display_name}", icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
        
        # Show channel selection
        view = ChannelSelectView(embed, self.lang)
        await interaction.response.send_message(
            t("moderator.news.channel_label", self.lang),
            view=view,
            ephemeral=True
        )


class ChannelSelectView(ui.View):
    def __init__(self, embed: discord.Embed, lang: str):
        super().__init__(timeout=60)
        self.embed = embed
        self.lang = lang
        
    @ui.select(
        cls=ui.ChannelSelect,
        placeholder="Select a channel...",
        min_values=1,
        max_values=1,
        channel_types=[discord.ChannelType.text]
    )
    async def channel_select(self, interaction: discord.Interaction, select: ui.ChannelSelect):
        selected_channel = select.values[0]
        
        try:
            # Get the actual channel object from the guild
            channel = interaction.guild.get_channel(selected_channel.id)
            if not channel:
                await interaction.response.edit_message(
                    content=t("moderator.news.error", self.lang, error="Channel not found"),
                    view=None
                )
                return
                
            # Send the news to selected channel
            await channel.send(embed=self.embed)
            
            await interaction.response.edit_message(
                content=t("moderator.news.sent_success", self.lang),
                view=None
            )
        except Exception as e:
            await interaction.response.edit_message(
                content=t("moderator.news.error", self.lang, error=str(e)),
                view=None
            )


class GiftCodeModal(ui.Modal):
    def __init__(self, lang: str):
        super().__init__(title="Gift Code", timeout=60)
        self.lang = lang
        
        # Gift code input
        self.code = ui.TextInput(
            label=t("moderator.gift_code.code_label", lang),
            placeholder=t("moderator.gift_code.code_placeholder", lang),
            max_length=50,
            required=True
        )
        self.add_item(self.code)
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Find all gift-code channels
            gift_channels = []
            for channel in interaction.guild.text_channels:
                if channel.name.endswith("-gift-codes"):
                    gift_channels.append(channel)
                    print(f"Found gift code channel: {channel.name}")
            
            print(f"Total gift code channels found: {len(gift_channels)}")
            
            if not gift_channels:
                await interaction.followup.send(
                    t("moderator.gift_code.no_channels", self.lang),
                    ephemeral=True
                )
                return
            
            # Create gift code embed
            embed = discord.Embed(
                title=t("moderator.gift_code.embed_title", self.lang),
                description=t("moderator.gift_code.embed_description", self.lang),
                color=discord.Color.gold(),
                timestamp=datetime.utcnow()
            )
            # Link for redeeming the code
            embed.add_field(
                name=t("moderator.gift_code.redeem_link", self.lang),
                value="[Redeem your gift code here](https://wos-giftcode.centurygame.com/)",
                inline=False
            )
            embed.add_field(
                name=t("moderator.gift_code.code_field", self.lang),
                value=f"```{self.code.value}```",
                inline=False
            )
            embed.add_field(
                name=t("moderator.gift_code.validity_field", self.lang),
                value=t("moderator.gift_code.validity_value", self.lang),
                inline=False
            )
            embed.set_footer(
                text=t("moderator.gift_code.shared_by", self.lang, moderator=interaction.user.display_name),
                icon_url=interaction.user.avatar.url if interaction.user.avatar else None
            )
            
            # Send to all gift-code channels
            sent_count = 0
            errors = []
            for channel in gift_channels:
                try:
                    await channel.send(embed=embed)
                    sent_count += 1
                    print(f"Successfully sent to: {channel.name}")
                except Exception as e:
                    error_msg = f"Failed to send to {channel.name}: {str(e)}"
                    errors.append(error_msg)
                    print(error_msg)
            
            # Prepare response message
            if sent_count > 0:
                response = t("moderator.gift_code.sent_success", self.lang, count=sent_count)
                if errors:
                    response += f"\n\n⚠️ Some channels had errors:\n" + "\n".join(errors[:5])  # Show max 5 errors
            else:
                response = t("moderator.gift_code.no_channels", self.lang)
                
            await interaction.followup.send(response, ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(
                t("moderator.gift_code.error", self.lang, error=str(e)),
                ephemeral=True
            )