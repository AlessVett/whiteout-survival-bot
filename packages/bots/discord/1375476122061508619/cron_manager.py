import asyncio
import discord
from datetime import datetime, timedelta
from typing import Dict, List, Any
from database import Database
from locales import t
import logging

logger = logging.getLogger(__name__)


class CronManager:
    def __init__(self, bot):
        self.bot = bot
        self.db = Database()
        self.running = False
        self.tasks = {}
        
    async def start(self):
        """Start the cron manager"""
        if self.running:
            return
            
        self.running = True
        logger.info("Starting CronManager")
        
        # Start the main cron loop
        self.bot.loop.create_task(self._cron_loop())
        
    async def stop(self):
        """Stop the cron manager"""
        self.running = False
        
        # Cancel all scheduled tasks
        for task_id, task in self.tasks.items():
            if not task.done():
                task.cancel()
        
        self.tasks.clear()
        logger.info("CronManager stopped")
    
    async def _cron_loop(self):
        """Main cron loop that checks for events and schedules reminders"""
        print("CronManager: Loop principale avviato")
        while self.running:
            try:
                await self._check_events()
                await asyncio.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Error in cron loop: {e}")
                print(f"ERRORE CronManager loop: {e}")
                await asyncio.sleep(60)
        print("CronManager: Loop principale terminato")
    
    async def _check_events(self):
        """Check all active events and schedule reminders"""
        try:
            # Get all active events
            events = await self.db.events.find({"active": True}).to_list(None)
            now = datetime.utcnow()
            print(f"CronManager: Controllo {len(events)} eventi attivi ({now.strftime('%H:%M:%S')} UTC)")
            
            for event in events:
                event_id = str(event['_id'])
                
                # Skip if already scheduled
                if event_id in self.tasks and not self.tasks[event_id].done():
                    now = datetime.utcnow()
                    print(f"CronManager: Evento {event['name']} già schedulato ({now.strftime('%H:%M:%S')} UTC)")
                    continue
                
                print(f"CronManager: Schedulando reminder per evento '{event['name']}' (inizio: {event['start_time']}) ({now.strftime('%H:%M:%S')} UTC)")
                
                # Schedule reminders for this event
                await self._schedule_event_reminders(event)
                
        except Exception as e:
            logger.error(f"Error checking events: {e}")
            print(f"ERRORE CronManager._check_events: {e}")
    
    async def _schedule_event_reminders(self, event: Dict[str, Any]):
        """Schedule all reminders for a specific event"""
        event_id = str(event['_id'])
        start_time = event['start_time']
        reminder_hours = event.get('reminder_hours', [])
        now = datetime.utcnow()
        
        print(f"CronManager: Evento '{event['name']}' - ora corrente: {now}, inizio evento: {start_time}")
        print(f"CronManager: Reminder configurati: {reminder_hours}")
        
        # Skip if event has already started
        if start_time <= now:
            print(f"CronManager: Evento '{event['name']}' già iniziato")
            # Check if it's a recurring event
            if event.get('recurring'):
                print(f"CronManager: Evento ricorrente, calcolando prossima occorrenza...")
                # Calculate next occurrence
                next_time = self._calculate_next_occurrence(start_time, event['recurring'])
                if next_time:
                    print(f"CronManager: Prossima occorrenza: {next_time}")
                    # Update event with new start time and reset reminders_sent
                    await self.db.events.update_one(
                        {"_id": event['_id']},
                        {
                            "$set": {
                                "start_time": next_time,
                                "reminders_sent": {}  # Reset reminders for new occurrence
                            }
                        }
                    )
                    event['start_time'] = next_time
                    event['reminders_sent'] = {}
                    start_time = next_time
                else:
                    print(f"CronManager: Impossibile calcolare prossima occorrenza")
                    return
            else:
                print(f"CronManager: Evento non ricorrente già iniziato, saltando")
                return
        
        # Create a task that handles all reminders for this event
        task = self.bot.loop.create_task(
            self._handle_event_reminders(event, reminder_hours)
        )
        self.tasks[event_id] = task
    
    async def _handle_event_reminders(self, event: Dict[str, Any], reminder_hours: List[float]):
        """Handle all reminders for a specific event"""
        event_id = str(event['_id'])
        start_time = event['start_time']
        
        print(f"CronManager: Gestendo reminder per evento '{event['name']}' (ID: {event_id})")
        
        try:
            # Sort reminder hours in descending order (earliest reminder first)
            reminder_hours_sorted = sorted(reminder_hours, reverse=True)
            print(f"CronManager: Reminder ordinati: {reminder_hours_sorted}")
            
            for hours in reminder_hours_sorted:
                reminder_time = start_time - timedelta(hours=hours)
                # Create a key for tracking sent reminders
                if hours == 0.25:
                    reminder_key = "15m"
                elif hours == 0.5:
                    reminder_key = "30m"
                else:
                    reminder_key = f"{hours}h"
                now = datetime.utcnow()
                
                print(f"CronManager: Reminder {hours}h - ora reminder: {reminder_time}, ora corrente: {now}")
                
                # Reload event to get latest reminders_sent status
                current_event = await self.db.events.find_one({"_id": event['_id']})
                if not current_event:
                    print(f"CronManager: Evento non trovato, saltando")
                    continue
                
                # Check if this reminder was already sent
                reminders_sent = current_event.get('reminders_sent', {})
                if reminder_key in reminders_sent and reminders_sent[reminder_key]:
                    print(f"CronManager: Reminder {hours}h già inviato, saltando")
                    continue
                
                # Skip if reminder time has passed (with 60-second tolerance)
                if reminder_time <= now - timedelta(seconds=60):
                    print(f"CronManager: Reminder {hours}h già passato (oltre tolleranza 60s), saltando")
                    continue
                
                # If reminder time is within tolerance window (-60s to +60s from now), send immediately
                if reminder_time <= now + timedelta(seconds=60):
                    print(f"CronManager: Reminder {hours}h entro finestra di tolleranza, invio immediato")
                    # Send reminder with retry logic
                    success = await self._send_reminder_with_retry(event, hours)
                    
                    # Update reminders_sent status
                    if success:
                        await self.db.events.update_one(
                            {"_id": event['_id']},
                            {"$set": {f"reminders_sent.{reminder_key}": True}}
                        )
                    continue
                
                # Wait until reminder time
                wait_seconds = (reminder_time - now).total_seconds()
                print(f"CronManager: Aspetto {wait_seconds:.0f} secondi per reminder {hours}h")
                await asyncio.sleep(wait_seconds)
                
                # Send reminder with retry logic
                now_send = datetime.utcnow()
                print(f"CronManager: Invio reminder {hours}h per evento '{event['name']}' ({now_send.strftime('%H:%M:%S')} UTC)")
                success = await self._send_reminder_with_retry(event, hours)
                
                # Update reminders_sent status
                if success:
                    await self.db.events.update_one(
                        {"_id": event['_id']},
                        {"$set": {f"reminders_sent.{reminder_key}": True}}
                    )
            
            # Wait for event start time
            now = datetime.utcnow()
            if start_time > now:
                wait_seconds = (start_time - now).total_seconds()
                await asyncio.sleep(wait_seconds)
                
                # Send event started notification
                now_start = datetime.utcnow()
                print(f"CronManager: Evento '{event['name']}' iniziato! ({now_start.strftime('%H:%M:%S')} UTC)")
                await self._send_event_started(event)
            
        except asyncio.CancelledError:
            logger.info(f"Reminder task cancelled for event {event_id}")
        except Exception as e:
            logger.error(f"Error handling reminders for event {event_id}: {e}")
        finally:
            # Remove task from tracking
            if event_id in self.tasks:
                del self.tasks[event_id]
    
    async def _send_reminder_with_retry(self, event: Dict[str, Any], hours_before: float, max_retries: int = 3) -> bool:
        """Send a reminder with retry logic"""
        for attempt in range(max_retries):
            try:
                await self._send_reminder(event, hours_before)
                return True
            except Exception as e:
                logger.error(f"Attempt {attempt + 1} failed to send reminder: {e}")
                if attempt < max_retries - 1:
                    # Wait before retrying (exponential backoff)
                    await asyncio.sleep(2 ** attempt)
                else:
                    logger.error(f"Failed to send reminder after {max_retries} attempts")
                    return False
        return False
    
    async def _send_reminder(self, event: Dict[str, Any], hours_before: float):
        """Send a reminder for an event"""
        try:
            # Get the event channel
            if not event.get('channel_id'):
                print(f"ERRORE: Evento '{event['name']}' non ha channel_id!")
                return
            
            channel = self.bot.get_channel(event['channel_id'])
            if not channel:
                print(f"ERRORE: Canale {event['channel_id']} per evento '{event['name']}' non trovato!")
                return
            
            print(f"CronManager: Invio reminder in canale {channel.name} (ID: {channel.id})")
            
            # Create reminder embed - SEMPRE IN INGLESE
            # Format time display for fractional hours
            if hours_before < 1:
                minutes = int(hours_before * 60)
                time_display = f"{minutes} minutes"
            elif hours_before == int(hours_before):
                time_display = f"{int(hours_before)} hours"
            else:
                hours = int(hours_before)
                minutes = int((hours_before - hours) * 60)
                time_display = f"{hours} hours {minutes} minutes"
            
            embed = discord.Embed(
                title="⏰ Event Reminder",
                description=f"**{event['name']}** starts in {time_display}!",
                color=discord.Color.gold(),
                timestamp=event['start_time']
            )
            
            if event.get('description'):
                embed.add_field(
                    name="Description",
                    value=event['description'],
                    inline=False
                )
            
            embed.set_footer(text="Event starts at")
            
            # Send reminder
            await channel.send(embed=embed)
            
            # Also send to alliance reminders channel if exists
            reminders_channel_name = f"{event['alliance'].lower()}-reminders"
            reminders_channel = discord.utils.get(
                channel.guild.text_channels,
                name=reminders_channel_name
            )
            if reminders_channel and reminders_channel.id != channel.id:
                await reminders_channel.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error sending reminder: {e}")
    
    async def _send_event_started(self, event: Dict[str, Any]):
        """Send notification that event has started"""
        try:
            # Get the event channel
            if not event.get('channel_id'):
                return
            
            channel = self.bot.get_channel(event['channel_id'])
            if not channel:
                return
            
            # Create started embed - SEMPRE IN INGLESE
            embed = discord.Embed(
                title="🚀 Event Started!",
                description=f"**{event['name']}** has started! Good luck to all participants!",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            
            if event.get('description'):
                embed.add_field(
                    name="Description",
                    value=event['description'],
                    inline=False
                )
            
            # Send notification
            await channel.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error sending event started notification: {e}")
    
    def _calculate_next_occurrence(self, start_time: datetime, recurring: str) -> datetime:
        """Calculate the next occurrence of a recurring event"""
        now = datetime.utcnow()
        
        if recurring == "daily":
            next_time = start_time + timedelta(days=1)
            while next_time <= now:
                next_time += timedelta(days=1)
            return next_time
            
        elif recurring == "2days":
            next_time = start_time + timedelta(days=2)
            while next_time <= now:
                next_time += timedelta(days=2)
            return next_time
            
        elif recurring == "weekly":
            next_time = start_time + timedelta(weeks=1)
            while next_time <= now:
                next_time += timedelta(weeks=1)
            return next_time
            
        elif recurring == "biweekly":
            next_time = start_time + timedelta(weeks=2)
            while next_time <= now:
                next_time += timedelta(weeks=2)
            return next_time
            
        elif recurring == "monthly":
            # Simple monthly calculation (may need refinement for edge cases)
            next_time = start_time
            while next_time <= now:
                if next_time.month == 12:
                    next_time = next_time.replace(year=next_time.year + 1, month=1)
                else:
                    next_time = next_time.replace(month=next_time.month + 1)
            return next_time
        
        return None
    
    async def refresh_event(self, event_id: str):
        """Refresh reminders for a specific event (after edit)"""
        # Cancel existing task if any
        if event_id in self.tasks and not self.tasks[event_id].done():
            self.tasks[event_id].cancel()
            del self.tasks[event_id]
        
        # Reload event and reschedule
        event = await self.db.events.find_one({"_id": event_id})
        if event and event.get('active'):
            await self._schedule_event_reminders(event)