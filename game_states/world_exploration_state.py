import pygame
import logging
import random
import math
import numpy as np
from enum import Enum
from game_state import GameState
from world_generator import WorldGenerator, TerrainType, LocationType, Location
from faction_system.faction_system import RelationshipStatus, FactionType

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
        self.encounter_chance_per_step = 0.05  # Reduced from 0.1
        self.steps_since_last_encounter = 0
        self.encounter_cooldown = 8  # Increased from 3
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
        
        # Faction system
        self.faction_manager = None
        self.show_territories = True  # Toggle for showing faction territories
        self.territory_alpha = 128  # Transparency for territory overlay
        self.territory_borders = {}  # Cache for territory border calculations
        
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
        self.event_bus.subscribe("territory_contested", self._handle_territory_contested)
        
        logger.info("WorldExplorationState initialized")
    
    def enter(self, data=None):
        """Set up the state when entered."""
        super().enter(data)
        
        # Initialize font
        pygame.font.init()
        self.font = pygame.font.SysFont(None, 24)
        
        # Get faction manager from persistent data
        self.faction_manager = self.state_manager.get_persistent_data("faction_manager")
        
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
        
        # If we have a faction manager, assign territories to factions
        if self.faction_manager:
            self._setup_faction_territories()
        
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
        
        # Check current territory for player
        self._check_current_territory()
        
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
    
    def _handle_enter_location(self, data):
        """Handle entering a location event."""
        location_name = data.get("name", "Unknown")
        location_type = data.get("type")
        location_id = data.get("id")
        
        logger.info(f"Entering location: {location_name}")
        
        # Update current location information
        self.current_location = {
            "name": location_name,
            "type": location_type,
            "id": location_id
        }
        
        # Show notification
        self.event_bus.publish("show_notification", {
            "title": f"Entering {location_name}",
            "message": f"You have arrived at {location_name}",
            "duration": 3.0
        })
        
        # Handle location specific actions
        if location_type == LocationType.TOWN.value:
            # Push town state with location data
            self.state_manager.push_state("town", {"location_name": location_name, "location_id": location_id})
        elif location_type == LocationType.DUNGEON.value:
            # Push dungeon state with location data
            self.state_manager.push_state("dungeon", {"location_name": location_name, "location_id": location_id})
    
    def _handle_exit_location(self, data):
        """Handle exiting a location event."""
        location_name = data.get("name", "Unknown")
        
        logger.info(f"Exiting location: {location_name}")
        
        # Clear current location
        self.current_location = None
        
        # Show notification
        self.event_bus.publish("show_notification", {
            "title": f"Leaving {location_name}",
            "message": f"You have left {location_name}",
            "duration": 2.0
        })
    
    def _get_location_at(self, x, y):
        """Get location at the specified coordinates."""
        for location in self.world["locations"]:
            if math.sqrt((x - location.x)**2 + (y - location.y)**2) < 1.0:
                return location
        return None
    
    def _interact_with_location(self, location):
        """Handle player interaction with a location."""
        logger.info(f"Interacting with location: {location.name}")
        
        # Mark as visited if discovered
        if location.discovered:
            location.visited = True
            
            # Publish location entered event
            self.event_bus.publish("enter_location", {
                "name": location.name,
                "type": location.location_type.value,
                "id": location.name.lower().replace(" ", "_")
            })
            
            # Notify quest system that location was visited
            self.event_bus.publish("location_visited", {
                "location_id": location.name.lower().replace(" ", "_"),
                "location_name": location.name,
                "location_type": location.location_type.value
            })
            
    def _check_location_discovery(self):
        """Check for and discover locations near the player."""
        if not self.world or "locations" not in self.world:
            return
            
        player_x, player_y = self.player_x, self.player_y
        
        # Check each location to see if it's within discovery radius
        for location in self.world["locations"]:
            # Calculate distance to location
            dx = location.x - player_x
            dy = location.y - player_y
            distance = math.sqrt(dx*dx + dy*dy)
            
            # If within discovery radius, mark as discovered
            if distance <= self.discover_radius and not location.discovered:
                location.discovered = True
                logger.info(f"Discovered location: {location.name} ({location.location_type.name})")
                
                # Publish location discovered event
                self.event_bus.publish("location_discovered", {
                    "location_id": location.name.lower().replace(" ", "_"),
                    "location_name": location.name,
                    "location_type": location.location_type.value,
                    "x": location.x,
                    "y": location.y
                })
                
                # Show notification
                self.event_bus.publish("show_notification", {
                    "title": f"Discovered {location.name}",
                    "message": f"You have discovered {location.name}, a {location.location_type.name.lower().replace('_', ' ')}.",
                    "duration": 3.0
                })
    
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
            
            # Toggle territories display with T key
            elif event.key == pygame.K_t:
                self.show_territories = not self.show_territories
                logger.info(f"Territories display {'enabled' if self.show_territories else 'disabled'}")
                return True
                
            # View faction info with F key
            elif event.key == pygame.K_f:
                # Get current controlling faction
                if self.faction_manager:
                    current_loc = self._get_current_location_id()
                    controlling_faction = self.faction_manager.get_controlling_faction(current_loc)
                    if controlling_faction:
                        faction = self.faction_manager.get_faction(controlling_faction)
                        # Show faction info notification
                        self.event_bus.publish("show_notification", {
                            "title": f"Territory of {faction.name}",
                            "message": f"Type: {faction.faction_type.name}, Status: {self.faction_manager.get_player_faction_status(controlling_faction).name}",
                            "duration": 3.0
                        })
                return True
                
        elif event.type == pygame.KEYUP:
            # Handle key releases for movement
            if event.key == pygame.K_w or event.key == pygame.K_UP:
                self.player_direction = (self.player_direction[0], 0)
            elif event.key == pygame.K_s or event.key == pygame.K_DOWN:
                self.player_direction = (self.player_direction[0], 0)
            elif event.key == pygame.K_a or event.key == pygame.K_LEFT:
                self.player_direction = (0, self.player_direction[1])
            elif event.key == pygame.K_d or event.key == pygame.K_RIGHT:
                self.player_direction = (0, self.player_direction[1])
            
            if self.player_direction == (0, 0):
                self.player_moving = False
        
        elif event.type == pygame.MOUSEBUTTONDOWN:
            # Handle mouse clicks
            if event.button == 1:  # Left mouse button
                mouse_x, mouse_y = event.pos
                world_x, world_y = self._screen_to_world(mouse_x, mouse_y)
                
                # Round to nearest tile
                tile_x, tile_y = int(world_x), int(world_y)
                
                # Check if click is within map bounds
                if 0 <= tile_x < self.world_width and 0 <= tile_y < self.world_height:
                    # Check if clicked on a location
                    location = self._get_location_at(tile_x, tile_y)
                    if location and location.discovered:
                        # Handle location click
                        self._interact_with_location(location)
                    else:
                        # Otherwise move player to clicked position
                        self.target_x = tile_x
                        self.target_y = tile_y
                        self.player_moving = True
                        logger.debug(f"Moving to ({tile_x}, {tile_y})")
                
                return True
        
        return False
    
    def update(self, dt):
        """Update game state."""
        if not self.visible:
            return
        
        # Update time of day
        self._update_time_and_weather(dt)
        
        # Store player position for movement detection
        self.last_position = (self.player_x, self.player_y)
        
        # Update player position
        self._move_player(dt)
        
        # Check for location discovery
        self._check_location_discovery()
        
        # Update current location
        self._update_current_location()
        
        # Check if player has entered a new territory
        self._check_current_territory()
    
    def render(self, screen):
        """Render the game state."""
        if not self.visible:
            return
        
        # Fill background with skybox color based on time of day and weather
        screen.fill(self._get_sky_color())
        
        # Render visible terrain and features
        self._render_terrain(screen)
        
        # Render faction territories if enabled
        if self.show_territories and self.faction_manager:
            self._render_territories(screen)
        
        # Render locations
        self._render_locations(screen)
        
        # Render rivers
        self._render_rivers(screen)
        
