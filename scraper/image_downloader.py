import asyncio
import aiohttp
import aiofiles
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Tuple
import re
from config.settings import settings

class ImageDownloader:
    """Handles downloading and saving images from Discord messages."""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.semaphore = asyncio.Semaphore(settings.CONCURRENT_DOWNLOADS)
        self.max_file_size = settings.MAX_FILE_SIZE_MB * 1024 * 1024  # Convert to bytes
        self.supported_formats = [fmt.lower() for fmt in settings.SUPPORTED_FORMATS]
        self.last_request_time = 0  # Track last request time for rate limiting
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def _rate_limit_delay(self):
        """Apply rate limiting delay between requests."""
        current_time = asyncio.get_event_loop().time()
        time_since_last = current_time - self.last_request_time
        
        delay = settings.get_rate_limit_delay()
        if time_since_last < delay:
            sleep_time = delay - time_since_last
            await asyncio.sleep(sleep_time)
        
        self.last_request_time = asyncio.get_event_loop().time()
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename to be safe for filesystem."""
        # Remove invalid characters
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        # Limit length
        if len(filename) > 200:
            name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
            filename = name[:200-len(ext)-1] + '.' + ext if ext else name[:200]
        return filename
    
    def _get_file_extension(self, url: str, content_type: Optional[str] = None) -> str:
        """Get file extension from URL or content type."""
        # Try to get extension from URL
        url_path = url.split('?')[0]  # Remove query parameters
        if '.' in url_path:
            ext = url_path.split('.')[-1].lower()
            if ext in self.supported_formats:
                return ext
        
        # Try to get extension from content type
        if content_type:
            content_type_map = {
                'image/jpeg': 'jpg',
                'image/jpg': 'jpg',
                'image/png': 'png',
                'image/gif': 'gif',
                'image/webp': 'webp',
                'image/bmp': 'bmp'
            }
            return content_type_map.get(content_type.lower(), 'jpg')
        
        return 'jpg'  # Default
    
    def _create_filename(self, message_id: str, attachment_filename: str, 
                        message_timestamp: datetime, index: int = 0) -> str:
        """Create a structured filename for the downloaded image."""
        # Format: YYYY-MM-DD_MessageID_Index_OriginalName
        date_str = message_timestamp.strftime('%Y-%m-%d')
        
        # Clean original filename
        clean_name = self._sanitize_filename(attachment_filename)
        
        # Add index if multiple attachments
        if index > 0:
            name_parts = clean_name.rsplit('.', 1) if '.' in clean_name else [clean_name, '']
            if len(name_parts) == 2:
                clean_name = f"{name_parts[0]}_{index}.{name_parts[1]}"
            else:
                clean_name = f"{clean_name}_{index}"
        
        return f"{date_str}_{message_id}_{clean_name}"
    
    def _get_download_path(self, server_name: str, server_id: str, 
                          channel_name: str, channel_id: str, filename: str) -> Path:
        """Get the full download path for a file."""
        # Sanitize server and channel names
        safe_server_name = self._sanitize_filename(f"{server_name}_{server_id}")
        safe_channel_name = self._sanitize_filename(f"{channel_name}_{channel_id}")
        
        # Create directory structure
        download_dir = settings.DOWNLOADS_DIR / safe_server_name / safe_channel_name
        download_dir.mkdir(parents=True, exist_ok=True)
        
        return download_dir / filename
    
    async def download_image(self, url: str, file_path: Path) -> Tuple[bool, str]:
        """Download a single image from URL to file path."""
        if not self.session:
            return False, "Session not initialized"
            
        async with self.semaphore:
            try:
                # Apply rate limiting
                await self._rate_limit_delay()
                
                async with self.session.get(url) as response:
                    if response.status != 200:
                        return False, f"HTTP {response.status}"
                    
                    # Check content type
                    content_type = response.headers.get('content-type', '')
                    if not content_type.startswith('image/'):
                        return False, f"Not an image: {content_type}"
                    
                    # Check file size
                    content_length = response.headers.get('content-length')
                    if content_length and int(content_length) > self.max_file_size:
                        return False, f"File too large: {content_length} bytes"
                    
                    # Download and save
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    async with aiofiles.open(file_path, 'wb') as f:
                        downloaded_size = 0
                        async for chunk in response.content.iter_chunked(8192):
                            downloaded_size += len(chunk)
                            if downloaded_size > self.max_file_size:
                                # Clean up partial file
                                await f.close()
                                file_path.unlink(missing_ok=True)
                                return False, f"File too large during download: {downloaded_size} bytes"
                            await f.write(chunk)
                    
                    return True, f"Downloaded {downloaded_size} bytes"
                    
            except asyncio.TimeoutError:
                return False, "Download timeout"
            except Exception as e:
                return False, f"Download error: {str(e)}"
    
    async def process_message_attachments(self, message, server_name: str, 
                                        server_id: str, channel_name: str, 
                                        channel_id: str) -> List[Tuple[bool, str, str]]:
        """Process all image attachments in a message."""
        if not message.attachments:
            return []
        
        results = []
        image_attachments = []
        
        # Filter for image attachments
        for attachment in message.attachments:
            if attachment.filename:
                ext = attachment.filename.split('.')[-1].lower() if '.' in attachment.filename else ''
                if ext in self.supported_formats:
                    image_attachments.append(attachment)
        
        if not image_attachments:
            return []
        
        # Download each image
        for index, attachment in enumerate(image_attachments):
            filename = self._create_filename(
                str(message.id), 
                attachment.filename, 
                message.created_at,
                index
            )
            
            file_path = self._get_download_path(
                server_name, str(server_id),
                channel_name, str(channel_id),
                filename
            )
            
            # Skip if file already exists
            if file_path.exists():
                results.append((True, filename, "Already exists"))
                continue
            
            success, message_result = await self.download_image(attachment.url, file_path)
            results.append((success, filename, message_result))
        
        return results
    
    async def process_messages_in_batches(self, messages: List, server_name: str, 
                                        server_id: str, channel_name: str, 
                                        channel_id: str) -> List[Tuple[bool, str, str]]:
        """Process messages in batches to control download rate."""
        all_results = []
        
        # Collect all image download tasks first
        download_tasks = []
        
        for message in messages:
            if not message.attachments:
                continue
                
            for index, attachment in enumerate(message.attachments):
                if not attachment.filename:
                    continue
                    
                ext = attachment.filename.split('.')[-1].lower() if '.' in attachment.filename else ''
                if ext not in self.supported_formats:
                    continue
                
                filename = self._create_filename(
                    str(message.id), 
                    attachment.filename, 
                    message.created_at,
                    index
                )
                
                file_path = self._get_download_path(
                    server_name, str(server_id),
                    channel_name, str(channel_id),
                    filename
                )
                
                # Skip if file already exists
                if file_path.exists():
                    all_results.append((True, filename, "Already exists"))
                    continue
                
                download_tasks.append((attachment.url, file_path, filename))
        
        # Process downloads in batches
        batch_size = settings.DOWNLOAD_BATCH_SIZE
        for i in range(0, len(download_tasks), batch_size):
            batch = download_tasks[i:i + batch_size]
            
            print(f"Processing batch {i//batch_size + 1}/{(len(download_tasks) + batch_size - 1)//batch_size} "
                  f"({len(batch)} images)")
            
            # Download all images in this batch concurrently
            batch_tasks = [self.download_image(url, file_path) for url, file_path, _ in batch]
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # Process results
            for j, result in enumerate(batch_results):
                filename = batch[j][2]
                if isinstance(result, Exception):
                    all_results.append((False, filename, f"Exception: {str(result)}"))
                else:
                    success, message = result
                    all_results.append((success, filename, message))
            
            # Small delay between batches
            if i + batch_size < len(download_tasks):
                await asyncio.sleep(0.5)
        
        return all_results
    
    def is_image_attachment(self, attachment) -> bool:
        """Check if an attachment is a supported image."""
        if not attachment.filename:
            return False
        
        ext = attachment.filename.split('.')[-1].lower() if '.' in attachment.filename else ''
        return ext in self.supported_formats 