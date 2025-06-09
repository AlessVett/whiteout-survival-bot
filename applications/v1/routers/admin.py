"""
Admin Panel API Router for DWOS Infrastructure Management

This module provides comprehensive administrative endpoints for managing
the entire DWOS platform including services, databases, monitoring, and logs.
"""

import asyncio
import json
import os
import psutil
import shutil
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path

from fastapi import APIRouter, HTTPException, Depends, Request, Query
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import aiofiles
import motor.motor_asyncio
from pymongo import MongoClient
import structlog

from configs.settings import settings
from applications.v1.core.log_collector import log_collector
from applications.v1.core.ticket_system import (
    TicketManager, Ticket, TicketCreate, TicketUpdate, TicketReply,
    TicketStatus, TicketPriority
)

logger = structlog.get_logger()

# Security
security = HTTPBearer()

# Templates
templates_dir = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    responses={404: {"description": "Not found"}},
)

# Pydantic models
class ServiceStatus(BaseModel):
    name: str
    status: str
    health: str
    uptime: Optional[str] = None
    cpu_usage: Optional[float] = None
    memory_usage: Optional[float] = None
    last_check: datetime

class DatabaseStats(BaseModel):
    total_users: int
    total_alliances: int
    total_events: int
    verified_users: int
    active_events: int
    database_size: str

class SystemMetrics(BaseModel):
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    network_io: Dict[str, float]
    service_count: int
    uptime: str

class LogEntry(BaseModel):
    timestamp: datetime
    level: str
    service: str
    message: str
    metadata: Optional[Dict] = None

class ServiceAction(BaseModel):
    action: str  # start, stop, restart, reload
    service_name: str

class DatabaseQuery(BaseModel):
    collection: str
    query: Optional[Dict] = {}
    limit: int = 50
    skip: int = 0

