"""
Ticket System for DWOS Infrastructure

This module provides ticket management functionality for support requests
from Discord users, with integration to the admin panel.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum
from pydantic import BaseModel, Field
import motor.motor_asyncio
from bson import ObjectId
import structlog

logger = structlog.get_logger()

class TicketStatus(str, Enum):
    """Ticket status enumeration"""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    WAITING_RESPONSE = "waiting_response"
    RESOLVED = "closed"
    CLOSED = "closed"

class TicketPriority(str, Enum):
    """Ticket priority enumeration"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

class TicketMessage(BaseModel):
    """Message within a ticket thread"""
    author_id: str
    author_name: str
    author_type: str = "user"  # user or admin
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    attachments: List[str] = []

class Ticket(BaseModel):
    """Ticket model"""
    ticket_id: str
    user_id: str
    user_name: str
    guild_id: str
    channel_id: Optional[str] = None  # Discord channel created for the ticket
    
    title: str
    description: str
    status: TicketStatus = TicketStatus.OPEN
    priority: TicketPriority = TicketPriority.MEDIUM
    
    category: Optional[str] = None
    tags: List[str] = []
    
    messages: List[TicketMessage] = []
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    
    assigned_to: Optional[str] = None  # Admin who is handling the ticket
    resolution_notes: Optional[str] = None

class TicketCreate(BaseModel):
    """Model for creating a new ticket"""
    user_id: str
    user_name: str
    guild_id: str
    title: str
    description: str
    priority: TicketPriority = TicketPriority.MEDIUM
    category: Optional[str] = None

class TicketUpdate(BaseModel):
    """Model for updating a ticket"""
    status: Optional[TicketStatus] = None
    priority: Optional[TicketPriority] = None
    assigned_to: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    resolution_notes: Optional[str] = None

class TicketReply(BaseModel):
    """Model for replying to a ticket"""
    content: str
    author_type: str = "admin"
    close_ticket: bool = False

