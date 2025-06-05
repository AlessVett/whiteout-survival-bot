from fastapi import APIRouter, Depends, Request
from typing import Dict, Any
import asyncio
from datetime import datetime

from ..core.service_discovery import ServiceRegistry

router = APIRouter(prefix="/health", tags=["health"])


def get_service_registry(request: Request) -> ServiceRegistry:
    return request.state.service_registry


@router.get("")
async def health_check() -> Dict[str, Any]:
    """API Gateway health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "api-gateway"
    }


@router.get("/services")
async def services_health(
    request: Request,
    service_registry: ServiceRegistry = Depends(get_service_registry)
) -> Dict[str, Any]:
    """Get health status of all registered services"""
    if not service_registry:
        return {"error": "Service registry not available"}
    
    services_status = {}
    
    # Get all registered services
    index, services = await asyncio.to_thread(service_registry.consul.catalog.services)
    
    for service_name in services:
        if service_name == "consul":  # Skip consul itself
            continue
            
        instances = await service_registry.get_all_services(service_name)
        services_status[service_name] = {
            "healthy_instances": len(instances),
            "instances": instances
        }
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "services": services_status
    }