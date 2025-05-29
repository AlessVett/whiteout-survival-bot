import discord
from discord.ext import commands
from datetime import datetime

from src.config import Config
from locales import t
from src.utils.utils import get_or_create_role
from src.database import get_database

class AllianceChangeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = get_database()
    
    def get_user_lang(self, user_data: dict) -> str:
        """Ottiene la lingua dell'utente dal database o usa default"""
        return user_data.get('language', 'en') if user_data else 'en'
    
    async def handle_alliance_change_type(self, interaction: discord.Interaction, new_type: str):
        """Gestisce il cambio tipo alleanza (con alleanza, senza, altro stato)"""
        await interaction.response.defer()
        member = interaction.user
        guild = interaction.guild
        
        # Ottieni dati utente
        user_data = await self.db.get_user(member.id)
        if not user_data:
            return
        
        lang = self.get_user_lang(user_data)
        old_alliance = user_data.get('alliance')
        old_type = user_data.get('alliance_type')
        
        # Rimuovi vecchi ruoli alleanza
        if old_alliance:
            # Rimuovi ruolo alleanza
            old_alliance_role = discord.utils.get(guild.roles, name=old_alliance)
            if old_alliance_role and old_alliance_role in member.roles:
                await member.remove_roles(old_alliance_role)
            
            # Rimuovi ruolo R1-R5
            if user_data.get('alliance_role'):
                old_rank_role = discord.utils.get(guild.roles, name=f"{old_alliance} - {user_data['alliance_role']}")
                if old_rank_role and old_rank_role in member.roles:
                    await member.remove_roles(old_rank_role)
        
        # Rimuovi vecchi ruoli tipo
        if old_type == 'no_alliance':
            old_role = discord.utils.get(guild.roles, name="No Alliance")
            if old_role and old_role in member.roles:
                await member.remove_roles(old_role)
        elif old_type == 'other_state':
            old_role = discord.utils.get(guild.roles, name="Other State")
            if old_role and old_role in member.roles:
                await member.remove_roles(old_role)
        
        # Aggiorna database
        await self.db.update_user_alliance(member.id, alliance_type=new_type)
        
        if new_type == "alliance":
            # Mostra modal per nome alleanza
            from src.views.alliance_views import AllianceChangeNameView
            embed = discord.Embed(
                description=t("alliance.enter_name", lang),
                color=Config.EMBED_COLOR
            )
            view = AllianceChangeNameView(lang, self)
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            
        elif new_type == "no_alliance":
            # Completa cambio senza alleanza
            await self.complete_alliance_change(interaction, new_type)
            
        elif new_type == "other_state":
            # Completa cambio come altro stato
            await self.complete_alliance_change(interaction, new_type)
    
    async def handle_alliance_change_name(self, interaction: discord.Interaction, alliance_name: str):
        """Gestisce l'inserimento del nuovo nome alleanza"""
        member = interaction.user
        user_data = await self.db.get_user(member.id)
        lang = self.get_user_lang(user_data)
        
        # Aggiorna alleanza nel database
        await self.db.update_user_alliance(member.id, alliance=alliance_name)
        
        # Mostra selezione ruolo
        from src.views.alliance_views import AllianceChangeRoleView
        embed = discord.Embed(
            title=alliance_name,
            description=t("alliance.choose_role", lang),
            color=Config.EMBED_COLOR
        )
        view = AllianceChangeRoleView(lang, self)
        await interaction.followup.send(embed=embed, view=view)
    
    async def handle_alliance_change_role(self, interaction: discord.Interaction, role: str):
        """Gestisce la selezione del nuovo ruolo nell'alleanza"""
        try:
            await interaction.response.defer()
            member = interaction.user
            
            print(f"Alliance change: User {member.name} selected role {role}")
            
            # Aggiorna ruolo nel database
            await self.db.update_user_alliance(member.id, alliance_role=role)
            
            # Completa cambio con alleanza
            await self.complete_alliance_change(interaction, "alliance", role)
        except Exception as e:
            print(f"ERROR in handle_alliance_change_role: {e}")
            import traceback
            traceback.print_exc()
            
            # Try to send error message
            try:
                await interaction.followup.send(
                    f"❌ An error occurred while changing your alliance role: {str(e)}",
                    ephemeral=True
                )
            except:
                pass
    
    async def complete_alliance_change(self, interaction: discord.Interaction, alliance_type: str, alliance_role: str = None):
        """Completa il cambio alleanza dell'utente"""
        try:
            member = interaction.user
            guild = interaction.guild
            
            # Recupera dati utente aggiornati
            user_data = await self.db.get_user(member.id)
            if not user_data:
                await interaction.followup.send("❌ User data not found", ephemeral=True)
                return
            
            lang = self.get_user_lang(user_data)
            game_nickname = user_data.get('game_nickname', member.name)
            prefix = ""
            
            if alliance_type == "alliance" and user_data.get('alliance'):
                # Assegna nuovo ruolo alleanza
                alliance = user_data['alliance']
                alliance_role_obj = await get_or_create_role(guild, alliance)
                await member.add_roles(alliance_role_obj)
                
                # Assegna ruolo R1-R5
                if alliance_role:
                    role_name = f"{alliance} - {alliance_role}"
                    role_obj = await get_or_create_role(guild, role_name)
                    await member.add_roles(role_obj)
                
                # Controlla se l'alleanza esiste e ha tutti i canali
                alliance_data = await self.db.get_alliance(alliance)
                
                # Se è R5, crea o verifica tutti i canali alleanza
                if alliance_role == "R5":
                    try:
                        print(f"Creating alliance channels for R5 {member.name} in alliance {alliance}")
                        from src.services.alliance_channels import AllianceChannels
                        alliance_channels = AllianceChannels()
                        
                        # Crea tutti i canali standard dell'alleanza
                        created_channels = await alliance_channels.create_all_alliance_channels(
                            guild,
                            alliance,
                            alliance_role_obj,
                            lang
                        )
                        print(f"Created channels: {list(created_channels.keys())}")
                        
                        # Se l'alleanza non esisteva, creala nel database
                        if not alliance_data:
                            general_channel = created_channels.get("general")
                            channel_id = general_channel.id if general_channel else None
                            await self.db.create_alliance(alliance, guild.id, channel_id, member.id, lang)
                            print(f"Created new alliance {alliance} in database")
                        else:
                            # Se l'alleanza esisteva ma mancavano canali, aggiornala
                            general_channel = created_channels.get("general")
                            if general_channel and not alliance_data.get('channel_id'):
                                await self.db.alliances.update_one(
                                    {"name": alliance},
                                    {
                                        "$set": {
                                            "channel_id": general_channel.id,
                                            "r5_discord_id": member.id,
                                            "updated_at": datetime.utcnow()
                                        }
                                    }
                                )
                                print(f"Updated existing alliance {alliance} with channels")
                        
                        # Crea anche il canale R5 Council se non esiste
                        await alliance_channels.ensure_state_r5_channel(guild, member, lang)
                        print(f"Ensured R5 Council channel exists")
                    except Exception as e:
                        print(f"ERROR creating alliance channels: {e}")
                        import traceback
                        traceback.print_exc()
                        # Continue anyway to complete the process
                
                prefix = f"[{alliance}]"
                
            elif alliance_type == "no_alliance":
                role = await get_or_create_role(guild, "No Alliance")
                await member.add_roles(role)
                
            elif alliance_type == "other_state":
                role = await get_or_create_role(guild, "Other State")
                await member.add_roles(role)
                prefix = "[OS]"
            
            # Rinomina utente
            try:
                nick = f"{prefix} {game_nickname}" if prefix else game_nickname
                await member.edit(nick=nick)
            except:
                pass
            
            # Messaggio di conferma
            embed = discord.Embed(
                title="✅ Alliance Changed",
                color=discord.Color.green()
            )
            
            if alliance_type == "alliance":
                embed.description = f"You have joined the alliance **{user_data['alliance']}** as **{alliance_role}**"
            elif alliance_type == "no_alliance":
                embed.description = "You are now without an alliance"
            elif alliance_type == "other_state":
                embed.description = "You are now marked as from another state"
            
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            print(f"ERROR in complete_alliance_change: {e}")
            import traceback
            traceback.print_exc()
            
            # Try to send error message
            try:
                await interaction.followup.send(
                    f"❌ An error occurred while completing alliance change: {str(e)}",
                    ephemeral=True
                )
            except:
                pass

async def setup(bot):
    await bot.add_cog(AllianceChangeCog(bot))