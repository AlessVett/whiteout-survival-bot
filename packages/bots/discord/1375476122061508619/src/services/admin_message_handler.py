"""
Admin Message Handler Service

This service monitors for admin messages from the web panel and processes them
using the Discord bot instance directly.
"""

import asyncio
import json
import os
import glob
import discord
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class AdminMessageHandler:
    def __init__(self, bot):
        self.bot = bot
        self.running = False
        self.task = None
        
    async def start(self):
        """Start monitoring for admin messages"""
        if self.running:
            return
            
        self.running = True
        self.task = asyncio.create_task(self._monitor_messages())
        logger.info("Admin message handler started")
        
    async def stop(self):
        """Stop monitoring for admin messages"""
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info("Admin message handler stopped")
        
    async def _monitor_messages(self):
        """Monitor /tmp directory for admin message files"""
        while self.running:
            try:
                # Look for message files
                message_files = glob.glob("/tmp/bot_message_*.json")
                
                for message_file in message_files:
                    # Skip if response file already exists
                    response_file = f"{message_file}.response"
                    if os.path.exists(response_file):
                        continue
                        
                    try:
                        await self._process_message_file(message_file, response_file)
                    except Exception as e:
                        logger.error(f"Error processing message file {message_file}: {e}")
                        # Create error response
                        await self._create_response_file(response_file, False, str(e))
                        
            except Exception as e:
                logger.error(f"Error in admin message monitor: {e}")
                
            await asyncio.sleep(0.5)  # Check every 500ms
            
    async def _process_message_file(self, message_file: str, response_file: str):
        """Process a single message file"""
        try:
            # Read message data
            with open(message_file, 'r') as f:
                message_data = json.load(f)
                
            action = message_data.get("action")
            
            if action == "send_admin_message":
                await self._handle_admin_message(message_data, response_file)
            else:
                await self._create_response_file(response_file, False, f"Unknown action: {action}")
                
        except Exception as e:
            await self._create_response_file(response_file, False, str(e))
            
    async def _handle_admin_message(self, message_data: dict, response_file: str):
        """Handle admin message sending"""
        try:
            channel_id = int(message_data["channel_id"])
            content = message_data["content"]
            admin_name = message_data["admin_name"]
            close_ticket = message_data.get("close_ticket", False)
            
            # Get the channel
            channel = self.bot.get_channel(channel_id)
            if not channel:
                # Try to fetch the channel if not in cache
                try:
                    channel = await self.bot.fetch_channel(channel_id)
                except discord.NotFound:
                    await self._create_response_file(response_file, False, "Channel not found")
                    return
                except discord.Forbidden:
                    await self._create_response_file(response_file, False, "No permission to access channel")
                    return
                    
            # Create embed for admin message
            embed = discord.Embed(
                description=content,
                color=0xFF0000,  # Red color for admin messages
                timestamp=datetime.utcnow()
            )
            embed.set_author(
                name=f"Admin Reply - {admin_name}",
                icon_url="https://cdn.discordapp.com/emojis/1234567890123456789.png"  # Optional admin icon
            )
            embed.set_footer(text="Reply from Admin Panel")
            
            # Send the message
            await channel.send(embed=embed)
            
            # If close_ticket is True, send closing message and delete channel
            if close_ticket:
                await asyncio.sleep(2)  # Small delay
                
                closing_embed = discord.Embed(
                    title="🔒 Ticket Closed",
                    description="This ticket has been closed by an administrator.",
                    color=0x808080  # Gray color
                )
                await channel.send(embed=closing_embed)
                
                # Send countdown message
                await channel.send("This channel will be deleted in 10 seconds...")
                
                # Wait and delete channel
                await asyncio.sleep(10)
                await channel.delete(reason="Ticket closed by admin")
                
            await self._create_response_file(response_file, True, "Message sent successfully")
            
        except discord.HTTPException as e:
            await self._create_response_file(response_file, False, f"Discord API error: {e}")
        except Exception as e:
            await self._create_response_file(response_file, False, str(e))
            
    async def _create_response_file(self, response_file: str, success: bool, message: str):
        """Create response file for the microservice"""
        try:
            response_data = {
                "success": success,
                "message": message if success else None,
                "error": message if not success else None,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            with open(response_file, 'w') as f:
                json.dump(response_data, f)
                
        except Exception as e:
            logger.error(f"Error creating response file: {e}")