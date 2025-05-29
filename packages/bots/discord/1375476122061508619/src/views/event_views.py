import discord
from discord import ui
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import asyncio
from src.database import Database
from locales import t
from src.services.alliance_channels import AllianceChannels


class EventTypeSelect(ui.Select):
    def __init__(self, lang: str):
        options = [
            discord.SelectOption(
                label=t("events.types.svs", lang),
                value="svs",
                description=t("events.types.svs_desc", lang)
            ),
            discord.SelectOption(
                label=t("events.types.ke", lang),
                value="ke",
                description=t("events.types.ke_desc", lang)
            ),
            discord.SelectOption(
                label=t("events.types.trap", lang),
                value="trap",
                description=t("events.types.trap_desc", lang)
            ),
            discord.SelectOption(
                label=t("events.types.bear_trap", lang),
                value="bear_trap",
                description=t("events.types.bear_trap_desc", lang)
            ),
            discord.SelectOption(
                label=t("events.types.custom", lang),
                value="custom",
                description=t("events.types.custom_desc", lang)
            )
        ]
        
        super().__init__(
            placeholder=t("events.select_type", lang),
            options=options,
            custom_id="event_type_select"
        )
        self.lang = lang
    
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(
            EventDetailsModal(self.values[0], self.lang)
        )


class EventDetailsModal(ui.Modal):
    def __init__(self, event_type: str, lang: str):
        super().__init__(
            title=t("events.create_event", lang),
            timeout=300
        )
        self.event_type = event_type
        self.lang = lang
        
        self.name = ui.TextInput(
            label=t("events.name_label", lang),
            placeholder=t("events.name_placeholder", lang),
            required=True,
            max_length=100
        )
        self.add_item(self.name)
        
        self.description = ui.TextInput(
            label=t("events.description_label", lang),
            placeholder=t("events.description_placeholder", lang),
            required=False,
            style=discord.TextStyle.paragraph,
            max_length=1000
        )
        self.add_item(self.description)
        
        self.start_time = ui.TextInput(
            label=t("events.start_time_label", lang) + " (UTC)",
            placeholder="YYYY-MM-DD HH:MM (UTC)",
            required=True,
            max_length=16
        )
        self.add_item(self.start_time)
        
        # Pre-fill recurring for bear trap events
        default_recurring = "2days" if event_type == "bear_trap" else ""
        self.recurring = ui.TextInput(
            label=t("events.recurring_label", lang),
            placeholder=t("events.recurring_placeholder", lang),
            default=default_recurring,
            required=False,
            max_length=20
        )
        self.add_item(self.recurring)
        
        self.reminders = ui.TextInput(
            label=t("events.reminders_label", lang),
            placeholder="e.g., 0.25, 0.5, 1, 2, 24 (hours before event)",
            required=False,
            max_length=100
        )
        self.add_item(self.reminders)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Parse start time
            start_time = datetime.strptime(self.start_time.value, "%Y-%m-%d %H:%M")
            
            # Parse reminders (comma-separated hours before event)
            reminder_hours = []
            if self.reminders.value:
                try:
                    reminder_hours = [float(h.strip()) for h in self.reminders.value.split(",")]
                    # Validate reminder values
                    for h in reminder_hours:
                        if h <= 0:
                            raise ValueError("Reminder hours must be positive")
                except ValueError:
                    await interaction.response.send_message(
                        t("events.invalid_reminders", self.lang),
                        ephemeral=True
                    )
                    return
            
            # Get user's alliance
            db = Database()
            user_data = await db.get_user(interaction.user.id)
            if not user_data or not user_data.get('alliance'):
                await interaction.response.send_message(
                    t("events.no_alliance", self.lang),
                    ephemeral=True
                )
                return
            
            # Create event data
            event_data = {
                "name": self.name.value,
                "description": self.description.value or "",
                "type": self.event_type,
                "alliance": user_data['alliance'],
                "creator_id": interaction.user.id,
                "start_time": start_time,
                "recurring": self.recurring.value or None,
                "reminder_hours": reminder_hours,
                "active": True,
                "channel_id": None,  # Will be set after channel creation
                "reminders_sent": {}  # Track which reminders have been sent
            }
            
            # Create event in database
            event = await db.create_event(event_data)
            
            # Create event channel
            alliance_channels = AllianceChannels()
            
            # Cerca il ruolo alleanza (formato corretto)
            alliance_role = discord.utils.get(
                interaction.guild.roles,
                name=user_data['alliance']  # Il nome del ruolo è solo il nome dell'alleanza
            )
            
            print(f"DEBUG: Cercando ruolo alleanza '{user_data['alliance']}' - Trovato: {alliance_role is not None}")
            
            if alliance_role:
                try:
                    channel = await alliance_channels.create_event_channel(
                        interaction.guild,
                        user_data['alliance'],
                        self.name.value,
                        self.description.value or "",
                        self.lang
                    )
                    
                    print(f"DEBUG: Canale evento creato: {channel.name} (ID: {channel.id})")
                    
                    # Update event with channel ID
                    await db.events.update_one(
                        {"_id": event['_id']},
                        {"$set": {"channel_id": channel.id}}
                    )
                    print(f"DEBUG: Evento aggiornato con channel_id: {channel.id}")
                    
                except Exception as e:
                    print(f"ERRORE creazione canale evento: {e}")
            else:
                # Fallback: usa il canale generale dell'alleanza se esiste
                print(f"DEBUG: Ruolo alleanza non trovato, cerco canale generale...")
                general_channel_data = await db.get_alliance_channel(user_data['alliance'], "general")
                if general_channel_data:
                    channel_id = general_channel_data['channel_id']
                    await db.events.update_one(
                        {"_id": event['_id']},
                        {"$set": {"channel_id": channel_id}}
                    )
                    print(f"DEBUG: Usando canale generale alleanza: {channel_id}")
                else:
                    print(f"ERRORE: Nessun canale trovato per alleanza '{user_data['alliance']}'!")
            
            await interaction.response.send_message(
                t("events.created_success", self.lang).format(name=self.name.value),
                ephemeral=True
            )
            
            # Refresh the event list view
            await interaction.followup.send(
                t("events.view_events", self.lang),
                view=EventListView(user_data['alliance'], self.lang),
                ephemeral=True
            )
            
        except ValueError:
            await interaction.response.send_message(
                t("events.invalid_date_format", self.lang),
                ephemeral=True
            )


