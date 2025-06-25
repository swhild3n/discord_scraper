import os
import random
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Settings:
    """Configuration settings for the Discord photo scraper."""
    
    # Discord API
    BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
    USER_TOKEN = os.getenv('DISCORD_USER_TOKEN')  # Optional, use with caution
    
    # File settings
    MAX_FILE_SIZE_MB = int(os.getenv('MAX_FILE_SIZE_MB', 50))
    SUPPORTED_FORMATS = os.getenv('SUPPORTED_FORMATS', 'jpg,jpeg,png,gif,webp,bmp').split(',')
    
    # Download settings
    CONCURRENT_DOWNLOADS = int(os.getenv('CONCURRENT_DOWNLOADS', 5))
    PROGRESS_REPORT_INTERVAL = int(os.getenv('PROGRESS_REPORT_INTERVAL', 100))
    
    # New: Batch and rate limiting settings
    DOWNLOAD_BATCH_SIZE = int(os.getenv('DOWNLOAD_BATCH_SIZE', 10))  # Images per batch
    RATE_LIMIT_MIN_MS = int(os.getenv('RATE_LIMIT_MIN_MS', 500))     # Minimum delay in ms
    RATE_LIMIT_MAX_MS = int(os.getenv('RATE_LIMIT_MAX_MS', 1500))    # Maximum delay in ms
    
    # Paths
    BASE_DIR = Path(__file__).parent.parent
    DATA_DIR = BASE_DIR / 'data'
    DOWNLOADS_DIR = DATA_DIR / 'downloads'
    PROGRESS_FILE = DATA_DIR / 'progress.json'
    
    # Rate limiting
    API_RATE_LIMIT = 50  # requests per second
    MESSAGE_BATCH_SIZE = 100
    
    @classmethod
    def get_rate_limit_delay(cls) -> float:
        """Get a random delay between min and max rate limit values in seconds."""
        delay_ms = random.randint(cls.RATE_LIMIT_MIN_MS, cls.RATE_LIMIT_MAX_MS)
        return delay_ms / 1000.0  # Convert to seconds
    
    @classmethod
    def validate(cls):
        """Validate required settings."""
        if not cls.BOT_TOKEN and not cls.USER_TOKEN:
            raise ValueError("Either DISCORD_BOT_TOKEN or DISCORD_USER_TOKEN must be set")
        
        # Validate rate limiting settings
        if cls.RATE_LIMIT_MIN_MS > cls.RATE_LIMIT_MAX_MS:
            raise ValueError("RATE_LIMIT_MIN_MS cannot be greater than RATE_LIMIT_MAX_MS")
        
        if cls.DOWNLOAD_BATCH_SIZE < 1:
            raise ValueError("DOWNLOAD_BATCH_SIZE must be at least 1")
        
        # Create directories if they don't exist
        cls.DATA_DIR.mkdir(exist_ok=True)
        cls.DOWNLOADS_DIR.mkdir(exist_ok=True)
        
        return True

# Create settings instance
settings = Settings() 