import random
import noise
import numpy as np
import logging
from enum import Enum

logger = logging.getLogger("world_generator")

class TerrainType(Enum):
    """Enum for different terrain types."""
    WATER = 0
    BEACH = 1
    PLAINS = 2
    FOREST = 3
    MOUNTAINS = 4

class LocationType(Enum):
    """Enum for different location types."""
    TOWN = 0
    DUNGEON = 1
    SPECIAL_SITE = 2
    BANDIT_CAMP = 3
    RUINS = 4

class Location:
    """Represents a special location on the world map."""
    
    def __init__(self, x, y, location_type, name, description, difficulty=1):
        """
        Initialize a location.
        
        Args:
            x: X coordinate on the world grid
            y: Y coordinate on the world grid
            location_type: Type of location (from LocationType enum)
            name: Name of the location
            description: Brief description of the location
            difficulty: Difficulty level (1-10) affecting encounters
        """
        self.x = x
        self.y = y
        self.location_type = location_type
        self.name = name
        self.description = description
        self.difficulty = difficulty
        self.discovered = False  # Whether player has discovered this location
        self.visited = False     # Whether player has visited this location
        self.cleared = False     # Whether location has been cleared (dungeons)
        self.connected_locations = []  # List of connected location IDs
    
    def to_dict(self):
        """Convert location to dictionary for serialization."""
        return {
            'x': self.x,
            'y': self.y,
            'type': self.location_type.value,
            'name': self.name,
            'description': self.description,
            'difficulty': self.difficulty,
            'discovered': self.discovered,
            'visited': self.visited,
            'cleared': self.cleared,
            'connected_locations': self.connected_locations
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create location from dictionary."""
        location = cls(
            data['x'],
            data['y'],
            LocationType(data['type']),
            data['name'],
            data['description'],
            data['difficulty']
        )
        location.discovered = data['discovered']
        location.visited = data['visited']
        location.cleared = data['cleared']
        location.connected_locations = data['connected_locations']
        return location

class River:
    """Represents a river flowing through the world."""
    
    def __init__(self, points):
        """
        Initialize a river.
        
        Args:
            points: List of (x, y) coordinates the river flows through
        """
        self.points = points
    
    def to_dict(self):
        """Convert river to dictionary for serialization."""
        return {
            'points': self.points
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create river from dictionary."""
        return cls(data['points'])

class WorldGenerator:
    """Procedural world generation system."""
    
    def __init__(self, width, height, seed=None):
        """
        Initialize the world generator.
        
        Args:
            width: Width of the world grid
            height: Height of the world grid
            seed: Random seed for generation (None for random)
        """
        self.width = width
        self.height = height
        
        # Set random seed
        self.seed = seed if seed is not None else random.randint(0, 1000000)
        random.seed(self.seed)
        
        # World data
        self.terrain = np.zeros((height, width), dtype=int)
        self.locations = []
        self.rivers = []
        
        logger.info(f"WorldGenerator initialized with size {width}x{height}, seed {self.seed}")
    
    def generate(self):
        """Generate a complete world with terrain, locations, and rivers."""
        logger.info("Starting world generation")
        
        self._generate_terrain()
        self._generate_rivers()
        self._generate_locations()
        
        logger.info("World generation completed")
        return {
            'terrain': self.terrain,
            'locations': self.locations,
            'rivers': self.rivers,
            'seed': self.seed,
            'width': self.width,
            'height': self.height
        }
    
    def _generate_terrain(self):
        """Generate the base terrain using noise functions."""
        logger.info("Generating terrain")
        
        # Parameters for noise generation
        scale = 100.0
        octaves = 6
        persistence = 0.5
        lacunarity = 2.0
        
        for y in range(self.height):
            for x in range(self.width):
                # Generate base noise value
                nx = x / self.width - 0.5
                ny = y / self.height - 0.5
                
                # Elevation noise
                elevation = noise.pnoise2(
                    nx * scale,
                    ny * scale,
                    octaves=octaves,
                    persistence=persistence,
                    lacunarity=lacunarity,
                    repeatx=self.width,
                    repeaty=self.height,
                    base=self.seed
                )
                
                # Moisture noise (for determining forest vs. plains)
                moisture = noise.pnoise2(
                    nx * scale * 2,
                    ny * scale * 2,
                    octaves=octaves - 2,
                    persistence=persistence,
                    lacunarity=lacunarity,
                    repeatx=self.width,
                    repeaty=self.height,
                    base=self.seed + 1
                )
                
                # Map noise values to terrain types
                if elevation < -0.2:
                    self.terrain[y][x] = TerrainType.WATER.value
                elif elevation < -0.15:
                    self.terrain[y][x] = TerrainType.BEACH.value
                elif elevation > 0.3:
                    self.terrain[y][x] = TerrainType.MOUNTAINS.value
                elif moisture > 0.1:
                    self.terrain[y][x] = TerrainType.FOREST.value
                else:
                    self.terrain[y][x] = TerrainType.PLAINS.value
    
    def _generate_rivers(self):
        """Generate rivers flowing from mountains to water."""
        logger.info("Generating rivers")
        
        # Find mountain and water tiles
        mountain_tiles = []
        water_tiles = []
        
        for y in range(self.height):
            for x in range(self.width):
                if self.terrain[y][x] == TerrainType.MOUNTAINS.value:
                    mountain_tiles.append((x, y))
                elif self.terrain[y][x] == TerrainType.WATER.value:
                    water_tiles.append((x, y))
        
        # Number of rivers to generate
        num_rivers = min(len(mountain_tiles) // 10 + 1, 10)
        
        for _ in range(num_rivers):
            if not mountain_tiles:
                break
                
            # Start from a random mountain tile
            start_idx = random.randint(0, len(mountain_tiles) - 1)
            start = mountain_tiles.pop(start_idx)
            
            # Find path to nearest water
            river_points = self._generate_river_path(start, water_tiles)
            
            if river_points:
                # Create river and mark tiles
                self.rivers.append(River(river_points))
                
                # Update terrain (ensure river tiles are marked as water)
                for x, y in river_points:
                    if 0 <= x < self.width and 0 <= y < self.height:
                        if self.terrain[y][x] != TerrainType.WATER.value:
                            self.terrain[y][x] = TerrainType.WATER.value
    
    def _generate_river_path(self, start, water_tiles):
        """
        Generate a path for a river from start to nearest water.
        
        Args:
            start: Starting (x, y) coordinates (mountain)
            water_tiles: List of (x, y) coordinates of water tiles
            
        Returns:
            List of (x, y) coordinates for the river path
        """
        if not water_tiles:
            return []
            
        # Find nearest water tile
        nearest_water = min(water_tiles, key=lambda w: ((w[0] - start[0])**2 + (w[1] - start[1])**2))
        
        # Generate path with some randomness
        path = [start]
        current = start
        
        while current != nearest_water:
            x, y = current
            
            # Potential moves (with diagonal moves)
            moves = [
                (x+1, y), (x-1, y), (x, y+1), (x, y-1),
                (x+1, y+1), (x+1, y-1), (x-1, y+1), (x-1, y-1)
            ]
            
            # Filter valid moves
            valid_moves = [
                move for move in moves
                if 0 <= move[0] < self.width and 0 <= move[1] < self.height
            ]
            
            if not valid_moves:
                break
                
            # Choose move that gets closest to water with some randomness
            move_scores = []
            for move in valid_moves:
                dist = ((move[0] - nearest_water[0])**2 + (move[1] - nearest_water[1])**2)
                # Add randomness to avoid straight lines
                randomness = random.uniform(0, 5)
                score = dist + randomness
                move_scores.append((move, score))
            
            next_move = min(move_scores, key=lambda x: x[1])[0]
            
            # Check if we've reached water
            if self.terrain[next_move[1]][next_move[0]] == TerrainType.WATER.value:
                path.append(next_move)
                break
                
            # Add to path and continue
            path.append(next_move)
            current = next_move
            
            # Prevent infinite loops
            if len(path) > (self.width + self.height):
                break
        
        return path
    
    def _generate_locations(self):
        """Generate special locations throughout the world."""
        logger.info("Generating locations")
        
        # Determine number of locations based on map size
        num_towns = max(3, self.width * self.height // 1000)
        num_dungeons = max(5, self.width * self.height // 800)
        num_special = max(2, self.width * self.height // 1200)
        
        # Generate towns (prefer plains near water)
        self._generate_towns(num_towns)
        
        # Generate dungeons (prefer mountains and forests)
        self._generate_dungeons(num_dungeons)
        
        # Generate special sites (can be anywhere)
        self._generate_special_sites(num_special)
        
        # Connect locations with paths
        self._connect_locations()
    
    def _generate_towns(self, count):
        """
        Generate town locations.
        
        Args:
            count: Number of towns to generate
        """
        suitable_tiles = []
        
        # Find suitable tiles for towns (plains near water)
        for y in range(self.height):
            for x in range(self.width):
                if self.terrain[y][x] == TerrainType.PLAINS.value:
                    # Check if near water
                    near_water = False
                    for dx in range(-2, 3):
                        for dy in range(-2, 3):
                            nx, ny = x + dx, y + dy
                            if (0 <= nx < self.width and 0 <= ny < self.height and 
                                self.terrain[ny][nx] == TerrainType.WATER.value):
                                near_water = True
                                break
                        if near_water:
                            break
                    
                    if near_water:
                        suitable_tiles.append((x, y))
        
        # If not enough suitable tiles, use any plains
        if len(suitable_tiles) < count:
            for y in range(self.height):
                for x in range(self.width):
                    if self.terrain[y][x] == TerrainType.PLAINS.value:
                        suitable_tiles.append((x, y))
        
        # Generate towns
        town_names = [
            "Riverdale", "Oakridge", "Pinecrest", "Meadowbrook",
            "Willowshire", "Elmwood", "Lakeview", "Springvale",
            "Highfield", "Brookside", "Greenholm", "Stonehaven"
        ]
        
        for i in range(min(count, len(suitable_tiles))):
            # Choose a location
            if suitable_tiles:
                idx = random.randint(0, len(suitable_tiles) - 1)
                x, y = suitable_tiles.pop(idx)
                
                # Generate town name
                name = random.choice(town_names)
                town_names.remove(name)
                if not town_names:  # Replenish if we run out
                    town_names = [f"New {name}" for name in town_names]
                
                # Create town location
                town = Location(
                    x, y,
                    LocationType.TOWN,
                    name,
                    f"{name} is a small settlement known for its {random.choice(['trade', 'fishing', 'farming', 'crafting'])}.",
                    difficulty=1  # Towns are safe
                )
                
                # Add to locations
                self.locations.append(town)
    
    def _generate_dungeons(self, count):
        """
        Generate dungeon locations.
        
        Args:
            count: Number of dungeons to generate
        """
        suitable_tiles = []
        
        # Find suitable tiles for dungeons (mountains and forests)
        for y in range(self.height):
            for x in range(self.width):
                if (self.terrain[y][x] == TerrainType.MOUNTAINS.value or 
                    self.terrain[y][x] == TerrainType.FOREST.value):
                    suitable_tiles.append((x, y))
        
        # Dungeon names and types
        dungeon_prefixes = ["Dark", "Cursed", "Ancient", "Forbidden", "Lost", "Haunted", "Forgotten"]
        dungeon_types = ["Caves", "Ruins", "Temple", "Catacombs", "Mines", "Tomb", "Lair"]
        
        for i in range(min(count, len(suitable_tiles))):
            if suitable_tiles:
                idx = random.randint(0, len(suitable_tiles) - 1)
                x, y = suitable_tiles.pop(idx)
                
                # Generate dungeon name
                prefix = random.choice(dungeon_prefixes)
                dungeon_type = random.choice(dungeon_types)
                name = f"{prefix} {dungeon_type}"
                
                # Set difficulty based on distance from center
                center_x, center_y = self.width // 2, self.height // 2
                distance = ((x - center_x)**2 + (y - center_y)**2)**0.5
                max_distance = ((self.width // 2)**2 + (self.height // 2)**2)**0.5
                difficulty = max(1, min(10, int(distance / max_distance * 10) + 1))
                
                # Create dungeon location
                dungeon = Location(
                    x, y,
                    LocationType.DUNGEON,
                    name,
                    f"{name} is said to be filled with {random.choice(['treasures', 'monsters', 'traps', 'mysteries'])}.",
                    difficulty=difficulty
                )
                
                # Add to locations
                self.locations.append(dungeon)
    
    def _generate_special_sites(self, count):
        """
        Generate special site locations.
        
        Args:
            count: Number of special sites to generate
        """
        # Find all tiles that don't already have a location
        available_tiles = []
        
        existing_locations = set((loc.x, loc.y) for loc in self.locations)
        
        for y in range(self.height):
            for x in range(self.width):
                if (self.terrain[y][x] != TerrainType.WATER.value and 
                    (x, y) not in existing_locations):
                    available_tiles.append((x, y))
        
        # Special site names and descriptions
        special_sites = [
            ("Ancient Shrine", "A shrine dedicated to forgotten gods."),
            ("Wizard's Tower", "A mysterious tower that seems to disappear at times."),
            ("Standing Stones", "A circle of stones with strange markings."),
            ("Giant Tree", "An enormous tree that reaches into the clouds."),
            ("Crystal Cave", "A cave with walls that shimmer like diamonds."),
            ("Abandoned Village", "A village where everyone mysteriously vanished."),
            ("Sky Pillar", "A pillar that seems to connect earth and sky."),
            ("Fairy Pool", "A shimmering pool said to be home to mystical beings.")
        ]
        
        for i in range(min(count, len(available_tiles), len(special_sites))):
            if available_tiles:
                idx = random.randint(0, len(available_tiles) - 1)
                x, y = available_tiles.pop(idx)
                
                # Choose a special site
                name, description = special_sites[i]
                
                # Set random difficulty
                difficulty = random.randint(2, 8)
                
                # Create special site location
                special_site = Location(
                    x, y,
                    LocationType.SPECIAL_SITE,
                    name,
                    description,
                    difficulty=difficulty
                )
                
                # Add to locations
                self.locations.append(special_site)
    
    def _connect_locations(self):
        """Create connections between locations to form paths."""
        if len(self.locations) < 2:
            return
            
        # Use a simple algorithm to connect all locations
        # First, connect closest pairs to form a minimum spanning tree
        connected = set([0])  # Start with the first location
        unconnected = set(range(1, len(self.locations)))
        
        while unconnected:
            best_distance = float('inf')
            best_connection = None
            
            # Find the closest connection between a connected and unconnected location
            for connected_idx in connected:
                connected_loc = self.locations[connected_idx]
                
                for unconnected_idx in unconnected:
                    unconnected_loc = self.locations[unconnected_idx]
                    
                    distance = ((connected_loc.x - unconnected_loc.x)**2 + 
                               (connected_loc.y - unconnected_loc.y)**2)**0.5
                    
                    if distance < best_distance:
                        best_distance = distance
                        best_connection = (connected_idx, unconnected_idx)
            
            if best_connection:
                idx1, idx2 = best_connection
                
                # Add connection
                self.locations[idx1].connected_locations.append(idx2)
                self.locations[idx2].connected_locations.append(idx1)
                
                # Update sets
                connected.add(idx2)
                unconnected.remove(idx2)
            else:
                break
        
        # Add a few more connections to create loops (about 10% more connections)
        extra_connections = max(1, len(self.locations) // 10)
        
        for _ in range(extra_connections):
            # Choose two random locations
            idx1 = random.randint(0, len(self.locations) - 1)
            idx2 = random.randint(0, len(self.locations) - 1)
            
            # Make sure they're different and not already connected
            if (idx1 != idx2 and
                idx2 not in self.locations[idx1].connected_locations):
                
                # Add connection
                self.locations[idx1].connected_locations.append(idx2)
                self.locations[idx2].connected_locations.append(idx1)
    
    def to_dict(self):
        """Convert world to dictionary for serialization."""
        return {
            'width': self.width,
            'height': self.height,
            'seed': self.seed,
            'terrain': self.terrain.tolist(),
            'locations': [loc.to_dict() for loc in self.locations],
            'rivers': [river.to_dict() for river in self.rivers]
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create world from dictionary."""
        world = cls(data['width'], data['height'], data['seed'])
        world.terrain = np.array(data['terrain'])
        world.locations = [Location.from_dict(loc_data) for loc_data in data['locations']]
        world.rivers = [River.from_dict(river_data) for river_data in data['rivers']]
        return world
