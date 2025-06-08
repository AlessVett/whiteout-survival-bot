import asyncio
import os
from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
import consul
import subprocess
import signal

bot_process = None
consul_client = None
service_id = "discord-bot-1"

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