# Authentication dependency
async def verify_admin_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify admin authentication token"""
    token = credentials.credentials
    
    # Simple token verification - in production use proper JWT
    if token != settings.admin_token:
        raise HTTPException(
            status_code=403,
            detail="Invalid admin token"
        )
    
    return {"user": "admin", "role": "administrator"}

# Database connection
async def get_database():
    """Get MongoDB connection for the Discord bot"""
    try:
        # Use environment variables directly as fallback
        import os
        mongodb_url = os.getenv('MONGODB_URI', settings.mongodb_url)
        database_name = os.getenv('MONGODB_DB', settings.database_name)
        
        logger.info(f"Attempting to connect to MongoDB: {mongodb_url}, database: {database_name}")
        
        client = motor.motor_asyncio.AsyncIOMotorClient(
            mongodb_url, 
            serverSelectionTimeoutMS=5000
        )
        # Test connection
        await client.server_info()
        database = client[database_name]
        return database
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        return None

@router.get("/", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    """Main admin dashboard page"""
    return templates.TemplateResponse(
        "admin/dashboard.html",
        {
            "request": request,
            "title": "DWOS Admin Panel",
            "version": settings.app_version
        }
    )

@router.get("/api/overview")
async def get_overview(request: Request, admin: dict = Depends(verify_admin_token)):
    """Get system overview with key metrics"""
    try:
        # Get service registry
        service_registry = request.state.service_registry
        
        # Get services status
        services = []
        if service_registry:
            try:
                # Get list of all service names from consul catalog
                _, service_dict = await asyncio.to_thread(service_registry.consul.catalog.services)
                
                for service_name in service_dict:
                    service_instances = await service_registry.get_all_services(service_name)
                    services.extend([
                        {
                            "name": service_name,
                            "id": inst["id"],
                            "address": inst["address"],
                            "port": inst["port"],
                            "status": "healthy"
                        } for inst in service_instances
                    ])
            except Exception as e:
                logger.warning(f"Could not get services from consul: {e}")
        
        # Get database stats
        db = await get_database()
        
        if db is not None:
            try:
                users_count = await db.users.count_documents({})
                verified_users = await db.users.count_documents({"verified": True})
                alliances_count = await db.alliances.count_documents({})
                events_count = await db.events.count_documents({})
                active_events = await db.events.count_documents({"active": True})
            except Exception as e:
                logger.warning(f"Could not get database stats: {e}")
                users_count = verified_users = alliances_count = events_count = active_events = 0
        else:
            users_count = verified_users = alliances_count = events_count = active_events = 0
        
        db_stats = DatabaseStats(
            total_users=users_count,
            total_alliances=alliances_count,
            total_events=events_count,
            verified_users=verified_users,
            active_events=active_events,
            database_size="Unknown"  # TODO: Implement database size calculation
        )
        
        # Get real system metrics
        real_metrics = await get_real_system_metrics()
        
        system_metrics = SystemMetrics(
            cpu_usage=real_metrics["cpu"]["usage_percent"],
            memory_usage=real_metrics["memory"]["usage_percent"],
            disk_usage=real_metrics["disk"]["usage_percent"],
            network_io={
                "in": real_metrics["network"]["bytes_received"] / (1024**2),  # Convert to MB
                "out": real_metrics["network"]["bytes_sent"] / (1024**2)     # Convert to MB
            },
            service_count=len(services),
            uptime=str(datetime.now() - datetime.now().replace(hour=0, minute=0, second=0))
        )
        
        return {
            "services": len(services),
            "healthy_services": len([s for s in services if s.get("status") == "healthy"]),
            "database_stats": db_stats.dict(),
            "system_metrics": system_metrics.dict(),
            "last_updated": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting overview: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/services")
async def get_services_status(request: Request, admin: dict = Depends(verify_admin_token)):
    """Get detailed status of all services"""
    try:
        service_registry = request.state.service_registry
        
        if not service_registry:
            return {"services": [], "message": "Service registry not available"}
        
        # Get all registered services
        all_services = []
        
        try:
            # Get list of all service names from consul catalog
            _, service_dict = await asyncio.to_thread(service_registry.consul.catalog.services)
            
            for service_name in service_dict:
                # Get all instances (healthy and unhealthy)
                _, all_instances = await asyncio.to_thread(
                    service_registry.consul.health.service, service_name
                )
                
                # Get healthy instances
                healthy_instances = await service_registry.get_all_services(service_name)
                healthy_ids = {inst["id"] for inst in healthy_instances}
                
                # Process all instances
                for instance in all_instances:
                    service_data = instance["Service"]
                    is_healthy = service_data["ID"] in healthy_ids
                    
                    all_services.append({
                        "service_name": service_name,
                        "service_id": service_data["ID"],
                        "address": service_data["Address"],
                        "port": service_data["Port"],
                        "tags": service_data.get("Tags", []),
                        "is_healthy": is_healthy
                    })
        except Exception as e:
            logger.warning(f"Could not get services from consul: {e}")
        
        services_status = []
        
        for service in all_services:
            is_healthy = service.get("is_healthy", False)
            
            services_status.append({
                "name": service["service_name"],
                "service_id": service["service_id"],
                "address": service["address"],
                "port": service["port"],
                "status": "running" if is_healthy else "stopped",
                "health": "healthy" if is_healthy else "unhealthy",
                "tags": service.get("tags", []),
                "last_check": datetime.utcnow().isoformat()
            })
        
        return {"services": services_status}
        
    except Exception as e:
        logger.error(f"Error getting services status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/services/action")
async def service_action(
    action: ServiceAction,
    request: Request,
    admin: dict = Depends(verify_admin_token)
):
    """Perform action on a service (start/stop/restart/reload)"""
    try:
        service_proxy = request.state.service_proxy
        
        if not service_proxy:
            raise HTTPException(status_code=503, detail="Service proxy not available")
        
        # Map actions to endpoints
        action_endpoints = {
            "restart": f"/admin/restart",
            "reload": f"/admin/reload",
            "stop": f"/admin/stop",
            "start": f"/admin/start"
        }
        
        if action.action not in action_endpoints:
            raise HTTPException(status_code=400, detail=f"Invalid action: {action.action}")
        
        endpoint = action_endpoints[action.action]
        
        # Send action to service
        try:
            response = await service_proxy.request(action.service_name, "POST", endpoint, json={})
            
            # Extract only serializable data from response
            response_data = {
                "status_code": response.status_code,
                "headers": dict(response.headers),
            }
            
            # Try to get JSON response if available
            try:
                response_data["json"] = response.json()
            except Exception:
                response_data["text"] = response.text
                
        except Exception as e:
            # Service might not have admin endpoints, which is normal
            response_data = {
                "status_code": 404,
                "error": f"Service action endpoint not available: {str(e)}"
            }
        
        return {
            "success": True,
            "action": action.action,
            "service": action.service_name,
            "response": response_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error performing service action: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/database/collections")
async def get_database_collections(admin: dict = Depends(verify_admin_token)):
    """Get list of database collections with document counts"""
    try:
        db = await get_database()
        
        if db is None:
            return {"collections": [], "message": "Database not available"}
        
        collections = await db.list_collection_names()
        collection_info = []
        
        for collection_name in collections:
            try:
                count = await db[collection_name].count_documents({})
                
                # Get sample document for structure
                sample = await db[collection_name].find_one({})
                
                collection_info.append({
                    "name": collection_name,
                    "count": count,
                    "sample_fields": list(sample.keys()) if sample else []
                })
            except Exception as e:
                logger.warning(f"Error getting info for collection {collection_name}: {e}")
                collection_info.append({
                    "name": collection_name,
                    "count": 0,
                    "sample_fields": []
                })
        
        return {"collections": collection_info}
        
    except Exception as e:
        logger.error(f"Error getting database collections: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/database/query")
async def query_database(
    query: DatabaseQuery,
    admin: dict = Depends(verify_admin_token)
):
    """Query database collection with pagination"""
    try:
        db = await get_database()
        
        if db is None:
            raise HTTPException(status_code=503, detail="Database not available")
        
        if query.collection not in await db.list_collection_names():
            raise HTTPException(status_code=404, detail=f"Collection {query.collection} not found")
        
        collection = db[query.collection]
        
        # Execute query with pagination
        cursor = collection.find(query.query).skip(query.skip).limit(query.limit)
        documents = await cursor.to_list(length=query.limit)
        
        # Get total count
        total_count = await collection.count_documents(query.query)
        
        # Convert ObjectId to string for JSON serialization
        for doc in documents:
            if "_id" in doc:
                doc["_id"] = str(doc["_id"])
            # Convert datetime objects to ISO strings
            for key, value in doc.items():
                if isinstance(value, datetime):
                    doc[key] = value.isoformat()
        
        return {
            "collection": query.collection,
            "documents": documents,
            "total_count": total_count,
            "current_page": (query.skip // query.limit) + 1,
            "per_page": query.limit,
            "total_pages": (total_count + query.limit - 1) // query.limit
        }
        
    except Exception as e:
        logger.error(f"Error querying database: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/logs")
async def get_logs(
    service: Optional[str] = Query(None, description="Filter by service"),
    level: Optional[str] = Query(None, description="Filter by log level"),
    limit: int = Query(100, description="Number of log entries to return"),
    since_minutes: int = Query(60, description="Get logs from last N minutes"),
    admin: dict = Depends(verify_admin_token)
):
    """Get system logs with filtering"""
    try:
        # Calculate since timestamp
        since = None
        if since_minutes:
            since = datetime.utcnow() - timedelta(minutes=since_minutes)
        
        # Get logs from collector
        logs = await log_collector.get_logs(
            service=service,
            level=level,
            limit=limit,
            since=since
        )
        
        # Get available services and levels for filtering
        available_services = log_collector.get_service_names()
        available_levels = log_collector.get_log_levels()
        
        return {
            "logs": logs,
            "total": len(logs),
            "filters": {
                "service": service,
                "level": level,
                "since_minutes": since_minutes
            },
            "available_services": available_services,
            "available_levels": available_levels
        }
        
    except Exception as e:
        logger.error(f"Error getting logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def get_real_system_metrics():
    """Get real system metrics using psutil"""
    try:
        # CPU metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        load_avg = psutil.getloadavg() if hasattr(psutil, 'getloadavg') else [0, 0, 0]
        
        # Memory metrics
        memory = psutil.virtual_memory()
        memory_total_gb = memory.total / (1024**3)
        memory_used_gb = memory.used / (1024**3)
        memory_available_gb = memory.available / (1024**3)
        
        # Disk metrics
        disk = psutil.disk_usage('/')
        disk_total_gb = disk.total / (1024**3)
        disk_used_gb = disk.used / (1024**3)
        disk_free_gb = disk.free / (1024**3)
        disk_usage_percent = (disk.used / disk.total) * 100
        
        # Network metrics
        network = psutil.net_io_counters()
        
        return {
            "cpu": {
                "usage_percent": round(cpu_percent, 1),
                "cores": cpu_count,
                "load_average": [round(x, 2) for x in load_avg]
            },
            "memory": {
                "usage_percent": round(memory.percent, 1),
                "total_gb": round(memory_total_gb, 1),
                "used_gb": round(memory_used_gb, 1),
                "available_gb": round(memory_available_gb, 1)
            },
            "disk": {
                "usage_percent": round(disk_usage_percent, 1),
                "total_gb": round(disk_total_gb, 1),
                "used_gb": round(disk_used_gb, 1),
                "available_gb": round(disk_free_gb, 1)
            },
            "network": {
                "bytes_sent": network.bytes_sent,
                "bytes_received": network.bytes_recv,
                "packets_sent": network.packets_sent,
                "packets_received": network.packets_recv
            }
        }
    except Exception as e:
        logger.warning(f"Could not get system metrics: {e}")
        # Fallback to default values
        return {
            "cpu": {"usage_percent": 0, "cores": 1, "load_average": [0, 0, 0]},
            "memory": {"usage_percent": 0, "total_gb": 1, "used_gb": 0, "available_gb": 1},
            "disk": {"usage_percent": 0, "total_gb": 10, "used_gb": 0, "available_gb": 10},
            "network": {"bytes_sent": 0, "bytes_received": 0, "packets_sent": 0, "packets_received": 0}
        }

@router.get("/api/metrics")
async def get_metrics(request: Request, admin: dict = Depends(verify_admin_token)):
    """Get system metrics and performance data"""
    try:
        # Get real system metrics
        system_metrics = await get_real_system_metrics()
        
        # Get service metrics
        service_registry = request.state.service_registry
        services_total = 0
        services_healthy = 0
        
        if service_registry:
            try:
                _, service_dict = await asyncio.to_thread(service_registry.consul.catalog.services)
                services_total = len(service_dict)
                
                for service_name in service_dict:
                    healthy_instances = await service_registry.get_all_services(service_name)
                    if healthy_instances:
                        services_healthy += 1
                        
            except Exception as e:
                logger.warning(f"Could not get service metrics: {e}")
        
        return {
            **system_metrics,
            "services": {
                "total": services_total,
                "healthy": services_healthy,
                "unhealthy": services_total - services_healthy
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/config")
async def get_configuration(admin: dict = Depends(verify_admin_token)):
    """Get current system configuration"""
    try:
        # Return sanitized configuration (excluding sensitive data)
        config = {
            "app_name": settings.app_name,
            "app_version": settings.app_version,
            "environment": getattr(settings, 'environment', 'development'),
            "api_port": settings.api_port,
            "cors_origins": [str(origin) for origin in settings.backend_cors_origins],
            "consul_host": settings.consul_host,
            "consul_port": settings.consul_port,
            "log_format": settings.log_format,
            # Note: Sensitive data like tokens, passwords are excluded
        }
        
        return {"configuration": config}
        
    except Exception as e:
        logger.error(f"Error getting configuration: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def admin_health():
    """Health check endpoint for admin panel"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "admin_panel": "operational"
    }

