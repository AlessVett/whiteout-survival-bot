import discord
from discord.ext import commands
from discord import app_commands

from config import Config
from locales import t
from database import get_database
from views import LanguageSelectView, VerificationView, AllianceTypeView, AllianceView, AllianceRoleView
from dashboard_views import DashboardView, AllianceManagementView
from alliance_views import AllianceChangeTypeView

class CommandsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = get_database()
    
    def get_user_lang(self, user_data: dict) -> str:
        """Ottiene la lingua dell'utente dal database o usa default"""
        return user_data.get('language', 'en') if user_data else 'en'
    
    @app_commands.command(name="start", description="Start or resume the verification process")
    async def start_command(self, interaction: discord.Interaction):
        """Comando per avviare o riprendere il processo di verifica"""
        member = interaction.user
        guild = interaction.guild
        
        # Recupera dati utente
        user_data = await self.db.get_user(member.id)
        
        # Se non esiste, crealo
        if not user_data:
            user_data = await self.db.create_user(member.id, member.name)
        
        lang = self.get_user_lang(user_data)
        
        # Controlla se già verificato
        if user_data.get('verified'):
            await interaction.response.send_message(
                t("commands.start.already_verified", lang), 
                ephemeral=True
            )
            return
        
        # Controlla se siamo nel canale giusto
        if user_data.get('verification_channel_id'):
            if interaction.channel.id != user_data['verification_channel_id']:
                await interaction.response.send_message(
                    t("commands.start.no_channel", lang), 
                    ephemeral=True
                )
                return
        
        # Mostra messaggio di ripresa
        await interaction.response.send_message(
            t("commands.start.resuming", lang),
            ephemeral=True
        )
        
        # Riprendi dal punto giusto basandosi sullo step salvato
        verification_step = user_data.get('verification_step', 'language_selection')
        
        # Importa il cog di verifica per accedere alle sue funzioni
        verification_cog = self.bot.get_cog('VerificationCog')
        if not verification_cog:
            return
        
        if verification_step == 'language_selection':
            # Mostra selezione lingua
            embed = discord.Embed(
                title="🌍 Language Selection / Selezione Lingua",
                description="Please select your preferred language:\nSeleziona la tua lingua preferita:",
                color=Config.EMBED_COLOR
            )
            view = LanguageSelectView(verification_cog)
            await interaction.followup.send(embed=embed, view=view)
            
        elif verification_step == 'id_verification':
            # Mostra richiesta ID
            embed = discord.Embed(
                title=t("welcome.title", lang),
                description=t("welcome.description", lang),
                color=Config.EMBED_COLOR
            )
            
            # Aggiungi informazioni su dove trovare l'ID
            embed.add_field(
                name=t("verification.id_help", lang),
                value=t("verification.id_location", lang),
                inline=False
            )
            
            # Aggiungi immagine tutorial se configurata
            if Config.PLAYER_ID_TUTORIAL_IMAGE:
                embed.set_image(url=Config.PLAYER_ID_TUTORIAL_IMAGE)
            
            view = VerificationView(lang, verification_cog)
            await interaction.followup.send(embed=embed, view=view)
            
        elif verification_step == 'alliance_type_selection':
            # Mostra selezione tipo alleanza
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
            
            view = AllianceTypeView(lang, verification_cog)
            await interaction.followup.send(embed=embed, view=view)
            
        elif verification_step == 'alliance_name':
            # Mostra richiesta nome alleanza
            embed = discord.Embed(
                description=t("alliance.enter_name", lang),
                color=Config.EMBED_COLOR
            )
            view = AllianceView(lang, verification_cog)
            await interaction.followup.send(embed=embed, view=view)
            
        elif verification_step == 'alliance_role':
            # Mostra selezione ruolo
            alliance_name = user_data.get('alliance', 'Alliance')
            embed = discord.Embed(
                title=alliance_name,
                description=t("alliance.choose_role", lang),
                color=Config.EMBED_COLOR
            )
            view = AllianceRoleView(lang, verification_cog)
            await interaction.followup.send(embed=embed, view=view)
    
    @app_commands.command(name="dashboard", description="Open your personal control panel")
    async def dashboard_command(self, interaction: discord.Interaction):
        """Comando per aprire il dashboard personale"""
        member = interaction.user
        
        # Recupera dati utente
        user_data = await self.db.get_user(member.id)
        if not user_data:
            await interaction.response.send_message(
                "❌ You need to be verified first. Use /start in a verification channel.",
                ephemeral=True
            )
            return
        
        lang = self.get_user_lang(user_data)
        
        # Controlla se siamo nel canale personale
        if interaction.channel.id != user_data.get('personal_channel_id'):
            await interaction.response.send_message(
                t("commands.dashboard.only_personal", lang),
                ephemeral=True
            )
            return
        
        # Crea e mostra dashboard
        embed = discord.Embed(
            title=t("commands.dashboard.title", lang),
            color=Config.EMBED_COLOR
        )
        
        # Mostra info utente
        embed.add_field(name="Game ID", value=user_data.get('game_id', 'N/A'), inline=True)
        embed.add_field(name="Nickname", value=user_data.get('game_nickname', 'N/A'), inline=True)
        
        if user_data.get('alliance'):
            embed.add_field(name="Alliance", value=user_data['alliance'], inline=True)
            embed.add_field(name="Role", value=user_data.get('alliance_role', 'N/A'), inline=True)
        else:
            embed.add_field(name="Alliance", value="None", inline=True)
        
        view = DashboardView(lang, user_data, self)
        await interaction.response.send_message(embed=embed, view=view)
    
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
            stats_cog = self.bot.get_cog('ServerStatsCog')
            if stats_cog:
                await stats_cog.stats.update_stats(interaction.guild)
                await interaction.followup.send("✅ Statistiche aggiornate!", ephemeral=True)
            else:
                await interaction.followup.send("❌ Sistema statistiche non trovato!", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Errore aggiornamento statistiche: {e}", ephemeral=True)
    
    @app_commands.command(name="cleanup_stats", description="[Admin] Clean up duplicate statistics channels")
    @app_commands.default_permissions(administrator=True)
    async def cleanup_stats(self, interaction: discord.Interaction):
        """Pulisce i canali statistiche duplicati"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Ottieni il cog delle statistiche
            stats_cog = self.bot.get_cog('ServerStatsCog')
            if stats_cog:
                # Trova la categoria stats
                category = discord.utils.get(interaction.guild.categories, name="📊 Server Statistics")
                if category:
                    await stats_cog.stats._cleanup_duplicate_stats(category)
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
                await self.bot.cron_manager._schedule_event(event_data)
                
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
            from alliance_channels import AllianceChannels
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