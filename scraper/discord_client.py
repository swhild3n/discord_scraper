import discord
import asyncio
from typing import Optional, AsyncGenerator, Tuple
from config.settings import settings

class DiscordClientWrapper:
    """Wrapper for Discord API client with authentication and error handling."""
    
    def __init__(self):
        # Configure intents for both bot and user tokens
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        
        self.client = discord.Client(intents=intents)
        self.is_ready = False
        
        # Set up event handlers
        @self.client.event
        async def on_ready():
            print(f'Logged in as {self.client.user} (ID: {self.client.user.id})')
            self.is_ready = True
    
    async def start_client(self):
        """Start the Discord client."""
        token = settings.BOT_TOKEN or settings.USER_TOKEN
        if not token:
            raise ValueError("No Discord token provided. Set DISCORD_BOT_TOKEN or DISCORD_USER_TOKEN")
        
        try:
            # Start client in background
            task = asyncio.create_task(self.client.start(token))
            
            # Wait for client to be ready
            while not self.is_ready:
                await asyncio.sleep(1)
                if task.done():
                    # If task is done but we're not ready, there was an error
                    await task  # This will raise the exception
            
            return task
        except discord.LoginFailure:
            raise ValueError("Invalid Discord token")
        except Exception as e:
            raise RuntimeError(f"Failed to start Discord client: {e}")
    
    async def close(self):
        """Close the Discord client."""
        if self.client and not self.client.is_closed():
            await self.client.close()
    
    def get_guild(self, guild_id: int) -> Optional[discord.Guild]:
        """Get a guild by ID."""
        return self.client.get_guild(guild_id)
    
    def get_channel(self, channel_id: int) -> Optional[discord.TextChannel]:
        """Get a text channel by ID."""
        channel = self.client.get_channel(channel_id)
        if isinstance(channel, discord.TextChannel):
            return channel
        return None
    
    async def get_channel_history(self, channel: discord.TextChannel, 
                                 after_message_id: Optional[str] = None,
                                 oldest_first: bool = True) -> AsyncGenerator[discord.Message, None]:
        """Get channel message history with optional starting point."""
        try:
            # Convert message ID to discord object if provided
            after = None
            if after_message_id:
                try:
                    # Create a fake message object with the ID for the 'after' parameter
                    after = discord.Object(id=int(after_message_id))
                except ValueError:
                    print(f"Warning: Invalid message ID format: {after_message_id}")
            
            # Get message history
            async for message in channel.history(
                limit=None,
                after=after,
                oldest_first=oldest_first
            ):
                yield message
                
        except discord.Forbidden:
            raise PermissionError(f"No permission to read message history in #{channel.name}")
        except discord.NotFound:
            raise ValueError(f"Channel #{channel.name} not found")
        except Exception as e:
            raise RuntimeError(f"Error fetching message history: {e}")
    
    async def validate_channel_access(self, guild_id: int, channel_id: int) -> Tuple[bool, str, Optional[discord.Guild], Optional[discord.TextChannel]]:
        """Validate access to a specific channel."""
        try:
            # Get guild
            guild = self.get_guild(guild_id)
            if not guild:
                return False, f"Guild {guild_id} not found or bot not in guild", None, None
            
            # Get channel
            channel = self.get_channel(channel_id)
            if not channel:
                return False, f"Channel {channel_id} not found", guild, None
            
            # Check if channel is in the guild
            if channel.guild.id != guild_id:
                return False, f"Channel {channel_id} not in guild {guild_id}", guild, None
            
            # Test permissions by attempting to read recent messages
            try:
                messages = []
                async for message in channel.history(limit=1):
                    messages.append(message)
                return True, "Access validated", guild, channel
            except discord.Forbidden:
                return False, f"No permission to read messages in #{channel.name}", guild, channel
            
        except Exception as e:
            return False, f"Validation error: {e}", None, None
    
    def get_all_guilds(self) -> list:
        """Get all guilds the bot is in."""
        return list(self.client.guilds)
    
    def get_text_channels_in_guild(self, guild: discord.Guild) -> list:
        """Get all text channels in a guild."""
        return [channel for channel in guild.channels if isinstance(channel, discord.TextChannel)]
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.start_client()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close() 