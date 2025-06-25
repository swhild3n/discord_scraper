#!/usr/bin/env python3
"""
Discord Photo Scraper - Main Entry Point

Usage:
    python main.py --server-id 123456 --channel-id 789012
    python main.py --server-id 123456 --channel-id 789012 --resume
    python main.py --list-guilds
    python main.py --list-channels --server-id 123456
    python main.py --stats --server-id 123456 --channel-id 789012
"""

import asyncio
import argparse
import sys
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import settings
from scraper.message_processor import MessageProcessor

async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Discord Photo Scraper - Download images from Discord channels",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --server-id 123456789 --channel-id 987654321
  python main.py --server-id 123456789 --channel-id 987654321 --resume
  python main.py --list-guilds
  python main.py --list-channels --server-id 123456789
  python main.py --stats --server-id 123456789 --channel-id 987654321
        """
    )
    
    # Main actions
    parser.add_argument('--server-id', type=int, help='Discord server (guild) ID')
    parser.add_argument('--channel-id', type=int, help='Discord channel ID')
    parser.add_argument('--resume', action='store_true', 
                       help='Resume from last processed message (default: True)')
    parser.add_argument('--fresh', action='store_true', 
                       help='Start fresh, ignore previous progress')
    parser.add_argument('--no-batch', action='store_true',
                       help='Disable batch mode (process images individually)')
    
    # Information commands
    parser.add_argument('--list-guilds', action='store_true', 
                       help='List all available guilds/servers')
    parser.add_argument('--list-channels', action='store_true', 
                       help='List all channels in a guild (requires --server-id)')
    parser.add_argument('--stats', action='store_true', 
                       help='Show statistics for a channel')
    parser.add_argument('--list-tracked', action='store_true', 
                       help='List all tracked channels with progress')
    
    args = parser.parse_args()
    
    # Validate settings
    try:
        settings.validate()
    except ValueError as e:
        print(f"Configuration error: {e}")
        print("\nPlease create a .env file in the config directory with:")
        print("DISCORD_BOT_TOKEN=your_bot_token_here")
        print("\nOr set the environment variable DISCORD_BOT_TOKEN")
        return 1
    
    try:
        async with MessageProcessor() as processor:
            
            # List guilds
            if args.list_guilds:
                await list_guilds(processor)
                return 0
            
            # List channels in guild
            if args.list_channels:
                if not args.server_id:
                    print("Error: --list-channels requires --server-id")
                    return 1
                await list_channels(processor, args.server_id)
                return 0
            
            # Show channel stats
            if args.stats:
                if not args.server_id or not args.channel_id:
                    print("Error: --stats requires both --server-id and --channel-id")
                    return 1
                await show_stats(processor, args.server_id, args.channel_id)
                return 0
            
            # List tracked channels
            if args.list_tracked:
                await list_tracked_channels(processor)
                return 0
            
            # Main processing
            if not args.server_id or not args.channel_id:
                print("Error: Server ID and Channel ID are required for processing")
                print("Use --list-guilds to see available servers")
                print("Use --list-channels --server-id <ID> to see available channels")
                return 1
            
            # Determine resume behavior
            resume = not args.fresh  # Default to resume unless --fresh is specified
            use_batch_mode = not args.no_batch  # Default to batch mode unless --no-batch is specified
            
            print(f"Starting Discord Photo Scraper")
            print(f"Server ID: {args.server_id}")
            print(f"Channel ID: {args.channel_id}")
            print(f"Resume mode: {'On' if resume else 'Off'}")
            print(f"Batch mode: {'On' if use_batch_mode else 'Off'}")
            print("-" * 50)
            
            # Process the channel
            result = await processor.process_channel(
                args.server_id, args.channel_id, resume=resume, use_batch_mode=use_batch_mode
            )
            
            if result['success']:
                print("\n" + "=" * 50)
                print("PROCESSING COMPLETE")
                print("=" * 50)
                stats = result['stats']
                info = result['channel_info']
                
                print(f"Channel: #{info['channel_name']} in {info['guild_name']}")
                print(f"Messages processed: {stats['messages_processed']}")
                print(f"Images found: {stats['images_found']}")
                print(f"Images downloaded: {stats['images_downloaded']}")
                print(f"Images skipped: {stats['images_skipped']}")
                print(f"Errors: {stats['errors']}")
                
                if stats['images_downloaded'] > 0:
                    print(f"\nImages saved to: data/downloads/{info['guild_name']}_{info['guild_id']}/{info['channel_name']}_{info['channel_id']}/")
                
                return 0
            else:
                print(f"\nProcessing failed: {result['error']}")
                return 1
                
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}")
        return 1

async def list_guilds(processor):
    """List all available guilds."""
    print("Available Discord Servers (Guilds):")
    print("-" * 50)
    
    guilds = await processor.list_available_guilds()
    
    if not guilds:
        print("No guilds found. Make sure the bot is added to Discord servers.")
        return
    
    for guild in guilds:
        print(f"ID: {guild['id']}")
        print(f"Name: {guild['name']}")
        print(f"Members: {guild['member_count']}")
        print(f"Text Channels: {guild['text_channels']}")
        print("-" * 30)

async def list_channels(processor, guild_id):
    """List all channels in a guild."""
    print(f"Text Channels in Guild {guild_id}:")
    print("-" * 50)
    
    channels = await processor.list_channels_in_guild(guild_id)
    
    if not channels:
        print("No channels found or bot doesn't have access to this guild.")
        return
    
    for channel in channels:
        print(f"ID: {channel['id']}")
        print(f"Name: #{channel['name']}")
        if channel['topic']:
            print(f"Topic: {channel['topic']}")
        if channel['nsfw']:
            print("⚠️  NSFW Channel")
        print("-" * 30)

async def show_stats(processor, guild_id, channel_id):
    """Show statistics for a channel."""
    print(f"Statistics for Channel {channel_id} in Guild {guild_id}:")
    print("-" * 50)
    
    stats = await processor.get_channel_stats(guild_id, channel_id)
    
    if not stats:
        print("No statistics found for this channel.")
        return
    
    if 'current_info' in stats:
        info = stats['current_info']
        print(f"Server: {info['guild_name']}")
        print(f"Channel: #{info['channel_name']}")
        if info.get('channel_topic'):
            print(f"Topic: {info['channel_topic']}")
        print()
    
    print(f"Last Message ID: {stats.get('last_message_id', 'None')}")
    print(f"Last Updated: {stats.get('last_updated', 'Never')}")
    print(f"Total Images Downloaded: {stats.get('total_images', 0)}")

async def list_tracked_channels(processor):
    """List all tracked channels."""
    print("Tracked Channels:")
    print("-" * 50)
    
    channels = processor.state_manager.get_all_tracked_channels()
    
    if not channels:
        print("No channels are currently being tracked.")
        return
    
    for channel in channels:
        print(f"Server: {channel['server_name']} (ID: {channel['server_id']})")
        print(f"Channel: #{channel['channel_name']} (ID: {channel['channel_id']})")
        print(f"Last Message: {channel['last_message_id']}")
        print(f"Last Updated: {channel['last_updated']}")
        print(f"Total Images: {channel['total_images']}")
        print("-" * 30)

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\nGoodbye!")
        sys.exit(0) 