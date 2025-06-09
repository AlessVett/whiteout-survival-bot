"""
Tickets API Router for Discord Bot Integration

This module provides endpoints for Discord bot to create and manage tickets
without requiring admin authentication.
"""

from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel
import structlog

from configs.settings import settings
from applications.v1.core.ticket_system import (
    TicketManager, TicketCreate, TicketPriority
)

logger = structlog.get_logger()

router = APIRouter(
    prefix="/api/discord/tickets",
    tags=["discord-tickets"],
    responses={404: {"description": "Not found"}},
)

class DiscordTicketCreate(BaseModel):
    """Model for creating a ticket from Discord"""
    user_id: str
    user_name: str
    guild_id: str
    title: str
    description: str
    priority: TicketPriority = TicketPriority.MEDIUM
    category: str = "Discord Support"

class DiscordTicketMessage(BaseModel):
    """Model for adding a message to a ticket from Discord"""
    user_id: str
    user_name: str
    content: str
    is_admin: bool = False

# Simple API key authentication for Discord bot
async def verify_discord_bot_token(x_api_key: str = Header(None)):
    """Verify Discord bot API key"""
    if not x_api_key or x_api_key != settings.discord_bot_api_key:
        raise HTTPException(
            status_code=403,
            detail="Invalid or missing Discord bot API key"
        )
    return True

# Database connection (reuse from admin module)
async def get_database():
    """Get MongoDB connection"""
    try:
        import os
        import motor.motor_asyncio
        
        mongodb_url = os.getenv('MONGODB_URI', settings.mongodb_url)
        database_name = os.getenv('MONGODB_DB', settings.database_name)
        
        client = motor.motor_asyncio.AsyncIOMotorClient(
            mongodb_url, 
            serverSelectionTimeoutMS=5000
        )
        await client.server_info()
        database = client[database_name]
        return database
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        return None

@router.post("/create")
async def create_ticket(
    ticket_data: DiscordTicketCreate,
    authenticated: bool = Depends(verify_discord_bot_token)
):
    """Create a new support ticket from Discord"""
    try:
        db = await get_database()
        if db is None:
            raise HTTPException(status_code=503, detail="Database not available")
            
        ticket_manager = TicketManager(db)
        
        # Convert Discord ticket data to internal format
        create_data = TicketCreate(
            user_id=ticket_data.user_id,
            user_name=ticket_data.user_name,
            guild_id=ticket_data.guild_id,
            title=ticket_data.title,
            description=ticket_data.description,
            priority=ticket_data.priority,
            category=ticket_data.category
        )
        
        ticket = await ticket_manager.create_ticket(create_data)
        
        logger.info(f"Created ticket {ticket.ticket_id} from Discord for user {ticket.user_name}")
        
        return {
            "success": True,
            "ticket_id": ticket.ticket_id,
            "message": f"Ticket {ticket.ticket_id} created successfully",
            "ticket": {
                "id": ticket.ticket_id,
                "title": ticket.title,
                "status": ticket.status,
                "priority": ticket.priority,
                "created_at": ticket.created_at.isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Error creating ticket from Discord: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{ticket_id}/channel")
async def update_ticket_channel(
    ticket_id: str,
    channel_data: Dict[str, Any],
    authenticated: bool = Depends(verify_discord_bot_token)
):
    """Update ticket with Discord channel information"""
    try:
        db = await get_database()
        if db is None:
            raise HTTPException(status_code=503, detail="Database not available")
            
        # Update ticket with channel_id
        result = await db.tickets.update_one(
            {"_id": ticket_id},
            {
                "$set": {
                    "channel_id": channel_data.get("channel_id"),
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Ticket not found")
            
        logger.info(f"Updated ticket {ticket_id} with channel {channel_data.get('channel_id')}")
        
        return {
            "success": True,
            "message": "Ticket channel updated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating ticket channel: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{ticket_id}/message")
async def add_ticket_message(
    ticket_id: str,
    message_data: DiscordTicketMessage,
    authenticated: bool = Depends(verify_discord_bot_token)
):
    """Add a message to an existing ticket"""
    try:
        db = await get_database()
        if db is None:
            raise HTTPException(status_code=503, detail="Database not available")
            
        ticket_manager = TicketManager(db)
        
        # Add message to ticket
        success = await ticket_manager.add_message(
            ticket_id=ticket_id,
            author_id=message_data.user_id,
            author_name=message_data.user_name,
            content=message_data.content,
            author_type="admin" if message_data.is_admin else "user"
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Ticket not found")
            
        logger.info(f"Added message to ticket {ticket_id} from {message_data.user_name}")
        
        return {
            "success": True,
            "message": "Message added successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding message to ticket: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{ticket_id}")
async def get_ticket(
    ticket_id: str,
    authenticated: bool = Depends(verify_discord_bot_token)
):
    """Get ticket details for Discord bot"""
    try:
        db = await get_database()
        if not db:
            raise HTTPException(status_code=503, detail="Database not available")
            
        ticket_manager = TicketManager(db)
        ticket = await ticket_manager.get_ticket(ticket_id)
        
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")
            
        # Convert datetime objects for JSON serialization
        ticket_dict = ticket.dict()
        for key, value in ticket_dict.items():
            if isinstance(value, datetime):
                ticket_dict[key] = value.isoformat()
        for msg in ticket_dict.get("messages", []):
            if isinstance(msg.get("timestamp"), datetime):
                msg["timestamp"] = msg["timestamp"].isoformat()
                
        return {
            "success": True,
            "ticket": ticket_dict
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting ticket {ticket_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{ticket_id}/close")
async def close_ticket(
    ticket_id: str,
    authenticated: bool = Depends(verify_discord_bot_token)
):
    """Close a ticket (used when Discord channel is deleted)"""
    try:
        db = await get_database()
        if db is None:
            raise HTTPException(status_code=503, detail="Database not available")
            
        # Update ticket status to closed
        result = await db.tickets.update_one(
            {"_id": ticket_id},
            {
                "$set": {
                    "status": "closed",
                    "closed_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Ticket not found")
            
        logger.info(f"Closed ticket {ticket_id} from Discord")
        
        return {
            "success": True,
            "message": "Ticket closed successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error closing ticket: {e}")
        raise HTTPException(status_code=500, detail=str(e))