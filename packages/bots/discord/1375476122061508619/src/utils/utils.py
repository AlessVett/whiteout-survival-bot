import hashlib

import aiohttp
import discord
from typing import Optional
from src.config import Config
import time


async def verify_game_id(game_id: str) -> tuple[bool, Optional[dict]]:
    """Verifica se un ID di gioco esiste tramite API e restituisce i dati"""
    try:
        async with aiohttp.ClientSession() as session:
            sign_time = str(time.time() * 1000).split('.')[0]
            sign = hashlib.md5(b'fid=' + game_id.encode() + b'&time=' + sign_time.encode() + b'tB87#kPtkxqOS2').hexdigest()
            form_data = {
                "sign": sign,
                "fid": game_id,
                "time": sign_time,
            }

            async with session.post(f"{Config.GAME_API_URL}", data=form_data) as response:
                print(f"Status code: {response.status}")
                print(f"Response headers: {response.headers}")
                if response.status == 200:
                    try:
                        data = await response.json()
                        print(f"Response data: {data}")
                        
                        if data.get("code") == 0 and data.get("msg") == "success":
                            print("API verification successful!")
                            return True, data.get("data", {})
                        else:
                            print(f"API returned error - code: {data.get('code')}, msg: {data.get('msg')}")
                            return False, None
                    except Exception as json_error:
                        print(f"Failed to parse JSON response: {json_error}")
                        response_text = await response.text()
                        print(f"Raw response: {response_text}")
                        return False, None
                else:
                    print(f"HTTP error: {response.status}")
                    return False, None
    except Exception as e:
        print(f"Errore durante la verifica dell'ID di gioco: {e}")
        return False, None


async def get_or_create_role(guild: discord.Guild, role_name: str) -> discord.Role:
    """Ottiene un ruolo esistente o lo crea se non esiste"""
    role = discord.utils.get(guild.roles, name=role_name)
    if not role:
        role = await guild.create_role(
            name=role_name,
            color=discord.Color.random(),
            mentionable=True
        )
    return role


async def setup_member_channel(guild: discord.Guild, member: discord.Member, category_name: str,
                               channel_name: str) -> discord.TextChannel:
    """Crea un canale dedicato per un membro in una categoria specifica"""
    # Trova o crea la categoria
    category = discord.utils.get(guild.categories, name=category_name)
    if not category:
        category = await guild.create_category(category_name)

    # Crea il canale con permessi speciali
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        member: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_messages=True)
    }

    channel = await guild.create_text_channel(
        name=channel_name,
        category=category,
        overwrites=overwrites
    )

    return channel
