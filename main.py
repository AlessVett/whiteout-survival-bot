import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import structlog
from prometheus_client import make_asgi_app

from configs.settings import settings
from applications.v1.core.service_discovery import ServiceRegistry, ServiceProxy
from applications.v1.core.message_queue import MessageBroker, EventBus
from applications.v1.routers import health, services, admin, service_admin, tickets
from applications.v1.core.log_processor import configure_logging

# Configure structured logging with log collector
configure_logging(service_name="api-gateway")

logger = structlog.get_logger()

# Global instances
service_registry: ServiceRegistry = None
service_proxy: ServiceProxy = None
message_broker: MessageBroker = None
event_bus: EventBus = None

# Rate limiting
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    global service_registry, service_proxy, message_broker, event_bus
    
    logger.info("Starting DWOS API Gateway", version=settings.app_version)
    
    # Initialize service registry
    service_registry = ServiceRegistry(settings.consul_host, settings.consul_port)
    service_proxy = ServiceProxy(service_registry)
    
    # Initialize message broker
    message_broker = MessageBroker(settings.rabbitmq_url)
    try:
        await message_broker.connect()
        event_bus = EventBus(message_broker)
        logger.info("Connected to RabbitMQ")
    except Exception as e:
        logger.warning(f"Could not connect to RabbitMQ: {e}")
        event_bus = None
    
    # Register API Gateway itself
    try:
        await service_registry.register_service(
            name="api-gateway",
            service_id="api-gateway-1",
            address="api-gateway",  # Use Docker service name
            port=settings.api_port,
            tags=["gateway", "api", "v1"]
        )
        # Start health check
        await service_registry.start_health_check()
    except Exception as e:
        logger.warning(f"Could not register with Consul: {e}")
    
    # Start event bus if available
    if event_bus:
        try:
            await event_bus.start()
        except Exception as e:
            logger.warning(f"Could not start event bus: {e}")
    
    logger.info("API Gateway started successfully")
    
    yield
    
    # Cleanup
    logger.info("Shutting down API Gateway")
    
    try:
        await service_registry.stop_health_check()
    except Exception as e:
        logger.warning(f"Error stopping health check: {e}")
    
    await service_proxy.close()
    
    if message_broker and message_broker.connection:
        try:
            await message_broker.disconnect()
        except Exception as e:
            logger.warning(f"Error disconnecting from RabbitMQ: {e}")
    
    try:
        await service_registry.deregister_service("api-gateway-1")
    except Exception as e:
        logger.warning(f"Could not deregister from Consul: {e}")
    
    logger.info("API Gateway shutdown complete")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[str(origin) for origin in settings.backend_cors_origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add rate limit error handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Mount Prometheus metrics
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# Mount static files for admin panel
app.mount("/static", StaticFiles(directory="applications/v1/static"), name="static")

# Dependency injection functions
def get_service_registry(request: Request):
    return request.state.service_registry

def get_service_proxy(request: Request):
    return request.state.service_proxy

# Include routers
app.include_router(health.router, prefix=settings.api_v1_str)
app.include_router(services.router, prefix=settings.api_v1_str)
app.include_router(admin.router)
app.include_router(service_admin.router)
app.include_router(tickets.router)

# Dependency injection
@app.middleware("http")
async def inject_dependencies(request: Request, call_next):
    """Inject dependencies into request state"""
    request.state.service_registry = service_registry
    request.state.service_proxy = service_proxy
    request.state.message_broker = message_broker
    request.state.event_bus = event_bus
    
    response = await call_next(request)
    return response


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "docs": "/api/docs"
    }


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )