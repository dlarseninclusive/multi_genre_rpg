import pygame
import logging
import random
import math
from enum import Enum
import numpy as np
from game_state import GameState
from world_generator import LocationType

logger = logging.getLogger("dungeon")

class TileType(Enum):
    """Dungeon tile types."""
    WALL = 0
    FLOOR = 1
    DOOR = 2
    STAIRS_UP = 3
    STAIRS_DOWN = 4
    TRAP = 5
    WATER = 6
    LAVA = 7

class EntityType(Enum):
    """Entity types within the dungeon."""
    PLAYER = 0
    MONSTER = 1
    ITEM = 2
    CHEST = 3
    NPC = 4

class Entity:
    """Base class for all entities in the dungeon."""
    
    def __init__(self, x, y, entity_type, name, color=(255, 255, 255)):
        """
        Initialize an entity.
        
        Args:
            x: X position in dungeon
            y: Y position in dungeon
            entity_type: Type from EntityType enum
            name: Entity name
            color: RGB color tuple
        """
        self.x = x
        self.y = y
        self.entity_type = entity_type
        self.name = name
        self.color = color
        self.visible = True
        self.blocks_movement = True
    
    def move(self, dx, dy, dungeon):
        """
        Move the entity.
        
        Args:
            dx: X direction
            dy: Y direction
            dungeon: Dungeon instance
            
        Returns:
            Boolean indicating if move was successful
        """
        new_x = self.x + dx
        new_y = self.y + dy
        
        # Check if new position is valid
        if dungeon.is_position_valid(new_x, new_y):
            self.x = new_x
            self.y = new_y
            return True
        
        return False
    
    def distance_to(self, other):
        """
        Calculate distance to another entity.
        
        Args:
            other: Other entity
            
        Returns:
            Euclidean distance
        """
        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)

class Monster(Entity):
    """Monster entity that can attack the player."""
    
    def __init__(self, x, y, name, health, damage, color=(255, 0, 0)):
        """
        Initialize a monster.
        
        Args:
            x: X position in dungeon
            y: Y position in dungeon
            name: Monster name
            health: Health points
            damage: Attack damage
            color: RGB color tuple
        """
        super().__init__(x, y, EntityType.MONSTER, name, color)
        self.health = health
        self.max_health = health
        self.damage = damage
        self.aggro_range = 6  # How far away the monster can detect the player
        self.state = "idle"   # idle, alert, attacking
    
    def update(self, dungeon, player):
        """
        Update the monster's state and actions.
        
        Args:
            dungeon: Dungeon instance
            player: Player entity
        """
        # Check if monster can see player
        distance = self.distance_to(player)
        
        if distance <= self.aggro_range:
            # If player is in range, chase them
            self.state = "alert"
            
            # Get direction to player
            path = self._get_path_to_player(dungeon, player)
            
            if path and len(path) > 1:
                # Move along path
                next_pos = path[1]  # First step after current position
                dx = next_pos[0] - self.x
                dy = next_pos[1] - self.y
                
                # Check for entities at target position
                target_entity = dungeon.get_entity_at(self.x + dx, self.y + dy)
                
                if target_entity and target_entity.entity_type == EntityType.PLAYER:
                    # Attack the player
                    self.attack(player, dungeon)
                elif not target_entity or not target_entity.blocks_movement:
                    # Move if no blocking entity
                    self.move(dx, dy, dungeon)
        else:
            # If player is out of range, go idle
            self.state = "idle"
            
            # Occasionally move randomly when idle
            if random.random() < 0.2:
                dx = random.choice([-1, 0, 1])
                dy = random.choice([-1, 0, 1])
                self.move(dx, dy, dungeon)
    
    def _get_path_to_player(self, dungeon, player):
        """
        Get path to player using simple pathfinding.
        
        Args:
            dungeon: Dungeon instance
            player: Player entity
            
        Returns:
            List of (x, y) tuples representing the path, or None if no path found
        """
        # Using a simplified A* algorithm
        start = (self.x, self.y)
        goal = (player.x, player.y)
        
        # If direct path is very short, return it
        if self.distance_to(player) <= 1.5:
            return [start, goal]
        
        # For longer paths, use A*
        frontier = [(0, start)]  # Priority queue with (priority, position)
        came_from = {start: None}
        cost_so_far = {start: 0}
        
        while frontier:
            # Get position with lowest priority
            current_priority, current = frontier.pop(0)
            
            # Check if goal reached
            if current == goal:
                break
                
            # Check all neighbors
            for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                next_pos = (current[0] + dx, current[1] + dy)
                
                # Skip if position is not valid
                if not dungeon.is_position_valid(next_pos[0], next_pos[1]):
                    continue
                
                # Calculate new cost
                new_cost = cost_so_far[current] + 1
                
                # If position not visited or new cost is lower
                if next_pos not in cost_so_far or new_cost < cost_so_far[next_pos]:
                    cost_so_far[next_pos] = new_cost
                    priority = new_cost + self._heuristic(next_pos, goal)
                    
                    # Add to frontier with priority
                    index = 0
                    while index < len(frontier) and frontier[index][0] < priority:
                        index += 1
                    frontier.insert(index, (priority, next_pos))
                    
                    came_from[next_pos] = current
        
        # Reconstruct path if goal was reached
        if goal in came_from:
            path = [goal]
            current = goal
            
            while current != start:
                current = came_from[current]
                path.append(current)
            
            path.reverse()
            return path
        
        return None
    
    def _heuristic(self, a, b):
        """
        Heuristic function for A* pathfinding.
        
        Args:
            a: Start position tuple (x, y)
            b: Goal position tuple (x, y)
            
        Returns:
            Estimated cost to reach goal
        """
        # Manhattan distance
        return abs(a[0] - b[0]) + abs(a[1] - b[1])
    
    def attack(self, player, dungeon):
        """
        Attack the player.
        
        Args:
            player: Player entity
            dungeon: Dungeon instance
        """
        # Calculate actual damage (slight randomness)
        actual_damage = max(1, int(self.damage * random.uniform(0.8, 1.2)))
        
        # Apply damage to player
        player.take_damage(actual_damage, self.name)
        
        # Log attack
        logger.debug(f"{self.name} attacks player for {actual_damage} damage!")
        
        # Add message to dungeon log
        dungeon.add_message(f"{self.name} attacks you for {actual_damage} damage!")

class Item(Entity):
    """Item entity that can be picked up by the player."""
    
    def __init__(self, x, y, name, item_type, value=1, color=(255, 255, 0)):
        """
        Initialize an item.
        
        Args:
            x: X position in dungeon
            y: Y position in dungeon
            name: Item name
            item_type: Type of item (e.g., "weapon", "potion")
            value: Item value or effect strength
            color: RGB color tuple
        """
        super().__init__(x, y, EntityType.ITEM, name, color)
        self.item_type = item_type
        self.value = value
        self.blocks_movement = False
    
    def use(self, user, dungeon):
        """
        Use the item.
        
        Args:
            user: Entity using the item
            dungeon: Dungeon instance
            
        Returns:
            Boolean indicating if item was used successfully
        """
        # Different effects based on item type
        if self.item_type == "healing_potion":
            # Heal the user
            heal_amount = self.value
            user.health = min(user.max_health, user.health + heal_amount)
            dungeon.add_message(f"You drink the {self.name} and heal {heal_amount} health!")
            return True
        
        elif self.item_type == "scroll":
            # Generic scroll effect (just a message for now)
            dungeon.add_message(f"You read the {self.name}. Nothing happens...")
            return True
        
        return False

class Chest(Entity):
    """Chest entity that can contain items."""
    
    def __init__(self, x, y, items=None, locked=False, trap=None, color=(150, 100, 50)):
        """
        Initialize a chest.
        
        Args:
            x: X position in dungeon
            y: Y position in dungeon
            items: List of Item instances
            locked: Whether chest is locked
            trap: Trap type if trapped
            color: RGB color tuple
        """
        super().__init__(x, y, EntityType.CHEST, "Chest", color)
        self.items = items if items else []
        self.locked = locked
        self.trap = trap
        self.opened = False
    
    def open(self, player, dungeon):
        """
        Open the chest.
        
        Args:
            player: Player entity
            dungeon: Dungeon instance
            
        Returns:
            List of items obtained, or None if chest couldn't be opened
        """
        if self.opened:
            dungeon.add_message("This chest is already empty.")
            return []
        
        if self.locked:
            dungeon.add_message("This chest is locked. You need a key!")
            return None
        
        # Check for trap
        if self.trap:
            dungeon.add_message(f"The chest was trapped! A {self.trap} trap triggers!")
            # Apply trap effects based on type
            if self.trap == "poison":
                player.take_damage(5, "poison trap")
            elif self.trap == "dart":
                player.take_damage(3, "dart trap")
            elif self.trap == "alarm":
                dungeon.add_message("The alarm attracts nearby monsters!")
                # Spawn or alert monsters (implementation depends on dungeon)
            
            # Disarm trap after triggering
            self.trap = None
        
        # Mark as opened
        self.opened = True
        
        # Return items
        obtained_items = self.items.copy()
        self.items = []
        
        # Change appearance of opened chest
        self.name = "Empty Chest"
        self.color = (100, 70, 30)
        
        # Log items found
        if obtained_items:
            item_names = ", ".join(item.name for item in obtained_items)
            dungeon.add_message(f"You found: {item_names}")
        else:
            dungeon.add_message("The chest is empty.")
        
        return obtained_items

class Player(Entity):
    """Player entity controlled by the user."""
    
    def __init__(self, x, y, name, character=None):
        """
        Initialize player.
        
        Args:
            x: X position in dungeon
            y: Y position in dungeon
            name: Player name
            character: Optional Character instance from main game
        """
        super().__init__(x, y, EntityType.PLAYER, name, (0, 255, 255))
        
        # If character data is provided, use it
        self.character = character
        
        if character:
            # Use character's stats
            self.max_health = character.max_health
            self.health = character.health
            self.damage = 5 + (character.stats['strength'].value // 2)
        else:
            # Default stats
            self.max_health = 100
            self.health = 100
            self.damage = 10
        
        self.inventory = []
        self.max_inventory_slots = 20
        self.gold = 0
        self.keys = 0
    
    def attack(self, target, dungeon):
        """
        Attack a target.
        
        Args:
            target: Entity to attack
            dungeon: Dungeon instance
        """
        if hasattr(target, 'health'):
            # Calculate actual damage (slight randomness)
            actual_damage = max(1, int(self.damage * random.uniform(0.8, 1.2)))
            
            # Apply damage to target
            target.health -= actual_damage
            
            # Log attack
            logger.debug(f"Player attacks {target.name} for {actual_damage} damage!")
            
            # Add message to dungeon log
            dungeon.add_message(f"You attack {target.name} for {actual_damage} damage!")
            
            # Check if target died
            if target.health <= 0:
                dungeon.add_message(f"You defeated {target.name}!")
                dungeon.entities.remove(target)
                
                # Add experience, gold, etc.
                self.gold += random.randint(1, 10)
                
                # Character experience if character system is active
                if self.character:
                    self.character.gain_experience(50)
    
    def take_damage(self, amount, source):
        """
        Take damage from a source.
        
        Args:
            amount: Amount of damage
            source: Source of damage
            
        Returns:
            Actual damage taken
        """
        actual_damage = amount
        
        # Apply damage to health
        self.health -= actual_damage
        
        # Check for death
        if self.health <= 0:
            self.health = 0
            logger.info(f"Player was defeated by {source}!")
        
        return actual_damage
    
    def pickup_item(self, item, dungeon):
        """
        Pick up an item.
        
        Args:
            item: Item to pick up
            dungeon: Dungeon instance
            
        Returns:
            Boolean indicating if item was picked up
        """
        if len(self.inventory) >= self.max_inventory_slots:
            dungeon.add_message("Your inventory is full!")
            return False
        
        # Add to inventory
        self.inventory.append(item)
        
        # Remove from dungeon
        if item in dungeon.entities:
            dungeon.entities.remove(item)
        
        # Log pickup
        dungeon.add_message(f"You picked up {item.name}.")
        return True
    
    def use_item(self, item_index, dungeon):
        """
        Use an item from inventory.
        
        Args:
            item_index: Index of item in inventory
            dungeon: Dungeon instance
            
        Returns:
            Boolean indicating if item was used
        """
        if 0 <= item_index < len(self.inventory):
            item = self.inventory[item_index]
            
            # Use the item
            if item.use(self, dungeon):
                # Remove consumable items after use
                self.inventory.pop(item_index)
                return True
        
        return False
    
    def heal(self, amount):
        """
        Heal the player.
        
        Args:
            amount: Amount to heal
            
        Returns:
            Actual amount healed
        """
        old_health = self.health
        self.health = min(self.max_health, self.health + amount)
        return self.health - old_health

class Room:
    """Rectangular room in the dungeon."""
    
    def __init__(self, x, y, width, height, room_type="normal"):
        """
        Initialize a room.
        
        Args:
            x: X position of top-left corner
            y: Y position of top-left corner
            width: Room width
            height: Room height
            room_type: Type of room (e.g., "normal", "treasure", "boss")
        """
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.room_type = room_type
        self.connected = False  # Whether room is connected to another room
    
    @property
    def center(self):
        """Get the center coordinates of the room."""
        return (self.x + self.width // 2, self.y + self.height // 2)
    
    def intersects(self, other):
        """
        Check if this room intersects with another.
        
        Args:
            other: Other Room instance
            
        Returns:
            Boolean indicating if rooms intersect
        """
        # Add a buffer of 1 around the rooms to ensure walls don't touch
        return (self.x - 1 <= other.x + other.width and 
                self.x + self.width + 1 >= other.x and 
                self.y - 1 <= other.y + other.height and 
                self.y + self.height + 1 >= other.y)
    
    def is_valid(self, dungeon_width, dungeon_height):
        """
        Check if room is valid within dungeon bounds.
        
        Args:
            dungeon_width: Width of the dungeon
            dungeon_height: Height of the dungeon
            
        Returns:
            Boolean indicating if room is valid
        """
        return (self.x > 0 and self.y > 0 and 
                self.x + self.width < dungeon_width - 1 and 
                self.y + self.height < dungeon_height - 1)
    
    def get_random_position(self):
        """Get a random position within the room."""
        x = random.randint(self.x + 1, self.x + self.width - 2)
        y = random.randint(self.y + 1, self.y + self.height - 2)
        return (x, y)

class Dungeon:
    """Dungeon level with rooms, corridors, and entities."""
    
    def __init__(self, width, height, depth=1, difficulty=1, seed=None):
        """
        Initialize a dungeon.
        
        Args:
            width: Dungeon width in tiles
            height: Dungeon height in tiles
            depth: Dungeon depth level
            difficulty: Difficulty level (1-10)
            seed: Random seed (None for random)
        """
        self.width = width
        self.height = height
        self.depth = depth
        self.difficulty = difficulty
        
        # Set random seed
        self.seed = seed if seed is not None else random.randint(0, 1000000)
        random.seed(self.seed)
        
        # Initialize empty dungeon with walls
        self.tiles = np.full((height, width), TileType.WALL.value, dtype=int)
        
        # List of rooms
        self.rooms = []
        
        # List of entities (monsters, items, etc.)
        self.entities = []
        
        # Player entity (will be initialized when player enters dungeon)
        self.player = None
        
        # Message log
        self.messages = []
        self.max_messages = 10
        
        # Visibility and exploration
        self.visible = np.zeros((height, width), dtype=bool)
        self.explored = np.zeros((height, width), dtype=bool)
        
        # Dungeon generation
        self._generate_dungeon()
        
        logger.info(f"Dungeon level {depth} initialized with seed {self.seed}")
    
    def _generate_dungeon(self):
        """Generate the dungeon layout with rooms and corridors."""
        logger.info("Generating dungeon...")
        
        # Calculate room parameters based on dungeon size
        max_rooms = self.width * self.height // 100
        min_room_size = 5
        max_room_size = 10
        
        # Generate rooms
        for _ in range(max_rooms):
            # Random width and height
            width = random.randint(min_room_size, max_room_size)
            height = random.randint(min_room_size, max_room_size)
            
            # Random position
            x = random.randint(1, self.width - width - 1)
            y = random.randint(1, self.height - height - 1)
            
            # Create room
            new_room = Room(x, y, width, height)
            
            # Check if room is valid and doesn't intersect other rooms
            if new_room.is_valid(self.width, self.height) and all(not new_room.intersects(room) for room in self.rooms):
                # Add room to list
                self.rooms.append(new_room)
                
                # Carve out the room
                self._create_room(new_room)
                
                # Connect to previous room if this isn't the first room
                if len(self.rooms) > 1:
                    self._connect_rooms(self.rooms[-2], new_room)
                    new_room.connected = True
        
        # Place stairs
        self._place_stairs()
        
        # Place monsters and items
        self._populate_dungeon()
        
        logger.info(f"Dungeon generation completed with {len(self.rooms)} rooms")
    
    def _create_room(self, room):
        """
        Carve out a room in the dungeon.
        
        Args:
            room: Room instance
        """
        # Set floor tiles within room
        for y in range(room.y + 1, room.y + room.height - 1):
            for x in range(room.x + 1, room.x + room.width - 1):
                self.tiles[y][x] = TileType.FLOOR.value
    
    def _connect_rooms(self, room1, room2):
        """
        Create a corridor between two rooms.
        
        Args:
            room1: First Room instance
            room2: Second Room instance
        """
        # Get center coordinates of each room
        x1, y1 = room1.center
        x2, y2 = room2.center
        
        # Randomly decide whether to go horizontally or vertically first
        if random.random() < 0.5:
            # First horizontal, then vertical
            self._create_horizontal_tunnel(x1, x2, y1)
            self._create_vertical_tunnel(y1, y2, x2)
        else:
            # First vertical, then horizontal
            self._create_vertical_tunnel(y1, y2, x1)
            self._create_horizontal_tunnel(x1, x2, y2)
    
    def _create_horizontal_tunnel(self, x1, x2, y):
        """
        Create a horizontal tunnel.
        
        Args:
            x1: Start x-coordinate
            x2: End x-coordinate
            y: Y-coordinate
        """
        for x in range(min(x1, x2), max(x1, x2) + 1):
            if 0 <= x < self.width and 0 <= y < self.height:
                self.tiles[y][x] = TileType.FLOOR.value
                
                # Place doors at tunnel entrances with a 30% chance
                if random.random() < 0.3:
                    # Check if we're at corridor entrance (wall on one side, floor on the other)
                    is_entrance = False
                    for dx, dy in [(0, 1), (0, -1)]:
                        nx, ny = x + dx, y + dy
                        if (0 <= nx < self.width and 0 <= ny < self.height and
                            self.tiles[ny][nx] == TileType.WALL.value):
                            is_entrance = True
                            break
                    
                    if is_entrance:
                        self.tiles[y][x] = TileType.DOOR.value
    
    def _create_vertical_tunnel(self, y1, y2, x):
        """
        Create a vertical tunnel.
        
        Args:
            y1: Start y-coordinate
            y2: End y-coordinate
            x: X-coordinate
        """
        for y in range(min(y1, y2), max(y1, y2) + 1):
            if 0 <= x < self.width and 0 <= y < self.height:
                self.tiles[y][x] = TileType.FLOOR.value
                
                # Place doors at tunnel entrances with a 30% chance
                if random.random() < 0.3:
                    # Check if we're at corridor entrance (wall on one side, floor on the other)
                    is_entrance = False
                    for dx, dy in [(1, 0), (-1, 0)]:
                        nx, ny = x + dx, y + dy
                        if (0 <= nx < self.width and 0 <= ny < self.height and
                            self.tiles[ny][nx] == TileType.WALL.value):
                            is_entrance = True
                            break
                    
                    if is_entrance:
                        self.tiles[y][x] = TileType.DOOR.value
    
    def _place_stairs(self):
        """Place stairs up and down in the dungeon."""
        # Choose random rooms for stairs
        up_room = random.choice(self.rooms)
        down_room = random.choice([r for r in self.rooms if r != up_room])
        
        # Get random positions within rooms
        up_pos = up_room.get_random_position()
        down_pos = down_room.get_random_position()
        
        # Place stairs
        self.tiles[up_pos[1]][up_pos[0]] = TileType.STAIRS_UP.value
        self.tiles[down_pos[1]][down_pos[0]] = TileType.STAIRS_DOWN.value
        
        logger.debug(f"Placed stairs up at {up_pos} and stairs down at {down_pos}")
    
    def _populate_dungeon(self):
        """Populate the dungeon with monsters, items, and chests."""
        # Determine number of entities based on dungeon size and difficulty
        num_monsters = int(len(self.rooms) * self.difficulty * 0.5)
        num_items = int(len(self.rooms) * 0.3)
        num_chests = int(len(self.rooms) * 0.2)
        
        # Place monsters
        monster_names = ["Goblin", "Skeleton", "Zombie", "Rat", "Bat", "Spider", "Orc"]
        monster_colors = [(0, 255, 0), (200, 200, 200), (100, 150, 100), 
                         (150, 100, 100), (100, 100, 150), (150, 0, 0)]
        
        for _ in range(num_monsters):
            # Choose random room
            room = random.choice(self.rooms)
            
            # Get random position within room
            x, y = room.get_random_position()
            
            # Create monster with difficulty-scaled stats
            monster_type = random.choice(monster_names)
            health = 10 + (self.difficulty * 2)
            damage = 2 + self.difficulty
            color = random.choice(monster_colors)
            
            monster = Monster(x, y, monster_type, health, damage, color)
            self.entities.append(monster)
        
        # Place items
        item_types = ["healing_potion", "scroll"]
        item_names = {
            "healing_potion": "Healing Potion",
            "scroll": "Scroll of Identify"
        }
        item_colors = {
            "healing_potion": (255, 0, 0),
            "scroll": (200, 200, 100)
        }
        
        for _ in range(num_items):
            # Choose random room
            room = random.choice(self.rooms)
            
            # Get random position within room
            x, y = room.get_random_position()
            
            # Create item
            item_type = random.choice(item_types)
            name = item_names[item_type]
            color = item_colors[item_type]
            value = 10 + (self.difficulty * 2)  # Scale value with difficulty
            
            item = Item(x, y, name, item_type, value, color)
            self.entities.append(item)
        
        # Place chests
        for _ in range(num_chests):
            # Choose random room
            room = random.choice(self.rooms)
            
            # Get random position within room
            x, y = room.get_random_position()
            
            # Generate chest contents
            chest_items = []
            num_chest_items = random.randint(0, 3)
            
            for _ in range(num_chest_items):
                item_type = random.choice(item_types)
                name = item_names[item_type]
                color = item_colors[item_type]
                value = 10 + (self.difficulty * 2)
                
                chest_items.append(Item(x, y, name, item_type, value, color))
            
            # Determine if chest is locked/trapped
            locked = random.random() < 0.3
            trap = None
            if random.random() < 0.2:
                trap = random.choice(["poison", "dart", "alarm"])
            
            chest = Chest(x, y, chest_items, locked, trap)
            self.entities.append(chest)
        
        logger.info(f"Populated dungeon with {num_monsters} monsters, {num_items} items, and {num_chests} chests")
    
    def is_position_valid(self, x, y):
        """
        Check if a position is valid for movement.
        
        Args:
            x: X-coordinate
            y: Y-coordinate
            
        Returns:
            Boolean indicating if position is valid
        """
        # Check bounds
        if not (0 <= x < self.width and 0 <= y < self.height):
            return False
        
        # Check for walls
        if self.tiles[y][x] == TileType.WALL.value:
            return False
        
        # Check for blocking entities
        for entity in self.entities:
            if entity.blocks_movement and entity.x == x and entity.y == y:
                return False
        
        return True
    
    def get_entity_at(self, x, y):
        """
        Get an entity at a position.
        
        Args:
            x: X-coordinate
            y: Y-coordinate
            
        Returns:
            Entity at the position, or None if no entity found
        """
        for entity in self.entities:
            if entity.x == x and entity.y == y:
                return entity
        
        # Check if player is at position
        if self.player and self.player.x == x and self.player.y == y:
            return self.player
        
        return None
    
    def update_visibility(self):
        """Update which tiles are visible from the player's position."""
        # Reset visibility
        self.visible = np.zeros((self.height, self.width), dtype=bool)
        
        # Set visibility radius based on lighting
        visibility_radius = 8
        
        # Mark all tiles within FOV as visible
        for y in range(max(0, self.player.y - visibility_radius), min(self.height, self.player.y + visibility_radius + 1)):
            for x in range(max(0, self.player.x - visibility_radius), min(self.width, self.player.x + visibility_radius + 1)):
                # Calculate distance to player
                dx = x - self.player.x
                dy = y - self.player.y
                distance = math.sqrt(dx*dx + dy*dy)
                
                # If within visibility radius, check line of sight
                if distance <= visibility_radius:
                    if self._has_line_of_sight(self.player.x, self.player.y, x, y):
                        self.visible[y][x] = True
                        self.explored[y][x] = True
    
    def _has_line_of_sight(self, x1, y1, x2, y2):
        """
        Check if there's a clear line of sight between two points.
        
        Args:
            x1: Start x-coordinate
            y1: Start y-coordinate
            x2: End x-coordinate
            y2: End y-coordinate
            
        Returns:
            Boolean indicating if there's line of sight
        """
        # Simple Bresenham's line algorithm
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        sx = 1 if x1 < x2 else -1
        sy = 1 if y1 < y2 else -1
        err = dx - dy
        
        while True:
            # Check if we've reached the target
            if x1 == x2 and y1 == y2:
                return True
            
            # Check if current tile blocks vision
            if self.tiles[y1][x1] == TileType.WALL.value:
                # Allow starting point to be a wall
                if x1 != self.player.x or y1 != self.player.y:
                    return False
            
            # Calculate next position
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x1 += sx
            if e2 < dx:
                err += dx
                y1 += sy
    
    def add_message(self, text):
        """
        Add a message to the dungeon log.
        
        Args:
            text: Message text
        """
        self.messages.append(text)
        
        # Trim message log if it gets too long
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages:]
    
    def update(self):
        """Update dungeon state."""
        # Update entities
        for entity in list(self.entities):  # Create a copy to allow removal during iteration
            if entity.entity_type == EntityType.MONSTER:
                entity.update(self, self.player)
                
                # Check if monster died
                if hasattr(entity, 'health') and entity.health <= 0:
                    self.entities.remove(entity)
        
        # Update visibility
        self.update_visibility()

class DungeonState(GameState):
    """
    Game state for roguelike dungeon crawling.
    
    This state handles:
    - Procedurally generated dungeons
    - Turn-based movement and combat
    - Item collection and chest opening
    - Dungeon exploration and mapping
    """
    
    def __init__(self, state_manager, event_bus, settings):
        """Initialize the dungeon state."""
        super().__init__(state_manager, event_bus, settings)
        
        # Current dungeon
        self.dungeon = None
        self.current_level = 1
        
        # UI elements
        self.tile_size = 32
        self.font = None
        self.message_log_height = 100
        self.sidebar_width = 200
        
        # Game state
        self.game_over = False
        self.turn_based = True  # True for turn-based, False for real-time
        self.player_turn = True
        
        # Colors
        self.colors = {
            TileType.WALL.value: (50, 50, 50),
            TileType.FLOOR.value: (100, 100, 100),
            TileType.DOOR.value: (150, 120, 70),
            TileType.STAIRS_UP.value: (200, 180, 50),
            TileType.STAIRS_DOWN.value: (150, 50, 200),
            TileType.TRAP.value: (200, 50, 50),
            TileType.WATER.value: (50, 100, 200),
            TileType.LAVA.value: (200, 100, 50)
        }
        
        # Key mapping
        self.movement_keys = {
            pygame.K_UP: (0, -1),
            pygame.K_DOWN: (0, 1),
            pygame.K_LEFT: (-1, 0),
            pygame.K_RIGHT: (1, 0),
            pygame.K_w: (0, -1),
            pygame.K_s: (0, 1),
            pygame.K_a: (-1, 0),
            pygame.K_d: (1, 0)
        }
        
        self.action_keys = {
            pygame.K_e: "interact",
            pygame.K_g: "pickup",
            pygame.K_i: "inventory",
            pygame.K_SPACE: "wait",
            pygame.K_ESCAPE: "exit"
        }
        
        logger.info("DungeonState initialized")
    
    def enter(self, data=None):
        """Set up the state when entered."""
        super().enter(data)
        
        # Initialize font
        pygame.font.init()
        self.font = pygame.font.SysFont(None, 24)
        
        # Get location data if provided
        location = None
        if data and "location" in data:
            location = data["location"]
            self.current_level = max(1, location.difficulty)
        
        # Create a new dungeon
        self._create_dungeon(self.current_level)
        
        # Get character from persistent data if available
        character = self.state_manager.get_persistent_data("player_character")
        
        # Create player
        self._create_player(character)
        
        # Update visibility
        self.dungeon.update_visibility()
        
        # Add welcome message
        self.dungeon.add_message(f"Welcome to the dungeon! Level {self.current_level}")
        if location:
            self.dungeon.add_message(f"Exploring {location.name}...")
        
        logger.info(f"Entered dungeon level {self.current_level}")
    
    def exit(self):
        """Clean up when leaving the state."""
        # If player character exists and player is alive, update character health
        character = self.state_manager.get_persistent_data("player_character")
        if character and self.dungeon.player and self.dungeon.player.health > 0:
            character.health = self.dungeon.player.health
            self.state_manager.set_persistent_data("player_character", character)
        
        super().exit()
        logger.info("Exited dungeon state")
    
    def handle_event(self, event):
        """Handle pygame events."""
        if not self.active or self.game_over:
            return
        
        if event.type == pygame.KEYDOWN:
            # Handle movement
            if event.key in self.movement_keys and self.player_turn:
                dx, dy = self.movement_keys[event.key]
                self._handle_player_move(dx, dy)
                
                # If turn-based, end player turn after movement
                if self.turn_based:
                    self.player_turn = False
            
            # Handle actions
            elif event.key in self.action_keys and self.player_turn:
                action = self.action_keys[event.key]
                
                if action == "interact":
                    self._handle_interact()
                
                elif action == "pickup":
                    self._handle_pickup()
                
                elif action == "inventory":
                    self._handle_inventory()
                
                elif action == "wait":
                    # Skip turn
                    self.player_turn = False
                    self.dungeon.add_message("You wait a turn.")
                
                elif action == "exit":
                    self._exit_dungeon()
    
    def update(self, dt):
        """Update game state."""
        if not self.active or self.game_over:
            return
        
        # In turn-based mode, process entity turns when it's not player's turn
        if self.turn_based and not self.player_turn:
            # Update dungeon state (entities move and act)
            self.dungeon.update()
            
            # Check if player died
            if self.dungeon.player.health <= 0:
                self._handle_player_death()
                return
            
            # Return to player's turn
            self.player_turn = True
        
        # In real-time mode, update regardless of turn
        elif not self.turn_based:
            # Update dungeon state
            self.dungeon.update()
            
            # Check if player died
            if self.dungeon.player.health <= 0:
                self._handle_player_death()
    
    def render(self, screen):
        """Render the game state."""
        if not self.visible:
            return
        
        # Fill background
        screen.fill((0, 0, 0))
        
        # Calculate viewport dimensions
        screen_width, screen_height = screen.get_size()
        viewport_width = screen_width - self.sidebar_width
        viewport_height = screen_height - self.message_log_height
        
        # Determine camera position (centered on player)
        camera_x = max(0, min(self.dungeon.width - viewport_width // self.tile_size,
                            self.dungeon.player.x - viewport_width // (2 * self.tile_size)))
        camera_y = max(0, min(self.dungeon.height - viewport_height // self.tile_size,
                            self.dungeon.player.y - viewport_height // (2 * self.tile_size)))
        
        # Render dungeon tiles
        for y in range(camera_y, min(camera_y + viewport_height // self.tile_size + 1, self.dungeon.height)):
            for x in range(camera_x, min(camera_x + viewport_width // self.tile_size + 1, self.dungeon.width)):
                # Skip if not visible or explored
                if not self.dungeon.visible[y][x] and not self.dungeon.explored[y][x]:
                    continue
                
                # Get tile type and color
                tile_type = self.dungeon.tiles[y][x]
                color = self.colors.get(tile_type, (100, 100, 100))
                
                # Darken if explored but not visible
                if self.dungeon.explored[y][x] and not self.dungeon.visible[y][x]:
                    color = (color[0] // 2, color[1] // 2, color[2] // 2)
                
                # Draw tile
                screen_x = (x - camera_x) * self.tile_size
                screen_y = (y - camera_y) * self.tile_size
                pygame.draw.rect(screen, color, (screen_x, screen_y, self.tile_size, self.tile_size))
                pygame.draw.rect(screen, (20, 20, 20), (screen_x, screen_y, self.tile_size, self.tile_size), 1)
        
        # Render entities
        for entity in self.dungeon.entities:
            # Skip if not visible
            if not self.dungeon.visible[entity.y][entity.x]:
                continue
            
            # Calculate screen position
            screen_x = (entity.x - camera_x) * self.tile_size + self.tile_size // 2
            screen_y = (entity.y - camera_y) * self.tile_size + self.tile_size // 2
            
            # Skip if not on screen
            if not (0 <= screen_x < viewport_width and 0 <= screen_y < viewport_height):
                continue
            
            # Draw entity
            pygame.draw.circle(screen, entity.color, (screen_x, screen_y), self.tile_size // 3)
            pygame.draw.circle(screen, (0, 0, 0), (screen_x, screen_y), self.tile_size // 3, 1)
        
        # Render player
        if self.dungeon.player:
            screen_x = (self.dungeon.player.x - camera_x) * self.tile_size + self.tile_size // 2
            screen_y = (self.dungeon.player.y - camera_y) * self.tile_size + self.tile_size // 2
            
            pygame.draw.circle(screen, self.dungeon.player.color, (screen_x, screen_y), self.tile_size // 2)
            pygame.draw.circle(screen, (0, 0, 0), (screen_x, screen_y), self.tile_size // 2, 2)
        
        # Render sidebar
        self._render_sidebar(screen, viewport_width, viewport_height)
        
        # Render message log
        self._render_message_log(screen, viewport_width, screen_height - self.message_log_height)
        
        # Render game over screen if needed
        if self.game_over:
            self._render_game_over(screen)
    
    def _create_dungeon(self, level):
        """
        Create a new dungeon level.
        
        Args:
            level: Dungeon level (affects difficulty)
        """
        # Calculate dungeon size based on level
        base_size = 40
        size_increase = 5 * ((level - 1) // 3)  # Increase size every 3 levels
        dungeon_size = base_size + size_increase
        
        # Create dungeon
        self.dungeon = Dungeon(dungeon_size, dungeon_size, depth=level, difficulty=level)
        
        logger.info(f"Created dungeon level {level} with size {dungeon_size}x{dungeon_size}")
    
    def _create_player(self, character=None):
        """
        Create the player entity.
        
        Args:
            character: Optional Character instance from main game
        """
        # Find starting position (stairs up)
        start_x, start_y = None, None
        
        for y in range(self.dungeon.height):
            for x in range(self.dungeon.width):
                if self.dungeon.tiles[y][x] == TileType.STAIRS_UP.value:
                    start_x, start_y = x, y
                    break
            
            if start_x is not None:
                break
        
        # If no stairs found, use center of first room
        if start_x is None and self.dungeon.rooms:
            start_x, start_y = self.dungeon.rooms[0].center
        
        # Create player
        player_name = "Adventurer"
        if character:
            player_name = character.name
        
        self.dungeon.player = Player(start_x, start_y, player_name, character)
        
        logger.info(f"Created player at position ({start_x}, {start_y})")
    
    def _handle_player_move(self, dx, dy):
        """
        Handle player movement.
        
        Args:
            dx: X direction
            dy: Y direction
        """
        player = self.dungeon.player
        target_x = player.x + dx
        target_y = player.y + dy
        
        # Check for entities at target position
        target_entity = self.dungeon.get_entity_at(target_x, target_y)
        
        if target_entity:
            # If entity is a monster, attack it
            if target_entity.entity_type == EntityType.MONSTER:
                player.attack(target_entity, self.dungeon)
                return
            
            # Otherwise, if entity blocks movement, can't move
            elif target_entity.blocks_movement:
                return
        
        # Check for special tiles
        if 0 <= target_x < self.dungeon.width and 0 <= target_y < self.dungeon.height:
            tile_type = self.dungeon.tiles[target_y][target_x]
            
            # Handle doors
            if tile_type == TileType.DOOR.value:
                # Open door
                self.dungeon.tiles[target_y][target_x] = TileType.FLOOR.value
                self.dungeon.add_message("You open the door.")
                return
            
            # Handle stairs
            elif tile_type == TileType.STAIRS_UP.value:
                self.dungeon.add_message("You see stairs leading up. Press E to use them.")
            elif tile_type == TileType.STAIRS_DOWN.value:
                self.dungeon.add_message("You see stairs leading down. Press E to use them.")
        
        # Move player if possible
        player.move(dx, dy, self.dungeon)
    
    def _handle_interact(self):
        """Handle player interaction with the environment."""
        player = self.dungeon.player
        
        # Check for entities to interact with in current and adjacent tiles
        for dx, dy in [(0, 0), (0, 1), (1, 0), (0, -1), (-1, 0)]:
            target_x = player.x + dx
            target_y = player.y + dy
            
            # Check bounds
            if not (0 <= target_x < self.dungeon.width and 0 <= target_y < self.dungeon.height):
                continue
            
            # Get entity at position
            entity = self.dungeon.get_entity_at(target_x, target_y)
            
            if entity and entity.entity_type == EntityType.CHEST:
                # Open chest
                items = entity.open(player, self.dungeon)
                
                if items:
                    # Add items to player inventory
                    for item in items:
                        player.pickup_item(item, self.dungeon)
                
                # End turn after interacting
                self.player_turn = False
                return
            
            # Check for stairs
            tile_type = self.dungeon.tiles[target_y][target_x]
            
            if tile_type == TileType.STAIRS_UP.value and (dx, dy) == (0, 0):
                # Exit dungeon
                self._exit_dungeon()
                return
            
            elif tile_type == TileType.STAIRS_DOWN.value and (dx, dy) == (0, 0):
                # Go to next level
                self._next_level()
                return
        
        # If no interaction, notify player
        self.dungeon.add_message("There's nothing to interact with here.")
    
    def _handle_pickup(self):
        """Handle player picking up items."""
        player = self.dungeon.player
        
        # Check for items at player's position
        entity = self.dungeon.get_entity_at(player.x, player.y)
        
        if entity and entity.entity_type == EntityType.ITEM:
            # Pick up item
            player.pickup_item(entity, self.dungeon)
            
            # End turn after picking up
            self.player_turn = False
        else:
            self.dungeon.add_message("There's nothing to pick up here.")
    
    def _handle_inventory(self):
        """Handle player inventory management."""
        player = self.dungeon.player
        
        if not player.inventory:
            self.dungeon.add_message("Your inventory is empty.")
            return
        
        # Display inventory
        self.dungeon.add_message("Inventory:")
        
        for i, item in enumerate(player.inventory):
            self.dungeon.add_message(f"{i+1}: {item.name}")
        
        # TODO: Implement proper inventory UI with item usage
        self.dungeon.add_message("Press 1-9 to use an item (not implemented yet).")
    
    def _handle_player_death(self):
        """Handle player death."""
        self.game_over = True
        self.dungeon.add_message("You have been defeated!")
        logger.info("Player died in dungeon")
        
        # If character system is active, update character health
        character = self.state_manager.get_persistent_data("player_character")
        if character:
            character.health = 0
            self.state_manager.set_persistent_data("player_character", character)
    
    def _exit_dungeon(self):
        """Exit the dungeon and return to world exploration."""
        logger.info("Exiting dungeon")
        
        # If exiting through stairs, mark dungeon as cleared
        location = None
        data = self.state_data.get("location")
        if data:
            location = data
            location.cleared = True
            self.event_bus.publish("show_notification", {
                "title": "Dungeon Cleared",
                "message": f"You have cleared {location.name}!",
                "duration": 3.0
            })
        
        # Return to world exploration
        self.change_state("world_exploration")
    
    def _next_level(self):
        """Go to the next dungeon level."""
        # If character system is active, update character health
        character = self.state_manager.get_persistent_data("player_character")
        if character and self.dungeon.player:
            character.health = self.dungeon.player.health
            self.state_manager.set_persistent_data("player_character", character)
        
        # Increase level
        self.current_level += 1
        
        # Create new dungeon
        self._create_dungeon(self.current_level)
        
        # Create player
        self._create_player(character)
        
        # Update visibility
        self.dungeon.update_visibility()
        
        # Add message
        self.dungeon.add_message(f"You descend to dungeon level {self.current_level}.")
        
        logger.info(f"Descended to dungeon level {self.current_level}")
    
    def _render_sidebar(self, screen, x_offset, y_offset):
        """
        Render the sidebar with player stats.
        
        Args:
            screen: Pygame surface to render to
            x_offset: X offset for sidebar
            y_offset: Y offset for sidebar
        """
        sidebar_x = x_offset
        sidebar_y = 0
        
        # Draw sidebar background
        pygame.draw.rect(screen, (30, 30, 30), (sidebar_x, sidebar_y, self.sidebar_width, y_offset))
        pygame.draw.rect(screen, (50, 50, 50), (sidebar_x, sidebar_y, self.sidebar_width, y_offset), 1)
        
        # Draw player info
        player = self.dungeon.player
        
        # Draw name
        name_text = self.font.render(f"{player.name}", True, (255, 255, 255))
        screen.blit(name_text, (sidebar_x + 10, sidebar_y + 10))
        
        # Draw health bar
        health_text = self.font.render(f"Health: {player.health}/{player.max_health}", True, (255, 255, 255))
        screen.blit(health_text, (sidebar_x + 10, sidebar_y + 40))
        
        bar_width = self.sidebar_width - 20
        bar_height = 15
        fill_width = int(bar_width * (player.health / player.max_health))
        
        pygame.draw.rect(screen, (100, 0, 0), (sidebar_x + 10, sidebar_y + 60, bar_width, bar_height))
        pygame.draw.rect(screen, (255, 0, 0), (sidebar_x + 10, sidebar_y + 60, fill_width, bar_height))
        pygame.draw.rect(screen, (150, 150, 150), (sidebar_x + 10, sidebar_y + 60, bar_width, bar_height), 1)
        
        # Draw dungeon level
        level_text = self.font.render(f"Dungeon Level: {self.current_level}", True, (255, 255, 255))
        screen.blit(level_text, (sidebar_x + 10, sidebar_y + 90))
        
        # Draw inventory count
        inventory_text = self.font.render(f"Inventory: {len(player.inventory)}/{player.max_inventory_slots}", True, (255, 255, 255))
        screen.blit(inventory_text, (sidebar_x + 10, sidebar_y + 120))
        
        # Draw gold count
        gold_text = self.font.render(f"Gold: {player.gold}", True, (255, 255, 0))
        screen.blit(gold_text, (sidebar_x + 10, sidebar_y + 150))
        
        # Draw controls help
        controls_y = sidebar_y + 200
        controls_text = self.font.render("Controls:", True, (200, 200, 200))
        screen.blit(controls_text, (sidebar_x + 10, controls_y))
        
        controls = [
            "Arrows/WASD: Move",
            "E: Interact",
            "G: Pick up",
            "I: Inventory",
            "Space: Wait",
            "Esc: Exit dungeon"
        ]
        
        for i, control in enumerate(controls):
            text = self.font.render(control, True, (180, 180, 180))
            screen.blit(text, (sidebar_x + 10, controls_y + 30 + i * 25))
    
    def _render_message_log(self, screen, x_offset, y_offset):
        """
        Render the message log.
        
        Args:
            screen: Pygame surface to render to
            x_offset: X offset for message log
            y_offset: Y offset for message log
        """
        # Draw message log background
        pygame.draw.rect(screen, (30, 30, 30), (0, y_offset, x_offset, self.message_log_height))
        pygame.draw.rect(screen, (50, 50, 50), (0, y_offset, x_offset, self.message_log_height), 1)
        
        # Draw message log title
        title_text = self.font.render("Message Log", True, (255, 255, 255))
        screen.blit(title_text, (10, y_offset + 10))
        
        # Draw messages
        for i, message in enumerate(self.dungeon.messages):
            message_text = self.font.render(message, True, (200, 200, 200))
            screen.blit(message_text, (10, y_offset + 40 + i * 20))
    
    def _render_game_over(self, screen):
        """
        Render the game over screen.
        
        Args:
            screen: Pygame surface to render to
        """
        # Create semi-transparent overlay
        overlay = pygame.Surface((screen.get_width(), screen.get_height()))
        overlay.set_alpha(180)
        overlay.fill((0, 0, 0))
        screen.blit(overlay, (0, 0))
        
        # Draw game over text
        font_large = pygame.font.SysFont(None, 72)
        game_over_text = font_large.render("GAME OVER", True, (255, 0, 0))
        
        text_rect = game_over_text.get_rect(center=(screen.get_width() // 2, screen.get_height() // 2 - 50))
        screen.blit(game_over_text, text_rect)
        
        # Draw continue text
        continue_text = self.font.render("Press ESC to exit dungeon", True, (255, 255, 255))
        
        text_rect = continue_text.get_rect(center=(screen.get_width() // 2, screen.get_height() // 2 + 50))
        screen.blit(continue_text, text_rect)
