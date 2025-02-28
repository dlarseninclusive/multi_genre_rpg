import pygame
import logging
import random
import math
from enum import Enum
from game_state import GameState
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
            self.player_pos = player_pos
        else:
            # Default to center of town
            self.player_pos = (self.town.size[0] // 2, self.town.size[1] // 2)
        
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
    
    def _screen_to_world(self, screen_pos):
        """
        Convert screen coordinates to world coordinates.
        
        Args:
            screen_pos: (x, y) screen position
            
        Returns:
            (x, y) world position
        """
        return (screen_pos[0] + self.camera_x, screen_pos[1] + self.camera_y)
    
    def _world_to_screen(self, world_pos):
        """
        Convert world coordinates to screen coordinates.
        
        Args:
            world_pos: (x, y) world position
            
        Returns:
            (x, y) screen position
        """
        return (world_pos[0] - self.camera_x, world_pos[1] - self.camera_y)
    
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
            
            dx = building_center[0] - self.player_pos[0]
            dy = building_center[1] - self.player_pos[1]
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
            dx = npc.position[0] - self.player_pos[0]
            dy = npc.position[1] - self.player_pos[1]
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
        """
        Render the player character.
        
        Args:
            screen: Pygame surface to render to
        """
        # Convert world position to screen position
        screen_x, screen_y = self._world_to_screen(self.player_pos)
        
        # Draw player
        pygame.draw.circle(screen, self.colors['player'], (int(screen_x), int(screen_y)), 15)
        pygame.draw.circle(screen, (0, 0, 0), (int(screen_x), int(screen_y)), 15, 2)