class EventListView(ui.View):
    def __init__(self, alliance: str, lang: str):
        super().__init__(timeout=600)
        self.alliance = alliance
        self.lang = lang
        self.current_page = 0
        self.events_per_page = 5
        
    async def setup(self):
        db = Database()
        self.events = await db.get_alliance_events(self.alliance)
        self.total_pages = (len(self.events) - 1) // self.events_per_page + 1 if self.events else 1
        self.update_buttons()
    
    def update_buttons(self):
        self.clear_items()
        
        # Create new event button
        create_btn = ui.Button(
            label=t("events.create_new", self.lang),
            style=discord.ButtonStyle.success,
            custom_id="create_event"
        )
        create_btn.callback = self.create_event
        self.add_item(create_btn)
        
        # Add event buttons for current page
        start_idx = self.current_page * self.events_per_page
        end_idx = min(start_idx + self.events_per_page, len(self.events))
        
        for i in range(start_idx, end_idx):
            event = self.events[i]
            btn = ui.Button(
                label=f"{event['name']} ({event['type'].upper()})",
                style=discord.ButtonStyle.primary,
                custom_id=f"event_{str(event['_id'])}",
                row=1 + (i - start_idx) // 2
            )
            btn.callback = self.make_event_callback(event)
            self.add_item(btn)
        
        # Navigation buttons
        if self.total_pages > 1:
            prev_btn = ui.Button(
                label="◀",
                style=discord.ButtonStyle.secondary,
                disabled=self.current_page == 0,
                custom_id="prev_page",
                row=4
            )
            prev_btn.callback = self.prev_page
            self.add_item(prev_btn)
            
            page_label = ui.Button(
                label=f"{self.current_page + 1}/{self.total_pages}",
                style=discord.ButtonStyle.secondary,
                disabled=True,
                row=4
            )
            self.add_item(page_label)
            
            next_btn = ui.Button(
                label="▶",
                style=discord.ButtonStyle.secondary,
                disabled=self.current_page >= self.total_pages - 1,
                custom_id="next_page",
                row=4
            )
            next_btn.callback = self.next_page
            self.add_item(next_btn)
    
    def make_event_callback(self, event):
        async def callback(interaction: discord.Interaction):
            await interaction.response.send_message(
                embed=self.create_event_embed(event),
                view=EventDetailView(event, self.lang),
                ephemeral=True
            )
        return callback
    
    def create_event_embed(self, event):
        embed = discord.Embed(
            title=event['name'],
            description=event.get('description', t("events.no_description", self.lang)),
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name=t("events.type", self.lang),
            value=event['type'].upper(),
            inline=True
        )
        
        embed.add_field(
            name=t("events.start_time", self.lang),
            value=event['start_time'].strftime("%Y-%m-%d %H:%M UTC"),
            inline=True
        )
        
        if event.get('recurring'):
            embed.add_field(
                name=t("events.recurring", self.lang),
                value=event['recurring'],
                inline=True
            )
        
        if event.get('reminder_hours'):
            embed.add_field(
                name=t("events.reminders", self.lang),
                value=", ".join([f"{h}h" for h in event['reminder_hours']]),
                inline=True
            )
        
        embed.add_field(
            name=t("events.status", self.lang),
            value=t("events.active" if event.get('active', True) else "events.inactive", self.lang),
            inline=True
        )
        
        embed.set_footer(
            text=t("events.created_by", self.lang).format(id=event['creator_id'])
        )
        
        return embed
    
    async def create_event(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            t("events.select_type_prompt", self.lang),
            view=EventTypeSelectView(self.lang),
            ephemeral=True
        )
    
    async def prev_page(self, interaction: discord.Interaction):
        self.current_page -= 1
        self.update_buttons()
        await interaction.response.edit_message(view=self)
    
    async def next_page(self, interaction: discord.Interaction):
        self.current_page += 1
        self.update_buttons()
        await interaction.response.edit_message(view=self)


