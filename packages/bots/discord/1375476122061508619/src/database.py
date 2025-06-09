from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
from typing import Optional, Dict, Any
from config import Config

class Database:
    def __init__(self):
        self.client = AsyncIOMotorClient(Config.MONGODB_URI)
        self.db = self.client[Config.MONGODB_DB]
        self.users = self.db.users
        self.alliances = self.db.alliances
        self.events = self.db.events
        self.alliance_channels = self.db.alliance_channels
        self.rules = self.db.rules
        self.automation_logs = self.db.automation_logs
        
    async def create_indexes(self):
        """Crea gli indici necessari per le performance"""
        await self.users.create_index("discord_id", unique=True)
        await self.users.create_index("game_id")
        await self.users.create_index("alliance")
        await self.alliances.create_index("name", unique=True)
        await self.alliances.create_index("guild_id")
        await self.events.create_index([("alliance", 1), ("event_date", 1)])
        await self.events.create_index("next_reminder")
        await self.alliance_channels.create_index([("alliance", 1), ("channel_type", 1)])
        await self.rules.create_index("guild_id")
        await self.automation_logs.create_index("timestamp")
        await self.automation_logs.create_index("guild_id")
        
    async def get_user(self, discord_id: int) -> Optional[Dict[str, Any]]:
        """Ottiene un utente dal database"""
        return await self.users.find_one({"discord_id": discord_id})
    
    async def create_user(self, discord_id: int, discord_name: str) -> Dict[str, Any]:
        """Crea un nuovo utente"""
        user_data = {
            "discord_id": discord_id,
            "discord_name": discord_name,
            "game_id": None,
            "game_nickname": None,
            "alliance": None,
            "alliance_role": None,  # R1, R2, R3, R4, R5
            "alliance_type": None,  # 'alliance', 'no_alliance', 'other_state'
            "language": "en",  # Default to English
            "verified": False,
            "verification_date": None,
            "verification_step": "language_selection",  # Traccia lo step corrente
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "personal_channel_id": None,
            "verification_channel_id": None,
            "stove_lv": None,
            "kid": None
        }
        await self.users.insert_one(user_data)
        return user_data
    
    async def update_user_verification(self, discord_id: int, game_id: str, game_data: Dict) -> bool:
        """Aggiorna i dati di verifica dell'utente"""
        update_data = {
            "game_id": game_id,
            "game_nickname": game_data.get("nickname"),
            "verified": True,
            "verification_date": datetime.utcnow(),
            "stove_lv": game_data.get("stove_lv"),
            "kid": game_data.get("kid"),
            "updated_at": datetime.utcnow()
        }
        
        result = await self.users.update_one(
            {"discord_id": discord_id},
            {"$set": update_data}
        )
        return result.modified_count > 0
    
    async def update_user_alliance(self, discord_id: int, alliance: str = None, 
                                  alliance_role: str = None, alliance_type: str = None) -> bool:
        """Aggiorna l'alleanza dell'utente"""
        update_data = {"updated_at": datetime.utcnow()}
        
        if alliance is not None:
            update_data["alliance"] = alliance
        if alliance_role is not None:
            update_data["alliance_role"] = alliance_role
        if alliance_type is not None:
            update_data["alliance_type"] = alliance_type
            
        result = await self.users.update_one(
            {"discord_id": discord_id},
            {"$set": update_data}
        )
        return result.modified_count > 0
    
    async def update_user_channels(self, discord_id: int, personal_channel_id: int = None, 
                                 verification_channel_id: int = None) -> bool:
        """Aggiorna gli ID dei canali dell'utente"""
        update_data = {"updated_at": datetime.utcnow()}
        
        if personal_channel_id is not None:
            update_data["personal_channel_id"] = personal_channel_id
        if verification_channel_id is not None:
            update_data["verification_channel_id"] = verification_channel_id
            
        result = await self.users.update_one(
            {"discord_id": discord_id},
            {"$set": update_data}
        )
        return result.modified_count > 0
    
    async def update_user_language(self, discord_id: int, language: str) -> bool:
        """Aggiorna la lingua preferita dell'utente"""
        result = await self.users.update_one(
            {"discord_id": discord_id},
            {"$set": {
                "language": language,
                "updated_at": datetime.utcnow()
            }}
        )
        return result.modified_count > 0
    
    async def update_user_verification_step(self, discord_id: int, step: str) -> bool:
        """Aggiorna lo step di verifica corrente dell'utente"""
        result = await self.users.update_one(
            {"discord_id": discord_id},
            {"$set": {
                "verification_step": step,
                "updated_at": datetime.utcnow()
            }}
        )
        return result.modified_count > 0
    
    async def update_user(self, discord_id: int, update_data: Dict[str, Any]) -> bool:
        """Aggiorna i dati dell'utente in modo generico"""
        update_data["updated_at"] = datetime.utcnow()
        result = await self.users.update_one(
            {"discord_id": discord_id},
            {"$set": update_data}
        )
        return result.modified_count > 0
    
    async def get_users_by_alliance(self, alliance: str) -> list:
        """Ottiene tutti gli utenti di un'alleanza"""
        cursor = self.users.find({"alliance": alliance})
        return await cursor.to_list(length=None)
    
    async def create_alliance(self, name: str, guild_id: int, channel_id: int, r5_discord_id: int, language: str = "en") -> Dict[str, Any]:
        """Crea una nuova alleanza"""
        alliance_data = {
            "name": name,
            "guild_id": guild_id,
            "channel_id": channel_id,
            "r5_discord_id": r5_discord_id,
            "language": language,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        await self.alliances.insert_one(alliance_data)
        return alliance_data
    
    async def create_alliance_placeholder(self, name: str, guild_id: int, language: str = "en") -> Dict[str, Any]:
        """Crea un placeholder per alleanza (senza canali, in attesa del primo R5)"""
        alliance_data = {
            "name": name,
            "guild_id": guild_id,
            "channel_id": None,  # Nessun canale ancora
            "r5_discord_id": None,  # Nessun R5 ancora
            "language": language,
            "is_placeholder": True,  # Flag per indicare che è un placeholder
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        await self.alliances.insert_one(alliance_data)
        return alliance_data
    
    async def get_alliance(self, name: str) -> Optional[Dict[str, Any]]:
        """Ottiene un'alleanza dal database"""
        return await self.alliances.find_one({"name": name})
    
    async def get_popular_alliances(self, limit: int = 5) -> list:
        """Ottiene le alleanze più popolari (con più membri)"""
        try:
            # Aggrega per ottenere le alleanze con più membri
            pipeline = [
                {"$match": {"alliance": {"$ne": None, "$ne": ""}}},  # Utenti con alleanza
                {"$group": {"_id": "$alliance", "member_count": {"$sum": 1}}},  # Conta membri per alleanza
                {"$sort": {"member_count": -1}},  # Ordina per numero di membri
                {"$limit": limit},  # Limita i risultati
                {"$project": {"name": "$_id", "member_count": 1, "_id": 0}}  # Proietta il formato desiderato
            ]
            
            cursor = self.users.aggregate(pipeline)
            return await cursor.to_list(length=limit)
        except Exception as e:
            print(f"Error getting popular alliances: {e}")
            return []
    
    async def update_alliance_r5(self, name: str, new_r5_discord_id: int) -> bool:
        """Aggiorna l'R5 di un'alleanza"""
        result = await self.alliances.update_one(
            {"name": name},
            {"$set": {
                "r5_discord_id": new_r5_discord_id,
                "updated_at": datetime.utcnow()
            }}
        )
        return result.modified_count > 0
    
    async def delete_alliance(self, name: str) -> bool:
        """Elimina un'alleanza"""
        result = await self.alliances.delete_one({"name": name})
        return result.deleted_count > 0
    
    async def get_alliance_by_channel(self, channel_id: int) -> Optional[Dict[str, Any]]:
        """Ottiene un'alleanza dal suo canale"""
        return await self.alliances.find_one({"channel_id": channel_id})
    
    async def create_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Crea un nuovo evento"""
        event_data['created_at'] = datetime.utcnow()
        event_data['updated_at'] = datetime.utcnow()
        await self.events.insert_one(event_data)
        return event_data
    
    async def get_alliance_events(self, alliance: str) -> list:
        """Ottiene tutti gli eventi di un'alleanza"""
        cursor = self.events.find({"alliance": alliance}).sort("event_date", 1)
        return await cursor.to_list(length=None)
    
    async def get_pending_reminders(self) -> list:
        """Ottiene tutti i reminder da inviare"""
        now = datetime.utcnow()
        cursor = self.events.find({
            "next_reminder": {"$lte": now},
            "reminder_enabled": True
        })
        return await cursor.to_list(length=None)
    
    async def update_event_reminder(self, event_id: str, next_reminder: datetime) -> bool:
        """Aggiorna il prossimo reminder per un evento"""
        from bson import ObjectId
        result = await self.events.update_one(
            {"_id": ObjectId(event_id)},
            {"$set": {
                "next_reminder": next_reminder,
                "updated_at": datetime.utcnow()
            }}
        )
        return result.modified_count > 0
    
    async def delete_event(self, event_id: str) -> bool:
        """Elimina un evento"""
        from bson import ObjectId
        result = await self.events.delete_one({"_id": ObjectId(event_id)})
        return result.deleted_count > 0
    
    async def save_alliance_channel(self, alliance: str, channel_type: str, channel_id: int) -> Dict[str, Any]:
        """Salva un canale dell'alleanza"""
        channel_data = {
            "alliance": alliance,
            "channel_type": channel_type,
            "channel_id": channel_id,
            "created_at": datetime.utcnow()
        }
        await self.alliance_channels.update_one(
            {"alliance": alliance, "channel_type": channel_type},
            {"$set": channel_data},
            upsert=True
        )
        return channel_data
    
    async def get_alliance_channel(self, alliance: str, channel_type: str) -> Optional[Dict[str, Any]]:
        """Ottiene un canale specifico dell'alleanza"""
        return await self.alliance_channels.find_one({
            "alliance": alliance,
            "channel_type": channel_type
        })
    
    async def get_all_alliance_channels(self, alliance: str) -> list:
        """Ottiene tutti i canali di un'alleanza"""
        cursor = self.alliance_channels.find({"alliance": alliance})
        return await cursor.to_list(length=None)
    
    async def delete_alliance_channels(self, alliance: str) -> int:
        """Elimina tutti i canali di un'alleanza"""
        result = await self.alliance_channels.delete_many({"alliance": alliance})
        return result.deleted_count
    
    async def close(self):
        """Chiude la connessione al database"""
        self.client.close()

# Istanza singleton del database
_db_instance = None

def get_database() -> Database:
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance