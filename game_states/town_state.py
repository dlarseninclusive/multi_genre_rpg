import pygame
import logging
import random
import math
from enum import Enum
from game_state import GameState
from world_generator import Location, LocationType
from ui_system import UIManager, UIButton, UILabel, UIPanel, UIImage, UIProgressBar

logger = logging.getLogger("town_state")

class BuildingType(Enum):
    """Types of buildings that can be found in towns."""
    TAVERN = 0
    SHOP = 1
    BLACKSMITH = 2
    INN = 3
    TEMPLE = 4
    GUILD = 5
    TOWNHALL = 6
    MARKET = 7
    HOUSE = 8

class NpcType(Enum):
    """Types of NPCs that can be found in towns."""
    MERCHANT = 0
    BLACKSMITH = 1
    INNKEEPER = 2
    GUARD = 3
    QUEST_GIVER = 4
    TRAINER = 5
    VILLAGER = 6
    NOBLE = 7
    BEGGAR = 8

class TownBuilding:
    """Represents a building in a town."""
    
    def __init__(self, building_type, name, position, size):
        """
        Initialize a town building.
        
        Args:
            building_type: Type from BuildingType enum
            name: Building name
            position: (x, y) tuple for position
            size: (width, height) tuple for size
        """
        self.building_type = building_type
        self.name = name
        self.position = position
        self.size = size
        self.npcs = []
        self.interactable = True
        self.discovered = False
        self.services = []  # List of services offered by this building
        self.items = []     # Items that can be bought/sold here
        self.quest_hooks = []  # Quests that can be started or continued here
    
    def add_npc(self, npc):
        """
        Add an NPC to this building.
        
        Args:
            npc: Npc instance
        """
        self.npcs.append(npc)
        npc.building = self
    
    def remove_npc(self, npc):
        """
        Remove an NPC from this building.
        
        Args:
            npc: Npc instance
            
        Returns:
            Boolean indicating if NPC was removed
        """
        if npc in self.npcs:
            self.npcs.remove(npc)
            npc.building = None
            return True
        return False
    
    def get_rect(self):
        """
        Get building rectangle.
        
        Returns:
            Pygame Rect
        """
        return pygame.Rect(*self.position, *self.size)
    
    def to_dict(self):
        """Convert to dictionary for serialization."""
        return {
            'building_type': self.building_type.value,
            'name': self.name,
            'position': self.position,
            'size': self.size,
            'npcs': [npc.to_dict() for npc in self.npcs],
            'interactable': self.interactable,
            'discovered': self.discovered,
            'services': self.services,
            'items': self.items,
            'quest_hooks': self.quest_hooks
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create from dictionary."""
        building = cls(
            BuildingType(data['building_type']),
            data['name'],
            data['position'],
            data['size']
        )
        building.interactable = data['interactable']
        building.discovered = data['discovered']
        building.services = data['services']
        building.items = data['items']
        building.quest_hooks = data['quest_hooks']
        
        # NPCs will be added separately
        
        return building

class Npc:
    """Represents an NPC in a town."""
    
    def __init__(self, npc_type, name, position):
        """
        Initialize an NPC.
        
        Args:
            npc_type: Type from NpcType enum
            name: NPC name
            position: (x, y) tuple for position
        """
        self.npc_type = npc_type
        self.name = name
        self.position = position
        self.building = None
        self.dialog = {}  # Dialog options by key
        self.inventory = []  # Items for sale if merchant
        self.quests = []  # Quests this NPC can give
        self.services = []  # Services offered by this NPC
        self.schedule = {}  # Schedule by hour of day
        self.discovered = False
    
    def get_dialog(self, dialog_key="greeting"):
        """
        Get dialog text for a specific key.
        
        Args:
            dialog_key: Dialog key to retrieve
            
        Returns:
            Dialog text or default greeting
        """
        return self.dialog.get(dialog_key, f"Hello, I'm {self.name}.")
    
    def add_dialog(self, dialog_key, text):
        """
        Add dialog option.
        
        Args:
            dialog_key: Dialog key
            text: Dialog text
        """
        self.dialog[dialog_key] = text
    
    def get_rect(self):
        """
        Get NPC rectangle.
        
        Returns:
            Pygame Rect
        """
        # NPCs are represented as 32x32 sprites
        return pygame.Rect(self.position[0], self.position[1], 32, 32)
    
    def to_dict(self):
        """Convert to dictionary for serialization."""
        return {
            'npc_type': self.npc_type.value,
            'name': self.name,
            'position': self.position,
            'building_type': self.building.building_type.value if self.building else None,
            'dialog': self.dialog,
            'inventory': self.inventory,
            'quests': self.quests,
            'services': self.services,
            'schedule': self.schedule,
            'discovered': self.discovered
        }
    
    @classmethod
    def from_dict(cls, data, buildings=None):
        """Create from dictionary."""
        npc = cls(
            NpcType(data['npc_type']),
            data['name'],
            data['position']
        )
        npc.dialog = data['dialog']
        npc.inventory = data['inventory']
        npc.quests = data['quests']
        npc.services = data['services']
        npc.schedule = data['schedule']
        npc.discovered = data['discovered']
        
        # Assign to building if specified
        if data['building_type'] is not None and buildings:
            building_type = BuildingType(data['building_type'])
            for building in buildings:
                if building.building_type == building_type:
                    building.add_npc(npc)
                    break
        
        return npc

class Town:
    """Represents a town with buildings and NPCs."""
    
    def __init__(self, name, size=(1200, 800)):
        """
        Initialize a town.
        
        Args:
            name: Town name
            size: (width, height) tuple for town size
        """
        self.name = name
        self.size = size
        self.buildings = []
        self.npcs = []
        self.roads = []  # List of road segments [(x1,y1), (x2,y2)]
        self.background_color = (100, 150, 100)  # Grass green
    
    def add_building(self, building):
        """
        Add a building to the town.
        
        Args:
            building: TownBuilding instance
        """
        self.buildings.append(building)
    
    def add_npc(self, npc):
        """
        Add an NPC to the town.
        
        Args:
            npc: Npc instance
        """
        self.npcs.append(npc)
    
    def add_road(self, start_pos, end_pos):
        """
        Add a road segment.
        
        Args:
            start_pos: (x, y) start position
            end_pos: (x, y) end position
        """
        self.roads.append((start_pos, end_pos))
    
    def get_building_at(self, position):
        """
        Get building at a specific position.
        
        Args:
            position: (x, y) position tuple
            
        Returns:
            TownBuilding at position or None
        """
        for building in self.buildings:
            if building.get_rect().collidepoint(position):
                return building
        return None
    
    def get_npc_at(self, position):
        """
        Get NPC at a specific position.
        
        Args:
            position: (x, y) position tuple
            
        Returns:
            Npc at position or None
        """
        for npc in self.npcs:
            if npc.get_rect().collidepoint(position):
                return npc
        return None
    
    def to_dict(self):
        """Convert to dictionary for serialization."""
        return {
            'name': self.name,
            'size': self.size,
            'buildings': [building.to_dict() for building in self.buildings],
            'npcs': [npc.to_dict() for npc in self.npcs],
            'roads': self.roads,
            'background_color': self.background_color
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create from dictionary."""
        town = cls(
            data['name'],
            data['size']
        )
        
        # Add buildings
        for building_data in data['buildings']:
            town.add_building(TownBuilding.from_dict(building_data))
        
        # Add NPCs and connect to buildings
        for npc_data in data['npcs']:
            town.add_npc(Npc.from_dict(npc_data, town.buildings))
        
        # Add roads
        town.roads = data['roads']
        
        # Set background color
        town.background_color = data['background_color']
        
        return town

class TownGenerator:
    """Generates procedural towns with buildings and NPCs."""
    
    def __init__(self):
        """Initialize the town generator."""
        # Building name templates
        self.building_names = {
            BuildingType.TAVERN: [
                "The {adj} {animal}",
                "The {adj} {weapon}",
                "The {color} {object}",
                "{name}'s Tavern"
            ],
            BuildingType.SHOP: [
                "General Goods",
                "{name}'s Trading Post",
                "{name}'s Emporium",
                "The {adj} Merchant"
            ],
            BuildingType.BLACKSMITH: [
                "{name}'s Forge",
                "The {adj} Anvil",
                "{name}'s Smithy",
                "The {adj} Hammer"
            ],
            BuildingType.INN: [
                "The {adj} {animal} Inn",
                "The Traveler's Rest",
                "{name}'s Inn",
                "The {color} {object} Inn"
            ],
            BuildingType.TEMPLE: [
                "Temple of {virtue}",
                "Shrine of the {adj} {virtue}",
                "The {color} Sanctuary",
                "{name}'s Chapel"
            ],
            BuildingType.GUILD: [
                "The {profession} Guild",
                "{name}'s {profession}s",
                "The {adj} {profession}",
                "Guild of {virtue}"
            ],
            BuildingType.TOWNHALL: [
                "{town_name} Town Hall",
                "{town_name} Council Hall",
                "The {adj} Council",
                "{town_name} Court"
            ],
            BuildingType.MARKET: [
                "{town_name} Market",
                "The {adj} Bazaar",
                "{town_name} Trading Square",
                "The {color} Market"
            ],
            BuildingType.HOUSE: [
                "{name}'s House",
                "The {color} House",
                "{name}'s Residence",
                "The {adj} Cottage"
            ]
        }
        
        # NPC name components
        self.first_names = [
            "John", "Mary", "Robert", "Emma", "William", "Elizabeth",
            "Richard", "Catherine", "Thomas", "Margaret", "James", "Anne",
            "Edward", "Jane", "Henry", "Alice", "Arthur", "Eleanor",
            "Walter", "Matilda", "Hugh", "Edith", "Roger", "Joan"
        ]
        
        self.last_names = [
            "Smith", "Miller", "Baker", "Taylor", "Clark", "Wright",
            "Fletcher", "Cooper", "Carter", "Farmer", "Cook", "Fisher",
            "Shepherd", "Potter", "Turner", "Thatcher", "Hunter", "Mason",
            "Weaver", "Gardner", "Walker", "Butler", "Brewer", "Carpenter"
        ]
        
        # Word lists for name generation
        self.adjectives = [
            "Rusty", "Golden", "Silver", "Iron", "Copper", "Bronze",
            "Broken", "Mighty", "Brave", "Noble", "Royal", "Ancient",
            "Crimson", "Azure", "Emerald", "Jade", "Amber", "Ivory",
            "Mystic", "Sacred", "Silent", "Whispering", "Roaring", "Wild"
        ]
        
        self.animals = [
            "Lion", "Dragon", "Griffin", "Eagle", "Bear", "Wolf",
            "Stag", "Horse", "Falcon", "Raven", "Fox", "Boar",
            "Bull", "Hawk", "Owl", "Serpent", "Tiger", "Unicorn"
        ]
        
        self.weapons = [
            "Sword", "Axe", "Dagger", "Bow", "Shield", "Spear",
            "Hammer", "Mace", "Flail", "Staff", "Wand", "Blade"
        ]
        
        self.objects = [
            "Crown", "Chalice", "Goblet", "Ring", "Amulet", "Gem",
            "Coin", "Lantern", "Cauldron", "Kettle", "Wheel", "Book"
        ]
        
        self.colors = [
            "Red", "Blue", "Green", "Yellow", "Purple", "Black",
            "White", "Gray", "Brown", "Crimson", "Azure", "Emerald",
            "Golden", "Silver", "Bronze", "Copper", "Iron", "Ivory"
        ]
        
        self.virtues = [
            "Truth", "Justice", "Valor", "Honor", "Wisdom", "Mercy",
            "Compassion", "Courage", "Loyalty", "Faith", "Hope", "Charity",
            "Fortitude", "Temperance", "Prudence", "Patience", "Kindness", "Humility"
        ]
        
        self.professions = [
            "Mage", "Fighter", "Thief", "Cleric", "Ranger", "Bard",
            "Merchant", "Crafter", "Alchemist", "Scholar", "Hunter", "Healer"
        ]
    
    def _generate_name(self, template, town_name=None):
        """
        Generate a name using a template.
        
        Args:
            template: Name template with placeholders
            town_name: Optional town name for templates using it
            
        Returns:
            Generated name string
        """
        # Create substitution dictionary
        subs = {
            "adj": random.choice(self.adjectives),
            "animal": random.choice(self.animals),
            "weapon": random.choice(self.weapons),
            "object": random.choice(self.objects),
            "color": random.choice(self.colors),
            "virtue": random.choice(self.virtues),
            "profession": random.choice(self.professions),
            "name": random.choice(self.first_names),
            "town_name": town_name or "Town"
        }
        
        # Apply substitutions
        for key, value in subs.items():
            template = template.replace("{" + key + "}", value)
        
        return template
    
    def _generate_npc_name(self):
        """
        Generate an NPC name.
        
        Returns:
            Full name string
        """
        first_name = random.choice(self.first_names)
        last_name = random.choice(self.last_names)
        return f"{first_name} {last_name}"
    
    def _generate_building_name(self, building_type, town_name=None):
        """
        Generate a building name.
        
        Args:
            building_type: Type from BuildingType enum
            town_name: Optional town name for templates using it
            
        Returns:
            Building name string
        """
        templates = self.building_names.get(building_type, ["Building"])
        template = random.choice(templates)
        return self._generate_name(template, town_name)
    
    def _generate_building_layout(self, town_size):
        """
        Generate a layout of buildings for a town.
        
        Args:
            town_size: (width, height) tuple
            
        Returns:
            List of (building_type, position, size) tuples
        """
        width, height = town_size
        
        # Create a grid-based layout
        grid_size = 150  # Size of each grid cell
        grid_width = width // grid_size
        grid_height = height // grid_size
        
        # Track occupied grid cells
        occupied_cells = set()
        
        # Place town hall in center
        center_x = grid_width // 2
        center_y = grid_height // 2
        town_hall_pos = (center_x * grid_size + 25, center_y * grid_size + 25)
        town_hall_size = (grid_size - 50, grid_size - 50)
        
        buildings = [(BuildingType.TOWNHALL, town_hall_pos, town_hall_size)]
        occupied_cells.add((center_x, center_y))
        
        # Place market near town hall
        market_x = center_x
        market_y = center_y + 1
        if 0 <= market_x < grid_width and 0 <= market_y < grid_height and (market_x, market_y) not in occupied_cells:
            market_pos = (market_x * grid_size + 10, market_y * grid_size + 10)
            market_size = (grid_size - 20, grid_size - 20)
            buildings.append((BuildingType.MARKET, market_pos, market_size))
            occupied_cells.add((market_x, market_y))
        
        # Place other important buildings near town hall
        important_buildings = [
            BuildingType.TAVERN,
            BuildingType.SHOP,
            BuildingType.BLACKSMITH,
            BuildingType.INN,
            BuildingType.TEMPLE,
            BuildingType.GUILD
        ]
        
        # Generate positions around town hall
        positions = []
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx == 0 and dy == 0:
                    continue  # Skip town hall position
                
                x = center_x + dx
                y = center_y + dy
                
                if 0 <= x < grid_width and 0 <= y < grid_height and (x, y) not in occupied_cells:
                    positions.append((x, y))
        
        # Shuffle positions
        random.shuffle(positions)
        
        # Place important buildings
        for i, building_type in enumerate(important_buildings):
            if i < len(positions):
                x, y = positions[i]
                pos = (x * grid_size + 20, y * grid_size + 20)
                size = (grid_size - 40, grid_size - 40)
                buildings.append((building_type, pos, size))
                occupied_cells.add((x, y))
        
        # Fill remaining cells with houses
        num_houses = min(10, grid_width * grid_height - len(occupied_cells))
        
        available_cells = []
        for x in range(grid_width):
            for y in range(grid_height):
                if (x, y) not in occupied_cells:
                    available_cells.append((x, y))
        
        random.shuffle(available_cells)
        
        for i in range(num_houses):
            if i < len(available_cells):
                x, y = available_cells[i]
                # Houses are smaller
                pos = (x * grid_size + 30, y * grid_size + 30)
                size = (grid_size - 60, grid_size - 60)
                buildings.append((BuildingType.HOUSE, pos, size))
                occupied_cells.add((x, y))
        
        return buildings
    
    def _generate_roads(self, town_size, buildings):
        """
        Generate roads connecting buildings.
        
        Args:
            town_size: (width, height) tuple
            buildings: List of (building_type, position, size) tuples
            
        Returns:
            List of road segments [(x1,y1), (x2,y2)]
        """
        roads = []
        
        # Find town hall (should be first building)
        town_hall = buildings[0]
        town_hall_center = (
            town_hall[1][0] + town_hall[2][0] // 2,
            town_hall[1][1] + town_hall[2][1] // 2
        )
        
        # Connect all buildings to town hall with roads
        for building in buildings[1:]:
            building_center = (
                building[1][0] + building[2][0] // 2,
                building[1][1] + building[2][1] // 2
            )
            
            # Create L-shaped road (horizontal then vertical)
            midpoint = (building_center[0], town_hall_center[1])
            
            # Add road segments
            roads.append((town_hall_center, midpoint))
            roads.append((midpoint, building_center))
        
        return roads
    
    def _generate_npcs(self, town_name, buildings):
        """
        Generate NPCs for a town.
        
        Args:
            town_name: Town name
            buildings: List of TownBuilding instances
            
        Returns:
            List of Npc instances
        """
        npcs = []
        
        # Create NPCs for each building based on type
        for building in buildings:
            # Determine how many NPCs for this building
            if building.building_type == BuildingType.TOWNHALL:
                npc_count = 1
                npc_types = [NpcType.NOBLE]
            elif building.building_type == BuildingType.TAVERN:
                npc_count = 2
                npc_types = [NpcType.INNKEEPER, NpcType.QUEST_GIVER]
            elif building.building_type == BuildingType.SHOP:
                npc_count = 1
                npc_types = [NpcType.MERCHANT]
            elif building.building_type == BuildingType.BLACKSMITH:
                npc_count = 1
                npc_types = [NpcType.BLACKSMITH]
            elif building.building_type == BuildingType.INN:
                npc_count = 1
                npc_types = [NpcType.INNKEEPER]
            elif building.building_type == BuildingType.TEMPLE:
                npc_count = 1
                npc_types = [NpcType.QUEST_GIVER]
            elif building.building_type == BuildingType.GUILD:
                npc_count = 1
                npc_types = [NpcType.TRAINER]
            elif building.building_type == BuildingType.MARKET:
                npc_count = 3
                npc_types = [NpcType.MERCHANT, NpcType.MERCHANT, NpcType.GUARD]
            elif building.building_type == BuildingType.HOUSE:
                npc_count = 1
                npc_types = [NpcType.VILLAGER]
            else:
                npc_count = 0
                npc_types = []
            
            # Generate NPCs
            for i in range(npc_count):
                npc_type = npc_types[i] if i < len(npc_types) else NpcType.VILLAGER
                
                # Calculate position (inside building)
                pos_x = building.position[0] + building.size[0] // 2
                pos_y = building.position[1] + building.size[1] // 2
                
                # Add some randomness to position
                pos_x += random.randint(-building.size[0] // 4, building.size[0] // 4)
                pos_y += random.randint(-building.size[1] // 4, building.size[1] // 4)
                
                # Create NPC
                npc = Npc(npc_type, self._generate_npc_name(), (pos_x, pos_y))
                
                # Add NPC to building
                building.add_npc(npc)
                
                # Add dialog
                if npc_type == NpcType.MERCHANT:
                    npc.add_dialog("greeting", f"Welcome to my shop! Looking to buy or sell?")
                    npc.add_dialog("farewell", "Thank you for your business. Come again!")
                elif npc_type == NpcType.BLACKSMITH:
                    npc.add_dialog("greeting", f"Need something forged? I'm the best smith in {town_name}.")
                    npc.add_dialog("farewell", "Stay sharp out there!")
                elif npc_type == NpcType.INNKEEPER:
                    npc.add_dialog("greeting", f"Welcome traveler! Need a room or just a drink?")
                    npc.add_dialog("farewell", "Safe travels, friend.")
                elif npc_type == NpcType.GUARD:
                    npc.add_dialog("greeting", f"Keep out of trouble while in {town_name}.")
                    npc.add_dialog("farewell", "Move along now.")
                elif npc_type == NpcType.QUEST_GIVER:
                    npc.add_dialog("greeting", f"You look capable. I might have a job for someone like you.")
                    npc.add_dialog("farewell", "Come back when you've finished that task.")
                elif npc_type == NpcType.TRAINER:
                    npc.add_dialog("greeting", f"Looking to improve your skills? You've come to the right place.")
                    npc.add_dialog("farewell", "Practice makes perfect!")
                elif npc_type == NpcType.VILLAGER:
                    npc.add_dialog("greeting", f"Hello stranger. New to {town_name}?")
                    npc.add_dialog("farewell", "Good day to you.")
                elif npc_type == NpcType.NOBLE:
                    npc.add_dialog("greeting", f"Welcome to {town_name}. I am the mayor here.")
                    npc.add_dialog("farewell", "I have other matters to attend to now.")
                
                npcs.append(npc)
        
        # Add some wandering NPCs not tied to buildings
        wandering_count = random.randint(3, 6)
        
        for _ in range(wandering_count):
            # Random position in town
            pos_x = random.randint(50, min(1150, buildings[0].position[0] + buildings[0].size[0] * 2))
            pos_y = random.randint(50, min(750, buildings[0].position[1] + buildings[0].size[1] * 2))
            
            # Create NPC
            npc_type = random.choice([NpcType.VILLAGER, NpcType.GUARD, NpcType.BEGGAR])
            npc = Npc(npc_type, self._generate_npc_name(), (pos_x, pos_y))
            
            # Add dialog
            if npc_type == NpcType.VILLAGER:
                npc.add_dialog("greeting", random.choice([
                    f"Hello there! Lovely day in {town_name}, isn't it?",
                    f"You're not from around here, are you?",
                    f"Have you been to the tavern yet? Best ale in the region!"
                ]))
            elif npc_type == NpcType.GUARD:
                npc.add_dialog("greeting", random.choice([
                    f"Move along, citizen.",
                    f"I'm keeping an eye on you, stranger.",
                    f"Report any suspicious activity immediately."
                ]))
            elif npc_type == NpcType.BEGGAR:
                npc.add_dialog("greeting", random.choice([
                    f"Spare a coin for the poor?",
                    f"Please help a fellow in need...",
                    f"Haven't eaten in days... anything helps..."
                ]))
            
            npcs.append(npc)
        
        return npcs
    
    def generate_town(self, name=None, size=(1200, 800)):
        """
        Generate a complete town.
        
        Args:
            name: Town name (or None for random)
            size: (width, height) tuple
            
        Returns:
            Town instance
        """
        # Generate town name if not provided
        if name is None:
            prefixes = ["North", "South", "East", "West", "New", "Old", "Upper", "Lower"]
            suffixes = ["ville", "ton", "burgh", "field", "ford", "haven", "wood", "port", "bridge"]
            
            prefix = random.choice(prefixes)
            middle = random.choice(self.first_names)
            suffix = random.choice(suffixes)
            
            name = f"{prefix} {middle}{suffix}"
        
        # Create town
        town = Town(name, size)
        
        # Generate building layout
        building_layout = self._generate_building_layout(size)
        
        # Create building instances
        for building_type, position, building_size in building_layout:
            building_name = self._generate_building_name(building_type, name)
            building = TownBuilding(building_type, building_name, position, building_size)
            town.add_building(building)
        
        # Generate roads
        road_layout = self._generate_roads(size, building_layout)
        for start, end in road_layout:
            town.add_road(start, end)
        
        # Generate NPCs
        npcs = self._generate_npcs(name, town.buildings)
        
        # Add NPCs to town
        for npc in npcs:
            if npc not in town.npcs:
                town.add_npc(npc)
        
        logger.info(f"Generated town '{name}' with {len(town.buildings)} buildings and {len(town.npcs)} NPCs")
        
        return town

class TownState(GameState):
    """
    Game state for town exploration and interaction.
    
    This state handles:
    - Town exploration
    - Building/NPC interaction
    - Shopping and services
    - Quests and dialog
    """
    
    def __init__(self, state_manager, event_bus, settings):
        """Initialize the town state."""
        super().__init__(state_manager, event_bus, settings)
        
        # Town data
        self.town = None
        self.town_generator = TownGenerator()
        
        # Player
        self.player_pos = (600, 400)
        self.player_speed = 200  # Pixels per second
        self.player_direction = (0, 0)
        self.player_moving = False
        
        # Camera
        self.camera_x = 0
        self.camera_y = 0
        
        # UI
        self.ui_manager = None
        self.dialog_panel = None
        self.dialog_text = None
        self.dialog_options = []
        
        # Interaction
        self.current_building = None
        self.current_npc = None
        self.in_conversation = False
        self.in_shop = False
        self.shop_inventory = []
        
        # UI colors
        self.colors = {
            'player': (0, 0, 255),
            'building': {
                BuildingType.TAVERN: (150, 100, 50),
                BuildingType.SHOP: (150, 150, 100),
                BuildingType.BLACKSMITH: (100, 100, 100),
                BuildingType.INN: (150, 120, 80),
                BuildingType.TEMPLE: (200, 200, 250),
                BuildingType.GUILD: (100, 100, 150),
                BuildingType.TOWNHALL: (200, 150, 100),
                BuildingType.MARKET: (200, 200, 150),
                BuildingType.HOUSE: (180, 150, 120)
            },
            'npc': {
                NpcType.MERCHANT: (150, 150, 50),
                NpcType.BLACKSMITH: (100, 100, 100),
                NpcType.INNKEEPER: (150, 120, 80),
                NpcType.GUARD: (100, 100, 150),
                NpcType.QUEST_GIVER: (200, 150, 50),
                NpcType.TRAINER: (150, 100, 150),
                NpcType.VILLAGER: (100, 150, 100),
                NpcType.NOBLE: (200, 150, 100),
                NpcType.BEGGAR: (150, 150, 150)
            },
            'road': (150, 150, 150),
            'text': (255, 255, 255),
            'dialog_bg': (0, 0, 0, 180),
            'button': (100, 100, 150),
            'button_hover': (150, 150, 200)
        }
        
        logger.info("TownState initialized")
    
    def enter(self, data=None):
        """Set up the state when entered."""
        super().enter(data)
        
        # Initialize UI manager
        screen = pygame.display.get_surface()
        self.ui_manager = UIManager(screen)
        
        # If location data is provided, use it to determine town
        location = None
        if data and "location" in data:
            location = data["location"]
            logger.info(f"Entering town at location: {location.name}")
        
        # Get existing town data or create a new town
        town_data = self.state_manager.get_persistent_data("current_town")
        if town_data:
            self.town = Town.from_dict(town_data)
            logger.info(f"Loaded existing town: {self.town.name}")
        else:
            # Create new town
            if location:
                town_name = location.name
            else:
                town_name = None
            
            self.town = self.town_generator.generate_town(town_name)
            logger.info(f"Generated new town: {self.town.name}")
        
        # Get player position if available
        player_pos = self.state_manager.get_persistent_data("player_town_position")
        if player_pos:
            self.player_town_position = player_pos
        else:
            # Default to center of town
            self.player_town_position = (self.town.width // 2, self.town.height // 2)
        
        # Center camera on player
        self._center_camera()
        
        # Set up UI for interaction
        self._setup_ui()
        
        logger.info(f"Entered town state for {self.town.name}")
    
    def exit(self):
        """Clean up when leaving the state."""
        # Save town data
        self.state_manager.set_persistent_data("current_town", self.town.to_dict())
        
        # Save player position
        self.state_manager.set_persistent_data("player_town_position", self.player_pos)
        
        super().exit()
        logger.info(f"Exited town state for {self.town.name}")
    
    def handle_event(self, event):
        """Handle pygame events."""
        if not self.active:
            return
        
        # Handle UI events first
        if self.ui_manager.handle_event(event):
            return
        
        # If in conversation or shop, only handle UI events
        if self.in_conversation or self.in_shop:
            return
        
        if event.type == pygame.KEYDOWN:
            # Movement keys
            if event.key == pygame.K_w or event.key == pygame.K_UP:
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
            
            # Interaction key
            elif event.key == pygame.K_e or event.key == pygame.K_RETURN:
                self._handle_interaction()
                
            # Exit town
            elif event.key == pygame.K_ESCAPE:
                self._exit_town()
        
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
            # Handle mouse clicks for interaction
            if event.button == 1:  # Left click
                # Convert screen position to world position
                world_pos = self._screen_to_world(event.pos)
                
                # Check if clicked on a building or NPC
                building = self.town.get_building_at(world_pos)
                npc = self.town.get_npc_at(world_pos)
                
                if building:
                    self.current_building = building
                    self._show_building_info(building)
                elif npc:
                    self.current_npc = npc
                    self._start_conversation(npc)
    
    def update(self, dt):
        """Update game state."""
        if not self.active:
            return
        
        # Update UI
        self.ui_manager.update(dt)
        
        # Skip world updates if in conversation or shop
        if self.in_conversation or self.in_shop:
            return
        
        # Update player movement
        if self.player_moving:
            # Calculate movement based on direction and speed
            dx = self.player_direction[0] * self.player_speed * dt
            dy = self.player_direction[1] * self.player_speed * dt
            
            # Calculate new position
            new_x = self.player_pos[0] + dx
            new_y = self.player_pos[1] + dy
            
            # Clamp to town boundaries
            new_x = max(0, min(self.town.size[0], new_x))
            new_y = max(0, min(self.town.size[1], new_y))
            
            # Check for collision with buildings
            collision = False
            for building in self.town.buildings:
                if building.get_rect().collidepoint(new_x, new_y):
                    collision = True
                    break
            
            # Update position if no collision
            if not collision:
                self.player_pos = (new_x, new_y)
                
                # Update camera
                self._center_camera()
        
        # Update NPCs (simple random movement for now)
        for npc in self.town.npcs:
            # Only update NPCs not in buildings and with 1% chance per frame
            if npc.building is None and random.random() < 0.01:
                # Random direction
                dx = random.choice([-1, 0, 1])
                dy = random.choice([-1, 0, 1])
                
                # Small movement
                new_x = npc.position[0] + dx * 5
                new_y = npc.position[1] + dy * 5
                
                # Clamp to town boundaries
                new_x = max(0, min(self.town.size[0], new_x))
                new_y = max(0, min(self.town.size[1], new_y))
                
                # Update position
                npc.position = (new_x, new_y)
        
        # Check for nearby buildings and NPCs
        self._check_nearby_entities()
    
    def render(self, screen):
        """Render the game state."""
        if not self.visible:
            return
        
        # Fill background with town color
        screen.fill(self.town.background_color)
        
        # Render town elements
        self._render_town(screen)
        
        # Render player
        self._render_player(screen)
        
        # Render UI
        self.ui_manager.render()
    
    def _setup_ui(self):
        """Set up UI elements."""
        screen_width, screen_height = pygame.display.get_surface().get_size()
        
        # Create dialog panel (initially hidden)
        self.dialog_panel = self.ui_manager.create_panel(
            pygame.Rect(50, screen_height - 250, screen_width - 100, 200)
        )
        self.dialog_panel.visible = False
        
        # Create dialog text label
        self.dialog_text = self.ui_manager.create_label(
            pygame.Rect(20, 20, self.dialog_panel.rect.width - 40, 60),
            "Dialog text here",
            self.dialog_panel
        )
        
        # Create close button for dialog
        close_button = self.ui_manager.create_button(
            pygame.Rect(self.dialog_panel.rect.width - 100, self.dialog_panel.rect.height - 50, 80, 30),
            "Close",
            self._close_dialog,
            self.dialog_panel
        )
    
    def _center_camera(self):
        """Center camera on player."""
        screen_width, screen_height = pygame.display.get_surface().get_size()
        
        self.camera_x = self.player_pos[0] - screen_width // 2
        self.camera_y = self.player_pos[1] - screen_height // 2
        
        # Clamp camera to town boundaries
        self.camera_x = max(0, min(self.town.size[0] - screen_width, self.camera_x))
        self.camera_y = max(0, min(self.town.size[1] - screen_height, self.camera_y))
    
    
    def _world_to_screen(self, world_pos):
        """
        Convert world coordinates to screen coordinates.
        
        Args:
            world_pos: (x, y) world position
            
        Returns:
            (x, y) screen position
        """
        return (world_pos[0] - self.camera_x, world_pos[1] - self.camera_y)

    def _screen_to_world(self, screen_pos):
        """
        Convert screen coordinates to world coordinates.
        
        Args:
            screen_pos: (x, y) screen position
            
        Returns:
            (x, y) world position
        """
        return (screen_pos[0] + self.camera_x, screen_pos[1] + self.camera_y)
    
    def _handle_interaction(self):
        """Handle player interaction with nearby objects."""
        # Check if near a building
        nearest_building = None
        nearest_building_dist = float('inf')
        
        for building in self.town.buildings:
            building_rect = building.get_rect()
            
            # Calculate distance to building center
            building_center = (
                building_rect.centerx,
                building_rect.centery
            )
            
            dx = building_center[0] - self.player_town_position[0]
            dy = building_center[1] - self.player_town_position[1]
            distance = math.sqrt(dx*dx + dy*dy)
            
            # Check if closer than current nearest
            if distance < nearest_building_dist and distance < 100:
                nearest_building = building
                nearest_building_dist = distance
        
        # Check if near an NPC
        nearest_npc = None
        nearest_npc_dist = float('inf')
        
        for npc in self.town.npcs:
            npc_rect = npc.get_rect()
            
            # Calculate distance to NPC
            dx = npc.position[0] - self.player_town_position[0]
            dy = npc.position[1] - self.player_town_position[1]
            distance = math.sqrt(dx*dx + dy*dy)
            
            # Check if closer than current nearest
            if distance < nearest_npc_dist and distance < 50:
                nearest_npc = npc
                nearest_npc_dist = distance
        
        # Prioritize NPC interaction
        if nearest_npc:
            self.current_npc = nearest_npc
            self._start_conversation(nearest_npc)
        elif nearest_building:
            self.current_building = nearest_building
            self._enter_building(nearest_building)
    
    def _check_nearby_entities(self):
        """Check for and highlight nearby buildings and NPCs."""
        # TODO: Implement highlighting of nearby interactable entities
        pass
    
    def _show_building_info(self, building):
        """
        Show information about a building.
        
        Args:
            building: TownBuilding instance
        """
        # Update dialog for building info
        self.dialog_text.set_text(f"{building.name} - {building.building_type.name}")
        
        # Clear and set up dialog options
        for button in self.dialog_options:
            self.ui_manager.remove_element(button)
        
        self.dialog_options = []
        
        # Add enter button
        enter_button = self.ui_manager.create_button(
            pygame.Rect(20, 100, 150, 30),
            "Enter Building",
            lambda _: self._enter_building(building),
            self.dialog_panel
        )
        self.dialog_options.append(enter_button)
        
        # Show dialog
        self.dialog_panel.visible = True
    
    def _enter_building(self, building):
        """
        Enter a building and show interior.
        
        Args:
            building: TownBuilding instance
        """
        logger.info(f"Entering building: {building.name}")
        
        # Update dialog for building interior
        self.dialog_text.set_text(f"You are inside {building.name}.")
        
        # Clear and set up dialog options
        for button in self.dialog_options:
            self.ui_manager.remove_element(button)
        
        self.dialog_options = []
        
        # Add options based on building type
        y_pos = 100
        
        if building.building_type == BuildingType.SHOP:
            shop_button = self.ui_manager.create_button(
                pygame.Rect(20, y_pos, 150, 30),
                "Shop",
                lambda _: self._open_shop(building),
                self.dialog_panel
            )
            self.dialog_options.append(shop_button)
            y_pos += 40
        
        elif building.building_type == BuildingType.TAVERN:
            rest_button = self.ui_manager.create_button(
                pygame.Rect(20, y_pos, 150, 30),
                "Rest",
                lambda _: self._rest_at_tavern(),
                self.dialog_panel
            )
            self.dialog_options.append(rest_button)
            y_pos += 40
            
            drink_button = self.ui_manager.create_button(
                pygame.Rect(20, y_pos, 150, 30),
                "Buy a Drink",
                lambda _: self._buy_drink(),
                self.dialog_panel
            )
            self.dialog_options.append(drink_button)
            y_pos += 40
        
        # Add exit button
        exit_button = self.ui_manager.create_button(
            pygame.Rect(20, y_pos, 150, 30),
            "Exit Building",
            lambda _: self._close_dialog(),
            self.dialog_panel
        )
        self.dialog_options.append(exit_button)
        
        # Show dialog
        self.dialog_panel.visible = True
    
    def _start_conversation(self, npc):
        """
        Start a conversation with an NPC.
        
        Args:
            npc: Npc instance
        """
        logger.info(f"Starting conversation with {npc.name}")
        
        # Set conversation flag
        self.in_conversation = True
        
        # Update dialog for conversation
        greeting = npc.get_dialog("greeting")
        self.dialog_text.set_text(f"{npc.name}: {greeting}")
        
        # Clear and set up dialog options
        for button in self.dialog_options:
            self.ui_manager.remove_element(button)
        
        self.dialog_options = []
        
        # Add dialog options based on NPC type
        y_pos = 100
        
        if npc.npc_type == NpcType.MERCHANT:
            shop_button = self.ui_manager.create_button(
                pygame.Rect(20, y_pos, 200, 30),
                "I'd like to see your wares",
                lambda _: self._open_shop(npc.building),
                self.dialog_panel
            )
            self.dialog_options.append(shop_button)
            y_pos += 40
        
        elif npc.npc_type == NpcType.QUEST_GIVER:
            quest_button = self.ui_manager.create_button(
                pygame.Rect(20, y_pos, 200, 30),
                "Do you have any work for me?",
                lambda _: self._offer_quest(npc),
                self.dialog_panel
            )
            self.dialog_options.append(quest_button)
            y_pos += 40
        
        # Add generic dialog options
        ask_button = self.ui_manager.create_button(
            pygame.Rect(20, y_pos, 200, 30),
            "Tell me about this town",
            lambda _: self._continue_dialog(npc, "about_town"),
            self.dialog_panel
        )
        self.dialog_options.append(ask_button)
        y_pos += 40
        
        farewell_button = self.ui_manager.create_button(
            pygame.Rect(20, y_pos, 200, 30),
            "Goodbye",
            lambda _: self._end_conversation(npc),
            self.dialog_panel
        )
        self.dialog_options.append(farewell_button)
        
        # Show dialog
        self.dialog_panel.visible = True
    
    def _continue_dialog(self, npc, dialog_key):
        """
        Continue dialog with new text.
        
        Args:
            npc: Npc instance
            dialog_key: Dialog key to display
        """
        # Check if NPC has this dialog
        if dialog_key in npc.dialog:
            response = npc.get_dialog(dialog_key)
        else:
            # Generate a response if not defined
            if dialog_key == "about_town":
                response = f"This is {self.town.name}. It's a decent place to live. " + \
                          f"We have a good tavern and the local merchants sell quality goods."
            else:
                response = "I don't know much about that."
            
            # Add to NPC's dialog
            npc.add_dialog(dialog_key, response)
        
        # Update dialog text
        self.dialog_text.set_text(f"{npc.name}: {response}")
    
    def _end_conversation(self, npc):
        """
        End conversation with an NPC.
        
        Args:
            npc: Npc instance
        """
        # Get farewell dialog
        farewell = npc.get_dialog("farewell")
        self.dialog_text.set_text(f"{npc.name}: {farewell}")
        
        # Clear dialog options except close
        for button in self.dialog_options:
            self.ui_manager.remove_element(button)
        
        self.dialog_options = []
        
        # Add close button
        close_button = self.ui_manager.create_button(
            pygame.Rect(20, 100, 150, 30),
            "Close",
            lambda _: self._close_dialog(),
            self.dialog_panel
        )
        self.dialog_options.append(close_button)
        
        # End conversation
        self.in_conversation = False
    
    def _open_shop(self, building):
        """
        Open shop interface.
        
        Args:
            building: Building containing the shop
        """
        logger.info(f"Opening shop in {building.name}")
        
        # Set shop flag
        self.in_shop = True
        
        # Clear dialog
        self.dialog_text.set_text(f"Welcome to {building.name}! What would you like to buy?")
        
        # Clear and set up shop options
        for button in self.dialog_options:
            self.ui_manager.remove_element(button)
        
        self.dialog_options = []
        
        # Generate shop inventory based on building type
        self.shop_inventory = []
        
        if building.building_type == BuildingType.SHOP:
            self.shop_inventory = [
                {"name": "Health Potion", "type": "consumable", "price": 10},
                {"name": "Mana Potion", "type": "consumable", "price": 15},
                {"name": "Torch", "type": "consumable", "price": 5},
                {"name": "Backpack", "type": "equipment", "price": 50}
            ]
        elif building.building_type == BuildingType.BLACKSMITH:
            self.shop_inventory = [
                {"name": "Iron Sword", "type": "weapon", "price": 100},
                {"name": "Steel Shield", "type": "armor", "price": 80},
                {"name": "Leather Armor", "type": "armor", "price": 120},
                {"name": "Arrows (20)", "type": "consumable", "price": 15}
            ]
        elif building.building_type == BuildingType.TAVERN:
            self.shop_inventory = [
                {"name": "Ale", "type": "consumable", "price": 2},
                {"name": "Wine", "type": "consumable", "price": 5},
                {"name": "Meal", "type": "consumable", "price": 8},
                {"name": "Room (1 night)", "type": "service", "price": 10}
            ]
        
        # Add items to shop display
        y_pos = 100
        
        for item in self.shop_inventory:
            item_button = self.ui_manager.create_button(
                pygame.Rect(20, y_pos, 300, 30),
                f"{item['name']} - {item['price']} gold",
                lambda _, item=item: self._buy_item(item),
                self.dialog_panel
            )
            self.dialog_options.append(item_button)
            y_pos += 40
        
        # Add exit button
        exit_button = self.ui_manager.create_button(
            pygame.Rect(20, y_pos, 150, 30),
            "Exit Shop",
            lambda _: self._close_shop(),
            self.dialog_panel
        )
        self.dialog_options.append(exit_button)
        
        # Show dialog
        self.dialog_panel.visible = True
    
    def _buy_item(self, item):
        """
        Buy an item from the shop.
        
        Args:
            item: Item data dictionary
        """
        logger.info(f"Buying item: {item['name']}")
        
        # Get player character
        character = self.state_manager.get_persistent_data("player_character")
        
        if character:
            # Check if player has enough gold
            if character.gold >= item["price"]:
                # Deduct gold
                character.gold -= item["price"]
                
                # Add item to inventory (simplified, just a message for now)
                self.dialog_text.set_text(f"You purchased {item['name']} for {item['price']} gold.")
                
                # Update character
                self.state_manager.set_persistent_data("player_character", character)
            else:
                self.dialog_text.set_text(f"You don't have enough gold to buy {item['name']}.")
        else:
            self.dialog_text.set_text("Error: Could not access player inventory.")
    
    def _close_shop(self):
        """Close the shop interface."""
        # Clear shop flag
        self.in_shop = False
        
        # Close dialog
        self._close_dialog()
    
    def _offer_quest(self, npc):
        """
        Offer a quest from an NPC.
        
        Args:
            npc: Npc instance
        """
        # Generate a simple quest if none exists
        if not npc.quests:
            quest_types = [
                "Fetch Quest: Bring me 5 herbs from the forest.",
                "Kill Quest: Clear out 10 monsters from the nearby cave.",
                "Delivery Quest: Take this package to the next town.",
                "Escort Quest: Help me reach the temple safely.",
                "Investigation Quest: Find out who's been stealing from the market."
            ]
            
            npc.quests.append(random.choice(quest_types))
        
        # Display quest
        quest_text = npc.quests[0]
        self.dialog_text.set_text(f"{npc.name}: I need your help. {quest_text}")
        
        # Update dialog options
        for button in self.dialog_options:
            self.ui_manager.remove_element(button)
        
        self.dialog_options = []
        
        # Add accept button
        accept_button = self.ui_manager.create_button(
            pygame.Rect(20, 100, 150, 30),
            "Accept Quest",
            lambda _: self._accept_quest(npc, quest_text),
            self.dialog_panel
        )
        self.dialog_options.append(accept_button)
        
        # Add decline button
        decline_button = self.ui_manager.create_button(
            pygame.Rect(180, 100, 150, 30),
            "Decline",
            lambda _: self._continue_dialog(npc, "quest_declined"),
            self.dialog_panel
        )
        self.dialog_options.append(decline_button)
    
    def _accept_quest(self, npc, quest_text):
        """
        Accept a quest from an NPC.
        
        Args:
            npc: Npc instance
            quest_text: Quest description
        """
        logger.info(f"Accepted quest from {npc.name}: {quest_text}")
        
        # Add response dialog
        npc.add_dialog("quest_accepted", 
                      "Excellent! Come back when you've completed the task.")
        
        # Update dialog
        self.dialog_text.set_text(f"{npc.name}: {npc.get_dialog('quest_accepted')}")
        
        # TODO: Add quest to player's quest log
        
        # Update dialog options
        for button in self.dialog_options:
            self.ui_manager.remove_element(button)
        
        self.dialog_options = []
        
        # Add close button
        close_button = self.ui_manager.create_button(
            pygame.Rect(20, 100, 150, 30),
            "Close",
            lambda _: self._close_dialog(),
            self.dialog_panel
        )
        self.dialog_options.append(close_button)
    
    def _rest_at_tavern(self):
        """Rest at tavern to recover health."""
        # Get player character
        character = self.state_manager.get_persistent_data("player_character")
        
        if character:
            # Deduct gold
            if character.gold >= 10:
                character.gold -= 10
                
                # Heal to full
                old_health = character.health
                character.health = character.max_health
                
                # Update dialog
                self.dialog_text.set_text(
                    f"You rest at the tavern and recover {character.health - old_health} health.")
                
                # Update character
                self.state_manager.set_persistent_data("player_character", character)
            else:
                self.dialog_text.set_text("You don't have enough gold to rest here.")
        else:
            self.dialog_text.set_text("Error: Could not access player data.")
    
    def _buy_drink(self):
        """Buy a drink at the tavern."""
        # Get player character
        character = self.state_manager.get_persistent_data("player_character")
        
        if character:
            # Deduct gold
            if character.gold >= 2:
                character.gold -= 2
                
                # Add some health
                old_health = character.health
                character.health = min(character.max_health, character.health + 5)
                
                # Update dialog
                self.dialog_text.set_text(
                    f"You enjoy a refreshing drink and recover {character.health - old_health} health.")
                
                # Update character
                self.state_manager.set_persistent_data("player_character", character)
            else:
                self.dialog_text.set_text("You don't have enough gold to buy a drink.")
        else:
            self.dialog_text.set_text("Error: Could not access player data.")
    
    def _close_dialog(self):
        """Close dialog panel and reset state."""
        self.dialog_panel.visible = False
        self.in_conversation = False
        self.in_shop = False
        self.current_building = None
        self.current_npc = None
        
        # Clear dialog options
        for button in self.dialog_options:
            self.ui_manager.remove_element(button)
        
        self.dialog_options = []
    
    def _exit_town(self):
        """Exit town and return to world map."""
        logger.info(f"Exiting town {self.town.name}")
        
        # Return to world exploration
        self.event_bus.publish("exit_location", None)
        self.change_state("world_exploration")
    
    def _render_town(self, screen):
        """
        Render the town.
        
        Args:
            screen: Pygame surface to render to
        """
        # Render roads
        for road in self.town.roads:
            start_pos = self._world_to_screen(road[0])
            end_pos = self._world_to_screen(road[1])
            
            pygame.draw.line(screen, self.colors['road'], start_pos, end_pos, 8)
        
        # Render buildings
        for building in self.town.buildings:
            # Convert world rect to screen rect
            building_world_rect = building.get_rect()
            building_screen_rect = pygame.Rect(
                building_world_rect.x - self.camera_x,
                building_world_rect.y - self.camera_y,
                building_world_rect.width,
                building_world_rect.height
            )
            
            # Skip if not visible on screen
            screen_rect = screen.get_rect()
            if not screen_rect.colliderect(building_screen_rect):
                continue
            
            # Get building color based on type
            color = self.colors['building'].get(building.building_type, (150, 150, 150))
            
            # Draw building
            pygame.draw.rect(screen, color, building_screen_rect)
            pygame.draw.rect(screen, (0, 0, 0), building_screen_rect, 2)
            
            # Draw building name if close enough to be readable
            if building_screen_rect.width >= 40 and building_screen_rect.height >= 40:
                # Create font if needed
                if not self.ui_manager.default_font:
                    self.ui_manager.default_font = pygame.font.SysFont(None, 20)
                
                # Render name (shortened if too long)
                name = building.name
                if len(name) > 20:
                    name = name[:17] + "..."
                
                name_surface = self.ui_manager.default_font.render(name, True, (0, 0, 0))
                name_rect = name_surface.get_rect(center=building_screen_rect.center)
                
                # Draw only if name fits in building
                if (name_rect.width <= building_screen_rect.width - 10 and 
                    name_rect.height <= building_screen_rect.height - 10):
                    screen.blit(name_surface, name_rect)
        
        # Render NPCs
        for npc in self.town.npcs:
            # Convert world position to screen position
            screen_x, screen_y = self._world_to_screen(npc.position)
            
            # Skip if not visible on screen
            if not (0 <= screen_x < screen.get_width() and 0 <= screen_y < screen.get_height()):
                continue
            
            # Get NPC color based on type
            color = self.colors['npc'].get(npc.npc_type, (200, 200, 200))
            
            # Draw NPC
            pygame.draw.circle(screen, color, (int(screen_x), int(screen_y)), 10)
            pygame.draw.circle(screen, (0, 0, 0), (int(screen_x), int(screen_y)), 10, 1)
    
    def _render_player(self, screen):
        """Render the player character with pixel art style similar to NPCs."""
        # Convert world position to screen coordinates
        screen_x, screen_y = self._world_to_screen(self.player_town_position)
        
        # Create player asset if it doesn't exist yet
        if not hasattr(self, 'player_asset') or not self.player_asset:
            tile_size = 32
            self.player_asset = pygame.Surface((tile_size, tile_size), pygame.SRCALPHA)
            # Player colors (distinctive blue theme)
            body_color = (0, 100, 200)
            head_color = (240, 200, 160)
            detail_color = (200, 200, 0)
            # Draw body similar to NPCs
            body_width = tile_size // 2
            body_height = tile_size // 2
            body_x = (tile_size - body_width) // 2
            body_y = tile_size - body_height - 2
            pygame.draw.rect(self.player_asset, body_color, (body_x, body_y, body_width, body_height))
            # Draw head
            head_size = tile_size // 3
            head_x = (tile_size - head_size) // 2
            head_y = body_y - head_size
            pygame.draw.rect(self.player_asset, head_color, (head_x, head_y, head_size, head_size))
            # Draw details
            detail_size = max(2, tile_size // 8)
            pygame.draw.rect(self.player_asset, detail_color, (body_x, body_y, body_width, detail_size))
            # Draw eyes
            eye_size = max(1, tile_size // 10)
            eye_y = head_y + head_size // 3
            pygame.draw.rect(self.player_asset, (0, 0, 0), (head_x + head_size // 4 - eye_size // 2, eye_y, eye_size, eye_size))
            pygame.draw.rect(self.player_asset, (0, 0, 0), (head_x + head_size * 3 // 4 - eye_size // 2, eye_y, eye_size, eye_size))
        
        asset_rect = self.player_asset.get_rect(center=(int(screen_x), int(screen_y)))
        screen.blit(self.player_asset, asset_rect)
        
        # Add a highlight circle when player is moving
        if self.player_moving:
            pygame.draw.circle(screen, (255, 255, 255, 128), (int(screen_x), int(screen_y)), 20, 1)
import pygame
import logging
import random
from game_state import GameState

logger = logging.getLogger("town")

class TownBuilding:
    """Represents a building in a town."""
    
    def __init__(self, name, building_type, position, size):
        self.name = name
        self.type = building_type
        self.position = position
        self.size = size
        self.description = f"A {building_type} called {name}"
        
        # Special properties based on type
        if building_type == "shop":
            self.shop_id = f"shop_{name.lower().replace(' ', '_')}"
        elif building_type == "inn":
            self.room_price = random.randint(5, 20)
        elif building_type == "guild":
            self.guild_type = random.choice(["adventurer", "mage", "warrior", "thief"])
    
    def get_rect(self):
        """Get pygame Rect for this building."""
        return pygame.Rect(
            self.position[0] * 32,  # Tile size
            self.position[1] * 32,
            self.size[0] * 32,
            self.size[1] * 32
        )
    
    def to_dict(self):
        """Convert to dictionary for serialization."""
        data = {
            'name': self.name,
            'type': self.type,
            'position': self.position,
            'size': self.size,
            'description': self.description
        }
        
        # Add special properties
        if self.type == "shop":
            data['shop_id'] = self.shop_id
        elif self.type == "inn":
            data['room_price'] = self.room_price
        elif self.type == "guild":
            data['guild_type'] = self.guild_type
            
        return data
    
    @classmethod
    def from_dict(cls, data):
        """Create from dictionary."""
        building = cls(
            data['name'],
            data['type'],
            data['position'],
            data['size']
        )
        
        building.description = data.get('description', building.description)
        
        # Restore special properties
        if data['type'] == "shop" and 'shop_id' in data:
            building.shop_id = data['shop_id']
        elif data['type'] == "inn" and 'room_price' in data:
            building.room_price = data['room_price']
        elif data['type'] == "guild" and 'guild_type' in data:
            building.guild_type = data['guild_type']
            
        return building

class Npc:
    """Represents an NPC in a town."""
    
    def __init__(self, name, npc_type, position):
        self.name = name
        self.type = npc_type
        self.position = position
        self.dialog = [f"Hello, I'm {name}!"]
        
        # Set dialog based on type
        if npc_type == "merchant":
            self.dialog.append("Would you like to see my wares?")
            self.dialog.append("I have the finest goods in town!")
        elif npc_type == "guard":
            self.dialog.append("Keep out of trouble, stranger.")
            self.dialog.append("I'm watching you.")
        elif npc_type == "villager":
            self.dialog.append("Nice weather we're having.")
            self.dialog.append("Have you heard about the trouble in the mines?")
        elif npc_type == "traveler":
            self.dialog.append("I've come from far away lands.")
            self.dialog.append("The roads are dangerous these days.")
    
    def get_rect(self):
        """Get pygame Rect for this NPC."""
        return pygame.Rect(
            self.position[0] * 32,  # Tile size
            self.position[1] * 32,
            32, 32
        )
    
    def get_random_dialog(self):
        """Get a random dialog line."""
        return random.choice(self.dialog)
    
    def to_dict(self):
        """Convert to dictionary for serialization."""
        return {
            'name': self.name,
            'type': self.type,
            'position': self.position,
            'dialog': self.dialog
        }
    
    @classmethod
    def from_dict(cls, data, buildings=None):
        """Create from dictionary."""
        npc = cls(
            data['name'],
            data['type'],
            data['position']
        )
        
        if 'dialog' in data:
            npc.dialog = data['dialog']
            
        return npc

class Town:
    """Represents a town with buildings and NPCs."""
    
    def __init__(self, id="town_1", name="Town", width=20, height=20):
        self.id = id
        self.name = name
        self.width = width
        self.height = height
        self.buildings = []
        self.npcs = []
        self.danger_level = random.randint(0, 5)
        self.enemy_types = ["bandit", "thief", "drunk"]
    
    def add_building(self, building):
        """Add a building to the town."""
        self.buildings.append(building)
    
    def add_npc(self, npc):
        """Add an NPC to the town."""
        self.npcs.append(npc)
    
    def get_building_at(self, position):
        """Get building at the given position."""
        for building in self.buildings:
            if (position[0] >= building.position[0] and 
                position[0] < building.position[0] + building.size[0] and
                position[1] >= building.position[1] and 
                position[1] < building.position[1] + building.size[1]):
                return building
        return None
    
    def get_npc_at(self, position):
        """Get NPC at the given position."""
        for npc in self.npcs:
            if npc.position == position:
                return npc
        return None
    
    def to_dict(self):
        """Convert to dictionary for serialization."""
        return {
            'id': self.id,
            'name': self.name,
            'width': self.width,
            'height': self.height,
            'buildings': [b.to_dict() for b in self.buildings],
            'npcs': [n.to_dict() for n in self.npcs],
            'danger_level': self.danger_level,
            'enemy_types': self.enemy_types
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create from dictionary."""
        town = cls(
            data['id'],
            data['name'],
            data['width'],
            data['height']
        )
        
        # Add buildings
        for building_data in data['buildings']:
            town.add_building(TownBuilding.from_dict(building_data))
        
        # Add NPCs
        for npc_data in data['npcs']:
            town.add_npc(Npc.from_dict(npc_data))
        
        # Other properties
        if 'danger_level' in data:
            town.danger_level = data['danger_level']
        
        if 'enemy_types' in data:
            town.enemy_types = data['enemy_types']
            
        return town

class TownState(GameState):
    """
    Game state for town exploration and interaction.
    
    This state handles:
    - Town exploration
    - Building/NPC interaction
    - Shopping and services
    - Quests and dialog
    """
    
    def __init__(self, state_manager, event_bus, settings):
        """Initialize town state."""
        super().__init__(state_manager, event_bus, settings)
        
        # Town data
        self.town = None
        self.town_id = "town_1"
        self.town_name = "Default Town"
        self.return_position = (0, 0)  # Position to return to on world map
        
        # Player data
        self.player_town_position = (10, 10)
        self.player_character = None
        self.player_speed = 5  # pixels per second
        self.player_direction = (0, 0)
        self.player_moving = False
        self.target_position = None
        
        # UI elements
        self.font = None
        self.font_small = None
        self.tile_size = 32
        
        # Interaction
        self.nearby_building = None
        self.nearby_npc = None
        self.show_dialog = False
        self.current_dialog = []
        self.dialog_index = 0
        
        # Random event timer
        self.event_timer = 0
        self.event_check_interval = 10  # seconds
        
        # Pixel art assets (placeholders)
        self.tile_assets = {}
        self.building_assets = {}
        self.npc_assets = {}
        self.player_asset = None
        self.town_size_multiplier = 2  # Make town larger
        
        logger.info("TownState initialized")
    
    def enter(self, data=None):
        """Enter town state with data from the world map."""
        super().enter(data)
        
        # Initialize fonts
        pygame.font.init()
        self.font = pygame.font.SysFont(None, 24)
        self.font_small = pygame.font.SysFont(None, 18)
        
        # Load pixel art assets
        self._load_assets()
        
        if data:
            # Check if location data is provided
            location = data.get("location")
            if location:
                self.town_id = f"town_{location.name.lower().replace(' ', '_')}"
                self.town_name = location.name
                logger.info(f"Entering town from location: {location.name}")
            else:
                self.town_id = data.get("town_id", "town_1")
                self.town_name = data.get("town_name", "Default Town")
                
            self.return_position = data.get("return_position", (0, 0))
            
            # Load town data or generate if not exists
            self.town = self._load_town(self.town_id)
            
            # Set player position at town entrance
            self.player_town_position = (self.town.width // 2, self.town.height - 2)
        
        # Get player character
        self.player_character = self.state_manager.get_persistent_data("player_character")
        
        # Subscribe to events
        self.event_bus.subscribe("building_interaction", self._handle_building_interaction)
        self.event_bus.subscribe("npc_interaction", self._handle_npc_interaction)
        
        # Notification that player entered town
        self.event_bus.publish("show_notification", {
            "title": self.town_name,
            "message": f"Welcome to {self.town_name}",
            "duration": 3.0
        })
        
        logger.info(f"Entered town: {self.town_name}")
    
    def exit(self):
        """Exit town state."""
        super().exit()
        
        # Unsubscribe from events
        self.event_bus.unsubscribe("building_interaction", self._handle_building_interaction)
        self.event_bus.unsubscribe("npc_interaction", self._handle_npc_interaction)
        
        # Save town data
        if self.town:
            self.state_manager.set_persistent_data(f"town_{self.town_id}", self.town.to_dict())
        
        logger.info(f"Exited town: {self.town_name}")
    
    def handle_event(self, event):
        """Handle pygame events in town."""
        if not super().handle_event(event):
            if event.type == pygame.KEYDOWN:
                # If showing dialog, advance dialog
                if self.show_dialog:
                    if event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                        self.dialog_index += 1
                        if self.dialog_index >= len(self.current_dialog):
                            self.show_dialog = False
                        return True
                    return False
                
                # Movement
                new_pos = list(self.player_town_position)
                
                if event.key == pygame.K_UP:
                    new_pos[1] -= 1
                elif event.key == pygame.K_DOWN:
                    new_pos[1] += 1
                elif event.key == pygame.K_LEFT:
                    new_pos[0] -= 1
                elif event.key == pygame.K_RIGHT:
                    new_pos[0] += 1
                elif event.key == pygame.K_ESCAPE:
                    # Return to world map
                    self.change_state("world_exploration", {
                        "return_position": self.return_position
                    })
                    return True
                elif event.key == pygame.K_RETURN:
                    # Interact with buildings or NPCs
                    self._interact()
                    return True
                
                # Check if the new position is valid
                if self._is_valid_position(new_pos):
                    self.player_town_position = tuple(new_pos)
                    self._check_nearby_entities()
                    return True
            
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left click
                    # Convert screen position to tile position directly without calling _screen_to_world
                    mouse_x, mouse_y = event.pos
                    tile_x = mouse_x // self.tile_size
                    tile_y = mouse_y // self.tile_size
                    world_pos = (tile_x, tile_y)
                
                    # Check if clicked on a building or NPC
                    building = self.town.get_building_at(world_pos)
                    npc = self.town.get_npc_at(world_pos)
                
                    if building:
                        self.current_building = building
                        self._show_building_info(building)
                        return True
                    elif npc:
                        self.current_npc = npc
                        self._start_conversation(npc)
                        return True
                    else:
                        # Movement handling (existing code)
                        mouse_x, mouse_y = event.pos
                        tile_x = mouse_x // self.tile_size
                        tile_y = mouse_y // self.tile_size
                        new_pos = (tile_x, tile_y)
                        if self._is_valid_position(new_pos):
                            dx = new_pos[0] - self.player_town_position[0]
                            dy = new_pos[1] - self.player_town_position[1]
                            dist = (dx*dx + dy*dy) ** 0.5
                            if dist < 5:
                                self.player_town_position = new_pos
                            else:
                                self.target_position = new_pos
                                self.player_moving = True
                                total = abs(dx) + abs(dy) if (abs(dx)+abs(dy)) != 0 else 1
                                self.player_direction = (dx/total, dy/total)
                            self._check_nearby_entities()
                            return True
        
        return False
    
    def update(self, dt):
        """Update town state."""
        super().update(dt)
        
        # Update event timer
        self.event_timer += dt
        if self.event_timer >= self.event_check_interval:
            self.event_timer = 0
            self._check_for_town_events()
        if hasattr(self, 'player_moving') and self.player_moving and not hasattr(self, 'player_speed'):
            self.player_speed = 5  # Default speed if not set
        
        # Update player movement (target-based)
        if hasattr(self, 'player_moving') and self.player_moving:
            dx = self.player_direction[0] * self.player_speed * dt
            dy = self.player_direction[1] * self.player_speed * dt
            new_x = self.player_town_position[0] + dx
            new_y = self.player_town_position[1] + dy
            if self.target_position:
                target_x, target_y = self.target_position
                if abs(new_x - target_x) < self.player_speed * dt * 1.5 and abs(new_y - target_y) < self.player_speed * dt * 1.5:
                    new_x, new_y = target_x, target_y
                    self.player_moving = False
                    self.target_position = None
                    self.player_direction = (0, 0)
            new_x = max(0, min(self.town.width, new_x))
            new_y = max(0, min(self.town.height, new_y))
            self.player_town_position = (new_x, new_y)
        
        # Check for nearby buildings and NPCs
        self._check_nearby_entities()
    
    def render(self, screen):
        """Render town state."""
        if not self.town:
            return
        
        # Fill background
        screen.fill((50, 100, 50))  # Green background for town
        
        # Draw town grid
        self._draw_town_grid(screen)
        
        # Draw buildings
        for building in self.town.buildings:
            self._draw_building(screen, building)
        
        # Draw NPCs
        for npc in self.town.npcs:
            self._draw_npc(screen, npc)
        
        # Draw player
        player_rect = pygame.Rect(
            self.player_town_position[0] * self.tile_size,
            self.player_town_position[1] * self.tile_size,
            self.tile_size,
            self.tile_size
        )
        pygame.draw.rect(screen, (0, 0, 255), player_rect)  # Blue rectangle for player
        
        # Draw UI
        self._draw_ui(screen)
        
        # Draw dialog if active
        if self.show_dialog:
            self._draw_dialog(screen)
    
    def _draw_town_grid(self, screen):
        """Draw the town grid with pixel art tiles."""
        # Draw ground tiles
        tile_types = ['grass', 'dirt', 'path', 'flower']
        weights = [0.7, 0.15, 0.1, 0.05]  # Probability weights
        
        # Check if we've already generated the tile map
        if not hasattr(self, 'tile_map') or self.tile_map is None:
            # Create a 2D array of tile types
            self.tile_map = []
            for y in range(self.town.height):
                row = []
                for x in range(self.town.width):
                    # Determine tile type
                    if (x == 0 or x == self.town.width - 1 or 
                        y == 0 or y == self.town.height - 1):
                        # Border is always path
                        tile = 'path'
                    else:
                        # Random tile based on weights
                        tile = random.choices(tile_types, weights=weights)[0]
                        
                        # Make paths more continuous
                        if (x > 0 and x-1 < len(row) and row[x-1] == 'path') or (y > 0 and x < len(self.tile_map[y-1]) and self.tile_map[y-1][x] == 'path'):
                            if random.random() < 0.7:
                                tile = 'path'
                
                row.append(tile)
                self.tile_map.append(row)
            
            # Ensure paths to town center
            center_x, center_y = min(self.town.width // 2, len(self.tile_map[0]) - 1), min(self.town.height // 2, len(self.tile_map) - 1)
            # Horizontal path
            for x in range(min(self.town.width, len(self.tile_map[center_y]))):
                self.tile_map[center_y][x] = 'path'
            # Vertical path
            for y in range(min(self.town.height, len(self.tile_map))):
                if center_x < len(self.tile_map[y]):
                    self.tile_map[y][center_x] = 'path'
        
        # Draw tiles
        for y in range(min(self.town.height, len(self.tile_map))):
            for x in range(min(self.town.width, len(self.tile_map[y]))):
                tile_type = self.tile_map[y][x]
                tile_image = self.tile_assets.get(tile_type, self.tile_assets['grass'])
                
                rect = pygame.Rect(
                    x * self.tile_size,
                    y * self.tile_size,
                    self.tile_size,
                    self.tile_size
                )
                
                screen.blit(tile_image, rect)
    
    def _draw_building(self, screen, building):
        """Draw a building on the screen with pixel art."""
        rect = pygame.Rect(
            building.position[0] * self.tile_size,
            building.position[1] * self.tile_size,
            building.size[0] * self.tile_size,
            building.size[1] * self.tile_size
        )
        
        # Get building asset
        building_image = self.building_assets.get(building.type, self.building_assets.get('house'))
        
        # Draw building
        screen.blit(building_image, rect)
        
        # Draw building name above
        name_text = self.font_small.render(building.name, True, (255, 255, 255))
        name_rect = name_text.get_rect(midbottom=(
            rect.centerx,
            rect.top - 2
        ))
        
        # Draw text with shadow for better visibility
        shadow_rect = name_rect.copy()
        shadow_rect.move_ip(1, 1)
        shadow_text = self.font_small.render(building.name, True, (0, 0, 0))
        screen.blit(shadow_text, shadow_rect)
        screen.blit(name_text, name_rect)
    
    def _draw_npc(self, screen, npc):
        """Draw an NPC on the screen with pixel art."""
        rect = pygame.Rect(
            npc.position[0] * self.tile_size,
            npc.position[1] * self.tile_size,
            self.tile_size,
            self.tile_size
        )
        
        # Get NPC asset
        npc_image = self.npc_assets.get(npc.type, self.npc_assets.get('villager'))
        
        # Draw NPC
        screen.blit(npc_image, rect)
        
        # Draw NPC name above
        name_text = self.font_small.render(npc.name, True, (255, 255, 255))
        name_rect = name_text.get_rect(midbottom=(
            rect.centerx,
            rect.top - 2
        ))
        
        # Draw text with shadow for better visibility
        shadow_rect = name_rect.copy()
        shadow_rect.move_ip(1, 1)
        shadow_text = self.font_small.render(npc.name, True, (0, 0, 0))
        screen.blit(shadow_text, shadow_rect)
        screen.blit(name_text, name_rect)
    
    def _draw_ui(self, screen):
        """Draw UI elements."""
        # Draw town name
        town_text = self.font.render(self.town_name, True, (255, 255, 255))
        screen.blit(town_text, (10, 10))
        
        # Draw player position
        pos_text = self.font_small.render(
            f"Position: {self.player_town_position[0]}, {self.player_town_position[1]}",
            True, (255, 255, 255)
        )
        screen.blit(pos_text, (10, 40))
        
        # Draw nearby building/NPC info
        if self.nearby_building:
            building_text = self.font_small.render(
                f"Nearby: {self.nearby_building.name} (Press ENTER to interact)",
                True, (255, 255, 255)
            )
            screen.blit(building_text, (10, 60))
        elif self.nearby_npc:
            npc_text = self.font_small.render(
                f"Nearby: {self.nearby_npc.name} (Press ENTER to talk)",
                True, (255, 255, 255)
            )
            screen.blit(npc_text, (10, 60))
        
        # Draw help text
        help_text = self.font_small.render(
            "Arrow keys: Move | ENTER: Interact | ESC: Exit town",
            True, (255, 255, 255)
        )
        help_rect = help_text.get_rect(midbottom=(
            screen.get_width() // 2,
            screen.get_height() - 10
        ))
        screen.blit(help_text, help_rect)
    
    def _screen_to_world(self, screen_pos):
        """
        Convert screen coordinates to world coordinates.
        
        Args:
            screen_pos: (x, y) screen position
            
        Returns:
            (x, y) world position
        """
        mouse_x, mouse_y = screen_pos
        tile_x = mouse_x // self.tile_size
        tile_y = mouse_y // self.tile_size
        return (tile_x, tile_y)
    
    def _show_building_info(self, building):
        """
        Show information about a building.
        
        Args:
            building: Building instance
        """
        # Store current building
        self.current_building = building
        
        # Show building information
        self.event_bus.publish("show_notification", {
            "title": building.name,
            "message": f"{building.description}",
            "duration": 2.0
        })
        
        # If it's a special building type, handle its interaction
        if hasattr(building, 'type'):
            self._handle_building_interaction({"building": building})
    
    def _start_conversation(self, npc):
        """
        Start a conversation with an NPC.
        
        Args:
            npc: Npc instance
        """
        logger.info(f"Starting conversation with {npc.name}")
        
        # Show dialog
        self.show_dialog = True
        self.dialog_index = 0
        
        # Store current NPC
        self.nearby_npc = npc
        
        # Get dialog lines
        if hasattr(npc, 'dialog') and npc.dialog:
            self.current_dialog = npc.dialog
        else:
            self.current_dialog = [f"Hello, I'm {npc.name}!"]
        
        # Publish notification
        self.event_bus.publish("show_notification", {
            "title": npc.name,
            "message": f"Talking to {npc.name}",
            "duration": 1.5
        })
    
    def _draw_dialog(self, screen):
        """Draw dialog box."""
        # Dialog box background
        dialog_width = screen.get_width() - 100
        dialog_height = 150
        dialog_rect = pygame.Rect(
            (screen.get_width() - dialog_width) // 2,
            screen.get_height() - dialog_height - 20,
            dialog_width,
            dialog_height
        )
        
        # Draw dialog box
        pygame.draw.rect(screen, (50, 50, 80), dialog_rect)
        pygame.draw.rect(screen, (255, 255, 255), dialog_rect, 2)
        
        # Draw speaker name
        if self.nearby_npc:
            speaker_text = self.font.render(self.nearby_npc.name, True, (255, 255, 200))
            screen.blit(speaker_text, (dialog_rect.left + 20, dialog_rect.top + 15))
        
        # Draw dialog text
        if self.dialog_index < len(self.current_dialog):
            dialog_text = self.current_dialog[self.dialog_index]
            
            # Wrap text
            words = dialog_text.split(' ')
            lines = []
            line = ""
            for word in words:
                test_line = line + word + " "
                test_width = self.font.size(test_line)[0]
                if test_width < dialog_width - 40:
                    line = test_line
                else:
                    lines.append(line)
                    line = word + " "
            lines.append(line)
            
            # Draw lines
            for i, line in enumerate(lines):
                line_text = self.font.render(line, True, (255, 255, 255))
                screen.blit(line_text, (dialog_rect.left + 20, dialog_rect.top + 50 + i * 25))
        
        # Draw continue prompt
        prompt_text = self.font_small.render("Press ENTER or click to continue...", True, (200, 200, 255))
        prompt_rect = prompt_text.get_rect(bottomright=(
            dialog_rect.right - 20,
            dialog_rect.bottom - 10
        ))
        screen.blit(prompt_text, prompt_rect)
    
    def _is_valid_position(self, position):
        """Check if a position is valid for movement."""
        x, y = position
        
        # Check town boundaries
        if x < 0 or x >= self.town.width or y < 0 or y >= self.town.height:
            return False
        
        # Check building collisions
        for building in self.town.buildings:
            if (x >= building.position[0] and x < building.position[0] + building.size[0] and
                y >= building.position[1] and y < building.position[1] + building.size[1]):
                return False
        
        # Check NPC collisions
        for npc in self.town.npcs:
            if npc.position == (x, y):
                return False
        
        return True
    
    def _check_nearby_entities(self):
        """Check for and highlight nearby buildings and NPCs."""
        prev_nearby_building = self.nearby_building
        prev_nearby_npc = self.nearby_npc
        
        self.nearby_building = None
        self.nearby_npc = None
        
        # Check for nearby buildings
        for building in self.town.buildings:
            building_rect = building.get_rect()
            
            # Calculate distance to building center
            building_center = (
                building_rect.centerx,
                building_rect.centery
            )
            
            dx = building_center[0] - self.player_town_position[0]
            dy = building_center[1] - self.player_town_position[1]
            distance = math.sqrt(dx*dx + dy*dy)
            
            # Check if close enough to interact
            if distance < 100:
                self.nearby_building = building
                break
        
        # Check for nearby NPCs
        for npc in self.town.npcs:
            dx = npc.position[0] - self.player_town_position[0]
            dy = npc.position[1] - self.player_town_position[1]
            distance = math.sqrt(dx*dx + dy*dy)
            
            # Check if close enough to interact
            if distance < 50:
                self.nearby_npc = npc
                
                # Make NPC "react" by turning toward player if this is a new interaction
                if npc != prev_nearby_npc:
                    move_amount = 3
                    total_dist = max(1, abs(dx) + abs(dy))
                    npc_dx = (dx / total_dist) * move_amount
                    npc_dy = (dy / total_dist) * move_amount
                    
                    new_x = npc.position[0] - npc_dx
                    new_y = npc.position[1] - npc_dy
                    
                    new_x = max(0, min(self.town.width, new_x))
                    new_y = max(0, min(self.town.height, new_y))
                    
                    npc.position = (new_x, new_y)
                    logger.debug(f"NPC {npc.name} noticed the player")
                break
        
        if self.nearby_building and self.nearby_building != prev_nearby_building:
            self.event_bus.publish("show_notification", {
                "title": self.nearby_building.name,
                "message": f"Press ENTER to interact with {self.nearby_building.name}",
                "duration": 2.0
            })
        
        if self.nearby_npc and self.nearby_npc != prev_nearby_npc:
            self.event_bus.publish("show_notification", {
                "title": self.nearby_npc.name,
                "message": f"Press ENTER to talk to {self.nearby_npc.name}",
                "duration": 2.0
            })
    
    def _is_adjacent_to(self, pos1, pos2, size):
        """Check if pos1 is adjacent to the rectangle at pos2 with given size."""
        # Check if pos1 is adjacent to any tile in the rectangle
        for dx in range(size[0]):
            for dy in range(size[1]):
                rect_pos = (pos2[0] + dx, pos2[1] + dy)
                
                # Check if positions are adjacent (including diagonals)
                if abs(pos1[0] - rect_pos[0]) <= 1 and abs(pos1[1] - rect_pos[1]) <= 1:
                    return True
        
        return False
    
    def _interact(self):
        """Interact with nearest building or NPC."""
        # Check for buildings
        if self.nearby_building:
            # Handle building interaction
            self.event_bus.publish("building_interaction", {
                "building": self.nearby_building,
                "player_position": self.player_town_position
            })
            return
        
        # Check for NPCs
        if self.nearby_npc:
            # Handle NPC interaction
            self.event_bus.publish("npc_interaction", {
                "npc": self.nearby_npc,
                "player_position": self.player_town_position
            })
            return
        
        # Check for exit (if at the bottom edge of town)
        if self.player_town_position[1] >= self.town.height - 1:
            self._exit_town()
    
    def _handle_building_interaction(self, data):
        """Handle interaction with a building."""
        building = data.get("building")
        if not building:
            return
        
        # Show building info
        self.event_bus.publish("show_notification", {
            "title": building.name,
            "message": building.description,
            "duration": 2.0
        })
        
        # Handle special buildings
        if building.type == "shop":
            # Open shop interface
            self.push_state("shop", {
                "shop_id": building.shop_id if hasattr(building, "shop_id") else None,
                "shop_name": building.name
            })
        elif building.type == "inn":
            # Open inn interface (or just rest for now)
            self._rest_at_inn(building)
        elif building.type == "tavern":
            # Open tavern interface (or just show dialog for now)
            self._visit_tavern(building)
        
        # Handle special buildings
        if building.type == "shop":
            # Open shop interface
            self.push_state("shop", {
                "shop_id": building.shop_id if hasattr(building, "shop_id") else None,
                "shop_name": building.name
            })
        elif building.type == "inn":
            # Open inn interface
            self.push_state("inn", {
                "inn_name": building.name,
                "room_price": building.room_price if hasattr(building, "room_price") else 10
            })
        elif building.type == "tavern":
            # Open tavern interface
            self.push_state("tavern", {
                "tavern_name": building.name
            })
        elif building.type == "guild":
            # Open guild interface
            self.push_state("guild", {
                "guild_type": building.guild_type if hasattr(building, "guild_type") else "adventurer",
                "guild_name": building.name
            })
    
    def _handle_npc_interaction(self, data):
        """Handle interaction with an NPC."""
        npc = data.get("npc")
        if not npc:
            return
        
        # Show dialog
        self.show_dialog = True
        self.dialog_index = 0
        
        # Get dialog lines
        if hasattr(npc, 'dialog') and npc.dialog:
            self.current_dialog = npc.dialog
        else:
            self.current_dialog = [f"Hello, I'm {npc.name}!"]
    
    def _check_for_town_events(self):
        """Check for random events in town."""
        # Small chance of random combat in bad parts of town
        if hasattr(self.town, "danger_level") and self.town.danger_level > 0:
            danger_chance = self.town.danger_level * 0.01  # 1% per danger level
            
            if random.random() < danger_chance:
                # Create appropriate enemies based on town
                if hasattr(self.town, "enemy_types") and self.town.enemy_types:
                    enemy_type = random.choice(self.town.enemy_types)
                else:
                    enemy_type = "bandit"  # Default enemy type
                    
                # Get player character
                player_character = self.state_manager.get_persistent_data("player_character")
                player_level = 1
                if player_character and hasattr(player_character, "level"):
                    player_level = player_character.level
                
                # Show notification before combat
                self.event_bus.publish("show_notification", {
                    "title": "Danger!",
                    "message": f"You've been ambushed by a {enemy_type} in {self.town_name}!",
                    "duration": 2.0
                })
                
                # Start combat
                self.change_state("combat", {
                    "enemies": [{"type": enemy_type, "level": max(1, player_level)}],
                    "location": {"type": "town", "name": self.town_name},
                    "combat_type": "random"
                })
    
    def _load_town(self, town_id):
        """Load town data from cache or generate new town."""
        # Check if town exists in cache
        town_data = self.state_manager.get_persistent_data(f"town_{town_id}")
        if town_data:
            return Town.from_dict(town_data)
        
        # Generate new town
        town = self._generate_town(town_id)
        
        # Cache town
        self.state_manager.set_persistent_data(f"town_{town_id}", town.to_dict())
        
        return town
    
    def _generate_town(self, town_id):
        """Generate a procedural town."""
        # Get town info from world
        town_info = None
        world_data = self.state_manager.get_persistent_data("world")
        
        if world_data and "locations" in world_data:
            for location in world_data["locations"]:
                if isinstance(location, Location) and location.location_type == LocationType.TOWN:
                    if town_id == f"town_{location.name.lower().replace(' ', '_')}":
                        town_info = {
                            'name': location.name,
                            'difficulty': location.difficulty
                        }
                        break
        
        # Make towns larger with the multiplier
        town_size_map = {
            'small': (20 * self.town_size_multiplier, 20 * self.town_size_multiplier),
            'medium': (30 * self.town_size_multiplier, 30 * self.town_size_multiplier),
            'large': (40 * self.town_size_multiplier, 40 * self.town_size_multiplier)
        }
        
        # Determine size based on difficulty
        if town_info and 'difficulty' in town_info:
            if town_info['difficulty'] <= 3:
                size = 'small'
            elif town_info['difficulty'] <= 7:
                size = 'medium'
            else:
                size = 'large'
        else:
            size = 'medium'
            
        width, height = town_size_map.get(size, (20, 20))
        
        # Create town
        town = Town(
            id=town_id,
            name=town_info['name'] if town_info else f"Town {town_id}",
            width=width,
            height=height
        )
        
        # Set danger level based on difficulty
        if town_info and 'difficulty' in town_info:
            town.danger_level = max(0, min(5, town_info['difficulty'] // 2))
        
        # Add buildings based on size
        if size == 'small':
            num_buildings = random.randint(5, 8)
            num_npcs = random.randint(3, 6)
        elif size == 'medium':
            num_buildings = random.randint(8, 12)
            num_npcs = random.randint(6, 10)
        else:  # large
            num_buildings = random.randint(12, 18)
            num_npcs = random.randint(10, 15)
            
        # Set enemy types based on location
        if town_info and 'difficulty' in town_info:
            if town_info['difficulty'] <= 3:
                town.enemy_types = ["thief", "drunk", "troublemaker"]
            elif town_info['difficulty'] <= 7:
                town.enemy_types = ["bandit", "thug", "mercenary"]
            else:
                town.enemy_types = ["assassin", "cultist", "criminal"]
        
        # Always include essential buildings
        essential_buildings = [
            {"name": "General Store", "type": "shop", "size": (2, 2)},
            {"name": "Inn", "type": "inn", "size": (3, 2)},
            {"name": "Tavern", "type": "tavern", "size": (2, 2)}
        ]
        
        # Add random extra buildings based on town type
        building_types = ["house", "storehouse", "smithy", "temple", "market", "guild"]
        
        # Place buildings
        placed_buildings = []
        
        # First place essential buildings
        for building_info in essential_buildings:
            self._place_building(town, building_info, placed_buildings)
        
        # Then add random buildings up to the total count
        while len(placed_buildings) < num_buildings:
            building_type = random.choice(building_types)
            building_info = {
                "name": f"{building_type.capitalize()}",
                "type": building_type,
                "size": (random.randint(1, 2), random.randint(1, 2))
            }
            self._place_building(town, building_info, placed_buildings)
        
        # Add NPCs
        for _ in range(num_npcs):
            # Find a valid position
            valid_position = False
            pos = (0, 0)
            
            while not valid_position:
                pos = (random.randint(1, town.width-2), random.randint(1, town.height-2))
                valid_position = True
                
                # Check if position collides with a building
                for building in town.buildings:
                    if (pos[0] >= building.position[0] and 
                        pos[0] < building.position[0] + building.size[0] and
                        pos[1] >= building.position[1] and 
                        pos[1] < building.position[1] + building.size[1]):
                        valid_position = False
                        break
                
                # Check if position collides with another NPC
                for npc in town.npcs:
                    if npc.position == pos:
                        valid_position = False
                        break
            
            # Generate NPC
            npc_type = random.choice(["villager", "merchant", "guard", "traveler"])
            npc_name = f"{npc_type.capitalize()} {random.randint(1, 100)}"
            
            town.add_npc(Npc(
                name=npc_name,
                npc_type=npc_type,
                position=pos
            ))
        
        return town
    
    def _place_building(self, town, building_info, placed_buildings):
        """Try to place a building in the town."""
        max_attempts = 50
        attempts = 0
        
        name = building_info["name"]
        building_type = building_info["type"]
        size = building_info["size"]
        
        while attempts < max_attempts:
            # Generate random position
            x = random.randint(1, town.width - size[0] - 1)
            y = random.randint(1, town.height - size[1] - 1)
            
            # Check for collisions with existing buildings
            collision = False
            for building in placed_buildings:
                if (x + size[0] > building["x"] and x < building["x"] + building["size"][0] and
                    y + size[1] > building["y"] and y < building["y"] + building["size"][1]):
                    collision = True
                    break
            
            if not collision:
                # Place building
                town.add_building(TownBuilding(
                    name=name,
                    building_type=building_type,
                    position=(x, y),
                    size=size
                ))
                
                placed_buildings.append({
                    "x": x,
                    "y": y,
                    "size": size
                })
                
                return True
            
            attempts += 1
        
        return False
    def _rest_at_inn(self, building):
        """Rest at an inn to recover health."""
        # Get player character
        character = self.state_manager.get_persistent_data("player_character")
        
        if character and hasattr(character, "health") and hasattr(character, "max_health"):
            # Deduct gold (if we have an economy system)
            room_price = getattr(building, "room_price", 10)
            if hasattr(character, "gold") and character.gold >= room_price:
                character.gold -= room_price
                
                # Heal to full
                old_health = character.health
                character.health = character.max_health
                
                # Update dialog
                self.event_bus.publish("show_notification", {
                    "title": f"{building.name}",
                    "message": f"You rest at the inn and recover {character.health - old_health} health.",
                    "duration": 3.0
                })
                
                # Update character
                self.state_manager.set_persistent_data("player_character", character)
            else:
                self.event_bus.publish("show_notification", {
                    "title": f"{building.name}",
                    "message": f"You don't have enough gold to rest here. (Costs {room_price} gold)",
                    "duration": 3.0
                })
        else:
            self.event_bus.publish("show_notification", {
                "title": f"{building.name}",
                "message": "You rest for a while and feel refreshed.",
                "duration": 3.0
            })
    
    def _visit_tavern(self, building):
        """Visit a tavern for information and drinks."""
        # Show tavern dialog
        self.event_bus.publish("show_notification", {
            "title": f"{building.name}",
            "message": "The tavern is bustling with activity. You hear rumors about nearby adventures.",
            "duration": 3.0
        })
        
        # TODO: Add proper tavern interface with rumors, drinks, etc.
    def _load_assets(self):
        """Load pixel art assets (placeholders)."""
        try:
            # For now, we'll create placeholder surfaces with colors
            # In a real implementation, you would load actual pixel art images
            
            # Create tile assets
            tile_size = self.tile_size
            self.tile_assets = {
                'grass': self._create_grass_tile(tile_size),
                'path': self._create_path_tile(tile_size),
                'dirt': self._create_dirt_tile(tile_size),
                'flower': self._create_flower_tile(tile_size)
            }
            
            # Create building assets
            for b_type in ["shop", "inn", "tavern", "house", "guild", "temple"]:
                self.building_assets[b_type] = self._create_building_asset(b_type, tile_size)
            
            # Create NPC assets
            for npc_type in ["merchant", "guard", "villager", "traveler"]:
                self.npc_assets[npc_type] = self._create_npc_asset(npc_type, tile_size)
            
            # Create player asset
            self.player_asset = self._create_player_asset(tile_size)
            
        except Exception as e:
            logger.error(f"Error loading assets: {e}")
    
    def _create_grass_tile(self, size):
        """Create a grass tile with pixel art style."""
        surface = pygame.Surface((size, size))
        base_color = (60, 120, 60)
        
        # Fill with base color
        surface.fill(base_color)
        
        # Add pixel details
        pixels = []
        for _ in range(10):
            x = random.randint(0, size-3)
            y = random.randint(0, size-3)
            color_var = random.randint(-10, 10)
            color = (base_color[0] + color_var, base_color[1] + color_var, base_color[2] + color_var)
            pixels.append((x, y, 2, 2, color))
        
        for px, py, w, h, color in pixels:
            pygame.draw.rect(surface, color, (px, py, w, h))
        
        return surface

    def _create_path_tile(self, size):
        """Create a path tile with pixel art style."""
        surface = pygame.Surface((size, size))
        base_color = (150, 140, 100)
        
        # Fill with base color
        surface.fill(base_color)
        
        # Add pixel details
        for _ in range(15):
            x = random.randint(0, size-2)
            y = random.randint(0, size-2)
            color_var = random.randint(-20, 20)
            color = (base_color[0] + color_var, base_color[1] + color_var, base_color[2] + color_var)
            pygame.draw.rect(surface, color, (x, y, 2, 2))
        
        return surface

    def _create_dirt_tile(self, size):
        """Create a dirt tile with pixel art style."""
        surface = pygame.Surface((size, size))
        base_color = (120, 100, 80)
        
        # Fill with base color
        surface.fill(base_color)
        
        # Add pixel details
        for _ in range(12):
            x = random.randint(0, size-2)
            y = random.randint(0, size-2)
            color_var = random.randint(-15, 15)
            color = (base_color[0] + color_var, base_color[1] + color_var, base_color[2] + color_var)
            pygame.draw.rect(surface, color, (x, y, 2, 2))
        
        return surface

    def _create_flower_tile(self, size):
        """Create a grass tile with flowers."""
        surface = self._create_grass_tile(size)
        
        # Add flowers
        for _ in range(3):
            x = random.randint(4, size-8)
            y = random.randint(4, size-8)
            color = random.choice([(255, 200, 200), (200, 200, 255), (255, 255, 200)])
            pygame.draw.rect(surface, color, (x, y, 4, 4))
            pygame.draw.rect(surface, (255, 255, 100), (x+1, y+1, 2, 2))
        
        return surface

    def _create_building_asset(self, b_type, tile_size):
        """Create a building asset with pixel art style."""
        # Different sizes based on building type
        if b_type == "shop":
            w, h = 2, 2
            color = (200, 100, 100)
        elif b_type == "inn":
            w, h = 3, 2
            color = (100, 100, 200)
        elif b_type == "tavern":
            w, h = 2, 2
            color = (200, 150, 50)
        elif b_type == "house":
            w, h = 1, 1
            color = (150, 150, 150)
        elif b_type == "guild":
            w, h = 2, 2
            color = (150, 100, 200)
        elif b_type == "temple":
            w, h = 2, 2
            color = (200, 200, 250)
        else:
            w, h = 1, 1
            color = (120, 120, 120)
        
        # Create surface
        surface = pygame.Surface((w * tile_size, h * tile_size))
        surface.fill(color)
        
        # Add roof
        roof_color = (min(color[0] + 50, 255), min(color[1] + 30, 255), min(color[2] + 20, 255))
        roof_height = h * tile_size // 3
        pygame.draw.rect(surface, roof_color, (0, 0, w * tile_size, roof_height))
        
        # Add door
        door_color = (80, 50, 20)
        door_width = tile_size // 3
        door_height = tile_size // 2
        door_x = (w * tile_size - door_width) // 2
        door_y = h * tile_size - door_height
        pygame.draw.rect(surface, door_color, (door_x, door_y, door_width, door_height))
        
        # Add window
        window_color = (200, 200, 255)
        window_size = tile_size // 4
        window_x = (w * tile_size) // 4
        window_y = (h * tile_size) // 2
        pygame.draw.rect(surface, window_color, (window_x, window_y, window_size, window_size))
        pygame.draw.rect(surface, window_color, (w * tile_size - window_x - window_size, window_y, window_size, window_size))
        
        # Add pixel details
        for _ in range(w * h * 10):
            x = random.randint(0, w * tile_size - 3)
            y = random.randint(0, h * tile_size - 3)
            color_var = random.randint(-30, 30)
            pixel_color = (
                max(0, min(255, surface.get_at((x, y))[0] + color_var)),
                max(0, min(255, surface.get_at((x, y))[1] + color_var)),
                max(0, min(255, surface.get_at((x, y))[2] + color_var))
            )
            pygame.draw.rect(surface, pixel_color, (x, y, 2, 2))
        
        # Add outline
        pygame.draw.rect(surface, (0, 0, 0), (0, 0, w * tile_size, h * tile_size), 1)
        
        return surface

    def _create_npc_asset(self, npc_type, tile_size):
        """Create an NPC asset with pixel art style."""
        # Create surface
        surface = pygame.Surface((tile_size, tile_size), pygame.SRCALPHA)
        
        # Different colors based on NPC type
        if npc_type == "merchant":
            body_color = (200, 150, 50)
            head_color = (240, 200, 160)
            detail_color = (150, 50, 50)
        elif npc_type == "guard":
            body_color = (100, 100, 150)
            head_color = (240, 200, 160)
            detail_color = (50, 50, 100)
        elif npc_type == "villager":
            body_color = (100, 150, 100)
            head_color = (240, 200, 160)
            detail_color = (50, 100, 50)
        else:  # traveler
            body_color = (150, 100, 150)
            head_color = (240, 200, 160)
            detail_color = (100, 50, 100)
        
        # Draw body
        body_width = tile_size // 2
        body_height = tile_size // 2
        body_x = (tile_size - body_width) // 2
        body_y = tile_size - body_height - 2
        pygame.draw.rect(surface, body_color, (body_x, body_y, body_width, body_height))
        
        # Draw head
        head_size = tile_size // 3
        head_x = (tile_size - head_size) // 2
        head_y = body_y - head_size
        pygame.draw.rect(surface, head_color, (head_x, head_y, head_size, head_size))
        
        # Draw details
        detail_size = max(2, tile_size // 8)
        pygame.draw.rect(surface, detail_color, (body_x, body_y, body_width, detail_size))  # Belt/collar
        
        # Draw eyes
        eye_size = max(1, tile_size // 10)
        eye_y = head_y + head_size // 3
        pygame.draw.rect(surface, (0, 0, 0), (head_x + head_size // 4 - eye_size // 2, eye_y, eye_size, eye_size))
        pygame.draw.rect(surface, (0, 0, 0), (head_x + head_size * 3 // 4 - eye_size // 2, eye_y, eye_size, eye_size))
        
        return surface

    def _create_player_asset(self, tile_size, race=None):
        """Create a player asset with customizable colors based on race."""
        # Create surface
        surface = pygame.Surface((tile_size, tile_size), pygame.SRCALPHA)
        
        # Default colors
        body_color = (0, 100, 200)       # Default blue
        head_color = (240, 200, 160)       # Default skin tone
        detail_color = (200, 200, 0)       # Default yellow
        
        # Customize based on race if provided
        if race:
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
        
        # Override with persistent appearance if available
        character = self.state_manager.get_persistent_data("player_character")
        if character and hasattr(character, "appearance"):
            if hasattr(character.appearance, "body_color"):
                body_color = character.appearance.body_color
            if hasattr(character.appearance, "skin_color"):
                head_color = character.appearance.skin_color
            if hasattr(character.appearance, "detail_color"):
                detail_color = character.appearance.detail_color
        
        # Draw body
        body_width = tile_size // 2
        body_height = tile_size // 2
        body_x = (tile_size - body_width) // 2
        body_y = tile_size - body_height - 2
        pygame.draw.rect(surface, body_color, (body_x, body_y, body_width, body_height))
        
        # Draw head
        head_size = tile_size // 3
        head_x = (tile_size - head_size) // 2
        head_y = body_y - head_size
        pygame.draw.rect(surface, head_color, (head_x, head_y, head_size, head_size))
        
        # Draw details (belt/collar)
        detail_size = max(2, tile_size // 8)
        pygame.draw.rect(surface, detail_color, (body_x, body_y, body_width, detail_size))
        
        # Draw eyes
        eye_size = max(1, tile_size // 10)
        eye_y = head_y + head_size // 3
        pygame.draw.rect(surface, (0, 0, 0), (head_x + head_size // 4 - eye_size // 2, eye_y, eye_size, eye_size))
        pygame.draw.rect(surface, (0, 0, 0), (head_x + head_size * 3 // 4 - eye_size // 2, eye_y, eye_size, eye_size))
        
        return surface
        
    def _exit_town(self):
        """Exit town and return to world map."""
        logger.info(f"Exiting town {self.town_name}")
        
        # Return to world exploration
        self.change_state("world_exploration", {
            "return_position": self.return_position
        })
