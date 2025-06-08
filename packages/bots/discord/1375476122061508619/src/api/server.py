"""
Discord Bot API Server for DWOS Admin Management

This module provides HTTP endpoints for managing the Discord bot
from the DWOS admin panel.
"""

import asyncio
import os
import sys
import signal
from datetime import datetime
from typing import Optional
import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Bot instance reference
bot_instance: Optional['CRMBot'] = None

# Create FastAPI app
app = FastAPI(
    title="Discord Bot API",
    description="API endpoints for managing the Discord bot",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "discord-bot",
        "status": "running",
        "version": "1.0.0",
        "bot_status": "online" if bot_instance and bot_instance.is_ready() else "offline"
    }

@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint for service discovery"""
    bot_ready = bot_instance and bot_instance.is_ready()
    
    return {
        "status": "healthy" if bot_ready else "unhealthy",
        "service": "discord-bot",
        "timestamp": datetime.utcnow().isoformat(),
        "bot_connected": bot_ready,
        "guild_count": len(bot_instance.guilds) if bot_instance else 0
    }

@app.get("/status")
async def get_status():
    """Get detailed bot status"""
    if not bot_instance:
        return {
            "status": "not_started",
            "bot_ready": False,
            "uptime": 0,
            "guilds": 0,
            "users": 0
        }
    
    return {
        "status": "running" if bot_instance.is_ready() else "starting",
        "bot_ready": bot_instance.is_ready(),
        "user_id": bot_instance.user.id if bot_instance.user else None,
        "username": str(bot_instance.user) if bot_instance.user else None,
        "guilds": len(bot_instance.guilds),
        "users": sum(guild.member_count for guild in bot_instance.guilds),
        "latency": round(bot_instance.latency * 1000, 2),  # ms
        "cogs_loaded": len(bot_instance.cogs),
        "cog_names": list(bot_instance.cogs.keys())
    }

@app.post("/admin/restart")
async def restart_bot():
    """Restart the Discord bot"""
    try:
        if bot_instance:
            # Gracefully close the bot
            await bot_instance.close()
            
            # Wait a moment for cleanup
            await asyncio.sleep(2)
            
            # The bot should automatically restart due to the Docker restart policy
            # or supervisor process, so we just need to close it properly
            
            return {
                "success": True,
                "action": "restart",
                "message": "Bot restart initiated",
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            return {
                "success": False,
                "action": "restart", 
                "message": "Bot instance not found",
                "timestamp": datetime.utcnow().isoformat()
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to restart bot: {str(e)}")

@app.post("/admin/reload")
async def reload_cogs():
    """Reload all bot cogs"""
    try:
        if not bot_instance:
            raise HTTPException(status_code=503, detail="Bot not available")
        
        reloaded_cogs = []
        failed_cogs = []
        
        # Get list of loaded cogs
        cog_names = list(bot_instance.cogs.keys())
        
        for cog_name in cog_names:
            try:
                await bot_instance.reload_extension(cog_name)
                reloaded_cogs.append(cog_name)
            except Exception as e:
                failed_cogs.append({"cog": cog_name, "error": str(e)})
        
        return {
            "success": True,
            "action": "reload",
            "message": f"Reloaded {len(reloaded_cogs)} cogs",
            "reloaded_cogs": reloaded_cogs,
            "failed_cogs": failed_cogs,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reload cogs: {str(e)}")

@app.post("/admin/stop")
async def stop_bot():
    """Stop the Discord bot"""
    try:
        if bot_instance:
            await bot_instance.close()
            
            return {
                "success": True,
                "action": "stop",
                "message": "Bot stopped successfully",
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            return {
                "success": False,
                "action": "stop",
                "message": "Bot instance not found", 
                "timestamp": datetime.utcnow().isoformat()
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stop bot: {str(e)}")

@app.get("/stats")
async def get_stats():
    """Get bot statistics"""
    if not bot_instance:
        raise HTTPException(status_code=503, detail="Bot not available")
    
    try:
        # Get database stats if available
        db_stats = {}
        if hasattr(bot_instance, 'db') and bot_instance.db:
            try:
                db_stats = {
                    "total_users": await bot_instance.db.users.count_documents({}),
                    "verified_users": await bot_instance.db.users.count_documents({"verified": True}),
                    "total_alliances": await bot_instance.db.alliances.count_documents({}),
                    "total_events": await bot_instance.db.events.count_documents({}),
                    "active_events": await bot_instance.db.events.count_documents({"active": True})
                }
            except Exception as e:
                db_stats = {"error": f"Database unavailable: {str(e)}"}
        
        return {
            "bot_stats": {
                "guilds": len(bot_instance.guilds),
                "users": sum(guild.member_count for guild in bot_instance.guilds),
                "channels": sum(len(guild.channels) for guild in bot_instance.guilds),
                "latency_ms": round(bot_instance.latency * 1000, 2)
            },
            "database_stats": db_stats,
            "cron_manager": {
                "running": bot_instance.cron_manager.running if bot_instance.cron_manager else False,
                "tasks": len(bot_instance.cron_manager.tasks) if bot_instance.cron_manager else 0
            } if hasattr(bot_instance, 'cron_manager') else None,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")

@app.get("/logs")
async def get_recent_logs():
    """Get recent bot logs"""
    # This would read from log files or in-memory log buffer
    # For now, return a placeholder
    return {
        "logs": [
            {
                "timestamp": datetime.utcnow().isoformat(),
                "level": "INFO",
                "message": "Bot is running normally",
                "module": "discord_bot"
            }
        ],
        "total": 1
    }

def set_bot_instance(bot):
    """Set the bot instance for the API server"""
    global bot_instance
    bot_instance = bot

async def start_api_server(host: str = "0.0.0.0", port: int = 8001):
    """Start the API server"""
    try:
        config = uvicorn.Config(
            app,
            host=host,
            port=port,
            log_level="info",
            access_log=True
        )
        
        server = uvicorn.Server(config)
        
        # Handle graceful shutdown
        def signal_handler(signum, frame):
            logging.info("Received signal to shutdown API server")
            asyncio.create_task(server.shutdown())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        logging.info(f"Starting API server on {host}:{port}")
        await server.serve()
        
    except OSError as e:
        if e.errno == 98:  # Address already in use
            logging.warning(f"Port {port} already in use, API server not started")
            # Don't crash the bot if API server can't start
            return
        else:
            raise e
    except Exception as e:
        logging.error(f"API server error: {e}")
    finally:
        logging.info("API server shutdown complete")

if __name__ == "__main__":
    # For testing the API server standalone
    uvicorn.run(app, host="0.0.0.0", port=8001)