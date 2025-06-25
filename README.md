# Discord Photo Scraper

A comprehensive Discord bot that downloads and organizes photos from any Discord channel, with intelligent duplicate prevention and progress tracking.

## Features

- 🖼️ **Download all images** from any Discord channel
- 🔄 **Resume capability** - picks up where it left off
- 📁 **Organized storage** - files sorted by server/channel
- 🚫 **Duplicate prevention** - tracks processed messages
- ⚡ **Concurrent downloads** - fast and efficient
- 📊 **Progress tracking** - detailed statistics and reporting
- 🛡️ **Error handling** - robust with retry logic

## Requirements

- Python 3.8 or higher
- Discord Bot Token (or User Token)
- Bot permissions: `Read Message History`, `View Channel`

## Installation

1. **Clone or download** this project to your desired location

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up Discord Bot:**
   - Go to [Discord Developer Portal](https://discord.com/developers/applications)
   - Create a new application
   - Go to "Bot" section and create a bot
   - Copy the bot token
   - Invite the bot to your server with "Read Message History" permissions

4. **Configure environment:**
   Create a `.env` file in the `config` directory:
   ```
   DISCORD_BOT_TOKEN=your_bot_token_here
   ```

## Usage

### Basic Commands

**List available servers:**
```bash
python main.py --list-guilds
```

**List channels in a server:**
```bash
python main.py --list-channels --server-id YOUR_SERVER_ID
```

**Download images from a channel:**
```bash
python main.py --server-id YOUR_SERVER_ID --channel-id YOUR_CHANNEL_ID
```

**Start fresh (ignore previous progress):**
```bash
python main.py --server-id YOUR_SERVER_ID --channel-id YOUR_CHANNEL_ID --fresh
```

**View channel statistics:**
```bash
python main.py --stats --server-id YOUR_SERVER_ID --channel-id YOUR_CHANNEL_ID
```

**List all tracked channels:**
```bash
python main.py --list-tracked
```

### How to Get Discord IDs

1. **Enable Developer Mode** in Discord:
   - User Settings → Advanced → Developer Mode (ON)

2. **Get Server ID:**
   - Right-click on server name → "Copy Server ID"

3. **Get Channel ID:**
   - Right-click on channel name → "Copy Channel ID"

## File Organization

Downloaded images are organized as follows:
```
data/
└── downloads/
    └── ServerName_ServerID/
        └── ChannelName_ChannelID/
            ├── 2024-01-15_MessageID_image1.jpg
            ├── 2024-01-15_MessageID_image2.png
            └── ...
```

## Configuration Options

You can customize the scraper by setting environment variables:

```bash
# Maximum file size in MB (default: 50)
MAX_FILE_SIZE_MB=100

# Number of concurrent downloads (default: 5)
CONCURRENT_DOWNLOADS=3

# Supported image formats (default: jpg,jpeg,png,gif,webp,bmp)
SUPPORTED_FORMATS=jpg,png,gif

# Progress report interval (default: 100 messages)
PROGRESS_REPORT_INTERVAL=50
```

## Progress Tracking

The scraper automatically saves progress in `data/progress.json`. This allows you to:

- **Resume interrupted downloads** - restart from where you left off
- **Avoid duplicates** - skip already downloaded images
- **Track statistics** - see total images downloaded per channel

## Safety Features

- **Rate limiting** - respects Discord's API limits
- **File size limits** - prevents downloading huge files
- **Permission checking** - validates access before starting
- **Error recovery** - handles network issues gracefully

## Troubleshooting

### Common Issues

**"No Discord token provided"**
- Make sure your `.env` file is in the `config` directory
- Verify the token is correct and properly formatted

**"Guild not found or bot not in guild"**
- Ensure the bot is invited to the Discord server
- Check that the server ID is correct

**"No permission to read message history"**
- The bot needs "Read Message History" permission
- Re-invite the bot with proper permissions

**"Channel not found"**
- Verify the channel ID is correct
- Ensure the bot has access to the channel

### Getting Help

1. **Check the error messages** - they usually indicate the exact problem
2. **Verify your Discord IDs** - use the `--list-guilds` and `--list-channels` commands
3. **Test bot permissions** - try accessing a public channel first

## Security Notes

- **Never share your bot token** - treat it like a password
- **Use bot tokens, not user tokens** - user tokens violate Discord's ToS
- **Store tokens securely** - use environment variables or `.env` files
- **Respect Discord's ToS** - don't scrape private content without permission

## Legal Disclaimer

This tool is for educational and personal use only. Users are responsible for:
- Complying with Discord's Terms of Service
- Respecting copyright and privacy rights
- Obtaining necessary permissions before scraping content
- Using downloaded content appropriately

---

**Happy scraping! 🎉** 