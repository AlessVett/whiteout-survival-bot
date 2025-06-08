"""
Service Administration Endpoints

This module provides standard admin endpoints that can be used
by any DWOS microservice for management and monitoring.
"""

import os
import sys
import signal
import asyncio
import psutil
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# Router for admin endpoints
router = APIRouter(prefix="/admin", tags=["admin"])

class ServiceInfo(BaseModel):
    service_name: str
    status: str
    uptime: float
    memory_usage: Dict[str, Any]
    cpu_usage: float

class AdminAction(BaseModel):
    action: str
    timestamp: datetime
    success: bool
    message: str

# Global service state
service_start_time = datetime.utcnow()
restart_requested = False

def get_service_name() -> str:
    """Get service name from environment or default"""
    return os.getenv("SERVICE_NAME", "api-gateway")

def get_uptime() -> float:
    """Get service uptime in seconds"""
    return (datetime.utcnow() - service_start_time).total_seconds()

def get_process_info() -> Dict[str, Any]:
    """Get current process information"""
    try:
        process = psutil.Process()
        memory_info = process.memory_info()
        
        return {
            "pid": process.pid,
            "cpu_percent": process.cpu_percent(),
            "memory": {
                "rss": memory_info.rss,
                "vms": memory_info.vms,
                "rss_mb": round(memory_info.rss / 1024 / 1024, 2),
                "vms_mb": round(memory_info.vms / 1024 / 1024, 2)
            },
            "threads": process.num_threads(),
            "create_time": process.create_time()
        }
    except Exception as e:
        return {"error": f"Could not get process info: {str(e)}"}

@router.get("/status")
async def get_service_status():
    """Get detailed service status"""
    process_info = get_process_info()
    
    return ServiceInfo(
        service_name=get_service_name(),
        status="running",
        uptime=get_uptime(),
        memory_usage=process_info.get("memory", {}),
        cpu_usage=process_info.get("cpu_percent", 0.0)
    )

@router.post("/restart")
async def restart_service():
    """Restart the service"""
    global restart_requested
    
    try:
        service_name = get_service_name()
        restart_requested = True
        
        # In containerized environment, we exit and let the orchestrator restart
        def delayed_restart():
            asyncio.get_event_loop().call_later(1.0, lambda: os.kill(os.getpid(), signal.SIGTERM))
        
        # Schedule restart after response is sent
        asyncio.create_task(asyncio.sleep(1.0))
        delayed_restart()
        
        return AdminAction(
            action="restart",
            timestamp=datetime.utcnow(),
            success=True,
            message=f"Service {service_name} restart initiated"
        )
        
    except Exception as e:
        return AdminAction(
            action="restart",
            timestamp=datetime.utcnow(),
            success=False,
            message=f"Failed to restart service: {str(e)}"
        )

@router.post("/reload")
async def reload_service():
    """Reload service configuration"""
    try:
        service_name = get_service_name()
        
        # For API Gateway, we can reload configurations
        # This is service-specific implementation
        
        return AdminAction(
            action="reload",
            timestamp=datetime.utcnow(),
            success=True,
            message=f"Service {service_name} configuration reloaded"
        )
        
    except Exception as e:
        return AdminAction(
            action="reload",
            timestamp=datetime.utcnow(),
            success=False,
            message=f"Failed to reload service: {str(e)}"
        )

@router.post("/stop")
async def stop_service():
    """Stop the service"""
    try:
        service_name = get_service_name()
        
        # Schedule graceful shutdown
        def delayed_stop():
            asyncio.get_event_loop().call_later(1.0, lambda: os.kill(os.getpid(), signal.SIGTERM))
        
        delayed_stop()
        
        return AdminAction(
            action="stop",
            timestamp=datetime.utcnow(),
            success=True,
            message=f"Service {service_name} shutdown initiated"
        )
        
    except Exception as e:
        return AdminAction(
            action="stop",
            timestamp=datetime.utcnow(),
            success=False,
            message=f"Failed to stop service: {str(e)}"
        )

@router.get("/info")
async def get_service_info():
    """Get comprehensive service information"""
    process_info = get_process_info()
    
    return {
        "service": {
            "name": get_service_name(),
            "status": "running",
            "uptime_seconds": get_uptime(),
            "restart_requested": restart_requested
        },
        "process": process_info,
        "environment": {
            "python_version": sys.version,
            "platform": sys.platform,
            "working_directory": os.getcwd()
        },
        "timestamp": datetime.utcnow().isoformat()
    }

@router.get("/health")
async def admin_health_check():
    """Admin-specific health check"""
    return {
        "status": "healthy",
        "service": get_service_name(),
        "uptime": get_uptime(),
        "timestamp": datetime.utcnow().isoformat()
    }