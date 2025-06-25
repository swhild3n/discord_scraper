import json
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Any
from config.settings import settings

class StateManager:
    """Manages progress state and prevents duplicate downloads."""
    
    def __init__(self):
        self.progress_file = settings.PROGRESS_FILE
        self.state = self._load_state()
        self._lock = asyncio.Lock()
    
    def _load_state(self) -> Dict[str, Any]:
        """Load progress state from file."""
        if self.progress_file.exists():
            try:
                with open(self.progress_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not load progress file: {e}")
        
        return {"servers": {}}
    
    async def save_state(self):
        """Save current state to file."""
        async with self._lock:
            try:
                with open(self.progress_file, 'w', encoding='utf-8') as f:
                    json.dump(self.state, f, indent=2, ensure_ascii=False)
            except IOError as e:
                print(f"Error saving progress file: {e}")
    
    def get_last_message_id(self, server_id: str, channel_id: str) -> Optional[str]:
        """Get the last processed message ID for a channel."""
        return (self.state
                .get("servers", {})
                .get(str(server_id), {})
                .get("channels", {})
                .get(str(channel_id), {})
                .get("last_message_id"))
    
    async def update_progress(self, server_id: str, channel_id: str, 
                            message_id: str, server_name: str = None, 
                            channel_name: str = None):
        """Update progress for a specific channel."""
        async with self._lock:
            # Initialize structure if not exists
            if "servers" not in self.state:
                self.state["servers"] = {}
            
            server_key = str(server_id)
            if server_key not in self.state["servers"]:
                self.state["servers"][server_key] = {
                    "name": server_name or f"Server_{server_id}",
                    "channels": {}
                }
            
            channel_key = str(channel_id)
            if channel_key not in self.state["servers"][server_key]["channels"]:
                self.state["servers"][server_key]["channels"][channel_key] = {
                    "name": channel_name or f"Channel_{channel_id}",
                    "last_message_id": None,
                    "last_updated": None,
                    "total_images": 0
                }
            
            # Update channel info
            channel_data = self.state["servers"][server_key]["channels"][channel_key]
            channel_data["last_message_id"] = str(message_id)
            channel_data["last_updated"] = datetime.now().isoformat()
            if channel_name:
                channel_data["name"] = channel_name
    
    async def increment_image_count(self, server_id: str, channel_id: str, count: int = 1):
        """Increment the total image count for a channel."""
        async with self._lock:
            server_key = str(server_id)
            channel_key = str(channel_id)
            
            if (server_key in self.state.get("servers", {}) and 
                channel_key in self.state["servers"][server_key].get("channels", {})):
                
                channel_data = self.state["servers"][server_key]["channels"][channel_key]
                channel_data["total_images"] = channel_data.get("total_images", 0) + count
    
    def get_channel_stats(self, server_id: str, channel_id: str) -> Dict[str, Any]:
        """Get statistics for a specific channel."""
        server_key = str(server_id)
        channel_key = str(channel_id)
        
        return (self.state
                .get("servers", {})
                .get(server_key, {})
                .get("channels", {})
                .get(channel_key, {}))
    
    def get_all_tracked_channels(self) -> list:
        """Get all tracked channels across all servers."""
        channels = []
        for server_id, server_data in self.state.get("servers", {}).items():
            for channel_id, channel_data in server_data.get("channels", {}).items():
                channels.append({
                    "server_id": server_id,
                    "server_name": server_data.get("name", f"Server_{server_id}"),
                    "channel_id": channel_id,
                    "channel_name": channel_data.get("name", f"Channel_{channel_id}"),
                    "last_message_id": channel_data.get("last_message_id"),
                    "last_updated": channel_data.get("last_updated"),
                    "total_images": channel_data.get("total_images", 0)
                })
        return channels 