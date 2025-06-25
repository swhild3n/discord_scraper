import asyncio
from typing import Optional, Dict, Any
from .discord_client import DiscordClientWrapper
from .image_downloader import ImageDownloader
from .state_manager import StateManager
from config.settings import settings

class MessageProcessor:
    """Processes Discord messages and coordinates image downloading."""
    
    def __init__(self):
        self.discord_client = DiscordClientWrapper()
        self.state_manager = StateManager()
        self.image_downloader = None
        self.stats = {
            'messages_processed': 0,
            'images_found': 0,
            'images_downloaded': 0,
            'images_skipped': 0,
            'errors': 0
        }
    
    async def process_channel(self, guild_id: int, channel_id: int, 
                            resume: bool = True, use_batch_mode: bool = True) -> Dict[str, Any]:
        """Process a Discord channel and download all images."""
        # Reset stats
        self.stats = {
            'messages_processed': 0,
            'images_found': 0,
            'images_downloaded': 0,
            'images_skipped': 0,
            'errors': 0
        }
        
        try:
            # Validate channel access
            valid, message, guild, channel = await self.discord_client.validate_channel_access(
                guild_id, channel_id
            )
            
            if not valid:
                return {
                    'success': False,
                    'error': message,
                    'stats': self.stats
                }
            
            print(f"Processing #{channel.name} in {guild.name}")
            print(f"Batch mode: {'Enabled' if use_batch_mode else 'Disabled'}")
            if use_batch_mode:
                print(f"Batch size: {settings.DOWNLOAD_BATCH_SIZE}")
                print(f"Rate limit: {settings.RATE_LIMIT_MIN_MS}-{settings.RATE_LIMIT_MAX_MS}ms")
            
            # Determine starting point
            last_message_id = None
            if resume:
                last_message_id = self.state_manager.get_last_message_id(
                    str(guild_id), str(channel_id)
                )
                if last_message_id:
                    print(f"Resuming from message ID: {last_message_id}")
                else:
                    print("No previous progress found, starting from beginning")
            else:
                print("Starting fresh scan (not resuming)")
            
            # Process messages
            async with ImageDownloader() as downloader:
                self.image_downloader = downloader
                
                if use_batch_mode:
                    await self._process_messages_in_batches(
                        channel, guild, last_message_id
                    )
                else:
                    await self._process_messages_individually(
                        channel, guild, last_message_id
                    )
            
            return {
                'success': True,
                'stats': self.stats,
                'channel_info': {
                    'guild_name': guild.name,
                    'guild_id': str(guild_id),
                    'channel_name': channel.name,
                    'channel_id': str(channel_id)
                }
            }
            
        except Exception as e:
            print(f"Error processing channel: {e}")
            return {
                'success': False,
                'error': str(e),
                'stats': self.stats
            }
    
    async def _process_messages_in_batches(self, channel, guild, last_message_id):
        """Process messages using batch mode for more efficient downloading."""
        message_batch = []
        
        async for message in self.discord_client.get_channel_history(
            channel, 
            after_message_id=last_message_id,
            oldest_first=True
        ):
            self.stats['messages_processed'] += 1
            message_batch.append(message)
            
            # Process batch when it reaches the batch size
            if len(message_batch) >= settings.MESSAGE_BATCH_SIZE:
                await self._process_message_batch(
                    message_batch, guild.name, str(guild.id), 
                    channel.name, str(channel.id)
                )
                
                # Update progress
                await self._save_progress_and_report(
                    str(guild.id), str(channel.id), str(message_batch[-1].id),
                    guild.name, channel.name
                )
                
                message_batch = []
        
        # Process remaining messages in the final batch
        if message_batch:
            await self._process_message_batch(
                message_batch, guild.name, str(guild.id), 
                channel.name, str(channel.id)
            )
            
            # Final progress save
            await self.state_manager.save_state()
    
    async def _process_messages_individually(self, channel, guild, last_message_id):
        """Process messages individually (original method)."""
        async for message in self.discord_client.get_channel_history(
            channel, 
            after_message_id=last_message_id,
            oldest_first=True
        ):
            await self._process_single_message(
                message, guild.name, str(guild.id), 
                channel.name, str(channel.id)
            )
            
            # Update progress periodically
            if self.stats['messages_processed'] % settings.PROGRESS_REPORT_INTERVAL == 0:
                await self._save_progress_and_report(
                    str(guild.id), str(channel.id), str(message.id),
                    guild.name, channel.name
                )
        
        # Final progress save
        if self.stats['messages_processed'] > 0:
            await self.state_manager.save_state()
    
    async def _process_message_batch(self, messages, guild_name: str, 
                                   guild_id: str, channel_name: str, 
                                   channel_id: str):
        """Process a batch of messages for image attachments."""
        try:
            # Count total images in batch
            total_images = 0
            for message in messages:
                if message.attachments:
                    image_count = sum(1 for att in message.attachments 
                                    if self.image_downloader.is_image_attachment(att))
                    total_images += image_count
            
            if total_images == 0:
                return
            
            self.stats['images_found'] += total_images
            print(f"Processing batch: {len(messages)} messages, {total_images} images")
            
            # Process all images in the batch
            results = await self.image_downloader.process_messages_in_batches(
                messages, guild_name, guild_id, channel_name, channel_id
            )
            
            # Process results
            for success, filename, result_message in results:
                if success:
                    if "Already exists" in result_message:
                        self.stats['images_skipped'] += 1
                        # Only print occasionally for existing files to reduce spam
                        if self.stats['images_skipped'] % 10 == 0:
                            print(f"  Skipped {self.stats['images_skipped']} existing files...")
                    else:
                        self.stats['images_downloaded'] += 1
                        print(f"  Downloaded: {filename}")
                else:
                    self.stats['errors'] += 1
                    print(f"  Failed: {filename} - {result_message}")
            
            # Update state with the last processed message
            if messages:
                last_message = messages[-1]
                await self.state_manager.update_progress(
                    guild_id, channel_id, str(last_message.id),
                    guild_name, channel_name
                )
                
                # Update image count
                downloaded_count = sum(1 for success, _, result in results 
                                     if success and "Already exists" not in result)
                if downloaded_count > 0:
                    await self.state_manager.increment_image_count(
                        guild_id, channel_id, downloaded_count
                    )
            
        except Exception as e:
            self.stats['errors'] += 1
            print(f"Error processing message batch: {e}")
    
    async def _process_single_message(self, message, guild_name: str, 
                                    guild_id: str, channel_name: str, 
                                    channel_id: str):
        """Process a single message for image attachments."""
        try:
            self.stats['messages_processed'] += 1
            
            # Check if message has image attachments
            if not message.attachments:
                return
            
            # Count image attachments
            image_count = sum(1 for att in message.attachments 
                            if self.image_downloader.is_image_attachment(att))
            
            if image_count == 0:
                return
            
            self.stats['images_found'] += image_count
            
            # Download images
            results = await self.image_downloader.process_message_attachments(
                message, guild_name, guild_id, channel_name, channel_id
            )
            
            # Process results
            for success, filename, result_message in results:
                if success:
                    if "Already exists" in result_message:
                        self.stats['images_skipped'] += 1
                        print(f"  Skipped: {filename} (already exists)")
                    else:
                        self.stats['images_downloaded'] += 1
                        print(f"  Downloaded: {filename}")
                else:
                    self.stats['errors'] += 1
                    print(f"  Failed: {filename} - {result_message}")
            
            # Update state with processed message
            await self.state_manager.update_progress(
                guild_id, channel_id, str(message.id),
                guild_name, channel_name
            )
            
            # Update image count
            downloaded_count = sum(1 for success, _, result in results 
                                 if success and "Already exists" not in result)
            if downloaded_count > 0:
                await self.state_manager.increment_image_count(
                    guild_id, channel_id, downloaded_count
                )
            
        except Exception as e:
            self.stats['errors'] += 1
            print(f"Error processing message {message.id}: {e}")
    
    async def _save_progress_and_report(self, guild_id: str, channel_id: str, 
                                      message_id: str, guild_name: str, 
                                      channel_name: str):
        """Save progress and report current stats."""
        await self.state_manager.update_progress(
            guild_id, channel_id, message_id, guild_name, channel_name
        )
        await self.state_manager.save_state()
        
        print(f"Progress: {self.stats['messages_processed']} messages, "
              f"{self.stats['images_found']} images found, "
              f"{self.stats['images_downloaded']} downloaded, "
              f"{self.stats['images_skipped']} skipped, "
              f"{self.stats['errors']} errors")
    
    async def list_available_guilds(self) -> list:
        """List all available guilds."""
        guilds = self.discord_client.get_all_guilds()
        return [{
            'id': guild.id,
            'name': guild.name,
            'member_count': guild.member_count,
            'text_channels': len(self.discord_client.get_text_channels_in_guild(guild))
        } for guild in guilds]
    
    async def list_channels_in_guild(self, guild_id: int) -> list:
        """List all text channels in a guild."""
        guild = self.discord_client.get_guild(guild_id)
        if not guild:
            return []
        
        channels = self.discord_client.get_text_channels_in_guild(guild)
        return [{
            'id': channel.id,
            'name': channel.name,
            'topic': channel.topic,
            'nsfw': channel.nsfw
        } for channel in channels]
    
    async def get_channel_stats(self, guild_id: int, channel_id: int) -> Dict[str, Any]:
        """Get statistics for a channel."""
        stats = self.state_manager.get_channel_stats(str(guild_id), str(channel_id))
        
        # Add channel info if available
        guild = self.discord_client.get_guild(guild_id)
        channel = self.discord_client.get_channel(channel_id)
        
        if guild and channel:
            stats['current_info'] = {
                'guild_name': guild.name,
                'channel_name': channel.name,
                'channel_topic': channel.topic
            }
        
        return stats
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.discord_client.start_client()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.discord_client.close() 