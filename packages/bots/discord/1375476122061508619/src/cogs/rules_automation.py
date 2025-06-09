"""
Rules Automation Cog for Discord Bot

Monitors the "rules" channel and automatically sends rules when it's empty.
Provides admin commands for managing rules content and automation settings.

Features:
- Automatic detection of empty "rules" channel
- Scheduled rules messaging
- Rules content management with default rules
- Registration process explanation
- Admin controls for automation settings
"""

import discord
from discord.ext import commands, tasks
from discord import app_commands
from typing import Optional, Dict, Any
import logging
from datetime import datetime, timedelta

from src.cogs.base import BaseCog


class RulesAutomationCog(BaseCog):
    """
    Cog for handling rules automation for the "rules" channel.
    
    Monitors the rules channel and automatically sends rules when empty.
    """
    
    def __init__(self, bot: commands.Bot) -> None:
        """Initialize the Rules Automation cog."""
        super().__init__(bot)
        self.rules_check_interval = 5  # 5 minutes
        self.automation_enabled = True
        self.rules_channel_name = "rules"
        
    async def cog_load(self):
        """Called when the cog is loaded."""
        self.logger.info("Rules Automation Cog loaded")
        # Add rules collection to database
        self.rules = self.db.db.rules
        self.automation_logs = self.db.db.automation_logs
        
        # Create indexes for rules collection
        await self._create_rules_indexes()
        
        # Start automation task
        if self.automation_enabled:
            self.rules_automation_task.start()
    
    async def cog_unload(self):
        """Called when the cog is unloaded."""
        self.rules_automation_task.cancel()
    
    async def _create_rules_indexes(self):
        """Create database indexes for rules collections."""
        try:
            await self.rules.create_index("guild_id")
            await self.automation_logs.create_index("timestamp")
            await self.automation_logs.create_index("guild_id")
            self.logger.info("Rules indexes created successfully")
        except Exception as e:
            self.logger.error(f"Failed to create rules indexes: {e}")
    
    @tasks.loop(minutes=5)
    async def rules_automation_task(self):
        """Periodic task to check rules channels."""
        await self._check_rules_channel()
    
    @rules_automation_task.before_loop
    async def before_rules_automation_task(self):
        """Wait until bot is ready before starting the task."""
        await self.bot.wait_until_ready()
    
    async def _check_rules_channel(self):
        """Check all guilds for empty rules channel and send rules if needed."""
        self.logger.info("Checking rules channels...")
        
        for guild in self.bot.guilds:
            try:
                await self._check_guild_rules_channel(guild)
            except Exception as e:
                self.logger.error(f"Error checking rules for guild {guild.id}: {e}")
    
    async def _check_guild_rules_channel(self, guild: discord.Guild):
        """Check a specific guild's rules channel and send rules if empty."""
        # Find the "rules" channel
        rules_channel = discord.utils.get(guild.text_channels, name=self.rules_channel_name)
        
        if not rules_channel:
            self.logger.info(f"No 'rules' channel found in guild {guild.id}")
            return
        
        try:
            # Check if channel has recent messages (last 24 hours)
            cutoff_time = datetime.utcnow() - timedelta(hours=24)
            recent_messages = []
            
            async for message in rules_channel.history(limit=10, after=cutoff_time):
                if not message.author.bot:  # Ignore bot messages
                    recent_messages.append(message)
            
            # If no recent human messages, send rules
            if not recent_messages:
                await self._send_rules_to_channel(rules_channel, guild.id)
                
        except discord.Forbidden:
            self.logger.warning(f"No permission to read rules channel in guild {guild.id}")
        except Exception as e:
            self.logger.error(f"Error checking rules channel in guild {guild.id}: {e}")
    
    async def _send_rules_to_channel(self, channel: discord.TextChannel, guild_id: int):
        """Send rules message to the rules channel."""
        try:
            # Get rules content for this guild
            rules_data = await self.get_guild_rules(guild_id)
            
            if not rules_data:
                # Use default rules if none configured
                rules_data = self._get_default_rules()
            
            # Create embed for rules
            embed = discord.Embed(
                title=rules_data.get('title', '🔰 Server Rules'),
                description=rules_data.get('content', 'No rules configured yet.'),
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            
            # Add footer
            embed.set_footer(text="Automated Rules Message • DWOS Bot")
            
            # Send rules message
            await channel.send(embed=embed)
            
            # Log the action
            await self._log_automation_action(
                guild_id=guild_id,
                channel_id=channel.id,
                action="rules_sent",
                details=f"Sent rules to #{channel.name} (empty channel detected)"
            )
            
            self.logger.info(f"Sent rules to #{channel.name} in guild {guild_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to send rules to channel {channel.id}: {e}")
    
    async def get_guild_rules(self, guild_id: int) -> Optional[Dict[str, Any]]:
        """Get rules content for a specific guild."""
        return await self.rules.find_one({"guild_id": guild_id})
    
    def _get_default_rules(self) -> Dict[str, Any]:
        """Get default rules content."""
        return {
            "title": "🔰 WhiteOut Survival Discord Server Rules",
            "content": """
**Welcome to the WhiteOut Survival Discord Server!**

Please follow these rules to maintain a positive and helpful community environment:

## 📋 General Rules

**1. Be Respectful**
• Treat all members with kindness and respect
• No harassment, bullying, or toxic behavior
• Keep discussions civil and constructive

**2. No Spam or Flooding**
• Avoid excessive messaging or repeated content
• Use appropriate channels for different topics
• No excessive use of caps lock or emojis

**3. Keep Content Appropriate**
• No NSFW, offensive, or inappropriate content
• Use appropriate language at all times
• Respect Discord's Terms of Service and Community Guidelines

**4. English Only**
• Please communicate in English in all channels
• This helps maintain clear communication for all members

## 🎮 Game-Related Rules

**5. Game Information Sharing**
• Share Game IDs only in designated channels
• Be helpful to new and existing players
• No selling or trading of accounts

**6. Alliance Coordination**
• Coordinate attacks and defenses properly with your alliance
• Support your alliance members when possible
• Follow your alliance leadership's guidance

**7. No Cheating or Exploits**
• Do not discuss or promote cheating methods
• Report any suspicious activity to moderators
• Play fair and maintain the integrity of the game

## 🛡️ Registration Process

**To get verified and access all server features:**

1. **Start Registration**: Use the `/start` command
2. **Select Language**: Choose your preferred language
3. **Provide Game ID**: Enter your WhiteOut Survival Game ID (found in game settings)
4. **Alliance Selection**: Choose your alliance status
5. **Verification**: Bot will verify your data and assign appropriate roles

## 📞 Support & Help

• Create a support ticket if you need assistance
• Contact moderators for rule violations or issues
• Use `/registration-help` for detailed registration guidance

**Violation of these rules may result in warnings, temporary mutes, or permanent bans depending on severity.**

*Thank you for helping us maintain a great community!*
            """
        }
    
    async def _log_automation_action(self, guild_id: int, channel_id: int, action: str, details: str):
        """Log automation actions to database."""
        log_entry = {
            "guild_id": guild_id,
            "channel_id": channel_id,
            "action": action,
            "details": details,
            "timestamp": datetime.utcnow()
        }
        await self.automation_logs.insert_one(log_entry)
    
    @app_commands.command(name="rules-set", description="Set or update server rules content")
    @app_commands.default_permissions(administrator=True)
    async def set_rules(self, interaction: discord.Interaction, *, content: str):
        """Set rules content for the current server."""
        try:
            await interaction.response.defer(ephemeral=True)
            
            # Update or create rules for this guild
            result = await self.rules.update_one(
                {"guild_id": interaction.guild.id},
                {
                    "$set": {
                        "title": "🔰 Server Rules",
                        "content": content,
                        "updated_by": interaction.user.id,
                        "updated_at": datetime.utcnow()
                    }
                },
                upsert=True
            )
            
            await interaction.followup.send(
                "✅ Rules have been updated successfully!",
                ephemeral=True
            )
            
            self.logger.info(f"Rules updated for guild {interaction.guild.id} by user {interaction.user.id}")
            
        except Exception as e:
            await self.handle_cog_error(interaction, e)
    
    @app_commands.command(name="rules-show", description="Show current server rules")
    async def show_rules(self, interaction: discord.Interaction):
        """Display current server rules."""
        try:
            rules_data = await self.get_guild_rules(interaction.guild.id)
            
            if not rules_data:
                rules_data = self._get_default_rules()
            
            embed = discord.Embed(
                title=rules_data.get('title', 'Server Rules'),
                description=rules_data.get('content', 'No rules configured.'),
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            
            embed.set_footer(text="Use /rules-set to update rules")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            await self.handle_cog_error(interaction, e)
    
    @app_commands.command(name="registration-help", description="Explain the registration process")
    async def registration_help(self, interaction: discord.Interaction):
        """Provide detailed explanation of the registration process."""
        try:
            embed = discord.Embed(
                title="📋 Registration Process Guide",
                description="Learn how to register and link your WhiteOut Survival account",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            
            embed.add_field(
                name="🚀 Step 1: Start Registration",
                value="Use the `/start` command to begin the verification process",
                inline=False
            )
            
            embed.add_field(
                name="🌐 Step 2: Select Language",
                value="Choose your preferred language for bot interactions",
                inline=False
            )
            
            embed.add_field(
                name="🎮 Step 3: Provide Game ID",
                value="Enter your WhiteOut Survival Game ID (found in game settings → profile)",
                inline=False
            )
            
            embed.add_field(
                name="🏰 Step 4: Alliance Selection",
                value="Choose your alliance type:\n• **Alliance Member** - You belong to an alliance\n• **No Alliance** - You play without an alliance\n• **Other State** - You're from a different state",
                inline=False
            )
            
            embed.add_field(
                name="✅ Step 5: Verification",
                value="The bot will verify your game data and assign appropriate roles automatically",
                inline=False
            )
            
            embed.add_field(
                name="🔧 What Happens After Verification?",
                value="• You'll get access to alliance-specific channels\n• Your game level and stats will be displayed\n• You can participate in alliance activities\n• Access to exclusive bot features",
                inline=False
            )
            
            embed.add_field(
                name="❓ Having Issues?",
                value="• Check your Game ID is correct\n• Ensure your game profile is public\n• Create a support ticket for help\n• Contact moderators if needed",
                inline=False
            )
            
            embed.set_footer(text="DWOS Registration System • Use /start to begin")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            await self.handle_cog_error(interaction, e)
    
    @app_commands.command(name="rules-automation", description="Toggle rules automation on/off")
    @app_commands.default_permissions(administrator=True)
    async def toggle_automation(self, interaction: discord.Interaction, enabled: bool):
        """Toggle rules automation for the server."""
        try:
            await interaction.response.defer(ephemeral=True)
            
            self.automation_enabled = enabled
            
            if enabled:
                if not self.rules_automation_task.is_running():
                    self.rules_automation_task.start()
                message = "✅ Rules automation has been **enabled**"
            else:
                if self.rules_automation_task.is_running():
                    self.rules_automation_task.cancel()
                message = "❌ Rules automation has been **disabled**"
            
            await interaction.followup.send(message, ephemeral=True)
            
            self.logger.info(f"Rules automation {'enabled' if enabled else 'disabled'} for guild {interaction.guild.id}")
            
        except Exception as e:
            await self.handle_cog_error(interaction, e)
    
    @app_commands.command(name="rules-logs", description="View recent automation logs")
    @app_commands.default_permissions(administrator=True)
    async def view_logs(self, interaction: discord.Interaction, limit: int = 10):
        """View recent automation logs for this server."""
        try:
            await interaction.response.defer(ephemeral=True)
            
            # Get recent logs for this guild
            logs = await self.automation_logs.find(
                {"guild_id": interaction.guild.id}
            ).sort("timestamp", -1).limit(limit).to_list(length=limit)
            
            if not logs:
                await interaction.followup.send("No automation logs found.", ephemeral=True)
                return
            
            embed = discord.Embed(
                title="📊 Rules Automation Logs",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            
            for log in logs:
                timestamp = log['timestamp'].strftime("%Y-%m-%d %H:%M:%S")
                embed.add_field(
                    name=f"{log['action']} - {timestamp}",
                    value=log['details'],
                    inline=False
                )
            
            embed.set_footer(text=f"Showing last {len(logs)} entries")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            await self.handle_cog_error(interaction, e)
    
    @app_commands.command(name="rules-send-now", description="Manually send rules to the rules channel")
    @app_commands.default_permissions(administrator=True)
    async def send_rules_now(self, interaction: discord.Interaction):
        """Manually send rules to the rules channel."""
        try:
            await interaction.response.defer(ephemeral=True)
            
            # Find the rules channel
            rules_channel = discord.utils.get(interaction.guild.text_channels, name=self.rules_channel_name)
            
            if not rules_channel:
                await interaction.followup.send(
                    f"❌ Channel '#{self.rules_channel_name}' not found!",
                    ephemeral=True
                )
                return
            
            # Send rules to channel
            await self._send_rules_to_channel(rules_channel, interaction.guild.id)
            
            await interaction.followup.send(
                f"✅ Rules sent successfully to #{self.rules_channel_name}!",
                ephemeral=True
            )
            
        except Exception as e:
            await self.handle_cog_error(interaction, e)


async def setup(bot: commands.Bot):
    """Setup function to load the cog."""
    await bot.add_cog(RulesAutomationCog(bot))