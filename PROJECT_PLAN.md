# Discord Channel Photo Scraper - Project Plan

## Overview
A comprehensive Discord bot/scraper that saves photos from any channel in any Discord server, with intelligent duplicate prevention and incremental updating capabilities.

## Core Requirements
1. **Multi-server/channel support**: Work with any Discord server and channel
2. **Complete history traversal**: Start from channel beginning, end at most recent
3. **Duplicate prevention**: Track last processed message to avoid re-downloading
4. **Incremental updates**: Resume from last position for future runs

## Technical Architecture

### Core Components
- **Discord API Client**: Use `discord.py` library for Python
- **Message Processor**: Handle message history retrieval and pagination
- **Image Downloader**: Download and save image attachments
- **State Manager**: Track progress and prevent duplicates
- **Configuration Manager**: Handle server/channel settings

### Required Libraries
```txt
discord.py>=2.3.0
aiohttp>=3.8.0
aiofiles>=23.0.0
python-dotenv>=1.0.0
```

### Project Structure
```
discord_photo_scraper/
├── main.py                 # Entry point
├── config/
│   ├── settings.py         # Configuration management
│   └── .env               # Environment variables (bot token)
├── scraper/
│   ├── discord_client.py   # Discord API wrapper
│   ├── message_processor.py # Message handling logic
│   ├── image_downloader.py # Download and save images
│   └── state_manager.py    # Progress tracking
├── data/
│   ├── progress.json       # Last processed message IDs
│   └── downloads/          # Downloaded images organized by server/channel
└── requirements.txt
```

## Implementation Details

### Authentication & Setup
- Use Discord Bot Token (requires creating a Discord application)
- Bot needs `Read Message History` and `View Channel` permissions
- Support for user tokens as alternative (with appropriate warnings)

### Message History Strategy
- Use `discord.TextChannel.history()` with `oldest_first=True`
- Implement proper pagination to handle large channels
- Handle API rate limits with exponential backoff

### State Tracking Schema
```json
{
  "servers": {
    "server_id": {
      "channels": {
        "channel_id": {
          "last_message_id": "123456789",
          "last_updated": "2024-01-15T10:30:00Z",
          "total_images": 150
        }
      }
    }
  }
}
```

### File Organization
```
downloads/
├── ServerName_123456789/
│   ├── ChannelName_987654321/
│   │   ├── 2024-01-15_MessageID_image1.jpg
│   │   ├── 2024-01-15_MessageID_image2.png
│   │   └── ...
```

## Core Features

### Command Line Interface
```bash
# Scrape specific channel
python main.py --server-id 123456 --channel-id 789012

# Resume scraping (use saved state)
python main.py --resume --server-id 123456 --channel-id 789012

# Scrape all channels in a server
python main.py --server-id 123456 --all-channels
```

### Configuration Options
- Supported image formats (jpg, png, gif, webp, etc.)
- Maximum file size limits
- Concurrent download limits
- Custom naming patterns
- Progress reporting frequency

## Error Handling & Edge Cases
- **Rate Limiting**: Implement exponential backoff
- **Network Issues**: Retry failed downloads
- **Permission Errors**: Graceful handling with informative messages
- **Large Files**: Optional size limits and warnings
- **Deleted Messages**: Handle missing message references
- **Channel Access**: Verify permissions before starting

## Implementation Phases

### Phase 1: Basic Structure
1. Set up Discord client connection
2. Implement basic message history retrieval
3. Create simple image download functionality
4. Basic state tracking (JSON file)

### Phase 2: Advanced Features
1. Multi-server/channel support
2. Resume functionality
3. Progress reporting and logging
4. Error handling and retry logic

### Phase 3: Optimization
1. Concurrent downloads
2. Advanced filtering options
3. Performance monitoring
4. Memory optimization for large channels

## Usage Flow
1. **Initial Setup**: Configure bot token and permissions
2. **First Run**: Specify server/channel, scraper processes entire history
3. **Subsequent Runs**: Automatically resume from last processed message
4. **Monitoring**: Progress logs and completion notifications

## Security & Compliance
- Store bot tokens securely (environment variables)
- Respect Discord's Terms of Service
- Implement proper rate limiting
- Option to exclude NSFW content
- User consent and privacy considerations

## Technical Considerations

### API Rate Limits
- Discord allows 50 requests per second for bots
- Message history: 1 request per 100 messages
- File downloads: Separate rate limit considerations
- Implement exponential backoff for 429 responses

### Memory Management
- Process messages in batches to avoid memory issues
- Use generators for large message histories
- Clean up temporary files and connections

### Performance Optimization
- Async/await for concurrent operations
- Connection pooling for downloads
- Progress checkpointing every N messages
- Resume capability from any point

## Future Enhancements
- GUI interface using tkinter or PyQt
- Web dashboard for monitoring progress
- Support for video files and other media types
- Advanced filtering (date ranges, file sizes, users)
- Export functionality (CSV reports, statistics)
- Integration with cloud storage services 