class TicketManager:
    """Manager class for ticket operations"""
    
    def __init__(self, db: motor.motor_asyncio.AsyncIOMotorDatabase):
        self.db = db
        self.collection = db.tickets
        
    async def create_ticket(self, ticket_data: TicketCreate) -> Ticket:
        """Create a new ticket"""
        try:
            # Generate unique ticket ID with retry logic
            max_retries = 5
            for attempt in range(max_retries):
                try:
                    # Get the highest existing ticket number
                    pipeline = [
                        {"$project": {"ticket_number": {"$toInt": {"$substr": ["$ticket_id", 7, -1]}}}},
                        {"$sort": {"ticket_number": -1}},
                        {"$limit": 1}
                    ]
                    
                    result = await self.collection.aggregate(pipeline).to_list(length=1)
                    
                    if result:
                        next_number = result[0]["ticket_number"] + 1
                    else:
                        next_number = 1
                    
                    ticket_id = f"TICKET-{next_number:05d}"
                    break
                    
                except Exception as e:
                    if attempt == max_retries - 1:
                        # Fallback to timestamp-based ID
                        import time
                        timestamp = int(time.time() * 1000) % 100000
                        ticket_id = f"TICKET-{timestamp:05d}"
                        break
                    continue
            
            # Create ticket document
            ticket = Ticket(
                ticket_id=ticket_id,
                user_id=ticket_data.user_id,
                user_name=ticket_data.user_name,
                guild_id=ticket_data.guild_id,
                title=ticket_data.title,
                description=ticket_data.description,
                priority=ticket_data.priority,
                category=ticket_data.category
            )
            
            # Add initial message
            ticket.messages.append(TicketMessage(
                author_id=ticket_data.user_id,
                author_name=ticket_data.user_name,
                author_type="user",
                content=ticket_data.description
            ))
            
            # Insert into database with duplicate key handling
            ticket_dict = ticket.dict()
            ticket_dict["_id"] = ticket_id
            
            try:
                await self.collection.insert_one(ticket_dict)
                logger.info(f"Created ticket {ticket_id} for user {ticket_data.user_name}")
                return ticket
                
            except Exception as insert_error:
                # If duplicate key error, try with timestamp-based ID
                if "duplicate key" in str(insert_error) or "E11000" in str(insert_error):
                    import time
                    timestamp = int(time.time() * 1000) % 100000
                    fallback_ticket_id = f"TICKET-{timestamp:05d}"
                    
                    # Update ticket with new ID
                    ticket.ticket_id = fallback_ticket_id
                    ticket_dict = ticket.dict()
                    ticket_dict["_id"] = fallback_ticket_id
                    
                    await self.collection.insert_one(ticket_dict)
                    logger.info(f"Created ticket {fallback_ticket_id} for user {ticket_data.user_name} (fallback ID)")
                    return ticket
                else:
                    raise insert_error
            
        except Exception as e:
            logger.error(f"Failed to create ticket: {e}")
            raise
    
    async def get_ticket(self, ticket_id: str) -> Optional[Ticket]:
        """Get a single ticket by ID"""
        try:
            ticket_doc = await self.collection.find_one({"_id": ticket_id})
            if ticket_doc:
                ticket_doc.pop("_id")
                return Ticket(**ticket_doc)
            return None
        except Exception as e:
            logger.error(f"Failed to get ticket {ticket_id}: {e}")
            return None
    
    async def get_tickets(
        self, 
        status: Optional[TicketStatus] = None,
        user_id: Optional[str] = None,
        assigned_to: Optional[str] = None,
        limit: int = 50,
        skip: int = 0
    ) -> List[Ticket]:
        """Get tickets with filters"""
        try:
            query = {}
            if status:
                query["status"] = status
            if user_id:
                query["user_id"] = user_id
            if assigned_to:
                query["assigned_to"] = assigned_to
                
            cursor = self.collection.find(query).sort("created_at", -1).skip(skip).limit(limit)
            tickets = []
            
            async for doc in cursor:
                doc.pop("_id", None)
                tickets.append(Ticket(**doc))
                
            return tickets
            
        except Exception as e:
            logger.error(f"Failed to get tickets: {e}")
            return []
    
    async def update_ticket(self, ticket_id: str, update_data: TicketUpdate) -> Optional[Ticket]:
        """Update a ticket"""
        try:
            update_dict = {k: v for k, v in update_data.dict().items() if v is not None}
            update_dict["updated_at"] = datetime.utcnow()
            
            # Handle status changes
            if update_data.status == TicketStatus.RESOLVED:
                update_dict["resolved_at"] = datetime.utcnow()
            elif update_data.status == TicketStatus.CLOSED:
                update_dict["closed_at"] = datetime.utcnow()
                
            result = await self.collection.update_one(
                {"_id": ticket_id},
                {"$set": update_dict}
            )
            
            if result.modified_count > 0:
                return await self.get_ticket(ticket_id)
                
            return None
            
        except Exception as e:
            logger.error(f"Failed to update ticket {ticket_id}: {e}")
            return None
    
    async def add_message(
        self, 
        ticket_id: str, 
        author_id: str,
        author_name: str,
        content: str,
        author_type: str = "user"
    ) -> bool:
        """Add a message to a ticket"""
        try:
            message = TicketMessage(
                author_id=author_id,
                author_name=author_name,
                author_type=author_type,
                content=content
            )
            
            result = await self.collection.update_one(
                {"_id": ticket_id},
                {
                    "$push": {"messages": message.dict()},
                    "$set": {"updated_at": datetime.utcnow()}
                }
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Failed to add message to ticket {ticket_id}: {e}")
            return False
    
    async def reply_to_ticket(
        self, 
        ticket_id: str,
        admin_id: str,
        admin_name: str,
        reply: TicketReply
    ) -> Optional[Ticket]:
        """Admin reply to a ticket"""
        try:
            # Add message
            await self.add_message(
                ticket_id=ticket_id,
                author_id=admin_id,
                author_name=admin_name,
                content=reply.content,
                author_type=reply.author_type
            )
            
            # Update status if needed
            update_data = {}
            if reply.close_ticket:
                update_data["status"] = TicketStatus.CLOSED
                update_data["closed_at"] = datetime.utcnow()
            else:
                # If admin replies, set to waiting_response
                current_ticket = await self.get_ticket(ticket_id)
                if current_ticket and current_ticket.status == TicketStatus.OPEN:
                    update_data["status"] = TicketStatus.WAITING_RESPONSE
                    
            if update_data:
                await self.collection.update_one(
                    {"_id": ticket_id},
                    {"$set": update_data}
                )
                
            return await self.get_ticket(ticket_id)
            
        except Exception as e:
            logger.error(f"Failed to reply to ticket {ticket_id}: {e}")
            return None
    
    async def get_ticket_stats(self) -> Dict[str, Any]:
        """Get ticket statistics"""
        try:
            pipeline = [
                {
                    "$group": {
                        "_id": "$status",
                        "count": {"$sum": 1}
                    }
                }
            ]
            
            status_counts = {}
            async for doc in self.collection.aggregate(pipeline):
                status_counts[doc["_id"]] = doc["count"]
                
            total_tickets = await self.collection.count_documents({})
            
            return {
                "total": total_tickets,
                "by_status": status_counts,
                "open": status_counts.get(TicketStatus.OPEN, 0),
                "in_progress": status_counts.get(TicketStatus.IN_PROGRESS, 0),
                "resolved": status_counts.get(TicketStatus.RESOLVED, 0),
                "closed": status_counts.get(TicketStatus.CLOSED, 0)
            }
            
        except Exception as e:
            logger.error(f"Failed to get ticket stats: {e}")
            return {
                "total": 0,
                "by_status": {},
                "open": 0,
                "in_progress": 0,
                "resolved": 0,
                "closed": 0
            }