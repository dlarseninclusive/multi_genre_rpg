import json
import os
import logging
import time
import pickle
from datetime import datetime

logger = logging.getLogger("save_system")

class SaveSystem:
    """
    System for saving and loading game state.
    
    Handles:
    - Multiple save slots
    - Save metadata (timestamps, screenshots)
    - Serialization of complex game objects
    """
    
    def __init__(self, save_dir="saves"):
        """
        Initialize the save system.
        
        Args:
            save_dir: Directory to store save files
        """
        self.save_dir = save_dir
        self.max_slots = 5
        
        # Create save directory if it doesn't exist
        os.makedirs(self.save_dir, exist_ok=True)
        
        logger.info(f"SaveSystem initialized with directory: {save_dir}")
    
    def save_game(self, slot, game_state, metadata=None):
        """
        Save the game to a slot.
        
        Args:
            slot: Save slot number (1-based)
            game_state: Dictionary containing game state
            metadata: Optional metadata about the save
            
        Returns:
            Boolean indicating success
        """
        if not 1 <= slot <= self.max_slots:
            logger.error(f"Invalid save slot: {slot}")
            return False
        
        # Create save data
        save_data = {
            "timestamp": time.time(),
            "datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "metadata": metadata if metadata else {},
            "game_state": game_state
        }
        
        # Save file path
        save_path = os.path.join(self.save_dir, f"save_{slot}.json")
        
        try:
            # Save as JSON
            with open(save_path, 'w') as f:
                json.dump(save_data, f, indent=2, default=self._json_serialize)
            
            logger.info(f"Game saved to slot {slot}")
            return True
        
        except Exception as e:
            logger.error(f"Error saving game to slot {slot}: {e}")
            return False
    
    def load_game(self, slot):
        """
        Load a game from a slot.
        
        Args:
            slot: Save slot number (1-based)
            
        Returns:
            Dictionary containing game state, or None if load failed
        """
        if not 1 <= slot <= self.max_slots:
            logger.error(f"Invalid save slot: {slot}")
            return None
        
        # Save file path
        save_path = os.path.join(self.save_dir, f"save_{slot}.json")
        
        # Check if save exists
        if not os.path.exists(save_path):
            logger.warning(f"No save file found in slot {slot}")
            return None
        
        try:
            # Load JSON
            with open(save_path, 'r') as f:
                save_data = json.load(f)
            
            logger.info(f"Game loaded from slot {slot}")
            return save_data.get("game_state")
        
        except Exception as e:
            logger.error(f"Error loading game from slot {slot}: {e}")
            return None
    
    def get_save_info(self, slot=None):
        """
        Get information about saves.
        
        Args:
            slot: Optional specific slot to get info for
            
        Returns:
            Dictionary with save info if slot specified,
            or list of dictionaries for all slots
        """
        if slot is not None:
            if not 1 <= slot <= self.max_slots:
                logger.error(f"Invalid save slot: {slot}")
                return None
            
            # Get info for specific slot
            save_path = os.path.join(self.save_dir, f"save_{slot}.json")
            
            if not os.path.exists(save_path):
                return {
                    "slot": slot,
                    "exists": False
                }
            
            try:
                with open(save_path, 'r') as f:
                    save_data = json.load(f)
                
                return {
                    "slot": slot,
                    "exists": True,
                    "timestamp": save_data.get("timestamp"),
                    "datetime": save_data.get("datetime"),
                    "metadata": save_data.get("metadata", {})
                }
            
            except Exception as e:
                logger.error(f"Error reading save info from slot {slot}: {e}")
                return {
                    "slot": slot,
                    "exists": True,
                    "error": str(e)
                }
        
        else:
            # Get info for all slots
            info = []
            
            for i in range(1, self.max_slots + 1):
                info.append(self.get_save_info(i))
            
            return info
    
    def delete_save(self, slot):
        """
        Delete a save.
        
        Args:
            slot: Save slot number (1-based)
            
        Returns:
            Boolean indicating success
        """
        if not 1 <= slot <= self.max_slots:
            logger.error(f"Invalid save slot: {slot}")
            return False
        
        # Save file path
        save_path = os.path.join(self.save_dir, f"save_{slot}.json")
        
        # Check if save exists
        if not os.path.exists(save_path):
            logger.warning(f"No save file found in slot {slot}")
            return False
        
        try:
            # Delete the file
            os.remove(save_path)
            logger.info(f"Deleted save in slot {slot}")
            return True
        
        except Exception as e:
            logger.error(f"Error deleting save in slot {slot}: {e}")
            return False
    
    def _json_serialize(self, obj):
        """
        Custom JSON serializer for handling complex objects.
        
        Args:
            obj: Object to serialize
            
        Returns:
            JSON serializable representation of object
        """
        # If object has to_dict method, use it
        if hasattr(obj, 'to_dict') and callable(obj.to_dict):
            return obj.to_dict()
        
        # If object has __dict__, convert to dictionary
        if hasattr(obj, '__dict__'):
            return {
                '_type': obj.__class__.__name__,
                '_module': obj.__class__.__module__,
                'data': {k: v for k, v in obj.__dict__.items() if not k.startswith('_')}
            }
        
        # If object is enumeration
        if hasattr(obj, 'value') and hasattr(obj, 'name'):
            return {
                '_type': 'Enum',
                'value': obj.value,
                'name': obj.name
            }
        
        # If all else fails, use pickle/base64
        import base64
        return {
            '_type': 'pickle',
            'data': base64.b64encode(pickle.dumps(obj)).decode('ascii')
        }
    
    def has_save(self, slot):
        """
        Check if a save exists in the given slot.
        
        Args:
            slot: Save slot number (1-based)
            
        Returns:
            Boolean indicating if save exists
        """
        if not 1 <= slot <= self.max_slots:
            return False
        
        save_path = os.path.join(self.save_dir, f"save_{slot}.json")
        return os.path.exists(save_path)
    
    def get_latest_save_slot(self):
        """
        Get the slot number of the most recent save.
        
        Returns:
            Slot number (1-based) or None if no saves exist
        """
        latest_slot = None
        latest_timestamp = 0
        
        for slot in range(1, self.max_slots + 1):
            info = self.get_save_info(slot)
            
            if info and info.get("exists") and info.get("timestamp", 0) > latest_timestamp:
                latest_timestamp = info.get("timestamp")
                latest_slot = slot
        
        return latest_slot
    
    def auto_save(self, game_state, metadata=None):
        """
        Save to the auto-save slot.
        
        Args:
            game_state: Dictionary containing game state
            metadata: Optional metadata about the save
            
        Returns:
            Boolean indicating success
        """
        # Use a special slot for auto-saves
        auto_save_slot = self.max_slots  # Last slot is for auto-saves
        
        # Add auto-save flag to metadata
        if metadata is None:
            metadata = {}
        
        metadata["auto_save"] = True
        
        return self.save_game(auto_save_slot, game_state, metadata)
    
    def export_save(self, slot, export_path):
        """
        Export a save to a file.
        
        Args:
            slot: Save slot number (1-based)
            export_path: Path to export to
            
        Returns:
            Boolean indicating success
        """
        if not 1 <= slot <= self.max_slots:
            logger.error(f"Invalid save slot: {slot}")
            return False
        
        # Save file path
        save_path = os.path.join(self.save_dir, f"save_{slot}.json")
        
        if not os.path.exists(save_path):
            logger.warning(f"No save file found in slot {slot}")
            return False
        
        try:
            # Copy file
            import shutil
            shutil.copy2(save_path, export_path)
            logger.info(f"Exported save from slot {slot} to {export_path}")
            return True
        
        except Exception as e:
            logger.error(f"Error exporting save from slot {slot}: {e}")
            return False
    
    def import_save(self, import_path, slot):
        """
        Import a save from a file.
        
        Args:
            import_path: Path to import from
            slot: Save slot number (1-based)
            
        Returns:
            Boolean indicating success
        """
        if not 1 <= slot <= self.max_slots:
            logger.error(f"Invalid save slot: {slot}")
            return False
        
        if not os.path.exists(import_path):
            logger.warning(f"Import file not found: {import_path}")
            return False
        
        # Save file path
        save_path = os.path.join(self.save_dir, f"save_{slot}.json")
        
        try:
            # Validate save file
            with open(import_path, 'r') as f:
                save_data = json.load(f)
            
            # Check if it has the expected structure
            if "timestamp" not in save_data or "game_state" not in save_data:
                logger.error(f"Invalid save file structure: {import_path}")
                return False
            
            # Copy file
            import shutil
            shutil.copy2(import_path, save_path)
            logger.info(f"Imported save to slot {slot} from {import_path}")
            return True
        
        except Exception as e:
            logger.error(f"Error importing save to slot {slot}: {e}")
            return False
