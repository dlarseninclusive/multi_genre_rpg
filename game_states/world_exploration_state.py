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
    EARLY_DAWN = 0
    DAWN = 1
    SUNRISE = 2
    MORNING = 3
    NOON = 4
    AFTERNOON = 5
    SUNSET = 6
    DUSK = 7
    EVENING = 8
    MIDNIGHT = 9
    LATE_NIGHT = 10

class Weather(Enum):
    """Enum for different weather conditions."""
    CLEAR = 0
    PARTLY_CLOUDY = 1
    CLOUDY = 2
    MISTY = 3
    LIGHT_RAIN = 4
    RAINY = 5
    STORMY = 6
    FOGGY = 7
    LIGHT_SNOW = 8
    SNOWY = 9
    BLIZZARD = 10

class WorldExplorationState(GameState):
    """
    Game state for world exploration mode.
    
    This state handles:
    - Procedurally generated overworld
    - Camera system following the player
    - Day/night cycle and weather
    - Location discovery and interaction
    - Random encounter generation
    - Transitions to combat, towns, and dungeons
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
        self.target_x = None
        self.target_y = None
        self.move_speed = 5.0  # Tiles per second (adjust as needed)
        
        # Time and weather
        self.time_of_day = TimeOfDay.NOON
        self.weather = Weather.CLEAR
        self.time_counter = 0
        self.weather_counter = 0
        self.day_night_cycle_duration = 600  # Seconds for a full day/night cycle
        self.weather_change_chance = 0.002   # Chance per second to change weather
        self.day_counter = 1
        self.time_cycle_completed = False
        
        # World data
        self.world = None
        self.discover_radius = 5  # Radius (in tiles) around player to discover locations

        # Random encounters
        self.encounter_chance_per_step = 0.02  # Base chance of encounter per tile moved
        self.steps_since_last_encounter = 0
        self.encounter_cooldown = 10  # Minimum steps before another encounter can happen
        self.terrain_encounter_modifiers = {
            TerrainType.WATER.value: 0.3,  # Low chance in water
            TerrainType.BEACH.value: 0.8,  # Slightly lower chance on beaches
            TerrainType.PLAINS.value: 1.0,  # Normal chance on plains
            TerrainType.FOREST.value: 1.5,  # Higher chance in forests
            TerrainType.MOUNTAINS.value: 2.0  # Highest chance in mountains
        }
        self.last_position = (0, 0)  # For tracking movement
        
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
            
        day_counter = self.state_manager.get_persistent_data("day_counter")
        if day_counter is not None:
            self.day_counter = day_counter
        
        # Create player graphic matching town style
        self.player_graphic = self._create_player_graphic()
        
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
        self.state_manager.set_persistent_data("day_counter", self.day_counter)
        
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
                return True
                
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
                
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Left mouse button
                # Convert screen position to world position
                mouse_x, mouse_y = event.pos
                world_x = (mouse_x + self.camera_x) / self.tile_size
                world_y = (mouse_y + self.camera_y) / self.tile_size
                
                # Check if clicking on a location
                clicked_location = None
                for location in self.world["locations"]:
                    if location.discovered:
                        dx = location.x - world_x
                        dy = location.y - world_y
                        distance = math.sqrt(dx*dx + dy*dy)
                        if distance < 1.0:  # Within 1 tile
                            clicked_location = location
                            break
                
                if clicked_location:
                    # Calculate distance to clicked location
                    dx = clicked_location.x - self.player_x
                    dy = clicked_location.y - self.player_y
                    distance = math.sqrt(dx*dx + dy*dy)
                    
                    if distance <= 1.5:  # If close enough, interact with it
                        self.current_location = clicked_location
                        self._interact_with_location()
                    else:  # Otherwise, set it as the movement target
                        self.target_x = clicked_location.x
                        self.target_y = clicked_location.y
                        self.player_moving = True
                    return True
                else:
                    # If clicking on walkable terrain, set it as target
                    if self._is_position_walkable(world_x, world_y):
                        self.target_x = world_x
                        self.target_y = world_y
                        self.player_moving = True
                        return True
    
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
        # If we have a target to move to
        if self.target_x is not None and self.target_y is not None:
            # Calculate direction to target
            dx = self.target_x - self.player_x
            dy = self.target_y - self.player_y
            distance = math.sqrt(dx*dx + dy*dy)
            
            # If close enough to target, snap to it and stop
            if distance < 0.1:  # Close enough threshold
                self.player_x = self.target_x
                self.player_y = self.target_y
                self.target_x = None
                self.target_y = None
                self.player_moving = False
            else:
                # Normalize direction
                dx /= distance
                dy /= distance
                
                # Move towards target
                move_distance = self.move_speed * dt
                # Don't overshoot target
                move_distance = min(move_distance, distance)
                
                new_x = self.player_x + dx * move_distance
                new_y = self.player_y + dy * move_distance
                
                # Check if new position is walkable
                if self._is_position_walkable(new_x, new_y):
                    self.player_x = new_x
                    self.player_y = new_y
                else:
                    # Hit an obstacle, stop moving
                    self.target_x = None
                    self.target_y = None
                    self.player_moving = False
            
            # Update camera to follow player
            self._center_camera_on_player()
            
            # Check for random encounters based on movement
            if abs(self.player_x - self.last_position[0]) > 0.1 or abs(self.player_y - self.last_position[1]) > 0.1:
                self.steps_since_last_encounter += 1
                
                # Get terrain type at current position
                terrain_x, terrain_y = int(self.player_x), int(self.player_y)
                if 0 <= terrain_x < self.world_width and 0 <= terrain_y < self.world_height:
                    terrain_type = self.world["terrain"][terrain_y][terrain_x]
                    terrain_modifier = self.terrain_encounter_modifiers.get(terrain_type, 1.0)
                    
                    # Calculate encounter chance based on terrain and steps since last encounter
                    base_chance = self.encounter_chance_per_step * terrain_modifier
                    cooldown_bonus = max(0, self.steps_since_last_encounter - self.encounter_cooldown) * 0.001
                    encounter_chance = base_chance + cooldown_bonus
                    
                    if random.random() < encounter_chance:
                        self._trigger_random_encounter(terrain_type)
                
                # Update last position for next check
                self.last_position = (self.player_x, self.player_y)
        else:
            # Original keyboard movement code
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
        
        # Calculate distance to location
        dx = self.current_location.x - self.player_x
        dy = self.current_location.y - self.player_y
        distance = math.sqrt(dx*dx + dy*dy)
        
        # Only allow interaction if player is close enough (within 1.5 tiles)
        if distance > 1.5:
            self.event_bus.publish("show_notification", {
                "title": "Too Far Away",
                "message": f"You need to get closer to enter {self.current_location.name}.",
                "duration": 2.0
            })
            return
        
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
                    "town_id": f"town_{self.current_location.name.lower().replace(' ', '_')}",
                    "town_name": self.current_location.name,
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
            
            # Check if we completed a full day cycle
            if next_time_index == 0 and not self.time_cycle_completed:
                self.day_counter += 1
                self.time_cycle_completed = True
                logger.info(f"Day {self.day_counter} has begun")
            elif next_time_index > 0:
                self.time_cycle_completed = False
            
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
            TimeOfDay.EARLY_DAWN: (40, 40, 70),
            TimeOfDay.DAWN: (100, 100, 150),
            TimeOfDay.SUNRISE: (255, 170, 120),
            TimeOfDay.MORNING: (200, 220, 255),
            TimeOfDay.NOON: (100, 180, 255),  # Brightest at noon
            TimeOfDay.AFTERNOON: (180, 220, 255),
            TimeOfDay.SUNSET: (255, 170, 120),
            TimeOfDay.DUSK: (255, 120, 100),
            TimeOfDay.EVENING: (100, 100, 180),
            TimeOfDay.MIDNIGHT: (30, 30, 60),
            TimeOfDay.LATE_NIGHT: (20, 20, 40)
        }
        
        # Weather modifiers
        weather_modifiers = {
            Weather.CLEAR: (0, 0, 0),
            Weather.PARTLY_CLOUDY: (-10, -10, -10),
            Weather.CLOUDY: (-30, -30, -20),
            Weather.MISTY: (10, -5, -10),
            Weather.LIGHT_RAIN: (-20, -20, -10),
            Weather.RAINY: (-50, -50, -30),
            Weather.STORMY: (-80, -80, -50),
            Weather.FOGGY: (20, 0, -20),
            Weather.LIGHT_SNOW: (20, 20, 30),
            Weather.SNOWY: (40, 40, 40),
            Weather.BLIZZARD: (60, 60, 70)
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
        
        # Add weather overlay effects
        if self.weather in [Weather.LIGHT_RAIN, Weather.RAINY, Weather.STORMY]:
            self._render_rain(screen)
        elif self.weather in [Weather.FOGGY, Weather.MISTY]:
            self._render_fog(screen)
        elif self.weather in [Weather.LIGHT_SNOW, Weather.SNOWY, Weather.BLIZZARD]:
            self._render_snow(screen)
    
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
    
    def _render_rain(self, screen):
        """Render rain overlay."""
        # Get screen dimensions
        screen_width, screen_height = screen.get_size()
        
        # Create a semi-transparent surface for the rain
        rain_surface = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
        
        # Rain intensity based on weather
        if self.weather == Weather.LIGHT_RAIN:
            count = 100
            color = (200, 200, 255, 100)
        elif self.weather == Weather.RAINY:
            count = 300
            color = (180, 180, 230, 150)
        else:  # STORMY
            count = 500
            color = (150, 150, 200, 200)
        
        # Draw rain drops
        for _ in range(count):
            x = random.randint(0, screen_width)
            y = random.randint(0, screen_height)
            length = random.randint(5, 15)
            pygame.draw.line(rain_surface, color, (x, y), (x - 2, y + length), 1)
        
        # Blit rain surface onto screen
        screen.blit(rain_surface, (0, 0))

    def _render_fog(self, screen):
        """Render fog overlay."""
        # Get screen dimensions
        screen_width, screen_height = screen.get_size()
        
        # Create a semi-transparent surface for the fog
        fog_surface = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
        
        # Fog density based on weather
        if self.weather == Weather.MISTY:
            alpha = 50
        else:  # FOGGY
            alpha = 120
        
        # Fill with fog color
        fog_surface.fill((255, 255, 255, alpha))
        
        # Blit fog surface onto screen
        screen.blit(fog_surface, (0, 0))

    def _render_snow(self, screen):
        """Render snow overlay."""
        # Get screen dimensions
        screen_width, screen_height = screen.get_size()
        
        # Create a semi-transparent surface for the snow
        snow_surface = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
        
        # Snow intensity based on weather
        if self.weather == Weather.LIGHT_SNOW:
            count = 100
            size_range = (1, 2)
        elif self.weather == Weather.SNOWY:
            count = 300
            size_range = (1, 3)
        else:  # BLIZZARD
            count = 500
            size_range = (1, 4)
        
        # Draw snowflakes
        for _ in range(count):
            x = random.randint(0, screen_width)
            y = random.randint(0, screen_height)
            size = random.randint(*size_range)
            pygame.draw.circle(snow_surface, (255, 255, 255, 200), (x, y), size)
        
        # Blit snow surface onto screen
        screen.blit(snow_surface, (0, 0))
    
    def _render_player(self, screen):
        """Render player character on the world map."""
        # Calculate screen position
        screen_x = int(self.player_x * self.tile_size - self.camera_x + self.tile_size // 2)
        screen_y = int(self.player_y * self.tile_size - self.camera_y + self.tile_size // 2)
        
        # Use the created player graphic if available
        if hasattr(self, 'player_graphic') and self.player_graphic:
            player_rect = self.player_graphic.get_rect(center=(screen_x, screen_y))
            screen.blit(self.player_graphic, player_rect)
        else:
            # Fallback to simple rectangle if graphic not available
            pygame.draw.rect(screen, (0, 0, 255), pygame.Rect(screen_x-5, screen_y-5, 10, 10))
    
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
        box_height = 70  # Increased height for day counter
        box_x = screen.get_width() - box_width - padding
        box_y = padding + 150 + padding  # Below minimap
        
        # Draw box background
        pygame.draw.rect(screen, (0, 0, 0, 150), (box_x, box_y, box_width, box_height))
        pygame.draw.rect(screen, (255, 255, 255), (box_x, box_y, box_width, box_height), 1)
        
        # Draw day counter
        day_text = self.font.render(f"Day: {self.day_counter}", True, (255, 255, 255))
        screen.blit(day_text, (box_x + 10, box_y + 10))
        
        # Draw time of day
        time_text = self.font.render(f"Time: {self.time_of_day.name}", True, (255, 255, 255))
        screen.blit(time_text, (box_x + 10, box_y + 30))
        
        # Draw weather
        weather_text = self.font.render(f"Weather: {self.weather.name}", True, (255, 255, 255))
        screen.blit(weather_text, (box_x + 10, box_y + 50))
    
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
    def _trigger_random_encounter(self, terrain_type):
        """Trigger a random combat encounter based on terrain."""
        # Reset counter
        self.steps_since_last_encounter = 0

        # Get player character
        player_character = self.state_manager.get_persistent_data("player_character")

        # Generate enemy data based on terrain and player level
        player_level = 1
        if player_character:
            player_level = player_character.level

        # Adjust encounter difficulty based on terrain
        terrain_names = {
            TerrainType.WATER.value: "water",
            TerrainType.BEACH.value: "beach",
            TerrainType.PLAINS.value: "plains",
            TerrainType.FOREST.value: "forest",
            TerrainType.MOUNTAINS.value: "mountains"
        }
        terrain_name = terrain_names.get(terrain_type, "plains")

        # Show encounter notification
        self.event_bus.publish("show_notification", {
            "title": "Combat Encounter!",
            "message": f"You've encountered enemies in the {terrain_name}!",
            "duration": 2.0
        })

        # Transition to combat state
        self.change_state("combat", {
            "encounter_type": "random",
            "terrain": terrain_name,
            "player_level": player_level,
            "return_position": (self.player_x, self.player_y)
        })

    def _create_player_graphic(self):
        """Create a player graphic matching the town's pixel art style."""
        tile_size = 32  # Adjust if your world map uses a different size
        surface = pygame.Surface((tile_size, tile_size), pygame.SRCALPHA)
        body_color = (0, 100, 200)       # Default blue
        head_color = (240, 200, 160)      # Default skin tone
        detail_color = (200, 200, 0)      # Default yellow
        character = self.state_manager.get_persistent_data("player_character")
        if character and hasattr(character, "race"):
            race = character.race
            if race.lower() == "elf":
                head_color = (230, 220, 180)
                body_color = (20, 130, 80)
                detail_color = (200, 220, 130)
            elif race.lower() == "dwarf":
                head_color = (220, 170, 140)
                body_color = (120, 70, 30)
                detail_color = (150, 100, 50)
            elif race.lower() == "orc":
                head_color = (100, 170, 100)
                body_color = (80, 80, 80)
                detail_color = (150, 30, 30)
        body_width = tile_size // 2
        body_height = tile_size // 2
        body_x = (tile_size - body_width) // 2
        body_y = tile_size - body_height - 2
        pygame.draw.rect(surface, body_color, (body_x, body_y, body_width, body_height))
        head_size = tile_size // 3
        head_x = (tile_size - head_size) // 2
        head_y = body_y - head_size
        pygame.draw.rect(surface, head_color, (head_x, head_y, head_size, head_size))
        detail_size = max(2, tile_size // 8)
        pygame.draw.rect(surface, detail_color, (body_x, body_y, body_width, detail_size))
        eye_size = max(1, tile_size // 10)
        eye_y = head_y + head_size // 3
        pygame.draw.rect(surface, (0, 0, 0), (head_x + head_size // 4 - eye_size // 2, eye_y, eye_size, eye_size))
        pygame.draw.rect(surface, (0, 0, 0), (head_x + head_size * 3 // 4 - eye_size // 2, eye_y, eye_size, eye_size))
        return surface
