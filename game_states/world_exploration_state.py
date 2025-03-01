import pygame
import logging
import random
import math
import numpy as np
from enum import Enum
from game_state import GameState
from world_generator import WorldGenerator, TerrainType, LocationType, Location

logger = logging.getLogger("world_exploration")

class TimeOfDay(Enum):
    """Enum for different times of day."""
    DAWN = 0
    MORNING = 1
    NOON = 2
    AFTERNOON = 3
    DUSK = 4
    EVENING = 5
    MIDNIGHT = 6
    LATE_NIGHT = 7

class Weather(Enum):
    """Enum for different weather conditions."""
    CLEAR = 0
    CLOUDY = 1
    RAINY = 2
    STORMY = 3
    FOGGY = 4
    SNOWY = 5

class WorldExplorationState(GameState):
    """
    Game state for world exploration mode.
    
    This state handles:
    - Procedurally generated overworld
    - Camera system following the player
    - Day/night cycle and weather
    - Location discovery and interaction
    """
    
    def __init__(self, state_manager, event_bus, settings):
        """Initialize world exploration state."""
        super().__init__(state_manager, event_bus, settings)
        
        # World generation parameters
        self.world_width = 100
        self.world_height = 100
        self.tile_size = 32
        
        # Camera parameters
        self.camera_x = 0
        self.camera_y = 0
        self.camera_speed = 300  # Pixels per second
        
        # Player position (in world coordinates)
        self.player_x = 0
        self.player_y = 0
        self.player_moving = False
        self.player_direction = (0, 0)
        
        # Time and weather
        self.time_of_day = TimeOfDay.NOON
        self.weather = Weather.CLEAR
        self.time_counter = 0
        self.weather_counter = 0
        self.day_night_cycle_duration = 600  # Seconds for a full day/night cycle
        self.weather_change_chance = 0.002   # Chance per second to change weather
        
        # World data
        self.world = None
        self.discover_radius = 5  # Radius (in tiles) around player to discover locations
        
        # UI elements
        self.font = None
        self.show_minimap = True
        self.show_location_labels = True
        self.current_location = None
        
        # Asset placeholders (replace with actual assets)
        self.tile_colors = {
            TerrainType.WATER.value: (0, 100, 255),
            TerrainType.BEACH.value: (255, 255, 150),
            TerrainType.PLAINS.value: (100, 255, 100),
            TerrainType.FOREST.value: (0, 150, 0),
            TerrainType.MOUNTAINS.value: (150, 150, 150)
        }
        
        self.location_colors = {
            LocationType.TOWN.value: (255, 255, 0),
            LocationType.DUNGEON.value: (255, 0, 0),
            LocationType.SPECIAL_SITE.value: (255, 0, 255),
            LocationType.BANDIT_CAMP.value: (200, 100, 0),
            LocationType.RUINS.value: (150, 150, 100)
        }
        
        self.player_color = (255, 255, 255)
        
        # Subscribe to events
        self.event_bus.subscribe("enter_location", self._handle_enter_location)
        self.event_bus.subscribe("exit_location", self._handle_exit_location)
        
        logger.info("WorldExplorationState initialized")
    
    def enter(self, data=None):
        """Set up the state when entered."""
        super().enter(data)
        
        # Initialize font
        pygame.font.init()
        self.font = pygame.font.SysFont(None, 24)
        
        # Get or generate world
        world_data = self.state_manager.get_persistent_data("world")
        if world_data:
            try:
                # Convert the world data back to proper objects if needed
                if isinstance(world_data, dict):
                    # Check if locations are dictionaries instead of Location objects
                    if world_data['locations'] and isinstance(world_data['locations'][0], dict):
                        # Convert location dictionaries to Location objects
                        world_data['locations'] = [
                            Location.from_dict(loc_data) if isinstance(loc_data, dict) else loc_data
                            for loc_data in world_data['locations']
                        ]
                    
                    # Check if rivers are dictionaries instead of River objects
                    if world_data['rivers'] and isinstance(world_data['rivers'][0], dict):
                        # Convert river dictionaries to River objects
                        from world_generator import River  # Import here to avoid circular imports
                        world_data['rivers'] = [
                            River.from_dict(river_data) if isinstance(river_data, dict) else river_data
                            for river_data in world_data['rivers']
                        ]
                    
                    # Ensure terrain is a numpy array
                    if isinstance(world_data['terrain'], list):
                        world_data['terrain'] = np.array(world_data['terrain'])
                    
                self.world = world_data
                logger.info("Loaded existing world")
            except Exception as e:
                logger.error(f"Error loading world data: {e}", exc_info=True)
                self._generate_world()  # Fallback to generating a new world
        else:
            # Generate new world
            self._generate_world()
        
        # Get player position or set default
        player_pos = self.state_manager.get_persistent_data("player_world_position")
        if player_pos:
            self.player_x, self.player_y = player_pos
        else:
            # Default to center of map
            self.player_x = self.world_width // 2
            self.player_y = self.world_height // 2
            
            # Look for a town to start at
            for location in self.world["locations"]:
                if location.location_type == LocationType.TOWN:
                    self.player_x, self.player_y = location.x, location.y
                    location.discovered = True
                    location.visited = True
                    break
        
        # Center camera on player
        self._center_camera_on_player()
        
        # Get time and weather or set defaults
        time_of_day = self.state_manager.get_persistent_data("time_of_day")
        if time_of_day is not None:
            self.time_of_day = time_of_day
        
        weather = self.state_manager.get_persistent_data("weather")
        if weather is not None:
            self.weather = weather
        
        logger.info(f"Entered world exploration at position ({self.player_x}, {self.player_y})")
    
    def exit(self):
        """Clean up when leaving the state."""
        # Save world data
        self.state_manager.set_persistent_data("world", self.world)
        
        # Save player position
        self.state_manager.set_persistent_data("player_world_position", (self.player_x, self.player_y))
        
        # Save time and weather
        self.state_manager.set_persistent_data("time_of_day", self.time_of_day)
        self.state_manager.set_persistent_data("weather", self.weather)
        
        super().exit()
        logger.info("Exited world exploration")
    
    def handle_event(self, event):
        """Handle pygame events."""
        if event.type == pygame.KEYDOWN:
            # Escape key for pause menu
            if event.key == pygame.K_ESCAPE:
                logger.info("Opening pause menu")
                self.push_state("pause_menu")
                return True
                
            # Movement keys
            elif event.key == pygame.K_w or event.key == pygame.K_UP:
                self.player_direction = (self.player_direction[0], -1)
                self.player_moving = True
            elif event.key == pygame.K_s or event.key == pygame.K_DOWN:
                self.player_direction = (self.player_direction[0], 1)
                self.player_moving = True
            elif event.key == pygame.K_a or event.key == pygame.K_LEFT:
                self.player_direction = (-1, self.player_direction[1])
                self.player_moving = True
            elif event.key == pygame.K_d or event.key == pygame.K_RIGHT:
                self.player_direction = (1, self.player_direction[1])
                self.player_moving = True
            
            # Toggle minimap
            elif event.key == pygame.K_m:
                self.show_minimap = not self.show_minimap
            
            # Toggle location labels
            elif event.key == pygame.K_l:
                self.show_location_labels = not self.show_location_labels
            
            # Interact key
            elif event.key == pygame.K_e or event.key == pygame.K_RETURN:
                self._interact_with_location()
                
            # Press 'C' to enter combat (for testing)
            elif event.key == pygame.K_c:
                logger.info("Entering combat mode (test)")
                self.change_state("combat")
        
        elif event.type == pygame.KEYUP:
            # Stop movement
            if event.key in (pygame.K_w, pygame.K_UP) and self.player_direction[1] < 0:
                self.player_direction = (self.player_direction[0], 0)
            elif event.key in (pygame.K_s, pygame.K_DOWN) and self.player_direction[1] > 0:
                self.player_direction = (self.player_direction[0], 0)
            elif event.key in (pygame.K_a, pygame.K_LEFT) and self.player_direction[0] < 0:
                self.player_direction = (0, self.player_direction[1])
            elif event.key in (pygame.K_d, pygame.K_RIGHT) and self.player_direction[0] > 0:
                self.player_direction = (0, self.player_direction[1])
            
            # Check if player is still moving
            if self.player_direction == (0, 0):
                self.player_moving = False
    
    def update(self, dt):
        """Update game state."""
        if not self.active:
            return
        
        # Update time of day
        self._update_time_and_weather(dt)
        
        # Update player movement
        if self.player_moving:
            self._move_player(dt)
        
        # Check for location discovery
        self._check_location_discovery()
        
        # Update current location
        self._update_current_location()
    
    def render(self, screen):
        """Render the game state."""
        if not self.visible:
            return
        
        # Fill background with skybox color based on time of day and weather
        screen.fill(self._get_sky_color())
        
        # Render visible terrain and features
        self._render_terrain(screen)
        
        # Render locations
        self._render_locations(screen)
        
        # Render rivers
        self._render_rivers(screen)
        
        # Render player
        self._render_player(screen)
        
        # Render UI overlays
        if self.show_minimap:
            self._render_minimap(screen)
        
        if self.show_location_labels:
            self._render_location_labels(screen)
        
        # Render current location info if player is at a location
        if self.current_location:
            self._render_location_info(screen)
        
        # Render time and weather indicators
        self._render_time_weather_indicator(screen)
    
    def _generate_world(self):
        """Generate a new world."""
        logger.info("Generating new world")
        
        try:
            # Create world generator
            generator = WorldGenerator(self.world_width, self.world_height)
            
            # Generate world
            self.world = generator.generate()
            
            # Store in persistent data
            self.state_manager.set_persistent_data("world", self.world)
            
            logger.info(f"World generated with {len(self.world['locations'])} locations")
        except Exception as e:
            logger.error(f"Error generating world: {e}", exc_info=True)
            
            # Create a minimal emergency world
            logger.info("Creating minimal emergency world")
            
            # Create a simple terrain array (all plains)
            terrain = np.zeros((self.world_height, self.world_width), dtype=int) + TerrainType.PLAINS.value
            
            # Add a single location (town) at the center
            center_x, center_y = self.world_width // 2, self.world_height // 2
            town = Location(
                center_x, center_y,
                LocationType.TOWN,
                "Emergency Town",
                "A safe haven in a glitched world.",
                difficulty=1
            )
            town.discovered = True
            town.visited = True
            
            # Create minimal world data
            self.world = {
                'terrain': terrain,
                'locations': [town],
                'rivers': [],
                'seed': 0,
                'width': self.world_width,
                'height': self.world_height
            }
            
            # Store in persistent data
            self.state_manager.set_persistent_data("world", self.world)
            
            # Set player position to town
            self.player_x, self.player_y = center_x, center_y
            
            # Show notification about the error
            self.event_bus.publish("show_notification", {
                "title": "World Generation Failed",
                "message": "Created emergency world due to an error.",
                "duration": 5.0
            })
    
    def _move_player(self, dt):
        """Update player position based on direction and speed."""
        # Calculate new position
        dx, dy = self.player_direction
        
        # Normalize diagonal movement
        if dx != 0 and dy != 0:
            dx *= 0.7071  # 1/sqrt(2)
            dy *= 0.7071
        
        new_x = self.player_x + dx * self.camera_speed * dt / self.tile_size
        new_y = self.player_y + dy * self.camera_speed * dt / self.tile_size
        
        # Ensure new position is within world bounds
        new_x = max(0, min(self.world_width - 1, new_x))
        new_y = max(0, min(self.world_height - 1, new_y))
        
        # Check if new position is walkable
        if self._is_position_walkable(new_x, new_y):
            self.player_x = new_x
            self.player_y = new_y
            
            # Update camera to follow player
            self._center_camera_on_player()
    
    def _is_position_walkable(self, x, y):
        """Check if a position is walkable."""
        # Get integer coordinates for tile lookup
        tile_x, tile_y = int(x), int(y)
        
        # Check bounds
        if not (0 <= tile_x < self.world_width and 0 <= tile_y < self.world_height):
            return False
        
        # Get terrain type
        terrain = self.world["terrain"][tile_y][tile_x]
        
        # Water is not walkable
        return terrain != TerrainType.WATER.value
    
    def _center_camera_on_player(self):
        """Center the camera on the player."""
        screen_width, screen_height = pygame.display.get_surface().get_size()
        
        # Calculate center position
        self.camera_x = self.player_x * self.tile_size - screen_width // 2
        self.camera_y = self.player_y * self.tile_size - screen_height // 2
        
        # Clamp camera to world bounds
        max_camera_x = self.world_width * self.tile_size - screen_width
        max_camera_y = self.world_height * self.tile_size - screen_height
        
        self.camera_x = max(0, min(max_camera_x, self.camera_x))
        self.camera_y = max(0, min(max_camera_y, self.camera_y))
    
    def _check_location_discovery(self):
        """Check if player has discovered new locations."""
        for location in self.world["locations"]:
            if not location.discovered:
                # Calculate distance to player
                dx = location.x - self.player_x
                dy = location.y - self.player_y
                distance = math.sqrt(dx*dx + dy*dy)
                
                # If within discovery radius, mark as discovered
                if distance <= self.discover_radius:
                    location.discovered = True
                    logger.info(f"Discovered location: {location.name}")
                    
                    # Show notification
                    self.event_bus.publish("show_notification", {
                        "title": "Location Discovered",
                        "message": f"You discovered {location.name}!",
                        "duration": 3.0
                    })
    
    def _update_current_location(self):
        """Update current location based on player position."""
        old_location = self.current_location
        self.current_location = None
        
        # Check if player is at a location
        for location in self.world["locations"]:
            # Only check discovered locations
            if location.discovered:
                # Calculate distance to player
                dx = location.x - self.player_x
                dy = location.y - self.player_y
                distance = math.sqrt(dx*dx + dy*dy)
                
                # If close enough, mark as current
                if distance < 0.5:  # Within half a tile
                    self.current_location = location
                    
                    # If first time visiting, mark as visited
                    if not location.visited:
                        location.visited = True
                        logger.info(f"Visited location: {location.name}")
                        
                        # Show notification
                        self.event_bus.publish("show_notification", {
                            "title": "Location Visited",
                            "message": f"You arrived at {location.name}!",
                            "duration": 3.0
                        })
                    
                    break
        
        # If changed, update UI
        if self.current_location != old_location:
            if self.current_location:
                logger.debug(f"Now at location: {self.current_location.name}")
            else:
                logger.debug("Left location")
    
    def _interact_with_location(self):
        """Interact with the current location."""
        if not self.current_location:
            return
        
        logger.info(f"Interacting with location: {self.current_location.name}")
        
        try:
            # Handle different location types
            if self.current_location.location_type == LocationType.TOWN:
                # Enter town state
                self.event_bus.publish("show_notification", {
                    "title": "Entering Town",
                    "message": f"Welcome to {self.current_location.name}!",
                    "duration": 3.0
                })
                
                # Change to town state with location data
                self.change_state("town", {
                    "location": self.current_location,
                    "return_position": (self.player_x, self.player_y)
                })
                
            elif self.current_location.location_type == LocationType.DUNGEON:
                # Show notification
                self.event_bus.publish("show_notification", {
                    "title": "Entering Dungeon",
                    "message": f"Entering {self.current_location.name}. Prepare for battle!",
                    "duration": 3.0
                })
                
                # Start combat instead of dungeon for now
                self.change_state("combat", {"location": self.current_location})
                
            elif self.current_location.location_type == LocationType.SPECIAL_SITE:
                # Handle special site interaction
                self.event_bus.publish("show_notification", {
                    "title": "Special Site",
                    "message": f"{self.current_location.description}",
                    "duration": 3.0
                })
        except Exception as e:
            logger.error(f"Error interacting with location: {e}", exc_info=True)
    
    def _update_time_and_weather(self, dt):
        """Update time of day and weather."""
        # Update time counter
        self.time_counter += dt
        
        # Check for day/night cycle progression
        time_per_state = self.day_night_cycle_duration / len(TimeOfDay)
        if self.time_counter >= time_per_state:
            # Move to next time of day
            current_time_index = self.time_of_day.value
            next_time_index = (current_time_index + 1) % len(TimeOfDay)
            self.time_of_day = TimeOfDay(next_time_index)
            
            # Reset counter
            self.time_counter = 0
            
            logger.debug(f"Time of day changed to {self.time_of_day.name}")
        
        # Update weather counter and check for weather change
        self.weather_counter += dt
        
        # Random chance to change weather
        if random.random() < self.weather_change_chance * dt:
            # Choose new weather, weighted toward current
            current_weather = self.weather.value
            weights = [0.1] * len(Weather)
            weights[current_weather] = 0.5  # Higher chance to keep current weather
            
            # Adjust for time of day (e.g., less storms at night)
            if self.time_of_day in [TimeOfDay.EVENING, TimeOfDay.MIDNIGHT, TimeOfDay.LATE_NIGHT]:
                weights[Weather.STORMY.value] *= 0.5
            
            new_weather_index = random.choices(range(len(Weather)), weights=weights)[0]
            self.weather = Weather(new_weather_index)
            
            logger.debug(f"Weather changed to {self.weather.name}")
    
    def _get_sky_color(self):
        """Get sky color based on time of day and weather."""
        # Base colors for different times of day
        base_colors = {
            TimeOfDay.DAWN: (150, 120, 150),
            TimeOfDay.MORNING: (200, 200, 255),
            TimeOfDay.NOON: (100, 180, 255),
            TimeOfDay.AFTERNOON: (180, 220, 255),
            TimeOfDay.DUSK: (255, 180, 150),
            TimeOfDay.EVENING: (100, 100, 180),
            TimeOfDay.MIDNIGHT: (50, 50, 80),
            TimeOfDay.LATE_NIGHT: (30, 30, 50)
        }
        
        # Weather modifiers
        weather_modifiers = {
            Weather.CLEAR: (0, 0, 0),
            Weather.CLOUDY: (-20, -20, -20),
            Weather.RAINY: (-50, -50, -30),
            Weather.STORMY: (-80, -80, -50),
            Weather.FOGGY: (20, 0, -20),
            Weather.SNOWY: (40, 40, 40)
        }
        
        # Get base color for current time
        r, g, b = base_colors[self.time_of_day]
        
        # Apply weather modifier
        mr, mg, mb = weather_modifiers[self.weather]
        r = max(0, min(255, r + mr))
        g = max(0, min(255, g + mg))
        b = max(0, min(255, b + mb))
        
        return (r, g, b)
    
    def _render_terrain(self, screen):
        """Render visible terrain."""
        screen_width, screen_height = screen.get_size()
        
        # Calculate visible tile range
        start_x = max(0, int(self.camera_x / self.tile_size))
        start_y = max(0, int(self.camera_y / self.tile_size))
        end_x = min(self.world_width, start_x + (screen_width // self.tile_size) + 2)
        end_y = min(self.world_height, start_y + (screen_height // self.tile_size) + 2)
        
        # Render tiles
        for y in range(start_y, end_y):
            for x in range(start_x, end_x):
                # Get terrain type and color
                terrain = self.world["terrain"][y][x]
                color = self.tile_colors[terrain]
                
                # Calculate screen position
                screen_x = x * self.tile_size - self.camera_x
                screen_y = y * self.tile_size - self.camera_y
                
                # Adjust color based on time of day
                if self.time_of_day in [TimeOfDay.EVENING, TimeOfDay.MIDNIGHT, TimeOfDay.LATE_NIGHT]:
                    # Darken at night
                    color = (color[0] // 2, color[1] // 2, color[2] // 2)
                
                # Draw tile
                pygame.draw.rect(screen, color, (screen_x, screen_y, self.tile_size, self.tile_size))
                
                # Draw tile border (grid)
                pygame.draw.rect(screen, (0, 0, 0), (screen_x, screen_y, self.tile_size, self.tile_size), 1)
    
    def _render_locations(self, screen):
        """Render discovered locations."""
        for location in self.world["locations"]:
            # Only render discovered locations
            if location.discovered:
                # Calculate screen position
                screen_x = location.x * self.tile_size - self.camera_x
                screen_y = location.y * self.tile_size - self.camera_y
                
                # Check if location is on screen
                if (0 <= screen_x < screen.get_width() and 
                    0 <= screen_y < screen.get_height()):
                    
                    # Get location color
                    color = self.location_colors[location.location_type.value]
                    
                    # Draw location marker
                    pygame.draw.circle(screen, color, 
                                      (int(screen_x + self.tile_size // 2), 
                                       int(screen_y + self.tile_size // 2)), 
                                      self.tile_size // 3)
                    
                    # Draw border
                    pygame.draw.circle(screen, (0, 0, 0), 
                                      (int(screen_x + self.tile_size // 2), 
                                       int(screen_y + self.tile_size // 2)), 
                                      self.tile_size // 3, 1)
    
    def _render_rivers(self, screen):
        """Render rivers."""
        for river in self.world["rivers"]:
            # Draw river as connected line segments
            points = river.points
            
            # Convert world coordinates to screen coordinates
            screen_points = [
                (int(x * self.tile_size - self.camera_x + self.tile_size // 2),
                 int(y * self.tile_size - self.camera_y + self.tile_size // 2))
                for x, y in points
            ]
            
            # Draw river line
            if len(screen_points) > 1:
                pygame.draw.lines(screen, (0, 100, 200), False, screen_points, 3)
    
    def _render_player(self, screen):
        """Render player character."""
        # Calculate screen position
        screen_x = int(self.player_x * self.tile_size - self.camera_x + self.tile_size // 2)
        screen_y = int(self.player_y * self.tile_size - self.camera_y + self.tile_size // 2)
        
        # Draw player marker
        pygame.draw.circle(screen, self.player_color, (screen_x, screen_y), self.tile_size // 2)
        pygame.draw.circle(screen, (0, 0, 0), (screen_x, screen_y), self.tile_size // 2, 2)
    
    def _render_minimap(self, screen):
        """Render mini-map in corner of screen."""
        minimap_size = 150
        minimap_tile_size = minimap_size / max(self.world_width, self.world_height)
        padding = 10
        
        # Create minimap surface
        minimap = pygame.Surface((minimap_size, minimap_size))
        minimap.set_alpha(180)  # Semi-transparent
        
        # Draw terrain
        for y in range(self.world_height):
            for x in range(self.world_width):
                terrain = self.world["terrain"][y][x]
                color = self.tile_colors[terrain]
                
                # Draw minimap tile
                pygame.draw.rect(minimap, color, (
                    x * minimap_tile_size,
                    y * minimap_tile_size,
                    minimap_tile_size,
                    minimap_tile_size
                ))
        
        # Draw discovered locations
        for location in self.world["locations"]:
            if location.discovered:
                color = self.location_colors[location.location_type.value]
                
                pygame.draw.rect(minimap, color, (
                    location.x * minimap_tile_size,
                    location.y * minimap_tile_size,
                    minimap_tile_size,
                    minimap_tile_size
                ))
        
        # Draw player position
        player_minimap_x = int(self.player_x * minimap_tile_size)
        player_minimap_y = int(self.player_y * minimap_tile_size)
        pygame.draw.circle(minimap, (255, 255, 255), 
                         (player_minimap_x, player_minimap_y), 
                         max(2, minimap_tile_size))
        
        # Draw viewport rectangle
        screen_width, screen_height = screen.get_size()
        viewport_width = (screen_width / self.tile_size) * minimap_tile_size
        viewport_height = (screen_height / self.tile_size) * minimap_tile_size
        
        viewport_x = (self.camera_x / self.tile_size) * minimap_tile_size
        viewport_y = (self.camera_y / self.tile_size) * minimap_tile_size
        
        pygame.draw.rect(minimap, (255, 255, 255), (
            viewport_x, viewport_y, viewport_width, viewport_height
        ), 1)
        
        # Draw minimap to screen
        screen.blit(minimap, (screen.get_width() - minimap_size - padding, padding))
    
    def _render_location_labels(self, screen):
        """Render labels for discovered locations."""
        for location in self.world["locations"]:
            # Only render discovered locations
            if location.discovered:
                # Calculate screen position
                screen_x = location.x * self.tile_size - self.camera_x + self.tile_size // 2
                screen_y = location.y * self.tile_size - self.camera_y - 10
                
                # Check if location is on screen
                if (0 <= screen_x < screen.get_width() and 
                    0 <= screen_y < screen.get_height()):
                    
                    # Render location name
                    text_surface = self.font.render(location.name, True, (255, 255, 255))
                    text_rect = text_surface.get_rect(center=(screen_x, screen_y))
                    
                    # Draw text background for better visibility
                    bg_rect = text_rect.inflate(10, 6)
                    pygame.draw.rect(screen, (0, 0, 0, 150), bg_rect)
                    
                    # Draw text
                    screen.blit(text_surface, text_rect)
    
    def _render_location_info(self, screen):
        """Render info box for current location."""
        location = self.current_location
        if not location:
            return
        
        # Create info box at bottom of screen
        box_height = 100
        box_width = screen.get_width() - 20
        box_x = 10
        box_y = screen.get_height() - box_height - 10
        
        # Draw box background
        pygame.draw.rect(screen, (0, 0, 0, 200), (box_x, box_y, box_width, box_height))
        pygame.draw.rect(screen, (255, 255, 255), (box_x, box_y, box_width, box_height), 2)
        
        # Draw location name
        name_text = self.font.render(location.name, True, (255, 255, 255))
        screen.blit(name_text, (box_x + 10, box_y + 10))
        
        # Draw location type
        type_text = self.font.render(f"Type: {location.location_type.name}", True, (200, 200, 200))
        screen.blit(type_text, (box_x + 10, box_y + 35))
        
        # Draw location description
        desc_text = self.font.render(location.description, True, (200, 200, 200))
        screen.blit(desc_text, (box_x + 10, box_y + 60))
        
        # Draw interaction prompt
        prompt_text = self.font.render("Press E to interact", True, (255, 255, 0))
        screen.blit(prompt_text, (box_x + box_width - prompt_text.get_width() - 10, box_y + box_height - 30))
    
    def _render_time_weather_indicator(self, screen):
        """Render time of day and weather indicators."""
        # Create indicator at top-right
        padding = 10
        box_width = 150
        box_height = 50
        box_x = screen.get_width() - box_width - padding
        box_y = padding + 150 + padding  # Below minimap
        
        # Draw box background
        pygame.draw.rect(screen, (0, 0, 0, 150), (box_x, box_y, box_width, box_height))
        pygame.draw.rect(screen, (255, 255, 255), (box_x, box_y, box_width, box_height), 1)
        
        # Draw time of day
        time_text = self.font.render(f"Time: {self.time_of_day.name}", True, (255, 255, 255))
        screen.blit(time_text, (box_x + 10, box_y + 10))
        
        # Draw weather
        weather_text = self.font.render(f"Weather: {self.weather.name}", True, (255, 255, 255))
        screen.blit(weather_text, (box_x + 10, box_y + 30))
    
    def _handle_enter_location(self, data):
        """Handle enter_location event from other states."""
        if "location_id" in data:
            location_id = data["location_id"]
            
            # Find location by ID (index in list)
            if 0 <= location_id < len(self.world["locations"]):
                location = self.world["locations"][location_id]
                
                # Set player position to location
                self.player_x = location.x
                self.player_y = location.y
                
                # Center camera
                self._center_camera_on_player()
                
                logger.info(f"Entered location {location.name} from external state")
    
    def _handle_exit_location(self, _):
        """Handle exit_location event from other states."""
        logger.info("Exited location from external state")
