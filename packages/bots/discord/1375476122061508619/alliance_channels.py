import discord
from typing import Dict, Optional
from config import Config
from locales import t
from database import get_database

class AllianceChannels:
    def __init__(self):
        self.db = get_database()
    
    async def create_all_alliance_channels(self, guild: discord.Guild, alliance: str, alliance_role: discord.Role, lang: str = "en"):
        """Crea tutti i canali standard per un'alleanza"""
        # Trova o crea la categoria per l'alleanza
        category_name = f"{alliance} Channels"
        category = discord.utils.get(guild.categories, name=category_name)
        if not category:
            category = await guild.create_category(category_name)
            
        # Definisci i canali da creare e i loro permessi - SEMPRE IN INGLESE
        channels_config = {
            "general": {
                "name": "general",
                "overwrites": self._get_standard_overwrites(guild, alliance_role),
                "welcome": f"Welcome to the {alliance} general channel!"
            },
            "reminders": {
                "name": "reminders",
                "overwrites": self._get_standard_overwrites(guild, alliance_role),
                "welcome": "📅 This channel is for event reminders and important notifications."
            },
            "gift-codes": {
                "name": "gift-codes",
                "overwrites": self._get_standard_overwrites(guild, alliance_role),
                "welcome": "🎁 Share gift codes here! Please mark them when used."
            },
            "r4-r5-only": {
                "name": "r4-r5-only",
                "overwrites": self._get_leadership_overwrites(guild, alliance),
                "welcome": "🔒 This is a private channel for R4 and R5 leadership only."
            },
            "university": {
                "name": "university",
                "overwrites": self._get_standard_overwrites(guild, alliance_role),
                "welcome": "📚 Welcome to the alliance university! Share tips, strategies, and help new members learn the game."
            }
        }
        
        # Crea i canali
        created_channels = {}
        for channel_type, config in channels_config.items():
            # Controlla se il canale esiste già
            existing = await self.db.get_alliance_channel(alliance, channel_type)
            if existing:
                channel = guild.get_channel(existing['channel_id'])
                if channel:
                    created_channels[channel_type] = channel
                    continue
            
            # Crea nuovo canale
            channel = await guild.create_text_channel(
                name=f"{alliance.lower()}-{config['name']}",
                category=category,
                overwrites=config['overwrites']
            )
            
            # Salva nel database
            await self.db.save_alliance_channel(alliance, channel_type, channel.id)
            
            # Invia messaggio di benvenuto
            embed = discord.Embed(
                description=config['welcome'],
                color=Config.EMBED_COLOR
            )
            await channel.send(embed=embed)
            
            created_channels[channel_type] = channel
        
        return created_channels
    
    def _get_standard_overwrites(self, guild: discord.Guild, alliance_role: discord.Role) -> Dict:
        """Ottiene i permessi standard per i canali alleanza"""
        return {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            alliance_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_messages=True)
        }
    
    def _get_leadership_overwrites(self, guild: discord.Guild, alliance: str) -> Dict:
        """Ottiene i permessi per i canali solo leadership"""
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_messages=True)
        }
        
        # Aggiungi permessi per R4 e R5
        for role_name in ["R4", "R5"]:
            role = discord.utils.get(guild.roles, name=f"{alliance} - {role_name}")
            if role:
                overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        
        return overwrites
    
    async def create_communication_channel(self, guild: discord.Guild, alliance: str, channel_name: str, creator_id: int, lang: str = "en"):
        """Crea un canale di comunicazione personalizzato"""
        # Trova la categoria dell'alleanza
        category_name = f"{alliance} Channels"
        category = discord.utils.get(guild.categories, name=category_name)
        if not category:
            category = await guild.create_category(category_name)
        
        # Ottieni ruolo alleanza
        alliance_role = discord.utils.get(guild.roles, name=alliance)
        if not alliance_role:
            return None
        
        # Crea canale
        channel = await guild.create_text_channel(
            name=f"{alliance.lower()}-{channel_name}",
            category=category,
            overwrites=self._get_standard_overwrites(guild, alliance_role)
        )
        
        # Salva nel database
        await self.db.save_alliance_channel(alliance, f"comm-{channel_name}", channel.id)
        
        # Invia messaggio di benvenuto - SEMPRE IN INGLESE
        embed = discord.Embed(
            description="📢 Direct communications channel for important announcements.",
            color=Config.EMBED_COLOR
        )
        embed.set_footer(text=f"Created by {guild.get_member(creator_id).display_name}")
        await channel.send(embed=embed)
        
        return channel
    
    async def create_event_channel(self, guild: discord.Guild, alliance: str, event_name: str, event_description: str, lang: str = "en"):
        """Crea un canale per un evento"""
        # Trova la categoria dell'alleanza
        category_name = f"{alliance} Channels"
        category = discord.utils.get(guild.categories, name=category_name)
        if not category:
            category = await guild.create_category(category_name)
        
        # Ottieni ruolo alleanza
        alliance_role = discord.utils.get(guild.roles, name=alliance)
        if not alliance_role:
            return None
        
        # Crea canale - SEMPRE IN INGLESE
        safe_event_name = event_name.lower().replace(" ", "-")[:20]
        channel = await guild.create_text_channel(
            name=f"event-{safe_event_name}",
            category=category,
            overwrites=self._get_standard_overwrites(guild, alliance_role),
            topic=event_description
        )
        
        # Invia messaggio di benvenuto - SEMPRE IN INGLESE
        embed = discord.Embed(
            title=event_name,
            description=f"📅 Channel for the event: {event_name}",
            color=Config.EMBED_COLOR
        )
        if event_description:
            embed.add_field(name="Description", value=event_description, inline=False)
        
        await channel.send(embed=embed)
        
        return channel
    
    async def ensure_state_r5_channel(self, guild: discord.Guild, member: discord.Member = None, lang: str = "en"):
        """Assicura che esista un canale per tutti gli R5 dello stato"""
        channel_name = "r5-council"  # SEMPRE IN INGLESE
        
        # Controlla se esiste già
        existing = discord.utils.get(guild.text_channels, name=channel_name)
        if existing:
            # Se esiste già e abbiamo un membro R5, aggiorna i permessi
            if member:
                # Trova il ruolo R5 del membro
                r5_role = None
                for role in member.roles:
                    if role.name.endswith(" - R5"):
                        r5_role = role
                        break
                
                if r5_role:
                    # Aggiungi permessi per questo ruolo R5
                    await existing.set_permissions(
                        r5_role,
                        read_messages=True,
                        send_messages=True
                    )
                    print(f"Updated R5 council permissions for {r5_role.name}")
            
            return existing
        
        # Crea categoria se non esiste
        category_name = "State Leadership"
        category = discord.utils.get(guild.categories, name=category_name)
        if not category:
            category = await guild.create_category(category_name)
        
        # Crea permessi - solo R5 di qualsiasi alleanza
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_messages=True)
        }
        
        # Aggiungi tutti i ruoli R5
        for role in guild.roles:
            if role.name.endswith(" - R5"):
                overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        
        # Crea canale
        channel = await guild.create_text_channel(
            name=channel_name,
            category=category,
            overwrites=overwrites,
            topic="Channel for all R5 leaders to coordinate state-wide strategies"
        )
        
        # Messaggio di benvenuto - SEMPRE IN INGLESE
        embed = discord.Embed(
            title="👑 State R5 Council",
            description="Welcome to the State R5 Council! This channel is for all R5 leaders to coordinate.",
            color=discord.Color.gold()
        )
        await channel.send(embed=embed)
        
        return channel
    
    async def update_r5_council_permissions(self, guild: discord.Guild):
        """Aggiorna i permessi del canale R5 Council quando cambia un R5"""
        channel_name = "r5-council"  # SEMPRE IN INGLESE
        channel = discord.utils.get(guild.text_channels, name=channel_name)
        
        if not channel:
            return
        
        # Ricrea i permessi
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_messages=True)
        }
        
        # Aggiungi tutti i ruoli R5 attuali
        for role in guild.roles:
            if role.name.endswith(" - R5"):
                overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        
        # Aggiorna permessi del canale
        await channel.edit(overwrites=overwrites)