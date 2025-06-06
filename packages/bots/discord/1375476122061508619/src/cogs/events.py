import discord
from discord.ext import commands
import random

from src.database import get_database
from locales import t

class EventsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = get_database()
    
    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        """Gestisce quando un membro lascia il server"""
        if member.bot:
            return
        
        # Controlla se l'utente era un R5
        user_data = await self.db.get_user(member.id)
        if not user_data:
            return
        
        if user_data.get('alliance_role') == 'R5' and user_data.get('alliance'):
            await self.handle_r5_departure(member.guild, user_data)
    
    async def handle_r5_departure(self, guild: discord.Guild, r5_data: dict):
        """Gestisce la partenza di un R5"""
        alliance_name = r5_data['alliance']
        
        # Trova tutti i membri R4 dell'alleanza
        alliance_members = await self.db.get_users_by_alliance(alliance_name)
        r4_members = [m for m in alliance_members if m.get('alliance_role') == 'R4' and m['discord_id'] != r5_data['discord_id']]
        
        if not r4_members:
            # Se non ci sono R4, cerca R3, poi R2, poi R1
            for role in ['R3', 'R2', 'R1']:
                candidates = [m for m in alliance_members if m.get('alliance_role') == role]
                if candidates:
                    r4_members = candidates
                    break
        
        if r4_members:
            # Scegli un nuovo R5 a caso
            new_r5_data = random.choice(r4_members)
            new_r5_id = new_r5_data['discord_id']
            
            # Aggiorna database
            await self.db.update_user_alliance(new_r5_id, alliance_role="R5")
            await self.db.update_alliance_r5(alliance_name, new_r5_id)
            
            # Aggiorna ruoli Discord
            new_r5_member = guild.get_member(new_r5_id)
            if new_r5_member:
                # Rimuovi vecchio ruolo
                old_role_name = new_r5_data.get('alliance_role', 'R1')
                old_role = discord.utils.get(guild.roles, name=f"{alliance_name} - {old_role_name}")
                if old_role and old_role in new_r5_member.roles:
                    await new_r5_member.remove_roles(old_role)
                
                # Aggiungi ruolo R5
                r5_role = discord.utils.get(guild.roles, name=f"{alliance_name} - R5")
                if r5_role:
                    await new_r5_member.add_roles(r5_role)
                
                # Notifica nel canale alleanza
                alliance_data = await self.db.get_alliance(alliance_name)
                if alliance_data:
                    channel = guild.get_channel(alliance_data['channel_id'])
                    if channel:
                        lang = new_r5_data.get('language', 'en')
                        embed = discord.Embed(
                            title="👑 Leadership Transfer",
                            color=0xFF6B35  # Orange for important alliance events
                        )
                        embed.set_author(
                            name="⚠️ Automatic Leadership Change",
                            icon_url="https://cdn.discordapp.com/emojis/crown_transfer.gif"
                        )
                        embed.description = (
                            f"┌────────────────────────────────────────┐\n"
                            f"│  **Alliance Leadership Change**       │\n"
                            f"└────────────────────────────────────────┘\n\n"
                            f"🔄 {t('alliance_management.r5_abandoned', lang, member=new_r5_member.mention)}\n\n"
                            f"**What happened:**\n"
                            f"🚪 Previous R5 left the alliance\n"
                            f"👑 Leadership automatically transferred\n"
                            f"⚡ Alliance continues under new leadership"
                        )
                        embed.add_field(
                            name="🎯 New Leader",
                            value=f"• {new_r5_member.mention}\n• Now has full R5 permissions\n• Can manage alliance settings",
                            inline=False
                        )
                        embed.set_footer(
                            text="🤖 Automatic system action • Alliance stability maintained",
                            icon_url="https://cdn.discordapp.com/emojis/robot.gif"
                        )
                        await channel.send(embed=embed)
        else:
            # Se non ci sono membri, sciogli l'alleanza
            await self.dissolve_abandoned_alliance(guild, alliance_name)
    
    async def dissolve_abandoned_alliance(self, guild: discord.Guild, alliance_name: str):
        """Sciogli un'alleanza abbandonata"""
        # Elimina canale alleanza
        alliance_data = await self.db.get_alliance(alliance_name)
        if alliance_data:
            channel = guild.get_channel(alliance_data['channel_id'])
            if channel:
                await channel.delete()
        
        # Elimina ruoli
        alliance_role = discord.utils.get(guild.roles, name=alliance_name)
        if alliance_role:
            await alliance_role.delete()
            
        for role_name in ["R1", "R2", "R3", "R4", "R5"]:
            role = discord.utils.get(guild.roles, name=f"{alliance_name} - {role_name}")
            if role:
                await role.delete()
        
        # Elimina alleanza dal database
        await self.db.delete_alliance(alliance_name)

async def setup(bot):
    await bot.add_cog(EventsCog(bot))