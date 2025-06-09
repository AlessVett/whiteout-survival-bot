import asyncio
import os
from fastapi import FastAPI, HTTPException, Header, Depends
from contextlib import asynccontextmanager
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import consul
import subprocess
import signal
import discord
import httpx

bot_process = None
consul_client = None
service_id = "discord-bot-1"

# Models for admin integration
class AdminMessage(BaseModel):
    channel_id: str
    content: str
    admin_name: str
    close_ticket: bool = False

# Simple API key authentication
async def verify_admin_api_key(x_api_key: str = Header(None)):
    """Verify admin panel API key"""
    api_key = os.getenv('DISCORD_BOT_ADMIN_API_KEY', 'admin-integration-key')
    if not x_api_key or x_api_key != api_key:
        raise HTTPException(
            status_code=403,
            detail="Invalid or missing API key"
        )
    return True

@asynccontextmanager
async def lifespan(app: FastAPI):
    global bot_process, consul_client
    
    # Start Discord bot
    bot_process = subprocess.Popen(["python", "main.py"])
    
    # Register with Consul
    consul_host = os.getenv("CONSUL_HOST", "localhost")
    consul_port = int(os.getenv("CONSUL_PORT", "8500"))
    service_port = int(os.getenv("SERVICE_PORT", "8001"))
    
    consul_client = consul.Consul(host=consul_host, port=consul_port)
    
    try:
        await asyncio.to_thread(
            consul_client.agent.service.register,
            name="discord-bot",
            service_id=service_id,
            address="discord-bot",  # Use Docker service name
            port=service_port,
            tags=["bot", "discord", "v1"],
            check=consul.Check.http(f"http://discord-bot:{service_port}/health", interval="10s")
        )
    except Exception as e:
        print(f"Failed to register with Consul: {e}")
    
    yield
    
    # Cleanup
    if bot_process:
        bot_process.terminate()
        bot_process.wait()
    
    if consul_client:
        try:
            await asyncio.to_thread(consul_client.agent.service.deregister, service_id)
        except Exception as e:
            print(f"Failed to deregister from Consul: {e}")

app = FastAPI(lifespan=lifespan)

@app.get("/health")
async def health():
    global bot_process
    if bot_process and bot_process.poll() is None:
        return {"status": "healthy", "service": "discord-bot"}
    return {"status": "unhealthy", "service": "discord-bot", "reason": "bot_process_not_running"}

@app.get("/admin/status")
async def status():
    global bot_process
    return {
        "service": "discord-bot",
        "running": bot_process and bot_process.poll() is None,
        "pid": bot_process.pid if bot_process else None
    }

@app.post("/admin/reload")
async def reload():
    global bot_process
    
    if bot_process:
        bot_process.terminate()
        bot_process.wait()
        bot_process.wait()

    bot_process = subprocess.Popen(["python", "main.py"])
    
    return {
        "action": "reload",
        "timestamp": "2025-06-06T15:40:00.000000",
        "success": True,
        "message": "Discord bot reloaded successfully",
        "pid": bot_process.pid
    }

@app.post("/admin/restart")
async def restart():
    global bot_process
    
    if bot_process:
        bot_process.terminate()
        bot_process.wait()
    
    bot_process = subprocess.Popen(["python", "main.py"])
    
    return {
        "action": "restart",
        "timestamp": "2025-06-06T15:40:00.000000", 
        "success": True,
        "message": "Discord bot restarted successfully",
        "pid": bot_process.pid
    }

@app.post("/admin/stop")
async def stop():
    global bot_process
    
    if bot_process:
        bot_process.terminate()
        bot_process.wait()
        bot_process = None
    
    return {
        "action": "stop",
        "timestamp": "2025-06-06T15:40:00.000000",
        "success": True,
        "message": "Discord bot stopped successfully"
    }

@app.post("/send-message")
async def send_message_to_channel(
    message: AdminMessage,
    authenticated: bool = Depends(verify_admin_api_key)
):
    """Send a message from admin to a Discord channel via Discord API"""
    try:
        # Get Discord bot token
        bot_token = os.getenv('DISCORD_TOKEN')
        if not bot_token:
            raise HTTPException(status_code=500, detail="Discord bot token not configured")
        
        # Send message via Discord API
        headers = {
            'Authorization': f'Bot {bot_token}',
            'Content-Type': 'application/json'
        }
        
        # Create embed for admin message
        embed = {
            "description": message.content,
            "color": 16711680,  # Red color for admin messages
            "author": {
                "name": f"Admin Reply - {message.admin_name}"
            },
            "footer": {
                "text": "Reply from Admin Panel"
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        data = {
            "embeds": [embed]
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://discord.com/api/v10/channels/{message.channel_id}/messages",
                headers=headers,
                json=data,
                timeout=10.0
            )
            
            if response.status_code not in [200, 201]:
                error_text = response.text
                try:
                    error_json = response.json()
                    error_detail = error_json.get('message', error_text)
                except:
                    error_detail = error_text
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Discord API error: {error_detail}"
                )
        
        # If close_ticket is True, send closing message and delete channel
        if message.close_ticket:
            await asyncio.sleep(2)  # Small delay
            
            closing_embed = {
                "title": "🔒 Ticket Closed",
                "description": "This ticket has been closed by an administrator.",
                "color": 8421504,  # Gray color
                "timestamp": datetime.utcnow().isoformat()
            }
            
            async with httpx.AsyncClient() as client:
                # Send closing message
                await client.post(
                    f"https://discord.com/api/v10/channels/{message.channel_id}/messages",
                    headers=headers,
                    json={"embeds": [closing_embed]},
                    timeout=10.0
                )
                
                # Send countdown message
                await client.post(
                    f"https://discord.com/api/v10/channels/{message.channel_id}/messages",
                    headers=headers,
                    json={"content": "This channel will be deleted in 10 seconds..."},
                    timeout=10.0
                )
                
                # Wait and delete channel
                await asyncio.sleep(10)
                await client.delete(
                    f"https://discord.com/api/v10/channels/{message.channel_id}",
                    headers=headers,
                    timeout=10.0
                )
        
        return {
            "success": True,
            "message": "Message sent successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))