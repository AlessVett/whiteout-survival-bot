"""
Admin Panel Integration API for Discord Bot

This module provides HTTP endpoints for the admin panel to communicate with the Discord bot.
"""

from fastapi import FastAPI, HTTPException, Header, Depends
from pydantic import BaseModel
import discord
import os
from typing import Optional
import logging

logger = logging.getLogger(__name__)

app = FastAPI()

# Discord bot instance (will be set by the bot)
discord_bot = None

class AdminMessage(BaseModel):
    """Model for admin messages to Discord channels"""
    channel_id: str
    content: str
    admin_name: str
    embed_color: Optional[int] = 0xFF0000  # Red for admin messages
    close_ticket: bool = False

class ChannelDelete(BaseModel):
    """Model for channel deletion requests"""
    channel_id: str
    reason: Optional[str] = "Ticket closed by admin"

# Simple API key authentication
async def verify_admin_api_key(x_api_key: str = Header(None)):
    """Verify admin panel API key"""
    api_key = os.getenv('ADMIN_API_KEY', 'your-secure-api-key-here')
    if not x_api_key or x_api_key != api_key:
        raise HTTPException(
            status_code=403,
            detail="Invalid or missing API key"
        )
    return True

@app.post("/send-message")
async def send_message_to_channel(
    message: AdminMessage,
    authenticated: bool = Depends(verify_admin_api_key)
):
    """Send a message from admin to a Discord channel"""
    try:
        if not discord_bot:
            raise HTTPException(status_code=503, detail="Discord bot not initialized")
        
        # Get the channel
        channel = discord_bot.get_channel(int(message.channel_id))
        if not channel:
            # Try to fetch the channel if not in cache
            try:
                channel = await discord_bot.fetch_channel(int(message.channel_id))
            except:
                raise HTTPException(status_code=404, detail="Channel not found")
        
        # Create embed for admin message
        embed = discord.Embed(
            description=message.content,
            color=message.embed_color
        )
        embed.set_author(
            name=f"Admin Reply - {message.admin_name}",
            icon_url="https://cdn.discordapp.com/attachments/1234567890/1234567890/admin_icon.png"  # Replace with your admin icon
        )
        embed.set_footer(text="Reply from Admin Panel")
        
        # Send the message
        await channel.send(embed=embed)
        
        # If close_ticket is True, send closing message and delete channel
        if message.close_ticket:
            closing_embed = discord.Embed(
                title="🔒 Ticket Closed",
                description="This ticket has been closed by an administrator.",
                color=0x808080  # Gray
            )
            await channel.send(embed=closing_embed)
            
            # Delete channel after a delay
            await channel.send("This channel will be deleted in 10 seconds...")
            await discord.utils.sleep_until(discord.utils.utcnow() + discord.timedelta(seconds=10))
            await channel.delete(reason="Ticket closed by admin")
        
        return {
            "success": True,
            "message": "Message sent successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending message to Discord: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/channel/{channel_id}")
async def delete_channel(
    channel_id: str,
    authenticated: bool = Depends(verify_admin_api_key)
):
    """Delete a Discord channel (used when closing tickets)"""
    try:
        if not discord_bot:
            raise HTTPException(status_code=503, detail="Discord bot not initialized")
        
        # Get the channel
        channel = discord_bot.get_channel(int(channel_id))
        if not channel:
            try:
                channel = await discord_bot.fetch_channel(int(channel_id))
            except:
                raise HTTPException(status_code=404, detail="Channel not found")
        
        # Delete the channel
        await channel.delete(reason="Ticket closed from admin panel")
        
        return {
            "success": True,
            "message": "Channel deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting channel: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "bot_connected": discord_bot is not None and not discord_bot.is_closed()
    }

def set_bot_instance(bot):
    """Set the Discord bot instance (called by the bot on startup)"""
    global discord_bot
    discord_bot = bot
    logger.info("Discord bot instance set for admin integration")