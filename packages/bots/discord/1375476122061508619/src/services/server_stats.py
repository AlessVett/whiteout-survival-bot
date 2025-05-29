import discord
from discord.ext import commands, tasks
from typing import Dict, List
from src.database import get_database
import asyncio


class ServerStats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = get_database()
        self.stats_category_name = "📊 Server Statistics"
        self.update_interval = 15  # Update every 15 seconds
        
    async def setup_stats_channels(self, guild: discord.Guild):
        """Setup all statistics channels"""
        # Find or create statistics category
        category = discord.utils.get(guild.categories, name=self.stats_category_name)
        if not category:
            category = await guild.create_category(
                self.stats_category_name,
                position=0  # Put at top
            )
        
        # Prima pulisci eventuali duplicati
        await self._cleanup_duplicate_stats(category)
        
        # Define stats channels to create
        stats_config = {
            "total_members": {
                "name": "👥 Total Members: {count}",
                "count": guild.member_count
            },
            "verified_members": {
                "name": "✅ Verified: {count}",
                "count": await self._get_verified_count(guild)
            },
            "alliances": {
                "name": "⚔️ Alliances: {count}",
                "count": await self._get_alliance_count()
            },
            "r5_leaders": {
                "name": "👑 R5 Leaders: {count}",
                "count": await self._get_r5_count(guild)
            },
            "r4_leaders": {
                "name": "🛡️ R4 Leaders: {count}",
                "count": await self._get_r4_count(guild)
            },
            "active_events": {
                "name": "📅 Active Events: {count}",
                "count": await self._get_active_events_count()
            },
            "no_alliance": {
                "name": "🚫 No Alliance: {count}",
                "count": await self._get_no_alliance_count(guild)
            },
            "other_state": {
                "name": "🌍 Other State: {count}",
                "count": await self._get_other_state_count(guild)
            },
            "online_members": {
                "name": "🟢 Online: {count}",
                "count": self._get_online_count(guild)
            },
            "channels": {
                "name": "💬 Channels: {count}",
                "count": len(guild.channels)
            }
        }
        
        # Identify existing channels using precise emoji matching
        existing_channels = {}
        emoji_mappings = {
            "👥": "total_members",
            "✅": "verified_members", 
            "⚔️": "alliances",
            "👑": "r5_leaders",
            "🛡️": "r4_leaders",
            "📅": "active_events",
            "🚫": "no_alliance",
            "🌍": "other_state",
            "🟢": "online_members",
            "💬": "channels"
        }
        
        for channel in category.voice_channels:
            # Match by first character (emoji)
            if len(channel.name) > 0:
                first_char = channel.name[0]
                if first_char in emoji_mappings:
                    stat_type = emoji_mappings[first_char]
                    existing_channels[stat_type] = channel
                    print(f"Canale esistente trovato: {stat_type} -> {channel.name}")
        
        # Create/update channels
        for stat_type, config in stats_config.items():
            channel_name = config['name'].format(count=config['count'])
            
            if stat_type in existing_channels:
                # Update existing channel
                channel = existing_channels[stat_type]
                if channel.name != channel_name:
                    await channel.edit(name=channel_name)
            else:
                # Create new channel
                overwrites = {
                    guild.default_role: discord.PermissionOverwrite(
                        connect=False,
                        view_channel=True
                    ),
                    guild.me: discord.PermissionOverwrite(
                        connect=True,
                        view_channel=True,
                        manage_channels=True
                    )
                }
                
                await guild.create_voice_channel(
                    name=channel_name,
                    category=category,
                    overwrites=overwrites
                )
    
    async def update_stats(self, guild: discord.Guild):
        """Update all statistics channels"""
        category = discord.utils.get(guild.categories, name=self.stats_category_name)
        if not category:
            return
        
        # Get current stats with same mapping as setup
        stats_config = {
            "total_members": {
                "name": "👥 Total Members: {count}",
                "count": guild.member_count
            },
            "verified_members": {
                "name": "✅ Verified: {count}",
                "count": await self._get_verified_count(guild)
            },
            "alliances": {
                "name": "⚔️ Alliances: {count}",
                "count": await self._get_alliance_count()
            },
            "r5_leaders": {
                "name": "👑 R5 Leaders: {count}",
                "count": await self._get_r5_count(guild)
            },
            "r4_leaders": {
                "name": "🛡️ R4 Leaders: {count}",
                "count": await self._get_r4_count(guild)
            },
            "active_events": {
                "name": "📅 Active Events: {count}",
                "count": await self._get_active_events_count()
            },
            "no_alliance": {
                "name": "🚫 No Alliance: {count}",
                "count": await self._get_no_alliance_count(guild)
            },
            "other_state": {
                "name": "🌍 Other State: {count}",
                "count": await self._get_other_state_count(guild)
            },
            "online_members": {
                "name": "🟢 Online: {count}",
                "count": self._get_online_count(guild)
            },
            "channels": {
                "name": "💬 Channels: {count}",
                "count": len(guild.channels)
            }
        }
        
        # Identify existing channels using precise emoji matching
        existing_channels = {}
        emoji_mappings = {
            "👥": "total_members",
            "✅": "verified_members", 
            "⚔️": "alliances",
            "👑": "r5_leaders",
            "🛡️": "r4_leaders",
            "📅": "active_events",
            "🚫": "no_alliance",
            "🌍": "other_state",
            "🟢": "online_members",
            "💬": "channels"
        }
        
        for channel in category.voice_channels:
            # Match by first character (emoji)
            if len(channel.name) > 0:
                first_char = channel.name[0]
                if first_char in emoji_mappings:
                    stat_type = emoji_mappings[first_char]
                    existing_channels[stat_type] = channel
        
        # Update channels
        for stat_type, config in stats_config.items():
            if stat_type in existing_channels:
                channel = existing_channels[stat_type]
                new_name = config['name'].format(count=config['count'])
                if channel.name != new_name:
                    try:
                        await channel.edit(name=new_name)
                        await asyncio.sleep(0.5)  # Rate limit prevention
                    except discord.HTTPException as e:
                        print(f"Errore aggiornamento canale {channel.name}: {e}")
                    except Exception as e:
                        print(f"Errore generico aggiornamento canale {channel.name}: {e}")
    
    async def _get_verified_count(self, guild: discord.Guild) -> int:
        """Count verified members"""
        verified_role = discord.utils.get(guild.roles, name="Verified")
        if verified_role:
            return len(verified_role.members)
        return 0
    
    async def _get_alliance_count(self) -> int:
        """Count unique alliances"""
        alliances = await self.db.alliances.distinct("name")
        return len(alliances)
    
    async def _get_r5_count(self, guild: discord.Guild) -> int:
        """Count R5 leaders"""
        r5_count = 0
        for role in guild.roles:
            if role.name.endswith(" - R5"):
                r5_count += len(role.members)
        return r5_count
    
    async def _get_r4_count(self, guild: discord.Guild) -> int:
        """Count R4 leaders"""
        r4_count = 0
        for role in guild.roles:
            if role.name.endswith(" - R4"):
                r4_count += len(role.members)
        return r4_count
    
    async def _get_no_alliance_count(self, guild: discord.Guild) -> int:
        """Count members with no alliance"""
        no_alliance_role = discord.utils.get(guild.roles, name="No Alliance")
        if no_alliance_role:
            return len(no_alliance_role.members)
        return 0
    
    async def _get_other_state_count(self, guild: discord.Guild) -> int:
        """Count members from other states"""
        other_state_role = discord.utils.get(guild.roles, name="Other State")
        if other_state_role:
            return len(other_state_role.members)
        return 0
    
    async def _get_active_events_count(self) -> int:
        """Count active events"""
        count = await self.db.events.count_documents({"active": True})
        return count
    
    def _get_online_count(self, guild: discord.Guild) -> int:
        """Count online members"""
        online_count = 0
        for member in guild.members:
            if member.status != discord.Status.offline:
                online_count += 1
        return online_count
    
    async def _cleanup_duplicate_stats(self, category: discord.CategoryChannel):
        """Rimuove canali statistiche duplicati"""
        print("Pulizia canali statistiche duplicati...")
        
        # Definisci le emoji uniche per ogni tipo di statistica
        unique_emojis = {"👥", "✅", "⚔️", "👑", "🛡️", "📅", "🚫", "🌍", "🟢", "💬"}
        found_emojis = set()
        
        channels_to_delete = []
        
        for channel in category.voice_channels:
            # Estrai emoji dal nome del canale
            if len(channel.name) > 0:
                first_char = channel.name[0]
                if first_char in unique_emojis:
                    if first_char in found_emojis:
                        # Emoji già trovata = duplicato
                        channels_to_delete.append(channel)
                        print(f"Canale duplicato trovato: {channel.name}")
                    else:
                        found_emojis.add(first_char)
                else:
                    # Canale senza emoji riconoscibile nelle stats
                    if any(keyword in channel.name for keyword in ["Members", "Verified", "Alliance", "Leaders", "Events", "Online", "Channels"]):
                        channels_to_delete.append(channel)
                        print(f"Canale stats senza emoji riconoscibile: {channel.name}")
        
        # Elimina i duplicati
        for channel in channels_to_delete:
            try:
                await channel.delete()
                print(f"Eliminato canale duplicato: {channel.name}")
                await asyncio.sleep(0.5)  # Rate limit protection
            except Exception as e:
                print(f"Errore eliminazione canale {channel.name}: {e}")


class ServerStatsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.stats = ServerStats(bot)
        self.update_stats_task.start()
    
    def cog_unload(self):
        self.update_stats_task.cancel()
    
    @commands.Cog.listener()
    async def on_ready(self):
        """Setup stats channels when bot is ready"""
        for guild in self.bot.guilds:
            await self.stats.setup_stats_channels(guild)
    
    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Update stats when member joins"""
        await self.stats.update_stats(member.guild)
    
    @commands.Cog.listener()
    async def on_member_remove(self, member):
        """Update stats when member leaves"""
        await self.stats.update_stats(member.guild)
    
    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        """Update stats when member roles change"""
        if before.roles != after.roles:
            await self.stats.update_stats(after.guild)
    
    @commands.Cog.listener()
    async def on_presence_update(self, before, after):
        """Update online count when presence changes"""
        if before.status != after.status:
            # Only update if status changed from/to offline
            if before.status == discord.Status.offline or after.status == discord.Status.offline:
                await self.stats.update_stats(after.guild)
    
    @tasks.loop(seconds=15)
    async def update_stats_task(self):
        """Periodically update all stats"""
        for guild in self.bot.guilds:
            await self.stats.update_stats(guild)
    
    @update_stats_task.before_loop
    async def before_update_stats(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(ServerStatsCog(bot))