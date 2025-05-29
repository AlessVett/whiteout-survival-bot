// MongoDB initialization script
// This runs when the MongoDB container is first created

// Switch to admin database to create user
db = db.getSiblingDB('admin');

// Create application user with readWrite permissions
db.createUser({
  user: process.env.MONGO_USER || 'bot_user',
  pwd: process.env.MONGO_PASSWORD || 'change_me_in_production',
  roles: [
    {
      role: 'readWrite',
      db: process.env.MONGO_DB || 'whiteout_survival_crm'
    }
  ]
});

// Switch to application database
db = db.getSiblingDB(process.env.MONGO_DB || 'whiteout_survival_crm');

// Create indexes for better performance
db.users.createIndex({ discord_id: 1 }, { unique: true });
db.users.createIndex({ game_id: 1 });
db.users.createIndex({ alliance: 1 });
db.users.createIndex({ alliance_role: 1 });

db.alliances.createIndex({ name: 1 }, { unique: true });
db.alliances.createIndex({ guild_id: 1 });

db.alliance_channels.createIndex({ alliance: 1, channel_type: 1 }, { unique: true });

db.events.createIndex({ alliance: 1 });
db.events.createIndex({ start_time: 1 });
db.events.createIndex({ active: 1 });

db.communication_channels.createIndex({ alliance: 1 });

print('MongoDB initialization completed successfully');