def _render_location_info(self, screen):
    """Render information about the current location."""
    if not self.current_location:
        return
    panel_height = 60
    panel_width = 400
    panel_x = (screen.get_width() - panel_width) // 2
    panel_y = 10
    pygame.draw.rect(screen, (0, 0, 0, 180), (panel_x, panel_y, panel_width, panel_height))
    pygame.draw.rect(screen, (255, 255, 255), (panel_x, panel_y, panel_width, panel_height), 2)
    name_text = self.font.render(self.current_location["name"], True, (255, 255, 255))
    screen.blit(name_text, (panel_x + 10, panel_y + 10))
    location_type = self.current_location["type"]
    type_text = self.font.render(f"Type: {location_type.replace('_', ' ').title()}", True, (200, 200, 200))
    screen.blit(type_text, (panel_x + 10, panel_y + 35))
    hint_text = self.font.render("Press ENTER to interact", True, (255, 255, 100))
    hint_x = panel_x + panel_width - hint_text.get_width() - 10
    screen.blit(hint_text, (hint_x, panel_y + 35))
        
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
        
        # Render territory info if in a faction territory
        if self.faction_manager:
            self._render_territory_info(screen)
    
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
    
    def _center_camera_on_player(self):
        """Center the camera on the player's position."""
        if hasattr(self, 'screen'):
            screen_width = self.screen.get_width()
            screen_height = self.screen.get_height()
        else:
            # Use default screen dimensions if screen not available yet
            screen_width = 800
            screen_height = 600

        # Calculate camera position to center player
        self.camera_x = int(self.player_x * self.tile_size - screen_width // 2)
        self.camera_y = int(self.player_y * self.tile_size - screen_height // 2)

        # Ensure camera doesn't go beyond map bounds
        self.camera_x = max(0, min(self.camera_x, self.world_width * self.tile_size - screen_width))
        self.camera_y = max(0, min(self.camera_y, self.world_height * self.tile_size - screen_height))

        logger.debug(f"Camera centered at ({self.camera_x}, {self.camera_y})")
        
    def _create_player_graphic(self):
        """Create a simple player graphic."""
        try:
            # Try to load player sprite from assets
            player_sprite = pygame.image.load('assets/characters/player.png').convert_alpha()
            logger.debug("Loaded player sprite from assets")
            return player_sprite
        except (pygame.error, FileNotFoundError):
            # If loading fails, create a simple colored surface
            logger.debug("Creating simple player graphic")
            size = self.tile_size
            surface = pygame.Surface((size, size), pygame.SRCALPHA)
            
            # Draw simple player representation (blue circle with white outline)
            center = size // 2
            radius = size // 3
            pygame.draw.circle(surface, (0, 100, 255), (center, center), radius)  # Blue fill
            pygame.draw.circle(surface, (255, 255, 255), (center, center), radius, 2)  # White outline
            
            # Add direction indicator (small triangle)
            pygame.draw.polygon(surface, (255, 255, 255), [
                (center, center - radius - 5),  # Top point
                (center - 5, center - radius + 5),  # Bottom left
                (center + 5, center - radius + 5)   # Bottom right
            ])
            
            return surface
        
    def _update_time_and_weather(self, dt):
        """Update time of day and weather."""
        # Update time counter
        self.time_counter += dt

        # Calculate current time of day
        day_progress = (self.time_counter % self.day_night_cycle_duration) / self.day_night_cycle_duration

        # Map progress to time of day
        time_values = list(TimeOfDay)
        time_index = int(day_progress * len(time_values))
        new_time = time_values[min(time_index, len(time_values) - 1)]

        # Check if we've completed a day cycle
        if self.time_of_day.value > new_time.value and not self.time_cycle_completed:
            self.day_counter += 1
            self.time_cycle_completed = True
            logger.info(f"Day {self.day_counter} has begun")

            # Publish day change event
            self.event_bus.publish("day_changed", {
                "day": self.day_counter,
                "time_of_day": new_time.name
            })
        elif self.time_of_day.value <= new_time.value:
            self.time_cycle_completed = False

        # Update time of day if changed
        if self.time_of_day != new_time:
            logger.debug(f"Time of day changed from {self.time_of_day.name} to {new_time.name}")
            self.time_of_day = new_time

            # Publish time changed event
            self.event_bus.publish("time_changed", {
                "time_of_day": self.time_of_day.name,
                "day": self.day_counter
            })

        # Update weather
        self.weather_counter += dt

        # Random chance to change weather based on elapsed time
        if random.random() < self.weather_change_chance * dt:
            # Reset counter
            self.weather_counter = 0

            # Get possible weather options based on current time and terrain
            weather_options = self._get_possible_weather()

            # Select new weather
            new_weather = random.choice(weather_options)

            # Update weather if changed
            if self.weather != new_weather:
                logger.info(f"Weather changed from {self.weather.name} to {new_weather.name}")
                self.weather = new_weather

                # Publish weather changed event
                self.event_bus.publish("weather_changed", {
                    "weather": self.weather.name,
                    "time_of_day": self.time_of_day.name
                })
    
    def _get_possible_weather(self):
        """Get possible weather options based on current conditions."""
        # Default options (always possible)
        options = [Weather.CLEAR, Weather.PARTLY_CLOUDY, Weather.CLOUDY]

        # Add time-of-day specific options
        if self.time_of_day in [TimeOfDay.MORNING, TimeOfDay.NOON, TimeOfDay.AFTERNOON]:
            # Daytime options
            options.extend([Weather.LIGHT_RAIN, Weather.RAINY])
        elif self.time_of_day in [TimeOfDay.DUSK, TimeOfDay.EVENING]:
            # Evening options
            options.extend([Weather.MISTY, Weather.FOGGY, Weather.LIGHT_RAIN])
        else:
            # Night options
            options.extend([Weather.FOGGY, Weather.STORMY])

        # Check player's terrain type for additional options
        if hasattr(self, 'world') and self.world is not None:
            try:
                x, y = int(self.player_x), int(self.player_y)
                if 0 <= x < self.world_width and 0 <= y < self.world_height:
                    terrain = self.world["terrain"][y][x]

                    # Add terrain-specific options
                    if terrain == TerrainType.MOUNTAINS.value:
                        if self.time_of_day in [TimeOfDay.EARLY_DAWN, TimeOfDay.MIDNIGHT, TimeOfDay.LATE_NIGHT]:
                            options.extend([Weather.LIGHT_SNOW, Weather.SNOWY])
                    elif terrain in [TerrainType.BEACH.value, TerrainType.WATER.value]:
                        options.extend([Weather.MISTY, Weather.RAINY, Weather.STORMY])
            except (IndexError, KeyError, AttributeError) as e:
                logger.warning(f"Error getting terrain for weather: {e}")

        return options
    
    def _get_sky_color(self):
        """Get sky color based on time of day and weather."""
        # Base colors for different times of day
        time_colors = {
            TimeOfDay.EARLY_DAWN: (50, 50, 80),
            TimeOfDay.DAWN: (150, 100, 150),
            TimeOfDay.SUNRISE: (255, 150, 100),
            TimeOfDay.MORNING: (200, 230, 255),
            TimeOfDay.NOON: (100, 180, 255),
            TimeOfDay.AFTERNOON: (120, 210, 255),
            TimeOfDay.SUNSET: (255, 120, 80),
            TimeOfDay.DUSK: (150, 100, 150),
            TimeOfDay.EVENING: (50, 50, 100),
            TimeOfDay.MIDNIGHT: (20, 20, 50),
            TimeOfDay.LATE_NIGHT: (10, 10, 30)
        }

        # Get base color for current time
        base_color = time_colors.get(self.time_of_day, (100, 180, 255))

        # Adjust for weather
        if self.weather == Weather.CLOUDY:
            return tuple(max(0, c - 50) for c in base_color)
        elif self.weather in [Weather.LIGHT_RAIN, Weather.RAINY, Weather.STORMY]:
            return tuple(max(0, min(c - 70, 150)) for c in base_color)
        elif self.weather in [Weather.FOGGY, Weather.MISTY]:
            return tuple(min(255, c + 50) for c in base_color)
        elif self.weather in [Weather.LIGHT_SNOW, Weather.SNOWY, Weather.BLIZZARD]:
            return tuple(min(255, c + 100) for c in base_color)
        else:
            return base_color

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
                
                # Log every 10 steps
                if self.steps_since_last_encounter % 10 == 0:
                    logger.debug(f"Steps since last encounter: {self.steps_since_last_encounter}")
                
                # Get terrain type at current position
                terrain_x, terrain_y = int(self.player_x), int(self.player_y)
                if 0 <= terrain_x < self.world_width and 0 <= terrain_y < self.world_height:
                    terrain_type = self.world["terrain"][terrain_y][terrain_x]
                    terrain_modifier = self.terrain_encounter_modifiers.get(terrain_type, 1.0)
                    
                    # Calculate encounter chance based on terrain and steps since last encounter
                    base_chance = self.encounter_chance_per_step * terrain_modifier
                    cooldown_bonus = max(0, self.steps_since_last_encounter - self.encounter_cooldown) * 0.001
                    encounter_chance = base_chance + cooldown_bonus
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
                old_x, old_y = self.player_x, self.player_y
                self.player_x = new_x
                self.player_y = new_y
                
                # Update camera to follow player
                self._center_camera_on_player()
                
                # Check for random encounters with keyboard movement too
                if abs(new_x - old_x) > 0.05 or abs(new_y - old_y) > 0.05:
                    self.steps_since_last_encounter += 1
                    
                    # Get terrain type at current position
                    terrain_x, terrain_y = int(self.player_x), int(self.player_y)
                    if 0 <= terrain_x < self.world_width and 0 <= terrain_y < self.world_height:
                        terrain_type = self.world["terrain"][terrain_y][terrain_x]
                        terrain_modifier = self.terrain_encounter_modifiers.get(terrain_type, 1.0)
                        
                        # Calculate encounter chance for keyboard movement
                        base_chance = self.encounter_chance_per_step * terrain_modifier
                        cooldown_bonus = max(0, self.steps_since_last_encounter - self.encounter_cooldown) * 0.001
                        encounter_chance = base_chance + cooldown_bonus
    
    def _update_current_location(self):
        """Update current location information based on player position."""
        current_location = None
        for location in self.world["locations"]:
            if math.sqrt((self.player_x - location.x)**2 + (self.player_y - location.y)**2) < 1.0:
                if location.discovered:
                    current_location = {
                        "name": location.name,
                        "type": location.location_type.value,
                        "id": location.name.lower().replace(" ", "_")
                    }
                    break
        if current_location != self.current_location:
            self.current_location = current_location
            if current_location:
                logger.debug(f"Player entered location: {current_location['name']}")
            else:
                logger.debug("Player left location")
    
    def _is_position_walkable(self, x, y):
        """Check if a position is walkable by the player."""
        # Convert to integer grid coordinates
        grid_x, grid_y = int(x), int(y)
        
        # Check map boundaries
        if grid_x < 0 or grid_x >= self.world_width or grid_y < 0 or grid_y >= self.world_height:
            return False
        
        # Check terrain type
        try:
            terrain = self.world["terrain"][grid_y][grid_x]
            
            # Water and mountains are not walkable
            if terrain == TerrainType.WATER.value:
                return False
                
            # Mountains are not walkable
            if terrain == TerrainType.MOUNTAINS.value:
                return False
                
            # All other terrain types are walkable
            return True
        except (IndexError, KeyError, TypeError) as e:
            logger.error(f"Error checking walkable position: {e}")
            # Default to not walkable if there's an error
            return False

    def _setup_faction_territories(self):
        """
        Assign territories to factions based on world locations.
        This is called once when the world is loaded.
        """
        if not self.faction_manager:
            logger.warning("No faction manager available to set up territories")
            return
        # Check if faction manager has factions attribute, if not initialize it
        if not hasattr(self.faction_manager, 'factions'):
            logger.warning("Faction manager missing factions attribute, initializing empty dictionary")
            self.faction_manager.factions = {}
        
        try:
            # Get all factions
            factions = list(self.faction_manager.factions.values())
            if not factions:
                logger.warning("No factions available to assign territories")
                return
            
            # For each town location, assign it to a faction if not already assigned
            for location in self.world["locations"]:
                if location.location_type == LocationType.TOWN:
                    location_id = location.name.lower().replace(" ", "_")
                    
                    # Check if already controlled
                    controlling_faction = self.faction_manager.get_controlling_faction(location_id)
                    if not controlling_faction:
                        # Assign to a random faction
                        faction = random.choice(factions)
                        faction.controlled_locations.add(location_id)
                        
                        # Create territory data if faction has territory manager
                        if hasattr(self.faction_manager, 'territory_manager'):
                            try:
                                # Add territory with random control level
                                control_level = random.randint(50, 90)
                                self.faction_manager.territory_manager.add_territory(
                                    location_id=location_id,
                                    controlling_faction_id=faction.id,
                                    control_level=control_level
                                )
                                logger.info(f"Assigned territory {location_id} to faction {faction.name}")
                            except Exception as e:
                                logger.error(f"Error adding territory to manager: {e}")
                        else:
                            logger.info(f"Assigned {location_id} to faction {faction.name}")
            
            # Calculate territory influence areas (for rendering)
            self._calculate_territory_borders()
            
        except Exception as e:
            logger.error(f"Error setting up faction territories: {e}")
    
    def _calculate_territory_borders(self):
        """
        Calculate influence areas for faction territories.
        This creates a mapping of tiles to controlling factions.
        """
        if not self.faction_manager:
            return
        
        # Clear existing borders
        self.territory_borders = {}
        
        # Get all controlled locations
        controlled_locations = []
        for faction_id, faction in self.faction_manager.factions.items():
            for location_id in faction.controlled_locations:
                # Find the actual location object
                for loc in self.world["locations"]:
                    loc_id = loc.name.lower().replace(" ", "_")
                    if loc_id == location_id:
                        controlled_locations.append((loc, faction_id))
                        break
        
        # For each tile in the world, determine controlling faction based on proximity
        for y in range(self.world_height):
            for x in range(self.world_width):
                # Skip water tiles
                if self.world["terrain"][y][x] == TerrainType.WATER.value:
                    continue
                
                # Find nearest controlled location
                min_distance = float('inf')
                controlling_faction = None
                
                for location, faction_id in controlled_locations:
                    distance = math.sqrt((x - location.x)**2 + (y - location.y)**2)
                    
                    # Weight distance by faction power if available
                    if hasattr(self.faction_manager.factions[faction_id], 'power_level'):
                        power = self.faction_manager.factions[faction_id].power_level
                        weighted_distance = distance * (100 / power)
                    else:
                        weighted_distance = distance
                    
                    # Territories extend roughly 15 tiles from center
                    influence_radius = 15
                    if weighted_distance < influence_radius and weighted_distance < min_distance:
                        min_distance = weighted_distance
                        controlling_faction = faction_id
                
                # If a faction controls this tile, add to borders
                if controlling_faction:
                    # Check if this is a border tile by looking at neighbors
                    is_border = False
                    
                    # Only store border tiles for efficiency
                    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        nx, ny = x + dx, y + dy
                        
                        # If neighbor is out of bounds or water, consider this a border
                        if (nx < 0 or nx >= self.world_width or ny < 0 or ny >= self.world_height or
                            self.world["terrain"][ny][nx] == TerrainType.WATER.value):
                            is_border = True
                            break
                    
                    # For now, store all territory tiles (could optimize to just borders)
                    self.territory_borders[(x, y)] = {
                        "faction_id": controlling_faction,
                        "is_border": is_border
                    }
    
    def _check_current_territory(self):
        """Check if player has entered a territory and notify."""
        if not self.faction_manager:
            return
        
        # Get current location ID for territory tracking
        location_id = self._get_current_location_id()
        
        # Check for factions territory at player location
        current_tile = (int(self.player_x), int(self.player_y))
        
        # Get controlling faction for this tile
        if current_tile in self.territory_borders:
            faction_id = self.territory_borders[current_tile]["faction_id"]
            
            # Publish territory entered event
            self.event_bus.publish("territory_entered", {
                "location_id": location_id,
                "name": location_id.replace("_", " ").title(),
                "faction_id": faction_id
            })
    
    def _get_current_location_id(self):
        """Get a identifier for the current player location."""
        # Check if at a named location
        for location in self.world["locations"]:
            if math.sqrt((self.player_x - location.x)**2 + (self.player_y - location.y)**2) < 1.5:
                return location.name.lower().replace(" ", "_")
        
        # Otherwise use grid coordinates
        return f"location_{int(self.player_x)}_{int(self.player_y)}"
    
    def _handle_territory_contested(self, data):
        """Handle territory contested event."""
        location_id = data.get("location_id")
        contesting_faction_id = data.get("contesting_faction_id")
        
        if not location_id or not contesting_faction_id:
            return
            
        try:
            # Find the location on the map
            for location in self.world["locations"]:
                loc_id = location.name.lower().replace(" ", "_")
                if loc_id == location_id:
                    # Visual effect for contested territory
                    flash_color = self.faction_manager.factions[contesting_faction_id].primary_color
                    
                    # Update territory visuals
                    self._calculate_territory_borders()
                    
                    # Show notification
                    controlling_faction_id = self.faction_manager.get_controlling_faction(location_id)
                    if controlling_faction_id:
                        controller = self.faction_manager.factions[controlling_faction_id].name
                        contester = self.faction_manager.factions[contesting_faction_id].name
                        
                        self.event_bus.publish("show_notification", {
                            "title": "Territory Contested!",
                            "message": f"{contester} is challenging {controller}'s control of {location.name}.",
                            "duration": 3.0
                        })
                    break
        except Exception as e:
            logger.error(f"Error handling territory contested event: {e}")
    
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
    
    def _render_territories(self, screen):
        """Render faction territory overlays."""
        if not self.faction_manager or not self.territory_borders:
            return
        
        # Calculate visible tile range
        screen_width, screen_height = screen.get_size()
        start_x = max(0, int(self.camera_x / self.tile_size))
        start_y = max(0, int(self.camera_y / self.tile_size))
        end_x = min(self.world_width, start_x + (screen_width // self.tile_size) + 2)
        end_y = min(self.world_height, start_y + (screen_height // self.tile_size) + 2)
        
        # Create a semi-transparent surface for territories
        territory_surface = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
        
        # Render territories
        for y in range(start_y, end_y):
            for x in range(start_x, end_x):
                if (x, y) in self.territory_borders:
                    # Get faction and check if it's a border tile
                    territory = self.territory_borders[(x, y)]
                    faction_id = territory["faction_id"]
                    is_border = territory["is_border"]
                    
                    # Get faction colors
                    if faction_id in self.faction_manager.factions:
                        faction = self.faction_manager.factions[faction_id]
                        
                        # Calculate screen position
                        screen_x = x * self.tile_size - self.camera_x
                        screen_y = y * self.tile_size - self.camera_y
                        
                        # Fill area with semi-transparent faction color
                        primary_color = list(faction.primary_color) + [50]  # Add alpha channel
                        pygame.draw.rect(territory_surface, primary_color, 
                                       (screen_x, screen_y, self.tile_size, self.tile_size))
                        
                        # Draw stronger border for territory edges
                        if is_border:
                            secondary_color = list(faction.secondary_color) + [150]  # More opaque
                            pygame.draw.rect(territory_surface, secondary_color, 
                                           (screen_x, screen_y, self.tile_size, self.tile_size), 2)
        
        # Blend territory surface onto screen
        screen.blit(territory_surface, (0, 0))
    
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
    
    def _render_territory_info(self, screen):
        """Render territory information if player is in a faction territory."""
        # Check if player is in a faction territory
        current_tile = (int(self.player_x), int(self.player_y))
        if current_tile not in self.territory_borders:
            return
            
        faction_id = self.territory_borders[current_tile]["faction_id"]
        if not faction_id or faction_id not in self.faction_manager.factions:
            return
            
        faction = self.faction_manager.factions[faction_id]
        player_status = self.faction_manager.get_player_faction_status(faction_id)
        
        # Create territory info panel at bottom of screen
        panel_height = 40
        panel_rect = pygame.Rect(
            10, 
            screen.get_height() - panel_height - 10,
            screen.get_width() - 20,
            panel_height
        )
        
        # Create semi-transparent panel
        panel_surface = pygame.Surface((panel_rect.width, panel_rect.height), pygame.SRCALPHA)
        panel_surface.fill((40, 40, 50, 180))  # Semi-transparent background
        
        # Add faction color stripe
        pygame.draw.rect(panel_surface, faction.primary_color, 
                        (0, 0, panel_rect.width, 5))
        
        # Add faction information text
        text = f"Territory: {faction.name} ({faction.faction_type.name}) - Status: {player_status.name}"
        text_surface = self.font.render(text, True, (255, 255, 255))
        panel_surface.blit(text_surface, (10, 12))
        
        # Add key hint
        hint = "Press F for details"
        hint_surface = self.font.render(hint, True, (200, 200, 200))
        panel_surface.blit(hint_surface, (panel_rect.width - hint_surface.get_width() - 10, 12))
        
        # Draw panel to screen
        screen.blit(panel_surface, panel_rect)
    
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
            size_range = (2, 4)
        
        # Draw snowflakes
        for _ in range(count):
            x = random.randint(0, screen_width)
            y = random.randint(0, screen_height)
            size = random.randint(*size_range)
            pygame.draw.circle(snow_surface, (255, 255, 255, 150), (x, y), size)
        
        # Blit snow surface onto screen
        screen.blit(snow_surface, (0, 0))
def _render_location_labels(self, screen):
    """Render labels for discovered locations."""
    if not self.font:
        return
    for location in self.world["locations"]:
        if location.discovered:
            screen_x = location.x * self.tile_size - self.camera_x
            screen_y = location.y * self.tile_size - self.camera_y
            if (-100 <= screen_x <= screen.get_width() + 100 and 
                -50 <= screen_y <= screen.get_height() + 50):
                text = location.name
                text_surface = self.font.render(text, True, (255, 255, 255))
                text_x = screen_x + self.tile_size // 2 - text_surface.get_width() // 2
                text_y = screen_y - text_surface.get_height() - 5
                shadow_surface = self.font.render(text, True, (0, 0, 0))
                screen.blit(shadow_surface, (text_x + 1, text_y + 1))
                screen.blit(text_surface, (text_x, text_y))
def _render_time_weather_indicator(self, screen):
    """Render time of day and weather indicators."""
    if not self.font:
        return
    time_text = f"Day {self.day_counter} - {self.time_of_day.name.replace('_', ' ').title()}"
    weather_text = f"Weather: {self.weather.name.replace('_', ' ').title()}"
    time_surface = self.font.render(time_text, True, (255, 255, 255))
    weather_surface = self.font.render(weather_text, True, (255, 255, 255))
    time_x = screen.get_width() - time_surface.get_width() - 10
    time_y = 10
    weather_x = screen.get_width() - weather_surface.get_width() - 10
    weather_y = 40
    shadow_time = self.font.render(time_text, True, (0, 0, 0))
    shadow_weather = self.font.render(weather_text, True, (0, 0, 0))
    screen.blit(shadow_time, (time_x + 1, time_y + 1))
    screen.blit(time_surface, (time_x, time_y))
    screen.blit(shadow_weather, (weather_x + 1, weather_y + 1))
    screen.blit(weather_surface, (weather_x, weather_y))
def _screen_to_world(self, screen_x, screen_y):
    """Convert screen coordinates to world coordinates."""
    world_x = (screen_x + self.camera_x) / self.tile_size
    world_y = (screen_y + self.camera_y) / self.tile_size
    return world_x, world_y
