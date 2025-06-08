"""
Log Processor for structlog integration

This module integrates with structlog to capture all logs and send them
to the log collector for centralized storage and retrieval.
"""

import asyncio
from datetime import datetime
from typing import Dict, Any
import structlog
from applications.v1.core.log_collector import log_collector

class LogProcessor:
    """Process structlog events and send to collector"""
    
    def __init__(self, service_name: str = "api-gateway"):
        self.service_name = service_name
        
    def __call__(self, logger, method_name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Process log event from structlog"""
        # Extract log data
        level = method_name.upper()
        message = event_dict.get("event", "")
        
        # Create log entry
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level,
            "service": self.service_name,
            "message": message,
            "metadata": {}
        }
        
        # Add metadata from event_dict
        for key, value in event_dict.items():
            if key not in ["event", "timestamp", "level"]:
                log_entry["metadata"][key] = str(value)
        
        # Send to collector asynchronously
        asyncio.create_task(self._send_to_collector(log_entry))
        
        return event_dict
        
    async def _send_to_collector(self, log_entry: Dict[str, Any]):
        """Send log entry to collector"""
        try:
            await log_collector.add_log(log_entry)
        except Exception:
            # Silently fail to avoid recursion
            pass

def configure_logging(service_name: str = "api-gateway"):
    """Configure structlog to use our log processor"""
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            LogProcessor(service_name),  # Our custom processor
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )