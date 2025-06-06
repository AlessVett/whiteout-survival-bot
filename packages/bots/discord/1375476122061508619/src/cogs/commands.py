import discord
from discord.ext import commands
from discord import app_commands
import json
import io
from datetime import datetime

from src.config import Config
from locales import t
from src.cogs.base import BaseCog
from src.views.views import LanguageSelectView, VerificationView, AllianceView, AllianceRoleView
from src.views.verification_views import AllianceSelectionView
from src.views.dashboard_views import DashboardView, AllianceManagementView
from src.views.alliance_views import AllianceChangeTypeView
from src.views.privacy_views import PrivacyView

class CommandsCog(BaseCog):
    """Main commands cog with improved error handling and base functionality."""
    
    def __init__(self, bot):
        super().__init__(bot)
    
    @app_commands.command(name="start", description="Start or resume the verification process")
    async def start_command(self, interaction: discord.Interaction):
        """Start or resume the verification process."""
        try:
            member = interaction.user
            
            # Get or create user data
            user_data = await self.ensure_user_exists(member.id, member.name)
            lang = self.get_user_lang(user_data)
            
            # Check if already verified
            if user_data.get('verified'):
                await self.send_success_message(
                    interaction,
                    "commands.start.already_verified",
                    lang=lang,
                    ephemeral=True
                )
                return
            
            # Check if we're in the right channel
            if user_data.get('verification_channel_id'):
                if interaction.channel.id != user_data['verification_channel_id']:
                    await self.send_error_message(
                        interaction,
                        "commands.start.wrong_channel",
                        lang=lang,
                        ephemeral=True
                )
                return
            
            # Show resuming message
            await self.send_success_message(
                interaction,
                "commands.start.resuming",
                lang=lang,
                ephemeral=True
            )
            
            # Resume from the appropriate step
            verification_step = user_data.get('verification_step', 'language_selection')
            
            # Get verification cog to use its functions
            verification_cog = self.bot.get_cog('VerificationCog')
            if not verification_cog:
                await self.send_error_message(
                    interaction,
                    "errors.verification_cog_not_found",
                    lang=lang,
                    ephemeral=True
                )
                return
            
            if verification_step == 'language_selection':
                # Show language selection
                embed = discord.Embed(
                    title="🌍 Language Selection / Selezione Lingua",
                    description="Please select your preferred language:\nSeleziona la tua lingua preferita:",
                    color=Config.EMBED_COLOR
                )
                view = LanguageSelectView(verification_cog)
                await interaction.followup.send(embed=embed, view=view)
                
            elif verification_step == 'id_verification':
                # Show ID verification
                embed = discord.Embed(
                    title=t("welcome.title", lang),
                    description=t("welcome.description", lang),
                    color=Config.EMBED_COLOR
                )
                
                # Add helpful information
                embed.add_field(
                    name=t("verification.id_help", lang),
                    value=t("verification.id_location", lang),
                    inline=False
                )
                
                # Add tutorial image if configured
                if Config.PLAYER_ID_TUTORIAL_IMAGE:
                    embed.set_image(url=Config.PLAYER_ID_TUTORIAL_IMAGE)
                
                view = VerificationView(lang, verification_cog)
                await interaction.followup.send(embed=embed, view=view)
                
            elif verification_step == 'alliance_type':
                # Show alliance type selection
                embed = discord.Embed(
                    title=t("verification.id_verified", lang),
                    description=t("alliance.choose_type", lang),
                    color=discord.Color.green()
                )
                
                if user_data.get('game_id'):
                    embed.add_field(name="Game ID", value=user_data['game_id'], inline=True)
                if user_data.get('game_nickname'):
                    embed.add_field(name="Nickname", value=user_data['game_nickname'], inline=True)
                if user_data.get('stove_lv'):
                    embed.add_field(name="Level", value=f"Lv. {user_data['stove_lv']}", inline=True)
                
                view = AllianceSelectionView(
                    callback=verification_cog.handle_alliance_type_selection,
                    user_id=interaction.user.id,
                    lang=lang
                )
                await interaction.followup.send(embed=embed, view=view)
                
            elif verification_step == 'alliance_selection':
                # Show alliance name input
                embed = discord.Embed(
                    description=t("alliance.enter_name", lang),
                    color=Config.EMBED_COLOR
                )
                view = AllianceView(lang, verification_cog)
                await interaction.followup.send(embed=embed, view=view)
                
            elif verification_step == 'alliance_role':
                # Show alliance role selection
                alliance_name = user_data.get('alliance', 'Alliance')
                embed = discord.Embed(
                    title=alliance_name,
                    description=t("alliance.choose_role", lang),
                    color=Config.EMBED_COLOR
                )
                view = AllianceRoleView(lang, verification_cog)
                await interaction.followup.send(embed=embed, view=view)
                
            elif verification_step == 'complete':
                # User is already verified
                await self.send_success_message(
                    interaction,
                    "commands.start.already_verified",
                    lang=lang,
                    ephemeral=True
                )
                
            else:
                # Unknown step, restart from language selection
                await self.db.update_user(interaction.user.id, {
                    'verification_step': 'language_selection'
                })
                embed = discord.Embed(
                    title="🌍 Language Selection / Selezione Lingua",
                    description="Please select your preferred language:\nSeleziona la tua lingua preferita:",
                    color=Config.EMBED_COLOR
                )
                view = LanguageSelectView(verification_cog)
                await interaction.followup.send(embed=embed, view=view)
            
        except Exception as e:
            await self.handle_cog_error(interaction, e)
    
    @app_commands.command(name="dashboard", description="Open your personal dashboard")
    async def dashboard_command(self, interaction: discord.Interaction):
        """Open user dashboard with management options."""
        try:
            # Get user data
            user_data = await self.ensure_user_exists(interaction.user.id, interaction.user.name)
            lang = self.get_user_lang(user_data)
            
            # Check if verified
            if not user_data.get('verified'):
                await self.send_error_message(
                    interaction,
                    "commands.dashboard.not_verified",
                    lang=lang,
                    ephemeral=True
                )
                return
            
            # Create enhanced dashboard embed
            embed = discord.Embed(
                title="🎛️ " + t("dashboard.title", lang),
                color=0x3498DB  # Professional blue
            )
            embed.set_author(
                name=f"Dashboard • {interaction.user.display_name}",
                icon_url=interaction.user.display_avatar.url
            )
            
            embed.description = (
                f"┌────────────────────────────────────┐\n"
                f"│  **Welcome to your Control Panel** │\n"
                f"└────────────────────────────────────┘\n\n"
                f"💫 {t('dashboard.description', lang)}"
            )
            
            # Create profile summary in code block
            profile_summary = "```yaml\n"
            profile_summary += f"Game ID: {user_data.get('game_id', 'N/A')}\n"
            profile_summary += f"Nickname: {user_data.get('game_nickname', 'N/A')}\n"
            profile_summary += f"Language: {user_data.get('language', 'en').upper()}\n"
            
            if user_data.get('alliance'):
                profile_summary += f"Alliance: {user_data['alliance']}\n"
                profile_summary += f"Role: {user_data.get('alliance_role', 'N/A')}\n"
            else:
                profile_summary += f"Status: Independent Player\n"
            
            if user_data.get('verified_at'):
                verified_date = user_data['verified_at'].strftime('%Y-%m-%d')
                profile_summary += f"Verified: {verified_date}\n"
            
            profile_summary += "```"
            
            embed.add_field(
                name="👤 Your Profile",
                value=profile_summary,
                inline=False
            )
            
            # Add quick actions guide
            embed.add_field(
                name="🚀 Quick Actions",
                value=(
                    "🌍 **Change Language** - Switch your interface language\n"
                    "⚔️ **Change Alliance** - Join/leave alliances\n"
                    "👥 **Manage Alliance** - Leadership tools (R4/R5 only)\n"
                    "🔒 **Privacy Settings** - Data management options"
                ),
                inline=False
            )
            
            embed.set_footer(
                text="💡 Use the buttons below to manage your account • All changes are instant",
                icon_url="https://cdn.discordapp.com/emojis/gear.gif"
            )
            embed.set_thumbnail(
                url="https://cdn.discordapp.com/attachments/dashboard_icon.png"
            )
            
            view = DashboardView(lang, user_data, self)
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            await self.handle_cog_error(interaction, e)
    
    @app_commands.command(name="privacy", description="Manage your personal data and privacy settings")
    async def privacy_command(self, interaction: discord.Interaction):
        """Comando per gestire privacy e dati personali"""
        member = interaction.user
        
        # Recupera dati utente per la lingua
        user_data = await self.db.get_user(member.id)
        lang = self.get_user_lang(user_data)
        
        # Create enhanced privacy embed
        embed = discord.Embed(
            title="🔒 " + t("privacy.title", lang),
            color=0xE74C3C  # Red for privacy/security
        )
        embed.set_author(
            name="Privacy & Data Management",
            icon_url="https://cdn.discordapp.com/emojis/shield.gif"
        )
        
        embed.description = (
            f"┌──────────────────────────────────────┐\n"
            f"│  **Your Data, Your Control**        │\n"
            f"└──────────────────────────────────────┘\n\n"
            f"🛡️ {t('privacy.description', lang)}\n\n"
            f"**🔐 Data Security Promise:**\n"
            f"└─ We protect your information with industry-standard security"
        )
        
        # Enhanced rights information
        embed.add_field(
            name="📋 " + t("privacy.your_rights", lang),
            value=(
                f"🔍 **View Data** - See all information we store about you\n"
                f"🗑️ **Delete Data** - Permanently remove your account and data\n"
                f"📝 **Modify Data** - Update your information anytime\n"
                f"🚫 **Data Portability** - Request your data in a readable format"
            ),
            inline=False
        )
        
        # Enhanced retention info
        embed.add_field(
            name="⏱️ " + t("privacy.data_retention", lang),
            value=(
                f"💾 **Active Account**: Data stored while you're an active member\n"
                f"🗂️ **Inactive Account**: Auto-deleted after 180 days of inactivity\n"
                f"🔥 **Manual Deletion**: Instant when you request it\n"
                f"🔒 **Security**: All data encrypted and securely stored"
            ),
            inline=False
        )
        
        embed.set_footer(
            text="💡 Use the buttons below to manage your data • GDPR Compliant",
            icon_url="https://cdn.discordapp.com/emojis/info.gif"
        )
        
        view = PrivacyView(lang, self)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    async def handle_view_data(self, interaction: discord.Interaction, lang: str):
        """Mostra tutti i dati dell'utente"""
        member = interaction.user
        user_data = await self.db.get_user(member.id)
        
        if not user_data:
            await interaction.response.send_message(
                t("privacy.no_data", lang),
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title=t("privacy.data_overview", lang),
            color=discord.Color.blue()
        )
        
        # Dati di base
        embed.add_field(
            name=t("privacy.discord_id", lang),
            value=str(user_data.get('discord_id', 'N/A')),
            inline=True
        )
        embed.add_field(
            name=t("privacy.game_id", lang),
            value=str(user_data.get('game_id', 'N/A')),
            inline=True
        )
        embed.add_field(
            name=t("privacy.nickname", lang),
            value=user_data.get('game_nickname', 'N/A'),
            inline=True
        )
        embed.add_field(
            name=t("privacy.alliance", lang),
            value=user_data.get('alliance', 'None'),
            inline=True
        )
        embed.add_field(
            name=t("privacy.alliance_role", lang),
            value=user_data.get('alliance_role', 'N/A'),
            inline=True
        )
        embed.add_field(
            name=t("privacy.language", lang),
            value=user_data.get('language', 'en'),
            inline=True
        )
        embed.add_field(
            name=t("privacy.verified", lang),
            value="✅ Yes" if user_data.get('verified') else "❌ No",
            inline=True
        )
        
        # Date se disponibili
        if user_data.get('created_at'):
            embed.add_field(
                name=t("privacy.created_at", lang),
                value=user_data['created_at'].strftime('%Y-%m-%d %H:%M UTC'),
                inline=True
            )
        if user_data.get('last_activity'):
            embed.add_field(
                name=t("privacy.last_activity", lang),
                value=user_data['last_activity'].strftime('%Y-%m-%d %H:%M UTC'),
                inline=True
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    async def handle_export_data(self, interaction: discord.Interaction, lang: str):
        """Esporta tutti i dati dell'utente in formato JSON"""
        member = interaction.user
        user_data = await self.db.get_user(member.id)
        
        if not user_data:
            await interaction.response.send_message(
                t("privacy.no_data", lang),
                ephemeral=True
            )
            return
        
        try:
            # Defer the response for file processing
            await interaction.response.defer(ephemeral=True)
            self.logger.info(f"Starting data export for user {member.id}")
            
            # Create export data
            export_data = {
                "export_info": {
                    "exported_by": f"{member.name}#{member.discriminator}",
                    "export_date": datetime.utcnow().isoformat(),
                    "format_version": "1.0"
                },
                "user_data": {}
            }
            
            # Clean and prepare user data for export
            for key, value in user_data.items():
                if key == '_id':
                    continue  # Skip MongoDB ObjectId
                if isinstance(value, datetime):
                    export_data["user_data"][key] = value.isoformat()
                else:
                    export_data["user_data"][key] = value
            
            # Create JSON file
            json_data = json.dumps(export_data, indent=2, ensure_ascii=False)
            
            # Create a Discord file
            filename = f"data_export_{member.id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
            
            # Convert string to bytes for Discord file
            json_bytes = json_data.encode('utf-8')
            file = discord.File(
                io.BytesIO(json_bytes),
                filename=filename
            )
            
            # Success embed
            embed = discord.Embed(
                title="📥 Data Export Complete",
                description="Your personal data export has been generated successfully!",
                color=0x27AE60  # Green for success
            )
            embed.set_author(
                name="📋 Personal Data Export",
                icon_url="https://cdn.discordapp.com/emojis/file_cabinet.gif"
            )
            
            embed.add_field(
                name="📄 File Information",
                value=f"• **Format**: JSON\n• **Size**: {len(json_data)} characters\n• **Generated**: <t:{int(datetime.utcnow().timestamp())}:R>",
                inline=False
            )
            
            embed.add_field(
                name="🔒 Privacy Notice",
                value="• This file contains all your personal data\n• Keep it secure and don't share publicly\n• Contains sensitive information like Discord ID",
                inline=False
            )
            
            embed.set_footer(
                text="💾 File generated on request • Delete after download if needed",
                icon_url="https://cdn.discordapp.com/emojis/lock.gif"
            )
            
            self.logger.info(f"Sending data export file to user {member.id}, size: {len(json_bytes)} bytes")
            
            await interaction.followup.send(
                embed=embed,
                file=file,
                ephemeral=True
            )
            
            self.logger.info(f"Data export sent successfully to user {member.id}")
            
        except Exception as e:
            self.logger.error(f"Error exporting data for user {member.id}: {e}")
            await interaction.followup.send(
                "❌ An error occurred while exporting your data. Please try again later.",
                ephemeral=True
            )
    
    async def handle_delete_data(self, interaction: discord.Interaction, lang: str):
        """Elimina tutti i dati dell'utente"""
        member = interaction.user
        guild = interaction.guild
        
        try:
            # Ottieni dati utente prima della cancellazione
            user_data = await self.db.get_user(member.id)
            
            if user_data:
                # Rimuovi ruoli Discord se è in un'alleanza
                if user_data.get('alliance'):
                    alliance_name = user_data['alliance']
                    
                    # Rimuovi ruolo alleanza principale
                    alliance_role = discord.utils.get(guild.roles, name=alliance_name)
                    if alliance_role and alliance_role in member.roles:
                        await member.remove_roles(alliance_role)
                    
                    # Rimuovi ruoli R1-R5
                    for role_name in ["R1", "R2", "R3", "R4", "R5"]:
                        role = discord.utils.get(guild.roles, name=f"{alliance_name} - {role_name}")
                        if role and role in member.roles:
                            await member.remove_roles(role)
                
                # Rimuovi ruoli di verifica
                verified_role = discord.utils.get(guild.roles, name="Verified")
                if verified_role and verified_role in member.roles:
                    await member.remove_roles(verified_role)
                
                no_alliance_role = discord.utils.get(guild.roles, name="No Alliance")
                other_state_role = discord.utils.get(guild.roles, name="Other State")
                
                if no_alliance_role and no_alliance_role in member.roles:
                    await member.remove_roles(no_alliance_role)
                if other_state_role and other_state_role in member.roles:
                    await member.remove_roles(other_state_role)
            
            # Elimina eventi creati dall'utente
            await self.db.events.delete_many({"creator_id": member.id})
            
            # Elimina dati utente dal database
            await self.db.users.delete_one({"discord_id": member.id})
            
            # Elimina canali personali se esistono
            if user_data and user_data.get('personal_channel_id'):
                personal_channel = guild.get_channel(user_data['personal_channel_id'])
                if personal_channel:
                    await personal_channel.delete()
            
            if user_data and user_data.get('verification_channel_id'):
                verification_channel = guild.get_channel(user_data['verification_channel_id'])
                if verification_channel:
                    await verification_channel.delete()
            
            await interaction.response.send_message(
                t("privacy.deletion_complete", lang),
                ephemeral=True
            )
            
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Error during data deletion: {str(e)}",
                ephemeral=True
            )
    
    async def handle_language_change(self, interaction: discord.Interaction, new_lang: str):
        """Gestisce il cambio lingua dal dashboard"""
        member = interaction.user
        
        # Aggiorna lingua nel database
        await self.db.update_user_language(member.id, new_lang)
        
        # Conferma
        await interaction.response.send_message(
            t("language.selected", new_lang),
            ephemeral=True
        )
    
    async def handle_alliance_change(self, interaction: discord.Interaction):
        """Gestisce il cambio alleanza dal dashboard"""
        try:
            member = interaction.user
            user_data = await self.db.get_user(member.id)
            lang = self.get_user_lang(user_data)

            # Mostra le opzioni per il tipo di alleanza
            embed = discord.Embed(
                description=t("alliance.choose_type", lang),
                color=Config.EMBED_COLOR
            )

            # Usa il cog specifico per il cambio alleanza
            alliance_change_cog = self.bot.get_cog('AllianceChangeCog')
            if not alliance_change_cog:
                await interaction.response.send_message("Alliance change system not available.", ephemeral=True)
                return

            view = AllianceChangeTypeView(lang, alliance_change_cog)
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(
                f"❌ An error occurred while processing your request: {str(e)}",
                ephemeral=True
            )
    
    async def handle_alliance_management(self, interaction: discord.Interaction):
        """Gestisce la gestione dell'alleanza"""
        print("Handling alliance management command")
        try:
            member = interaction.user
            user_data = await self.db.get_user(member.id)
            lang = self.get_user_lang(user_data)

            if not user_data.get('alliance') or user_data.get('alliance_role') not in ['R4', 'R5']:
                await interaction.response.send_message(
                    t("commands.dashboard.no_permission", lang),
                    ephemeral=True
                )
                return

            # Salva temporaneamente l'ID dell'utente corrente
            self.current_interaction_user_id = member.id

            # Ottieni membri dell'alleanza
            alliance_members = await self.db.get_users_by_alliance(user_data['alliance'])

            # Crea embed con info alleanza
            embed = discord.Embed(
                title=t("alliance_management.title", lang, alliance=user_data['alliance']),
                color=Config.EMBED_COLOR
            )
            embed.add_field(name=t("alliance_management.members", lang), value=len(alliance_members), inline=True)

            # Crea view per gestione
            view = AllianceManagementView(
                user_data['alliance'],
                alliance_members,
                user_data['alliance_role'],
                lang,
                self
            )

            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        except Exception as e:
            print(f"Error handling alliance management command: {e}")
            await interaction.response.send_message(
                f"❌ An error occurred while processing your request: {str(e)}",
                ephemeral=True
            )
    
    async def handle_role_change(self, interaction: discord.Interaction, target_member_id: int, new_role: str):
        """Gestisce il cambio ruolo di un membro"""
        user_data = await self.db.get_user(interaction.user.id)
        lang = self.get_user_lang(user_data)
        
        # Aggiorna ruolo nel database
        await self.db.update_user_alliance(target_member_id, alliance_role=new_role)
        
        # Aggiorna ruoli Discord
        guild = interaction.guild
        target_member = guild.get_member(target_member_id)
        if target_member:
            # Rimuovi vecchi ruoli R1-R5
            alliance = user_data['alliance']
            for role_name in ["R1", "R2", "R3", "R4", "R5"]:
                old_role = discord.utils.get(guild.roles, name=f"{alliance} - {role_name}")
                if old_role and old_role in target_member.roles:
                    await target_member.remove_roles(old_role)
            
            # Aggiungi nuovo ruolo
            new_role_obj = discord.utils.get(guild.roles, name=f"{alliance} - {new_role}")
            if new_role_obj:
                await target_member.add_roles(new_role_obj)
        
        await interaction.response.send_message(
            t("alliance_management.role_changed", lang),
            ephemeral=True
        )
    
    async def handle_leadership_transfer(self, interaction: discord.Interaction, new_r5_id: int):
        """Gestisce il trasferimento della leadership"""
        user_data = await self.db.get_user(interaction.user.id)
        lang = self.get_user_lang(user_data)
        alliance = user_data['alliance']
        
        # Aggiorna database
        await self.db.update_user_alliance(interaction.user.id, alliance_role="R4")
        await self.db.update_user_alliance(new_r5_id, alliance_role="R5")
        await self.db.update_alliance_r5(alliance, new_r5_id)
        
        # Aggiorna ruoli Discord
        guild = interaction.guild
        
        # Downgrade vecchio R5 a R4
        old_r5_role = discord.utils.get(guild.roles, name=f"{alliance} - R5")
        new_r4_role = discord.utils.get(guild.roles, name=f"{alliance} - R4")
        if old_r5_role:
            await interaction.user.remove_roles(old_r5_role)
        if new_r4_role:
            await interaction.user.add_roles(new_r4_role)
        
        # Upgrade nuovo R5
        new_member = guild.get_member(new_r5_id)
        if new_member:
            # Rimuovi vecchio ruolo
            for role_name in ["R1", "R2", "R3", "R4"]:
                old_role = discord.utils.get(guild.roles, name=f"{alliance} - {role_name}")
                if old_role and old_role in new_member.roles:
                    await new_member.remove_roles(old_role)
            
            # Aggiungi R5
            if old_r5_role:
                await new_member.add_roles(old_r5_role)
        
        await interaction.response.send_message(
            t("alliance_management.leadership_transferred", lang),
            ephemeral=True
        )
    
    @app_commands.command(name="sync", description="[Owner] Sync slash commands")
    async def sync_commands(self, interaction: discord.Interaction):
        """Sincronizza i comandi slash"""
        if interaction.user.id != interaction.guild.owner_id:
            await interaction.response.send_message("❌ Solo il proprietario del server può usare questo comando.", ephemeral=True)
            return
        
        try:
            synced = await self.bot.tree.sync()
            await interaction.response.send_message(f"✅ Sincronizzati {len(synced)} comandi.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Errore nella sincronizzazione: {e}", ephemeral=True)

    @app_commands.command(name="debug_alliances", description="[Admin] Show all alliances in database")
    @app_commands.default_permissions(administrator=True)
    async def debug_alliances(self, interaction: discord.Interaction):
        """Comando per debug delle alleanze nel database"""
        # Ottieni tutte le alleanze
        cursor = self.db.alliances.find({})
        alliances = await cursor.to_list(length=None)
        
        if not alliances:
            await interaction.response.send_message("❌ Nessuna alleanza trovata nel database.", ephemeral=True)
            return
        
        # Crea embed con le alleanze
        embed = discord.Embed(
            title="🗃️ Alleanze nel Database",
            color=discord.Color.blue()
        )
        
        for alliance in alliances:
            is_placeholder = alliance.get('is_placeholder', False)
            
            if is_placeholder:
                r5_name = "Nessun R5 (placeholder)"
                status_emoji = "⏳"
            else:
                r5_member = interaction.guild.get_member(alliance['r5_discord_id']) if alliance.get('r5_discord_id') else None
                r5_name = r5_member.display_name if r5_member else f"ID: {alliance['r5_discord_id']}"
                status_emoji = "⚔️"
            
            # Conta membri dell'alleanza
            member_count = await self.db.users.count_documents({"alliance": alliance['name']})
            
            embed.add_field(
                name=f"{status_emoji} {alliance['name']}",
                value=f"👑 R5: {r5_name}\n👥 Membri: {member_count}\n🌍 Lingua: {alliance.get('language', 'en')}\n📅 Creata: {alliance['created_at'].strftime('%Y-%m-%d')}\n🏷️ Status: {'Placeholder' if is_placeholder else 'Completa'}",
                inline=True
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="test", description="Test command to verify bot is working")
    async def test_command(self, interaction: discord.Interaction):
        """Comando di test"""
        await interaction.response.send_message("✅ Bot is working correctly!", ephemeral=True)
    
    @app_commands.command(name="refresh_stats", description="[Admin] Force refresh server statistics")
    @app_commands.default_permissions(administrator=True)
    async def refresh_stats(self, interaction: discord.Interaction):
        """Forza l'aggiornamento delle statistiche del server"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Ottieni il cog delle statistiche
            stats_cog = self.bot.get_cog('ServerStats')
            if stats_cog:
                await stats_cog.update_stats(interaction.guild)
                await interaction.followup.send("✅ Statistiche aggiornate!", ephemeral=True)
            else:
                await interaction.followup.send("❌ Sistema statistiche non trovato!", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Errore aggiornamento statistiche: {e}", ephemeral=True)
    
    @app_commands.command(name="setup_stats", description="[Admin] Setup server statistics channels")
    @app_commands.default_permissions(administrator=True)
    async def setup_stats(self, interaction: discord.Interaction):
        """Setup the statistics channels"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Get stats cog
            stats_cog = self.bot.get_cog('ServerStats')
            if stats_cog:
                await stats_cog.setup_stats_channels(interaction.guild)
                await interaction.followup.send("✅ Statistics channels setup completed!", ephemeral=True)
            else:
                await interaction.followup.send("❌ Statistics system not found!", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Error setting up statistics: {e}", ephemeral=True)
    
    @app_commands.command(name="cleanup_stats", description="[Admin] Clean up duplicate statistics channels")
    @app_commands.default_permissions(administrator=True)
    async def cleanup_stats(self, interaction: discord.Interaction):
        """Pulisce i canali statistiche duplicati"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Ottieni il cog delle statistiche
            stats_cog = self.bot.get_cog('ServerStats')
            if stats_cog:
                # Trova la categoria stats
                category = discord.utils.get(interaction.guild.categories, name="📊 Server Statistics")
                if category:
                    await stats_cog._cleanup_duplicate_stats(category)
                    await interaction.followup.send("✅ Pulizia canali duplicati completata!", ephemeral=True)
                else:
                    await interaction.followup.send("❌ Categoria statistiche non trovata!", ephemeral=True)
            else:
                await interaction.followup.send("❌ Sistema statistiche non trovato!", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Errore pulizia canali: {e}", ephemeral=True)
    
    @app_commands.command(name="debug_reminders", description="[Admin] Debug reminder status for events")
    @app_commands.default_permissions(administrator=True)
    async def debug_reminders(self, interaction: discord.Interaction):
        """Debug reminder tracking status"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Get all active events
            cursor = self.db.events.find({"active": True})
            events = await cursor.to_list(length=None)
            
            if not events:
                await interaction.followup.send("❌ No active events found!", ephemeral=True)
                return
            
            embed = discord.Embed(
                title="🔔 Reminder Status Debug",
                color=discord.Color.blue()
            )
            
            from datetime import datetime
            now = datetime.utcnow()
            
            for event in events[:10]:  # Limit to 10 events
                reminders_sent = event.get('reminders_sent', {})
                reminder_hours = event.get('reminder_hours', [])
                
                status_lines = []
                for hours in sorted(reminder_hours, reverse=True):
                    if hours == 0.25:
                        key = "15m"
                    elif hours == 0.5:
                        key = "30m"
                    else:
                        key = f"{hours}h"
                    
                    sent = reminders_sent.get(key, False)
                    status = "✅ Sent" if sent else "⏳ Pending"
                    status_lines.append(f"{key}: {status}")
                
                embed.add_field(
                    name=f"📅 {event['name']}",
                    value=f"**Start**: {event['start_time'].strftime('%Y-%m-%d %H:%M')} UTC\n" +
                          f"**Reminders**: {', '.join(status_lines) if status_lines else 'None'}",
                    inline=False
                )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error debugging reminders: {e}", ephemeral=True)
    
    @app_commands.command(name="debug_cron", description="[Admin] Debug cron manager and events")
    @app_commands.default_permissions(administrator=True)
    async def debug_cron(self, interaction: discord.Interaction):
        """Debug del sistema cron"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Ottieni gli eventi attivi
            cursor = self.db.events.find({"active": True})
            events = await cursor.to_list(length=None)
            
            if not events:
                await interaction.followup.send("❌ Nessun evento attivo trovato!", ephemeral=True)
                return
            
            embed = discord.Embed(
                title="🐛 Debug Sistema Cron",
                color=discord.Color.orange()
            )
            
            from datetime import datetime, timedelta
            now = datetime.utcnow()
            
            for event in events:
                start_time = event['start_time']
                reminder_hours = event.get('reminder_hours', [])
                
                # Calcola i tempi dei reminder
                reminder_times = []
                for hours in reminder_hours:
                    reminder_time = start_time - timedelta(hours=hours)
                    status = "⏰ Futuro" if reminder_time > now else "✅ Passato"
                    reminder_times.append(f"{hours}h: {reminder_time.strftime('%Y-%m-%d %H:%M')} {status}")
                
                status_evento = "🚀 Iniziato" if start_time <= now else "⏳ Futuro"
                
                embed.add_field(
                    name=f"📅 {event['name']}",
                    value=f"**Inizio**: {start_time.strftime('%Y-%m-%d %H:%M')} UTC {status_evento}\n" +
                          f"**Canale**: {event.get('channel_id', 'N/A')}\n" +
                          f"**Reminder**: {', '.join(reminder_times) if reminder_times else 'Nessuno'}",
                    inline=False
                )
            
            embed.add_field(
                name="🕒 Ora Corrente",
                value=f"{now.strftime('%Y-%m-%d %H:%M')} UTC",
                inline=False
            )
            
            # Controlla se CronManager è attivo
            if hasattr(self.bot, 'cron_manager') and self.bot.cron_manager:
                cron_status = "✅ Attivo" if self.bot.cron_manager.running else "❌ Inattivo"
                embed.add_field(
                    name="🔄 CronManager",
                    value=f"Status: {cron_status}\nTask attivi: {len(self.bot.cron_manager.tasks)}",
                    inline=False
                )
            else:
                embed.add_field(
                    name="🔄 CronManager",
                    value="❌ Non trovato",
                    inline=False
                )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Errore debug cron: {e}", ephemeral=True)
    
    @app_commands.command(name="test_reminder", description="[Admin] Test reminder system with a short-timer event")
    @app_commands.default_permissions(administrator=True)
    async def test_reminder(self, interaction: discord.Interaction):
        """Create a test event with reminders in the next few minutes"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            from datetime import datetime, timedelta
            
            # Get user's alliance
            user_data = await self.db.get_user(interaction.user.id)
            if not user_data or not user_data.get('alliance'):
                await interaction.followup.send("❌ You must be in an alliance to test reminders!", ephemeral=True)
                return
            
            # Create a test event that starts in 20 minutes
            start_time = datetime.utcnow() + timedelta(minutes=20)
            
            event_data = {
                "name": "Test Reminder Event",
                "description": "This is a test event to verify reminder system",
                "type": "test",
                "alliance": user_data['alliance'],
                "creator_id": interaction.user.id,
                "start_time": start_time,
                "recurring": None,
                "reminder_hours": [0.25, 0.5],  # 15min and 30min before
                "active": True,
                "channel_id": interaction.channel.id,
                "reminders_sent": {}
            }
            
            # Insert test event
            result = await self.db.events.insert_one(event_data)
            event_data['_id'] = result.inserted_id
            
            # Schedule the event
            if hasattr(self.bot, 'cron_manager') and self.bot.cron_manager:
                await self.bot.cron_manager.schedule_event(event_data)
                
                now = datetime.utcnow()
                reminder_15min = start_time - timedelta(minutes=15)
                reminder_30min = start_time - timedelta(minutes=30)
                
                embed = discord.Embed(
                    title="✅ Test Event Created",
                    description=f"Event will start at {start_time.strftime('%H:%M:%S')} UTC (in ~20 minutes)",
                    color=discord.Color.green()
                )
                embed.add_field(
                    name="Expected Reminders",
                    value=f"• 15 minutes before: {reminder_15min.strftime('%H:%M:%S')} UTC (in ~5 minutes)\n" +
                          f"• 30 minutes before: Would be at {reminder_30min.strftime('%H:%M:%S')} UTC (already passed)",
                    inline=False
                )
                embed.add_field(
                    name="Channel",
                    value=f"Reminders will be sent to: {interaction.channel.mention}",
                    inline=False
                )
                
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                await interaction.followup.send("❌ CronManager not found!", ephemeral=True)
                
        except Exception as e:
            await interaction.followup.send(f"❌ Error creating test event: {e}", ephemeral=True)
    
    @app_commands.command(name="fix_alliance_channels", description="[Admin] Fix missing alliance channels")
    @app_commands.default_permissions(administrator=True)
    async def fix_alliance_channels(self, interaction: discord.Interaction):
        """Fix missing alliance channels for all alliances"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            from src.services.alliance_channels import AllianceChannels
            alliance_channels_helper = AllianceChannels()
            
            # Get all alliances
            cursor = self.db.alliances.find({})
            alliances = await cursor.to_list(length=None)
            
            if not alliances:
                await interaction.followup.send("❌ No alliances found!", ephemeral=True)
                return
            
            fixed_count = 0
            report = []
            
            for alliance_data in alliances:
                alliance_name = alliance_data['name']
                
                # Skip placeholder alliances
                if alliance_data.get('is_placeholder'):
                    report.append(f"⏭️ {alliance_name} - Skipped (placeholder)")
                    continue
                
                # Get alliance role
                alliance_role = discord.utils.get(interaction.guild.roles, name=alliance_name)
                if not alliance_role:
                    report.append(f"❌ {alliance_name} - No role found")
                    continue
                
                # Check existing channels
                existing_channels = []
                cursor = self.db.alliance_channels.find({"alliance": alliance_name})
                channels = await cursor.to_list(length=None)
                for ch in channels:
                    existing_channels.append(ch['channel_type'])
                
                # Expected channels
                expected_channels = ["general", "reminders", "gift-codes", "r4-r5-only", "university"]
                missing_channels = [ch for ch in expected_channels if ch not in existing_channels]
                
                if missing_channels:
                    # Create missing channels
                    created = await alliance_channels_helper.create_all_alliance_channels(
                        interaction.guild,
                        alliance_name,
                        alliance_role,
                        "en"
                    )
                    fixed_count += 1
                    report.append(f"✅ {alliance_name} - Fixed! Created: {', '.join(missing_channels)}")
                else:
                    report.append(f"✔️ {alliance_name} - All channels exist")
            
            # Create response
            embed = discord.Embed(
                title="🔧 Alliance Channels Fix Report",
                description=f"Fixed {fixed_count} alliances",
                color=discord.Color.green() if fixed_count > 0 else discord.Color.blue()
            )
            
            # Split report into chunks if too long
            report_text = "\n".join(report)
            if len(report_text) > 1024:
                for i in range(0, len(report), 10):
                    chunk = report[i:i+10]
                    embed.add_field(
                        name=f"Alliances {i+1}-{min(i+10, len(report))}",
                        value="\n".join(chunk),
                        inline=False
                    )
            else:
                embed.add_field(name="Report", value=report_text, inline=False)
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error fixing alliance channels: {e}", ephemeral=True)
    
    @app_commands.command(name="fix_private_channels", description="[Admin] Fix private channels and stats visibility")
    @app_commands.default_permissions(administrator=True)
    async def fix_private_channels(self, interaction: discord.Interaction):
        """Fix private channels permissions and recreate missing ones"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            guild = interaction.guild
            fixed_count = 0
            recreated_count = 0
            stats_fixed = False
            report = []
            
            # Fix stats channels visibility first
            stats_category = discord.utils.get(guild.categories, name="📊 Server Statistics")
            if not stats_category:
                # Create stats if they don't exist
                stats_cog = self.bot.get_cog('ServerStats')
                if stats_cog:
                    await stats_cog.setup_stats_channels(guild)
                    stats_category = discord.utils.get(guild.categories, name="📊 Server Statistics")
                    report.append("✅ Created Server Statistics category and channels")
                    stats_fixed = True
                else:
                    report.append("❌ Stats system not available")
            
            if stats_category:
                verified_role = discord.utils.get(guild.roles, name="Verified")
                if verified_role:
                    # Update permissions for stats category
                    overwrites = {
                        guild.default_role: discord.PermissionOverwrite(read_messages=False),
                        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True),
                        verified_role: discord.PermissionOverwrite(read_messages=True, send_messages=False)
                    }
                    await stats_category.edit(overwrites=overwrites)
                    
                    # Apply to all channels in the category
                    for channel in stats_category.channels:
                        await channel.edit(overwrites=overwrites)
                    
                    stats_fixed = True
                    report.append("✅ Fixed stats visibility for Verified users")
                else:
                    report.append("❌ Verified role not found")
            
            # Fix private channels
            personal_category = discord.utils.get(guild.categories, name="Personal Channels")
            if not personal_category:
                # Create category if missing
                personal_category = await guild.create_category("Personal Channels")
                report.append("✅ Created Personal Channels category")
            
            # Get all users with private channels
            cursor = self.db.users.find({"personal_channel_id": {"$exists": True, "$ne": None}})
            users = await cursor.to_list(length=None)
            
            for user_data in users:
                member = guild.get_member(user_data['discord_id'])
                if not member:
                    report.append(f"⏭️ User {user_data['discord_id']} not in server")
                    continue
                
                channel_id = user_data.get('personal_channel_id')
                channel = guild.get_channel(channel_id) if channel_id else None
                
                if not channel:
                    # Recreate missing channel
                    game_nickname = user_data.get('game_nickname', member.name)
                    channel_name = f"private-{game_nickname}"
                    
                    # Create channel with proper permissions
                    overwrites = {
                        guild.default_role: discord.PermissionOverwrite(read_messages=False),
                        member: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
                    }
                    
                    channel = await personal_category.create_text_channel(
                        name=channel_name,
                        overwrites=overwrites
                    )
                    
                    # Update database
                    await self.db.update_user_channels(member.id, personal_channel_id=channel.id)
                    
                    # Send welcome message
                    welcome_embed = discord.Embed(
                        title="Welcome to your personal channel!",
                        description="This is your private space where you can manage your settings and receive important notifications.",
                        color=discord.Color.blue()
                    )
                    welcome_embed.add_field(
                        name="Use `/dashboard` to open your control panel where you can:",
                        value="• Change your language\n• Change your alliance\n• Manage alliance members (if you're R4 or R5)",
                        inline=False
                    )
                    await channel.send(embed=welcome_embed)
                    
                    recreated_count += 1
                    report.append(f"✅ Recreated channel for {member.display_name}")
                else:
                    # Fix permissions if channel exists
                    overwrites = {
                        guild.default_role: discord.PermissionOverwrite(read_messages=False),
                        member: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
                    }
                    
                    await channel.edit(overwrites=overwrites)
                    
                    # Move to correct category if needed
                    if channel.category != personal_category:
                        await channel.edit(category=personal_category)
                    
                    fixed_count += 1
                    report.append(f"✔️ Fixed permissions for {member.display_name}")
            
            # Create response embed
            embed = discord.Embed(
                title="🔧 Private Channels Fix Report",
                description=f"**Summary:**\n• Stats Fixed: {'Yes' if stats_fixed else 'No'}\n• Channels Fixed: {fixed_count}\n• Channels Recreated: {recreated_count}",
                color=discord.Color.green()
            )
            
            # Add detailed report
            if len(report) > 10:
                # Truncate if too many
                report_text = "\n".join(report[:10]) + f"\n... and {len(report)-10} more"
            else:
                report_text = "\n".join(report)
            
            embed.add_field(
                name="Details",
                value=report_text if report_text else "No actions needed",
                inline=False
            )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error fixing private channels: {e}", ephemeral=True)
    
    @app_commands.command(name="fix_r5_council", description="[Admin] Fix R5 council channel permissions")
    @app_commands.default_permissions(administrator=True)
    async def fix_r5_council(self, interaction: discord.Interaction):
        """Fix R5 council channel permissions for all R5 roles"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            channel_name = "r5-council"
            channel = discord.utils.get(interaction.guild.text_channels, name=channel_name)
            
            if not channel:
                await interaction.followup.send("❌ R5 council channel not found!", ephemeral=True)
                return
            
            # Reset permissions
            overwrites = {
                interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_messages=True)
            }
            
            # Add all R5 roles
            r5_count = 0
            for role in interaction.guild.roles:
                if role.name.endswith(" - R5"):
                    overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
                    r5_count += 1
            
            # Apply all permissions at once
            await channel.edit(overwrites=overwrites)
            
            await interaction.followup.send(
                f"✅ Fixed R5 council permissions! Added access for {r5_count} R5 roles.",
                ephemeral=True
            )
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error fixing R5 council: {e}", ephemeral=True)
    
    @app_commands.command(name="fix_events", description="[Admin] Fix events without channels")
    @app_commands.default_permissions(administrator=True)
    async def fix_events(self, interaction: discord.Interaction):
        """Corregge eventi senza canale associato"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Trova eventi senza canale
            cursor = self.db.events.find({"active": True, "$or": [{"channel_id": None}, {"channel_id": {"$exists": False}}]})
            events_without_channel = await cursor.to_list(length=None)
            
            if not events_without_channel:
                await interaction.followup.send("✅ Tutti gli eventi attivi hanno un canale associato!", ephemeral=True)
                return
            
            fixed_count = 0
            
            for event in events_without_channel:
                alliance = event['alliance']
                
                # Cerca il canale generale dell'alleanza
                general_channel_data = await self.db.get_alliance_channel(alliance, "general")
                if general_channel_data:
                    # Aggiorna l'evento con il canale generale
                    await self.db.events.update_one(
                        {"_id": event['_id']},
                        {"$set": {"channel_id": general_channel_data['channel_id']}}
                    )
                    fixed_count += 1
                    print(f"Evento '{event['name']}' aggiornato con canale generale di {alliance}")
                else:
                    print(f"ATTENZIONE: Nessun canale trovato per alleanza '{alliance}' dell'evento '{event['name']}'")
            
            await interaction.followup.send(
                f"✅ Corretti {fixed_count}/{len(events_without_channel)} eventi!\n"
                f"Eventi senza canale: {len(events_without_channel) - fixed_count}",
                ephemeral=True
            )
            
        except Exception as e:
            await interaction.followup.send(f"❌ Errore correzione eventi: {e}", ephemeral=True)

    async def handle_alliance_dissolution(self, interaction: discord.Interaction, alliance_name: str):
        """Gestisce lo scioglimento dell'alleanza"""
        user_data = await self.db.get_user(interaction.user.id)
        lang = self.get_user_lang(user_data)
        guild = interaction.guild
        
        # Ottieni tutti i membri dell'alleanza
        members = await self.db.get_users_by_alliance(alliance_name)
        
        # Rimuovi ruoli alleanza da tutti i membri
        alliance_role = discord.utils.get(guild.roles, name=alliance_name)
        for member_data in members:
            member = guild.get_member(member_data['discord_id'])
            if member and alliance_role:
                await member.remove_roles(alliance_role)
            
            # Rimuovi ruoli R1-R5
            for role_name in ["R1", "R2", "R3", "R4", "R5"]:
                role = discord.utils.get(guild.roles, name=f"{alliance_name} - {role_name}")
                if role and member and role in member.roles:
                    await member.remove_roles(role)
            
            # Aggiorna database
            await self.db.update_user_alliance(
                member_data['discord_id'],
                alliance=None,
                alliance_role=None,
                alliance_type="no_alliance"
            )
        
        # Elimina canale alleanza
        alliance_data = await self.db.get_alliance(alliance_name)
        if alliance_data:
            channel = guild.get_channel(alliance_data['channel_id'])
            if channel:
                await channel.delete()
        
        # Elimina ruoli
        if alliance_role:
            await alliance_role.delete()
        for role_name in ["R1", "R2", "R3", "R4", "R5"]:
            role = discord.utils.get(guild.roles, name=f"{alliance_name} - {role_name}")
            if role:
                await role.delete()
        
        # Elimina alleanza dal database
        await self.db.delete_alliance(alliance_name)
        
        await interaction.response.send_message(
            t("alliance_management.alliance_dissolved", lang),
            ephemeral=True
        )
    
    @commands.Cog.listener()
    async def on_ready(self):
        """Sincronizza i comandi slash quando il bot è pronto"""
        try:
            synced = await self.bot.tree.sync()
            print(f"Sincronizzati {len(synced)} comandi slash")
        except Exception as e:
            print(f"Errore nella sincronizzazione dei comandi: {e}")

async def setup(bot):
    await bot.add_cog(CommandsCog(bot))