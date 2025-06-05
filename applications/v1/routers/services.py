from fastapi import APIRouter, HTTPException, Depends, Request
from typing import Dict, Any
import httpx

from ..core.service_discovery import ServiceProxy

router = APIRouter(prefix="/services", tags=["services"])


def get_service_proxy(request: Request) -> ServiceProxy:
    return request.state.service_proxy


@router.post("/{service_name}/reload")
async def reload_service(
    service_name: str,
    request: Request,
    service_proxy: ServiceProxy = Depends(get_service_proxy)
) -> Dict[str, Any]:
    """Reload/restart a specific microservice"""
    if not service_proxy:
        raise HTTPException(status_code=503, detail="Service proxy not available")
    
    try:
        # Send reload command to the service
        response = await service_proxy.request(
            service_name,
            "POST",
            "/admin/reload"
        )
        
        return {
            "status": "success",
            "service": service_name,
            "message": f"Service {service_name} reloaded successfully"
        }
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except httpx.HTTPError as e:
        raise HTTPException(status_code=503, detail=f"Failed to reload service: {str(e)}")


@router.get("/{service_name}/status")
async def get_service_status(
    service_name: str,
    request: Request,
    service_proxy: ServiceProxy = Depends(get_service_proxy)
) -> Dict[str, Any]:
    """Get status of a specific microservice"""
    if not service_proxy:
        raise HTTPException(status_code=503, detail="Service proxy not available")
    
    try:
        # Get service status
        response = await service_proxy.request(
            service_name,
            "GET",
            "/admin/status"
        )
        
        return response.json()
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except httpx.HTTPError as e:
        raise HTTPException(status_code=503, detail=f"Failed to get service status: {str(e)}")


@router.api_route("/{service_name}/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_request(
    request: Request,
    service_name: str,
    path: str,
    service_proxy: ServiceProxy = Depends(get_service_proxy)
) -> Any:
    """Proxy requests to microservices"""
    if not service_proxy:
        raise HTTPException(status_code=503, detail="Service proxy not available")
    
    try:
        # Get request body if present
        body = None
        if request.method in ["POST", "PUT", "PATCH"]:
            body = await request.body()
        
        # Forward the request
        response = await service_proxy.request(
            service_name,
            request.method,
            f"/{path}",
            content=body,
            headers={
                key: value for key, value in request.headers.items()
                if key.lower() not in ["host", "content-length"]
            },
            params=dict(request.query_params)
        )
        
        # Return the response
        return response.json()
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except httpx.HTTPError as e:
        raise HTTPException(status_code=503, detail=f"Service request failed: {str(e)}")