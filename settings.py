import os
import json
import logging

logger = logging.getLogger("settings")

class Settings:
    """
    Game settings class for storing and loading configuration.
    
    Handles:
    - Screen resolution and display settings
    - Audio settings
    - Gameplay settings
    - Control bindings
    """
    
    def __init__(self, settings_file="settings.json"):
        """
        Initialize settings with default values.
        
        Args:
            settings_file: Path to settings file
        """
        self.settings_file = settings_file
        
        # Display settings
        self.screen_width = 1280
        self.screen_height = 720
        self.fullscreen = False
        self.vsync = True
        self.fps = 60
        
        # Audio settings
        self.sound_enabled = True
        self.music_enabled = True
        self.sound_volume = 0.7
        self.music_volume = 0.5
        
        # Gameplay settings
        self.difficulty = "normal"  # easy, normal, hard
        self.tutorial_enabled = True
        self.auto_save = True
        self.auto_save_interval = 10  # minutes
        
        # Control settings
        self.controls = {
            "move_up": "UP",
            "move_down": "DOWN",
            "move_left": "LEFT",
            "move_right": "RIGHT",
            "interact": "E",
            "inventory": "I",
            "map": "M",
            "pause": "ESCAPE",
            "attack": "SPACE",
            "special": "Q"
        }
        
        # Advanced settings
        self.particle_effects = True
        self.dynamic_lighting = True
        self.show_fps = False
        
        # Try to load settings from file
        self.load_settings()
        
        logger.info("Settings initialized")
    
    def load_settings(self):
        """
        Load settings from file.
        
        Returns:
            Boolean indicating if settings were loaded successfully
        """
        if not os.path.exists(self.settings_file):
            logger.info(f"Settings file not found: {self.settings_file}")
            return False
        
        try:
            with open(self.settings_file, 'r') as f:
                data = json.load(f)
            
            # Update display settings
            if "screen_width" in data:
                self.screen_width = data["screen_width"]
            if "screen_height" in data:
                self.screen_height = data["screen_height"]
            if "fullscreen" in data:
                self.fullscreen = data["fullscreen"]
            if "vsync" in data:
                self.vsync = data["vsync"]
            if "fps" in data:
                self.fps = data["fps"]
            
            # Update audio settings
            if "sound_enabled" in data:
                self.sound_enabled = data["sound_enabled"]
            if "music_enabled" in data:
                self.music_enabled = data["music_enabled"]
            if "sound_volume" in data:
                self.sound_volume = data["sound_volume"]
            if "music_volume" in data:
                self.music_volume = data["music_volume"]
            
            # Update gameplay settings
            if "difficulty" in data:
                self.difficulty = data["difficulty"]
            if "tutorial_enabled" in data:
                self.tutorial_enabled = data["tutorial_enabled"]
            if "auto_save" in data:
                self.auto_save = data["auto_save"]
            if "auto_save_interval" in data:
                self.auto_save_interval = data["auto_save_interval"]
            
            # Update control settings
            if "controls" in data:
                for control, key in data["controls"].items():
                    if control in self.controls:
                        self.controls[control] = key
            
            # Update advanced settings
            if "particle_effects" in data:
                self.particle_effects = data["particle_effects"]
            if "dynamic_lighting" in data:
                self.dynamic_lighting = data["dynamic_lighting"]
            if "show_fps" in data:
                self.show_fps = data["show_fps"]
            
            logger.info(f"Settings loaded from {self.settings_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading settings: {e}")
            return False
    
    def save_settings(self):
        """
        Save settings to file.
        
        Returns:
            Boolean indicating if settings were saved successfully
        """
        # Create settings directory if needed
        settings_dir = os.path.dirname(self.settings_file)
        if settings_dir and not os.path.exists(settings_dir):
            os.makedirs(settings_dir)
        
        try:
            # Create settings dictionary
            data = {
                # Display settings
                "screen_width": self.screen_width,
                "screen_height": self.screen_height,
                "fullscreen": self.fullscreen,
                "vsync": self.vsync,
                "fps": self.fps,
                
                # Audio settings
                "sound_enabled": self.sound_enabled,
                "music_enabled": self.music_enabled,
                "sound_volume": self.sound_volume,
                "music_volume": self.music_volume,
                
                # Gameplay settings
                "difficulty": self.difficulty,
                "tutorial_enabled": self.tutorial_enabled,
                "auto_save": self.auto_save,
                "auto_save_interval": self.auto_save_interval,
                
                # Control settings
                "controls": self.controls,
                
                # Advanced settings
                "particle_effects": self.particle_effects,
                "dynamic_lighting": self.dynamic_lighting,
                "show_fps": self.show_fps
            }
            
            # Save to file
            with open(self.settings_file, 'w') as f:
                json.dump(data, f, indent=4)
            
            logger.info(f"Settings saved to {self.settings_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving settings: {e}")
            return False
    
    def reset_to_defaults(self):
        """Reset all settings to default values."""
        # Display settings
        self.screen_width = 1280
        self.screen_height = 720
        self.fullscreen = False
        self.vsync = True
        self.fps = 60
        
        # Audio settings
        self.sound_enabled = True
        self.music_enabled = True
        self.sound_volume = 0.7
        self.music_volume = 0.5
        
        # Gameplay settings
        self.difficulty = "normal"
        self.tutorial_enabled = True
        self.auto_save = True
        self.auto_save_interval = 10
        
        # Control settings
        self.controls = {
            "move_up": "UP",
            "move_down": "DOWN",
            "move_left": "LEFT",
            "move_right": "RIGHT",
            "interact": "E",
            "inventory": "I",
            "map": "M",
            "pause": "ESCAPE",
            "attack": "SPACE",
            "special": "Q"
        }
        
        # Advanced settings
        self.particle_effects = True
        self.dynamic_lighting = True
        self.show_fps = False
        
        logger.info("Settings reset to defaults")
    
    def get_difficulty_multiplier(self):
        """
        Get difficulty multiplier for game calculations.
        
        Returns:
            Float multiplier (0.75 for easy, 1.0 for normal, 1.5 for hard)
        """
        if self.difficulty == "easy":
            return 0.75
        elif self.difficulty == "hard":
            return 1.5
        else:  # normal
            return 1.0
    
    def get_resolution(self):
        """
        Get current resolution as a tuple.
        
        Returns:
            (width, height) tuple
        """
        return (self.screen_width, self.screen_height)
    
    def get_key_binding(self, action):
        """
        Get key binding for a specific action.
        
        Args:
            action: Action name string
            
        Returns:
            Key name or None if action not found
        """
        return self.controls.get(action)
    
    def set_key_binding(self, action, key):
        """
        Set key binding for a specific action.
        
        Args:
            action: Action name string
            key: Key name string
            
        Returns:
            Boolean indicating success
        """
        if action in self.controls:
            self.controls[action] = key
            return True
        return False