def create_backup(self, slot):
        """
        Create a backup of a save file.
        
        Args:
            slot: Save slot number (1-based)
            
        Returns:
            Boolean indicating success
        """
        if not 1 <= slot <= self.max_slots:
            logger.error(f"Invalid save slot: {slot}")
            return False
        
        # Save file path
        save_path = os.path.join(self.save_dir, f"save_{slot}.json")
        backup_path = os.path.join(self.save_dir, f"save_{slot}_backup.json")
        
        if not os.path.exists(save_path):
            logger.warning(f"No save file found in slot {slot} to backup")
            return False
        
        try:
            # Copy file
            import shutil
            shutil.copy2(save_path, backup_path)
            logger.info(f"Created backup of save slot {slot}")
            return True
        except Exception as e:
            logger.error(f"Error creating backup of save slot {slot}: {e}")
            return False
    
    def restore_backup(self, slot):
        """
        Restore a save from its backup.
        
        Args:
            slot: Save slot number (1-based)
            
        Returns:
            Boolean indicating success
        """
        if not 1 <= slot <= self.max_slots:
            logger.error(f"Invalid save slot: {slot}")
            return False
        
        # Backup file path
        backup_path = os.path.join(self.save_dir, f"save_{slot}_backup.json")
        save_path = os.path.join(self.save_dir, f"save_{slot}.json")
        
        if not os.path.exists(backup_path):
            logger.warning(f"No backup found for save slot {slot}")
            return False
        
        try:
            # Copy file
            import shutil
            shutil.copy2(backup_path, save_path)
            logger.info(f"Restored save slot {slot} from backup")
            return True
        except Exception as e:
            logger.error(f"Error restoring backup for save slot {slot}: {e}")
            return False
    
    def save_screenshot(self, slot, surface):
        """
        Save a screenshot with the save file.
        
        Args:
            slot: Save slot number (1-based)
            surface: Pygame surface to save as screenshot
            
        Returns:
            Boolean indicating success
        """
        if not 1 <= slot <= self.max_slots:
            logger.error(f"Invalid save slot: {slot}")
            return False
        
        try:
            import pygame
            
            # Create screenshots directory if it doesn't exist
            screenshots_dir = os.path.join(self.save_dir, "screenshots")
            os.makedirs(screenshots_dir, exist_ok=True)
            
            # Screenshot path
            screenshot_path = os.path.join(screenshots_dir, f"save_{slot}.png")
            
            # Save screenshot
            pygame.image.save(surface, screenshot_path)
            logger.info(f"Saved screenshot for save slot {slot}")
            return True
        except Exception as e:
            logger.error(f"Error saving screenshot for save slot {slot}: {e}")
            return False
    
    def get_save_screenshot(self, slot):
        """
        Load the screenshot for a save slot.
        
        Args:
            slot: Save slot number (1-based)
            
        Returns:
            Pygame surface with the screenshot, or None if not found
        """
        if not 1 <= slot <= self.max_slots:
            logger.error(f"Invalid save slot: {slot}")
            return None
        
        try:
            import pygame
            
            # Screenshot path
            screenshot_path = os.path.join(self.save_dir, "screenshots", f"save_{slot}.png")
            
            if not os.path.exists(screenshot_path):
                logger.warning(f"No screenshot found for save slot {slot}")
                return None
            
            # Load screenshot
            return pygame.image.load(screenshot_path)
        except Exception as e:
            logger.error(f"Error loading screenshot for save slot {slot}: {e}")
            return None
    
    def save_quick(self, game_state, metadata=None):
        """
        Create a quick save.
        
        Args:
            game_state: Dictionary containing game state
            metadata: Optional metadata about the save
            
        Returns:
            Boolean indicating success
        """
        # Quick save always goes to a special slot
        quick_save_slot = self.max_slots - 1  # Second to last slot
        
        # Add quick save flag to metadata
        if metadata is None:
            metadata = {}
        
        metadata["quick_save"] = True
        metadata["save_type"] = "quick"
        
        return self.save_game(quick_save_slot, game_state, metadata)
    
    def load_quick(self):
        """
        Load the quick save.
        
        Returns:
            Dictionary containing game state, or None if load failed
        """
        # Quick save slot
        quick_save_slot = self.max_slots - 1
        
        return self.load_game(quick_save_slot)
    
    def compress_save_file(self, slot):
        """
        Compress a save file to reduce size.
        
        Args:
            slot: Save slot number (1-based)
            
        Returns:
            Boolean indicating success
        """
        if not 1 <= slot <= self.max_slots:
            logger.error(f"Invalid save slot: {slot}")
            return False
        
        # Save file path
        save_path = os.path.join(self.save_dir, f"save_{slot}.json")
        compressed_path = os.path.join(self.save_dir, f"save_{slot}.gz")
        
        if not os.path.exists(save_path):
            logger.warning(f"No save file found in slot {slot}")
            return False
        
        try:
            import gzip
            
            # Read the original file
            with open(save_path, 'rb') as f_in:
                data = f_in.read()
            
            # Write compressed file
            with gzip.open(compressed_path, 'wb') as f_out:
                f_out.write(data)
            
            # Optionally delete the original
            # os.remove(save_path)
            
            logger.info(f"Compressed save in slot {slot}")
            return True
        except Exception as e:
            logger.error(f"Error compressing save in slot {slot}: {e}")
            return False
    
    def decompress_save_file(self, slot):
        """
        Decompress a compressed save file.
        
        Args:
            slot: Save slot number (1-based)
            
        Returns:
            Boolean indicating success
        """
        if not 1 <= slot <= self.max_slots:
            logger.error(f"Invalid save slot: {slot}")
            return False
        
        # Save file paths
        compressed_path = os.path.join(self.save_dir, f"save_{slot}.gz")
        save_path = os.path.join(self.save_dir, f"save_{slot}.json")
        
        if not os.path.exists(compressed_path):
            logger.warning(f"No compressed save file found in slot {slot}")
            return False
        
        try:
            import gzip
            
            # Read compressed file
            with gzip.open(compressed_path, 'rb') as f_in:
                data = f_in.read()
            
            # Write decompressed file
            with open(save_path, 'wb') as f_out:
                f_out.write(data)
            
            logger.info(f"Decompressed save in slot {slot}")
            return True
        except Exception as e:
            logger.error(f"Error decompressing save in slot {slot}: {e}")
            return False
    
    def save_checkpoint(self, game_state, checkpoint_name, metadata=None):
        """
        Save a named checkpoint for key game moments.
        
        Args:
            game_state: Dictionary containing game state
            checkpoint_name: Name for this checkpoint
            metadata: Optional metadata about the save
            
        Returns:
            Boolean indicating success
        """
        # Create checkpoints directory
        checkpoints_dir = os.path.join(self.save_dir, "checkpoints")
        os.makedirs(checkpoints_dir, exist_ok=True)
        
        # Safe filename (replace spaces and special chars)
        safe_name = "".join(c if c.isalnum() else "_" for c in checkpoint_name)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        checkpoint_filename = f"{safe_name}_{timestamp}.json"
        
        # Create save data
        if metadata is None:
            metadata = {}
        
        metadata["checkpoint_name"] = checkpoint_name
        metadata["save_type"] = "checkpoint"
        
        save_data = {
            "timestamp": time.time(),
            "datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "metadata": metadata,
            "game_state": game_state
        }
        
        # Checkpoint path
        checkpoint_path = os.path.join(checkpoints_dir, checkpoint_filename)
        
        try:
            # Save as JSON
            with open(checkpoint_path, 'w') as f:
                json.dump(save_data, f, indent=2, default=self._json_serialize)
            
            logger.info(f"Game saved as checkpoint: {checkpoint_name}")
            return True
        except Exception as e:
            logger.error(f"Error saving checkpoint '{checkpoint_name}': {e}")
            return False
    
    def list_checkpoints(self):
        """
        Get a list of all available checkpoints.
        
        Returns:
            List of dictionaries with checkpoint info
        """
        checkpoints_dir = os.path.join(self.save_dir, "checkpoints")
        
        if not os.path.exists(checkpoints_dir):
            return []
        
        checkpoints = []
        
        for filename in os.listdir(checkpoints_dir):
            if not filename.endswith(".json"):
                continue
            
            filepath = os.path.join(checkpoints_dir, filename)
            
            try:
                with open(filepath, 'r') as f:
                    save_data = json.load(f)
                
                checkpoints.append({
                    "filename": filename,
                    "path": filepath,
                    "timestamp": save_data.get("timestamp"),
                    "datetime": save_data.get("datetime"),
                    "name": save_data.get("metadata", {}).get("checkpoint_name", "Unknown"),
                    "metadata": save_data.get("metadata", {})
                })
            except Exception as e:
                logger.error(f"Error reading checkpoint file {filename}: {e}")
        
        # Sort by timestamp
        checkpoints.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
        
        return checkpoints
    
    def load_checkpoint(self, checkpoint_filename):
        """
        Load a specific checkpoint.
        
        Args:
            checkpoint_filename: Filename of the checkpoint to load
            
        Returns:
            Dictionary containing game state, or None if load failed
        """
        checkpoint_path = os.path.join(self.save_dir, "checkpoints", checkpoint_filename)
        
        if not os.path.exists(checkpoint_path):
            logger.warning(f"Checkpoint file not found: {checkpoint_filename}")
            return None
        
        try:
            # Load JSON
            with open(checkpoint_path, 'r') as f:
                save_data = json.load(f)
            
            logger.info(f"Game loaded from checkpoint: {checkpoint_filename}")
            return save_data.get("game_state")
        except Exception as e:
            logger.error(f"Error loading checkpoint {checkpoint_filename}: {e}")
            return None