# Ticket Management Endpoints

@router.get("/api/tickets")
async def get_tickets(
    status: Optional[TicketStatus] = Query(None, description="Filter by status"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    assigned_to: Optional[str] = Query(None, description="Filter by assigned admin"),
    limit: int = Query(50, description="Number of tickets to return"),
    skip: int = Query(0, description="Number of tickets to skip"),
    admin: dict = Depends(verify_admin_token)
):
    """Get tickets with filtering and pagination"""
    try:
        db = await get_database()
        if db is None:
            raise HTTPException(status_code=503, detail="Database not available")
            
        ticket_manager = TicketManager(db)
        tickets = await ticket_manager.get_tickets(
            status=status,
            user_id=user_id,
            assigned_to=assigned_to,
            limit=limit,
            skip=skip
        )
        
        # Convert to dict for JSON serialization
        tickets_data = []
        for ticket in tickets:
            ticket_dict = ticket.dict()
            # Convert datetime objects to ISO strings
            for key, value in ticket_dict.items():
                if isinstance(value, datetime):
                    ticket_dict[key] = value.isoformat()
            # Handle messages datetime conversion
            for msg in ticket_dict.get("messages", []):
                if isinstance(msg.get("timestamp"), datetime):
                    msg["timestamp"] = msg["timestamp"].isoformat()
            tickets_data.append(ticket_dict)
        
        return {
            "tickets": tickets_data,
            "total": len(tickets_data),
            "filters": {
                "status": status,
                "user_id": user_id,
                "assigned_to": assigned_to
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting tickets: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/tickets/{ticket_id}")
async def get_ticket(
    ticket_id: str,
    admin: dict = Depends(verify_admin_token)
):
    """Get a specific ticket by ID"""
    try:
        db = await get_database()
        if db is None:
            raise HTTPException(status_code=503, detail="Database not available")
            
        ticket_manager = TicketManager(db)
        ticket = await ticket_manager.get_ticket(ticket_id)
        
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")
            
        # Convert to dict for JSON serialization
        ticket_dict = ticket.dict()
        for key, value in ticket_dict.items():
            if isinstance(value, datetime):
                ticket_dict[key] = value.isoformat()
        # Handle messages datetime conversion
        for msg in ticket_dict.get("messages", []):
            if isinstance(msg.get("timestamp"), datetime):
                msg["timestamp"] = msg["timestamp"].isoformat()
                
        return {"ticket": ticket_dict}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting ticket {ticket_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/api/tickets/{ticket_id}")
async def update_ticket(
    ticket_id: str,
    update_data: TicketUpdate,
    admin: dict = Depends(verify_admin_token)
):
    """Update a ticket"""
    try:
        db = await get_database()
        if db is None:
            raise HTTPException(status_code=503, detail="Database not available")
            
        ticket_manager = TicketManager(db)
        updated_ticket = await ticket_manager.update_ticket(ticket_id, update_data)
        
        if not updated_ticket:
            raise HTTPException(status_code=404, detail="Ticket not found or not updated")
            
        # Convert to dict for JSON serialization
        ticket_dict = updated_ticket.dict()
        for key, value in ticket_dict.items():
            if isinstance(value, datetime):
                ticket_dict[key] = value.isoformat()
        # Handle messages datetime conversion
        for msg in ticket_dict.get("messages", []):
            if isinstance(msg.get("timestamp"), datetime):
                msg["timestamp"] = msg["timestamp"].isoformat()
                
        return {
            "success": True,
            "ticket": ticket_dict,
            "message": "Ticket updated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating ticket {ticket_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/tickets/{ticket_id}/reply")
async def reply_to_ticket(
    ticket_id: str,
    reply: TicketReply,
    admin: dict = Depends(verify_admin_token)
):
    """Reply to a ticket"""
    try:
        db = await get_database()
        if db is None:
            raise HTTPException(status_code=503, detail="Database not available")
            
        ticket_manager = TicketManager(db)
        
        # Use admin info from token
        admin_id = admin.get("user", "admin")
        admin_name = f"Admin ({admin_id})"
        
        updated_ticket = await ticket_manager.reply_to_ticket(
            ticket_id=ticket_id,
            admin_id=admin_id,
            admin_name=admin_name,
            reply=reply
        )
        
        if not updated_ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")
            
        # Send message to Discord channel if channel_id exists
        ticket = await ticket_manager.get_ticket(ticket_id)
        if ticket and ticket.channel_id:
            await send_message_to_discord_channel(
                ticket.channel_id,
                reply.content,
                admin_name,
                is_admin=True,
                close_ticket=reply.close_ticket
            )
        
        # Convert to dict for JSON serialization
        ticket_dict = updated_ticket.dict()
        for key, value in ticket_dict.items():
            if isinstance(value, datetime):
                ticket_dict[key] = value.isoformat()
        # Handle messages datetime conversion
        for msg in ticket_dict.get("messages", []):
            if isinstance(msg.get("timestamp"), datetime):
                msg["timestamp"] = msg["timestamp"].isoformat()
                
        return {
            "success": True,
            "ticket": ticket_dict,
            "message": "Reply sent successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error replying to ticket {ticket_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/tickets-stats")
async def get_ticket_stats(admin: dict = Depends(verify_admin_token)):
    """Get ticket statistics"""
    try:
        db = await get_database()
        if db is None:
            raise HTTPException(status_code=503, detail="Database not available")
            
        ticket_manager = TicketManager(db)
        stats = await ticket_manager.get_ticket_stats()
        
        return {
            "stats": stats,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting ticket stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/tickets/create")
async def create_ticket_from_discord(
    ticket_data: TicketCreate,
    admin: dict = Depends(verify_admin_token)
):
    """Create a new ticket from Discord bot"""
    try:
        db = await get_database()
        if db is None:
            raise HTTPException(status_code=503, detail="Database not available")
            
        ticket_manager = TicketManager(db)
        ticket = await ticket_manager.create_ticket(ticket_data)
        
        # Convert to dict for JSON serialization
        ticket_dict = ticket.dict()
        for key, value in ticket_dict.items():
            if isinstance(value, datetime):
                ticket_dict[key] = value.isoformat()
        # Handle messages datetime conversion
        for msg in ticket_dict.get("messages", []):
            if isinstance(msg.get("timestamp"), datetime):
                msg["timestamp"] = msg["timestamp"].isoformat()
        
        logger.info(f"Created ticket {ticket.ticket_id} from Discord for user {ticket.user_name}")
        
        return {
            "success": True,
            "ticket": ticket_dict,
            "message": f"Ticket {ticket.ticket_id} created successfully"
        }
        
    except Exception as e:
        logger.error(f"Error creating ticket from Discord: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/api/tickets/{ticket_id}/channel")
async def update_ticket_channel(
    ticket_id: str,
    channel_data: dict,
    admin: dict = Depends(verify_admin_token)
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
            
        return {
            "success": True,
            "message": "Ticket channel updated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating ticket channel: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Discord Integration Functions

async def send_message_to_discord_channel(
    channel_id: str,
    message: str,
    author_name: str,
    is_admin: bool = True,
    close_ticket: bool = False
):
    """Send a message to Discord channel via bot API"""
    try:
        import httpx
        
        # Get Discord bot API configuration
        bot_api_url = os.getenv('DISCORD_BOT_API_URL', 'http://discord-bot:8001')
        api_key = os.getenv('DISCORD_BOT_ADMIN_API_KEY', 'admin-integration-key')
        
        # Prepare the request
        headers = {
            'X-API-Key': api_key,
            'Content-Type': 'application/json'
        }
        
        data = {
            'channel_id': channel_id,
            'content': message,
            'admin_name': author_name,
            'close_ticket': close_ticket
        }
        
        # Send the message to Discord bot API
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{bot_api_url}/send-message",
                headers=headers,
                json=data,
                timeout=10.0
            )
            
            if response.status_code != 200:
                logger.error(f"Failed to send message to Discord: {response.status_code} - {response.text}")
                return False
                
            logger.info(f"Admin message sent to Discord channel {channel_id}")
            return True
            
    except Exception as e:
        logger.error(f"Error sending message to Discord: {e}")
        return False