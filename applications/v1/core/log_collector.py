"""
Log Collector for DWOS Infrastructure

This module provides centralized log collection and storage functionality,
collecting logs from all services and storing them for retrieval via the admin panel.
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import deque
import aiofiles
from pathlib import Path
import structlog

logger = structlog.get_logger()

class LogCollector:
    """Centralized log collector for all DWOS services"""
    
    def __init__(self, max_logs: int = 10000, retention_hours: int = 24):
        """
        Initialize the log collector
        
        Args:
            max_logs: Maximum number of logs to keep in memory
            retention_hours: Hours to retain logs before cleanup
        """
        self.max_logs = max_logs
        self.retention_hours = retention_hours
        self.logs = deque(maxlen=max_logs)
        self.log_file_path = Path("logs/dwos_admin_logs.jsonl")
        self.log_file_path.parent.mkdir(parents=True, exist_ok=True)
        
    async def add_log(self, log_entry: Dict[str, Any]):
        """
        Add a log entry to the collector
        
        Args:
            log_entry: Dictionary containing log data
        """
        # Ensure required fields
        if "timestamp" not in log_entry:
            log_entry["timestamp"] = datetime.utcnow().isoformat()
        if "level" not in log_entry:
            log_entry["level"] = "INFO"
        if "service" not in log_entry:
            log_entry["service"] = "unknown"
            
        # Add to memory
        self.logs.append(log_entry)
        
        # Write to file asynchronously
        await self._write_to_file(log_entry)
        
    async def _write_to_file(self, log_entry: Dict[str, Any]):
        """Write log entry to file"""
        try:
            async with aiofiles.open(self.log_file_path, "a") as f:
                await f.write(json.dumps(log_entry) + "\n")
        except Exception as e:
            logger.error(f"Failed to write log to file: {e}")
            
    async def get_logs(
        self, 
        service: Optional[str] = None,
        level: Optional[str] = None,
        limit: int = 100,
        since: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve logs with filtering
        
        Args:
            service: Filter by service name
            level: Filter by log level
            limit: Maximum number of logs to return
            since: Get logs since this timestamp
            
        Returns:
            List of log entries
        """
        # First try to get from memory
        logs = list(self.logs)
        
        # If we need more logs or specific time range, read from file
        if len(logs) < limit or since:
            logs = await self._read_from_file(limit * 2, since)
            
        # Apply filters
        if service:
            logs = [log for log in logs if log.get("service") == service]
            
        if level:
            logs = [log for log in logs if log.get("level") == level]
            
        # Sort by timestamp (newest first)
        logs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        # Apply limit
        return logs[:limit]
        
    async def _read_from_file(
        self, 
        limit: int = 1000,
        since: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Read logs from file"""
        logs = []
        
        if not self.log_file_path.exists():
            return logs
            
        try:
            async with aiofiles.open(self.log_file_path, "r") as f:
                lines = await f.readlines()
                
            # Read from end of file (newest logs)
            for line in reversed(lines[-limit:]):
                try:
                    log_entry = json.loads(line.strip())
                    
                    # Check timestamp if needed
                    if since:
                        log_time = datetime.fromisoformat(log_entry.get("timestamp", ""))
                        if log_time < since:
                            break
                            
                    logs.append(log_entry)
                    
                    if len(logs) >= limit:
                        break
                        
                except Exception as e:
                    logger.warning(f"Failed to parse log line: {e}")
                    
        except Exception as e:
            logger.error(f"Failed to read logs from file: {e}")
            
        return logs
        
    async def cleanup_old_logs(self):
        """Remove logs older than retention period"""
        cutoff_time = datetime.utcnow() - timedelta(hours=self.retention_hours)
        
        # Clean memory logs
        while self.logs and self.logs[0].get("timestamp", "") < cutoff_time.isoformat():
            self.logs.popleft()
            
        # Clean file logs (rewrite file without old logs)
        await self._cleanup_file_logs(cutoff_time)
        
    async def _cleanup_file_logs(self, cutoff_time: datetime):
        """Clean up old logs from file"""
        if not self.log_file_path.exists():
            return
            
        try:
            # Read all logs
            logs_to_keep = []
            async with aiofiles.open(self.log_file_path, "r") as f:
                async for line in f:
                    try:
                        log_entry = json.loads(line.strip())
                        log_time = datetime.fromisoformat(log_entry.get("timestamp", ""))
                        
                        if log_time >= cutoff_time:
                            logs_to_keep.append(log_entry)
                            
                    except Exception:
                        pass
                        
            # Rewrite file with filtered logs
            async with aiofiles.open(self.log_file_path, "w") as f:
                for log_entry in logs_to_keep:
                    await f.write(json.dumps(log_entry) + "\n")
                    
        except Exception as e:
            logger.error(f"Failed to cleanup log file: {e}")
            
    def get_service_names(self) -> List[str]:
        """Get unique service names from logs"""
        services = set()
        for log in self.logs:
            if "service" in log:
                services.add(log["service"])
        return sorted(list(services))
        
    def get_log_levels(self) -> List[str]:
        """Get unique log levels from logs"""
        levels = set()
        for log in self.logs:
            if "level" in log:
                levels.add(log["level"])
        return sorted(list(levels))

# Global log collector instance
log_collector = LogCollector()