class EventTypeSelectView(ui.View):
    def __init__(self, lang: str):
        super().__init__(timeout=300)
        self.add_item(EventTypeSelect(lang))


class EventDetailView(ui.View):
    def __init__(self, event: Dict[str, Any], lang: str):
        super().__init__(timeout=300)
        self.event = event
        self.lang = lang
        
        # Toggle active/inactive button
        toggle_btn = ui.Button(
            label=t("events.deactivate" if event.get('active', True) else "events.activate", lang),
            style=discord.ButtonStyle.danger if event.get('active', True) else discord.ButtonStyle.success,
            custom_id="toggle_active"
        )
        toggle_btn.callback = self.toggle_active
        self.add_item(toggle_btn)
        
        # Edit button
        edit_btn = ui.Button(
            label=t("events.edit", lang),
            style=discord.ButtonStyle.primary,
            custom_id="edit_event"
        )
        edit_btn.callback = self.edit_event
        self.add_item(edit_btn)
        
        # Delete button
        delete_btn = ui.Button(
            label=t("events.delete", lang),
            style=discord.ButtonStyle.danger,
            custom_id="delete_event"
        )
        delete_btn.callback = self.delete_event
        self.add_item(delete_btn)
        
        # Back button
        back_btn = ui.Button(
            label=t("common.back", lang),
            style=discord.ButtonStyle.secondary,
            custom_id="back"
        )
        back_btn.callback = self.go_back
        self.add_item(back_btn)
    
    async def toggle_active(self, interaction: discord.Interaction):
        db = Database()
        new_status = not self.event.get('active', True)
        
        await db.events.update_one(
            {"_id": self.event['_id']},
            {"$set": {"active": new_status}}
        )
        
        self.event['active'] = new_status
        
        # Update button
        self.children[0].label = t(
            "events.deactivate" if new_status else "events.activate",
            self.lang
        )
        self.children[0].style = discord.ButtonStyle.danger if new_status else discord.ButtonStyle.success
        
        await interaction.response.edit_message(
            embed=EventListView(self.event['alliance'], self.lang).create_event_embed(self.event),
            view=self
        )
    
    async def edit_event(self, interaction: discord.Interaction):
        await interaction.response.send_modal(
            EventEditModal(self.event, self.lang)
        )
    
    async def delete_event(self, interaction: discord.Interaction):
        confirm_view = ConfirmDeleteView(self.event, self.lang)
        await interaction.response.send_message(
            t("events.confirm_delete", self.lang).format(name=self.event['name']),
            view=confirm_view,
            ephemeral=True
        )
    
    async def go_back(self, interaction: discord.Interaction):
        view = EventListView(self.event['alliance'], self.lang)
        await view.setup()
        await interaction.response.edit_message(
            content=t("events.view_events", self.lang),
            embed=None,
            view=view
        )


class EventEditModal(ui.Modal):
    def __init__(self, event: Dict[str, Any], lang: str):
        super().__init__(
            title=t("events.edit_event", lang),
            timeout=300
        )
        self.event = event
        self.lang = lang
        
        self.name = ui.TextInput(
            label=t("events.name_label", lang),
            default=event['name'],
            required=True,
            max_length=100
        )
        self.add_item(self.name)
        
        self.description = ui.TextInput(
            label=t("events.description_label", lang),
            default=event.get('description', ''),
            required=False,
            style=discord.TextStyle.paragraph,
            max_length=1000
        )
        self.add_item(self.description)
        
        self.start_time = ui.TextInput(
            label=t("events.start_time_label", lang) + " (UTC)",
            default=event['start_time'].strftime("%Y-%m-%d %H:%M"),
            required=True,
            max_length=16
        )
        self.add_item(self.start_time)
        
        self.recurring = ui.TextInput(
            label=t("events.recurring_label", lang),
            default=event.get('recurring', ''),
            required=False,
            max_length=20
        )
        self.add_item(self.recurring)
        
        reminder_str = ", ".join([str(h) for h in event.get('reminder_hours', [])])
        self.reminders = ui.TextInput(
            label=t("events.reminders_label", lang),
            placeholder=t("events.reminders_placeholder", lang),
            default=reminder_str,
            required=False,
            max_length=100
        )
        self.add_item(self.reminders)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Parse start time
            start_time = datetime.strptime(self.start_time.value, "%Y-%m-%d %H:%M")
            
            # Parse reminders
            reminder_hours = []
            if self.reminders.value:
                try:
                    reminder_hours = [float(h.strip()) for h in self.reminders.value.split(",")]
                    # Validate reminder values
                    for h in reminder_hours:
                        if h <= 0:
                            raise ValueError("Reminder hours must be positive")
                except ValueError:
                    await interaction.response.send_message(
                        t("events.invalid_reminders", self.lang),
                        ephemeral=True
                    )
                    return
            
            # Update event
            db = Database()
            update_data = {
                "name": self.name.value,
                "description": self.description.value,
                "start_time": start_time,
                "recurring": self.recurring.value or None,
                "reminder_hours": reminder_hours,
                "updated_at": datetime.utcnow()
            }
            
            await db.events.update_one(
                {"_id": self.event['_id']},
                {"$set": update_data}
            )
            
            # Update local event data
            self.event.update(update_data)
            
            await interaction.response.send_message(
                t("events.updated_success", self.lang),
                ephemeral=True
            )
            
        except ValueError:
            await interaction.response.send_message(
                t("events.invalid_date_format", self.lang),
                ephemeral=True
            )


class ConfirmDeleteView(ui.View):
    def __init__(self, event: Dict[str, Any], lang: str):
        super().__init__(timeout=60)
        self.event = event
        self.lang = lang
        
        confirm_btn = ui.Button(
            label=t("common.confirm", lang),
            style=discord.ButtonStyle.danger,
            custom_id="confirm"
        )
        confirm_btn.callback = self.confirm_delete
        self.add_item(confirm_btn)
        
        cancel_btn = ui.Button(
            label=t("common.cancel", lang),
            style=discord.ButtonStyle.secondary,
            custom_id="cancel"
        )
        cancel_btn.callback = self.cancel
        self.add_item(cancel_btn)
    
    async def confirm_delete(self, interaction: discord.Interaction):
        db = Database()
        
        # Delete event channel if exists
        if self.event.get('channel_id'):
            channel = interaction.guild.get_channel(self.event['channel_id'])
            if channel:
                await channel.delete()
        
        # Delete event from database
        await db.events.delete_one({"_id": self.event['_id']})
        
        await interaction.response.edit_message(
            content=t("events.deleted_success", self.lang).format(name=self.event['name']),
            view=None
        )
    
    async def cancel(self, interaction: discord.Interaction):
        await interaction.response.edit_message(
            content=t("events.delete_cancelled", self.lang),
            view=None
        )