import asyncio
import json
from typing import Dict, List, Optional
import consul
import httpx
from structlog import get_logger

logger = get_logger()


class ServiceRegistry:
    def __init__(self, consul_host: str, consul_port: int):
        self.consul = consul.Consul(host=consul_host, port=consul_port)
        self.services: Dict[str, Dict] = {}
        self._health_check_task: Optional[asyncio.Task] = None
        
    async def register_service(
        self, 
        name: str, 
        service_id: str,
        address: str, 
        port: int,
        tags: List[str] = None,
        check_interval: str = "10s"
    ):
        """Register a service with Consul"""
        try:
            self.consul.agent.service.register(
                service_id=service_id,
                name=name,
                tags=tags or [],
                address=address,
                port=port,
                check=consul.Check.http(f"http://{address}:{port}/api/v1/health", interval=check_interval)
            )
            logger.info(f"Service registered: {name} ({service_id})")
        except Exception as e:
            logger.error(f"Failed to register service: {e}")
        
    async def deregister_service(self, service_id: str):
        """Deregister a service from Consul"""
        try:
            self.consul.agent.service.deregister(service_id)
            logger.info(f"Service deregistered: {service_id}")
        except Exception as e:
            logger.error(f"Failed to deregister service: {e}")
        
    async def get_service(self, name: str) -> Optional[Dict]:
        """Get a healthy service instance"""
        try:
            _, services = self.consul.health.service(name, passing=True)
            
            if services:
                service = services[0]
                return {
                    "id": service["Service"]["ID"],
                    "address": service["Service"]["Address"],
                    "port": service["Service"]["Port"],
                    "tags": service["Service"]["Tags"],
                }
        except Exception as e:
            logger.error(f"Failed to get service {name}: {e}")
        return None
        
    async def get_all_services(self, name: str) -> List[Dict]:
        """Get all healthy instances of a service"""
        try:
            _, services = self.consul.health.service(name, passing=True)
            
            return [
                {
                    "id": service["Service"]["ID"],
                    "address": service["Service"]["Address"],
                    "port": service["Service"]["Port"],
                    "tags": service["Service"]["Tags"],
                }
                for service in services
            ]
        except Exception as e:
            logger.error(f"Failed to get services {name}: {e}")
            return []
        
    async def watch_services(self):
        """Watch for service changes"""
        index = None
        while True:
            try:
                # Use asyncio.to_thread for blocking consul calls
                index, services = await asyncio.to_thread(
                    self.consul.catalog.services, index=index, wait="30s"
                )
                
                for service_name in services:
                    _, service_instances = await asyncio.to_thread(
                        self.consul.health.service, service_name, passing=True
                    )
                    self.services[service_name] = service_instances
                    
                logger.debug(f"Updated service catalog: {list(services.keys())}")
                
            except Exception as e:
                logger.error(f"Error watching services: {e}")
                await asyncio.sleep(5)
                
    async def start_health_check(self):
        """Start background health check task"""
        if not self._health_check_task:
            self._health_check_task = asyncio.create_task(self.watch_services())
            
    async def stop_health_check(self):
        """Stop background health check task"""
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
            self._health_check_task = None


class ServiceProxy:
    """Proxy for making requests to microservices"""
    
    def __init__(self, service_registry: ServiceRegistry):
        self.registry = service_registry
        self.client = httpx.AsyncClient(timeout=30.0)
        
    async def request(
        self, 
        service_name: str, 
        method: str, 
        path: str,
        **kwargs
    ):
        """Make a request to a microservice"""
        service = await self.registry.get_service(service_name)
        
        if not service:
            raise ValueError(f"Service '{service_name}' not found or unhealthy")
            
        url = f"http://{service['address']}:{service['port']}{path}"
        
        try:
            response = await self.client.request(method, url, **kwargs)
            response.raise_for_status()
            return response
        except httpx.HTTPError as e:
            logger.error(f"Request to {service_name} failed: {e}")
            raise
            
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()