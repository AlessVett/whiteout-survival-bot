import discord
from discord.ext import commands
from typing import Dict
import asyncio
from datetime import datetime

from src.config import Config
from locales import t
from src.utils.utils import verify_game_id, get_or_create_role, setup_member_channel
from src.views.views import LanguageSelectView, VerificationView, AllianceTypeView, AllianceView, AllianceRoleView
from src.database import get_database
from src.services.alliance_channels import AllianceChannels

class VerificationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = get_database()
    
    def get_user_lang(self, user_data: dict) -> str:
        """Ottiene la lingua dell'utente dal database o usa default"""
        return user_data.get('language', 'en') if user_data else 'en'
    
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Gestisce l'ingresso di un nuovo membro"""
        if member.bot:
            return
        
        guild = member.guild
        
        # Controlla se l'utente esiste già nel database
        user_data = await self.db.get_user(member.id)
        lang = self.get_user_lang(user_data)
        
        if user_data and user_data.get('verified'):
            # Utente già verificato, ripristina ruoli e canale personale
            verified_role = await get_or_create_role(guild, t("roles.verified", lang))
            await member.add_roles(verified_role)
            
            # Gestisci in base al tipo di alleanza
            alliance_type = user_data.get('alliance_type', 'no_alliance')
            
            if alliance_type == 'alliance' and user_data.get('alliance'):
                alliance_role = await get_or_create_role(guild, user_data['alliance'])
                await member.add_roles(alliance_role)
                
                # Aggiungi ruolo R1-R5 se presente
                if user_data.get('alliance_role'):
                    role_name = f"{user_data['alliance']} - {user_data['alliance_role']}"
                    role = await get_or_create_role(guild, role_name)
                    await member.add_roles(role)
                    
            elif alliance_type == 'no_alliance':
                role = await get_or_create_role(guild, t("roles.no_alliance", lang))
                await member.add_roles(role)
                
            elif alliance_type == 'other_state':
                role = await get_or_create_role(guild, t("roles.other_state", lang))
                await member.add_roles(role)
            
            # Rinomina con il nickname del gioco
            if user_data.get('game_nickname'):
                prefix = ""
                if alliance_type == 'alliance' and user_data.get('alliance'):
                    prefix = f"[{user_data['alliance']}]"
                elif alliance_type == 'other_state':
                    prefix = "[OS]"
                    
                try:
                    nick = f"{prefix} {user_data['game_nickname']}" if prefix else user_data['game_nickname']
                    await member.edit(nick=nick)
                except:
                    pass
            return
        
        # Nuovo utente o non verificato
        if not user_data:
            user_data = await self.db.create_user(member.id, member.name)
        
        # Assegna ruolo non verificato (usa inglese per i ruoli di sistema)
        unverified_role = await get_or_create_role(guild, "Unverified")
        await member.add_roles(unverified_role)
        
        # Crea canale di verifica
        channel_name = f"verify-{member.name}"
        verification_channel = await setup_member_channel(
            guild, 
            member, 
            "Welcome",
            channel_name
        )
        
        # Aggiorna canale di verifica nel database
        await self.db.update_user_channels(member.id, verification_channel_id=verification_channel.id)
        
        # Invia messaggio per selezione lingua
        embed = discord.Embed(
            title="🌍 Language Selection / Selezione Lingua",
            description="Please select your preferred language:\nSeleziona la tua lingua preferita:",
            color=Config.EMBED_COLOR
        )
        embed.set_footer(text=f"User: {member.name}")
        
        view = LanguageSelectView(self)
        await verification_channel.send(embed=embed, view=view)
    
    async def handle_language_selection(self, interaction: discord.Interaction, lang_code: str):
        """Gestisce la selezione della lingua"""
        await interaction.response.defer()
        member = interaction.user
        
        # Aggiorna lingua nel database e step di verifica
        await self.db.update_user_language(member.id, lang_code)
        await self.db.update_user_verification_step(member.id, 'id_verification')
        
        # Mostra messaggio di conferma nella lingua selezionata
        embed = discord.Embed(
            description=t("language.selected", lang_code),
            color=discord.Color.green()
        )
        await interaction.followup.send(embed=embed)
        
        # Dopo 2 secondi, mostra il messaggio di benvenuto
        await asyncio.sleep(2)
        
        embed = discord.Embed(
            title=t("welcome.title", lang_code),
            description=t("welcome.description", lang_code),
            color=Config.EMBED_COLOR
        )
        
        # Aggiungi informazioni su dove trovare l'ID
        embed.add_field(
            name=t("verification.id_help", lang_code),
            value=t("verification.id_location", lang_code),
            inline=False
        )
        
        # Aggiungi immagine tutorial se configurata
        if Config.PLAYER_ID_TUTORIAL_IMAGE:
            embed.set_image(url=Config.PLAYER_ID_TUTORIAL_IMAGE)
        
        embed.set_footer(text=f"User: {member.name}")
        
        view = VerificationView(lang_code, self)
        await interaction.followup.send(embed=embed, view=view)
    
    async def handle_id_verification(self, interaction: discord.Interaction, game_id: str):
        """Gestisce la verifica dell'ID di gioco"""
        member = interaction.user
        
        # Verifica che l'utente esista nel database
        user_data = await self.db.get_user(member.id)
        if not user_data:
            await interaction.followup.send(t("errors.generic", "en"), ephemeral=True)
            return
        
        lang = self.get_user_lang(user_data)
        
        # Mostra messaggio di verifica in corso
        embed = discord.Embed(
            description=t("verification.in_progress", lang),
            color=discord.Color.yellow()
        )
        await interaction.followup.send(embed=embed)
        
        # Verifica ID
        is_valid, game_data = await verify_game_id(game_id)
        
        if is_valid and game_data:
            # Aggiorna database con i dati del gioco
            await self.db.update_user_verification(member.id, game_id, game_data)
            await self.db.update_user_verification_step(member.id, 'alliance_type_selection')
            
            # ID verificato, chiedi tipo di alleanza
            embed = discord.Embed(
                title=t("verification.id_verified", lang),
                description=t("alliance.choose_type", lang),
                color=discord.Color.green()
            )
            embed.add_field(name="Game ID", value=game_id, inline=True)
            embed.add_field(name="Nickname", value=game_data.get('nickname', 'N/A'), inline=True)
            embed.add_field(name="Level", value=f"Lv. {game_data.get('stove_lv', 'N/A')}", inline=True)
            
            view = AllianceTypeView(lang, self)
            await interaction.followup.send(embed=embed, view=view)
        else:
            # ID non valido
            embed = discord.Embed(
                description=t("verification.invalid_id", lang),
                color=discord.Color.red()
            )
            view = VerificationView(lang, self)
            await interaction.followup.send(embed=embed, view=view)
    
    async def handle_alliance_type_selection(self, interaction: discord.Interaction, alliance_type: str):
        """Gestisce la selezione del tipo di alleanza"""
        await interaction.response.defer()
        member = interaction.user
        
        # Ottieni lingua utente
        user_data = await self.db.get_user(member.id)
        lang = self.get_user_lang(user_data)
        
        # Aggiorna il tipo di alleanza nel database
        await self.db.update_user_alliance(member.id, alliance_type=alliance_type)
        
        if alliance_type == "alliance":
            await self.db.update_user_verification_step(member.id, 'alliance_name')
        
        if alliance_type == "alliance":
            # Chiedi nome alleanza
            embed = discord.Embed(
                description=t("alliance.enter_name", lang),
                color=Config.EMBED_COLOR
            )
            view = AllianceView(lang, self)
            await interaction.followup.send(embed=embed, view=view)
            
        elif alliance_type == "no_alliance":
            # Completa setup senza alleanza
            await self.complete_setup(interaction, alliance_type="no_alliance")
            
        elif alliance_type == "other_state":
            # Completa setup come altro stato
            await self.complete_setup(interaction, alliance_type="other_state")
    
    async def handle_alliance_submission(self, interaction: discord.Interaction, alliance_name: str):
        """Gestisce l'inserimento dell'alleanza"""
        member = interaction.user
        
        # Ottieni lingua utente
        user_data = await self.db.get_user(member.id)
        lang = self.get_user_lang(user_data)
        
        # Verifica se l'alleanza esiste già nel database
        alliance_data = await self.db.get_alliance(alliance_name)
        
        if alliance_data:
            print(f"Alleanza '{alliance_name}' già esistente nel database")
        else:
            # Crea un placeholder per l'alleanza
            await self.db.create_alliance_placeholder(alliance_name, interaction.guild.id, lang)
            print(f"Alleanza '{alliance_name}' creata come placeholder nel database (in attesa del primo R5)")
        
        # Aggiorna alleanza nel database utente
        await self.db.update_user_alliance(member.id, alliance=alliance_name)
        await self.db.update_user_verification_step(member.id, 'alliance_role')
        
        # Chiedi ruolo nell'alleanza
        embed = discord.Embed(
            title=alliance_name,
            description=t("alliance.choose_role", lang),
            color=Config.EMBED_COLOR
        )
        
        view = AllianceRoleView(lang, self)
        await interaction.followup.send(embed=embed, view=view)
    
    async def handle_alliance_role_selection(self, interaction: discord.Interaction, role: str):
        """Gestisce la selezione del ruolo nell'alleanza"""
        print(f"=== INIZIO handle_alliance_role_selection per {interaction.user.name} - Ruolo: {role} ===")
        await interaction.response.defer()
        member = interaction.user
        
        try:
            # Aggiorna ruolo alleanza nel database
            await self.db.update_user_alliance(member.id, alliance_role=role)
            await self.db.update_user_verification_step(member.id, 'completed')
            print(f"Database aggiornato per {member.name} - Ruolo: {role}")
            
            # Completa setup con alleanza
            await self.complete_setup(interaction, alliance_type="alliance", alliance_role=role)
            print(f"=== FINE handle_alliance_role_selection per {member.name} - SUCCESSO ===")
        except Exception as e:
            print(f"=== ERRORE in handle_alliance_role_selection per {member.name}: {e} ===")
            import traceback
            traceback.print_exc()
            await interaction.followup.send(t("errors.generic", "en"), ephemeral=True)
    
    async def complete_setup(self, interaction: discord.Interaction, alliance_type: str, alliance_role: str = None):
        """Completa il setup dell'utente"""
        member = interaction.user
        guild = interaction.guild
        
        print(f"=== INIZIO COMPLETE_SETUP per {member.name} ===")
        print(f"Alliance type: {alliance_type}, Role: {alliance_role}")
        
        # Recupera dati utente
        user_data = await self.db.get_user(member.id)
        if not user_data:
            await interaction.followup.send(t("errors.generic", "en"), ephemeral=True)
            return
        
        lang = self.get_user_lang(user_data)
        
        # Rimuovi ruolo non verificato e assegna verificato
        unverified_role = discord.utils.get(guild.roles, name="Unverified")
        verified_role = await get_or_create_role(guild, "Verified")
        
        if unverified_role:
            await member.remove_roles(unverified_role)
        await member.add_roles(verified_role)
        
        # Gestisci ruoli in base al tipo
        game_nickname = user_data.get('game_nickname', member.name)
        prefix = ""
        
        if alliance_type == "alliance" and user_data.get('alliance'):
            # Crea/assegna ruolo alleanza
            alliance = user_data['alliance']
            alliance_role_obj = await get_or_create_role(guild, alliance)
            await member.add_roles(alliance_role_obj)
            
            # Crea/assegna ruolo R1-R5
            if alliance_role:
                role_name = f"{alliance} - {alliance_role}"
                role_obj = await get_or_create_role(guild, role_name)
                await member.add_roles(role_obj)
            
            # Controlla se esiste già l'alleanza nel database
            alliance_data = await self.db.get_alliance(alliance)
            alliance_channels_exist = False
            
            # Verifica se esistono già i canali dell'alleanza
            if alliance_data and alliance_data.get('channel_id'):
                existing_channel = guild.get_channel(alliance_data['channel_id'])
                if existing_channel:
                    alliance_channels_exist = True
                    print(f"Alleanza '{alliance}' già esistente con canali attivi")
            
            # Crea canali se non esistono (per nuovo R5 o alleanza senza canali)
            if not alliance_channels_exist and alliance_role == "R5":
                print(f"Creando canali per alleanza '{alliance}'...")
                alliance_channels = AllianceChannels()
                created_channels = await alliance_channels.create_all_alliance_channels(
                    guild,
                    alliance,
                    alliance_role_obj,
                    lang
                )
                
                # Salva/aggiorna l'alleanza nel database
                general_channel = created_channels.get("general")
                channel_id = general_channel.id if general_channel else None
                
                if not alliance_data:
                    # Crea nuova alleanza completa
                    await self.db.create_alliance(alliance, guild.id, channel_id, member.id, lang)
                    print(f"Alleanza '{alliance}' creata nel database con R5: {member.name} (lingua: {lang})")
                else:
                    # Aggiorna alleanza esistente (o converte placeholder) con canali e R5
                    update_operation = {
                        "$set": {
                            "channel_id": channel_id,
                            "r5_discord_id": member.id,
                            "updated_at": datetime.utcnow()
                        }
                    }
                    
                    # Rimuovi il flag placeholder se esiste
                    if alliance_data.get('is_placeholder'):
                        update_operation["$unset"] = {"is_placeholder": ""}
                        print(f"Convertendo placeholder '{alliance}' in alleanza completa")
                    
                    try:
                        result = await self.db.alliances.update_one(
                            {"name": alliance},
                            update_operation
                        )
                        print(f"Alleanza '{alliance}' aggiornata con R5: {member.name} e canali (modificati: {result.modified_count})")
                    except Exception as e:
                        print(f"ERRORE aggiornamento alleanza '{alliance}': {e}")
                        print(f"Update operation: {update_operation}")
                        # Continua comunque con il processo
                        pass
            
            elif alliance_channels_exist:
                print(f"Alleanza '{alliance}' già configurata con canali esistenti")
            
            elif alliance_role != "R5":
                print(f"Utente non R5 si unisce all'alleanza esistente '{alliance}'")
            
            # Assicurati che l'utente R5 sia nel canale R5 council se è R5
            if alliance_role == "R5":
                try:
                    alliance_channels = AllianceChannels()
                    await alliance_channels.ensure_state_r5_channel(guild, member, lang)
                    print(f"Canale R5 council aggiornato per {member.name}")
                except Exception as e:
                    print(f"ERRORE creazione canale R5 council: {e}")
                    # Continua comunque
            
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
        
        # Crea canale personale permanente
        print(f"Creando canale personale per {member.name}...")
        personal_channel_name = f"private-{game_nickname}"
        try:
            personal_channel = await setup_member_channel(
                guild,
                member,
                "Personal Channels",
                personal_channel_name
            )
            print(f"Canale personale creato: {personal_channel.name}")
            
            # Aggiorna canale personale nel database
            await self.db.update_user_channels(member.id, personal_channel_id=personal_channel.id)
            print(f"Database aggiornato con canale personale per {member.name}")
        except Exception as e:
            print(f"ERRORE creazione canale personale per {member.name}: {e}")
            import traceback
            traceback.print_exc()
            raise
        
        # Invia messaggio di benvenuto nel canale personale - SEMPRE IN INGLESE
        welcome_embed = discord.Embed(
            title="Welcome to your personal channel!",
            description="This is your private space where you can manage your settings and receive important notifications.",
            color=Config.EMBED_COLOR
        )
        welcome_embed.add_field(
            name="Use `/dashboard` to open your control panel where you can:",
            value="• Change your language\n• Change your alliance\n• Manage alliance members (if you're R4 or R5)",
            inline=False
        )
        await personal_channel.send(embed=welcome_embed)
        
        # Messaggio di completamento
        embed = discord.Embed(
            title=t("setup.complete", lang),
            color=discord.Color.green()
        )
        
        if alliance_type == "alliance":
            embed.description = t("setup.complete_description", lang)
            embed.add_field(name="Game ID", value=user_data['game_id'], inline=True)
            embed.add_field(name="Nickname", value=game_nickname, inline=True)
            embed.add_field(name="Alliance", value=user_data['alliance'], inline=True)
            if lang == "it":
                embed.add_field(name="Ruolo", value=alliance_role or "N/A", inline=True)
            else:
                embed.add_field(name="Role", value=alliance_role or "N/A", inline=True)
        elif alliance_type == "no_alliance":
            embed.description = t("setup.complete_no_alliance", lang)
            embed.add_field(name="Game ID", value=user_data['game_id'], inline=True)
            embed.add_field(name="Nickname", value=game_nickname, inline=True)
        elif alliance_type == "other_state":
            embed.description = t("setup.complete_other_state", lang)
            embed.add_field(name="Game ID", value=user_data['game_id'], inline=True)
            embed.add_field(name="Nickname", value=game_nickname, inline=True)
        
        await interaction.followup.send(embed=embed)
        
        print(f"=== FINE COMPLETE_SETUP per {member.name} - SUCCESSO ===")
        
        # Dopo 10 secondi, elimina il canale di verifica
        verification_channel_id = user_data.get('verification_channel_id')
        if verification_channel_id:
            verification_channel = guild.get_channel(verification_channel_id)
            if verification_channel:
                await asyncio.sleep(10)
                try:
                    await verification_channel.delete()
                    # Rimuovi riferimento dal database
                    await self.db.update_user_channels(member.id, verification_channel_id=None)
                except:
                    pass

async def setup(bot):
    await bot.add_cog(VerificationCog(bot))