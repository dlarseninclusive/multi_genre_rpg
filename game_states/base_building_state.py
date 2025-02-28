import pygame
import logging
import random
import math
from enum import Enum
from game_state import GameState

logger = logging.getLogger("base_building")

class ResourceType(Enum):
    """Types of resources for base building."""
    WOOD = 0
    STONE = 1
    FOOD = 2
    GOLD = 3
    IRON = 4
    CRYSTAL = 5

class BuildingType(Enum):
    """Types of buildings that can be constructed."""
    HOUSE = 0          # Increases population capacity
    FARM = 1           # Produces food
    LUMBERMILL = 2     # Produces wood
    MINE = 3           # Produces stone and iron
    BARRACKS = 4       # Trains defenders
    WALL = 5           # Increases defense
    TOWER = 6          # Provides ranged defense
    STORAGE = 7        # Increases resource storage capacity
    WORKSHOP = 8       # Enables crafting
    MARKET = 9         # Enables trading
    TEMPLE = 10        # Provides bonuses and special abilities

class NpcRole(Enum):
    """Roles that NPCs can fulfill."""
    WORKER = 0         # Gathers resources
    DEFENDER = 1       # Protects base from attacks
    TRADER = 2         # Buys/sells resources
    CRAFTER = 3        # Crafts items
    FARMER = 4         # Works on farms
    MINER = 5          # Works in mines
    LUMBERJACK = 6     # Works at lumbermills
    BUILDER = 7        # Speeds up construction

class Resource:
    """A resource used in base building."""
    
    def __init__(self, resource_type, amount=0, max_amount=100):
        """
        Initialize a resource.
        
        Args:
            resource_type: Type from ResourceType enum
            amount: Current amount
            max_amount: Maximum storage capacity
        """
        self.resource_type = resource_type
        self.amount = amount
        self.max_amount = max_amount
        self.production_rate = 0  # Per game hour
        self.consumption_rate = 0  # Per game hour
    
    def add(self, amount):
        """
        Add to resource amount.
        
        Args:
            amount: Amount to add
            
        Returns:
            Amount actually added (may be limited by max_amount)
        """
        before = self.amount
        self.amount = min(self.max_amount, self.amount + amount)
        return self.amount - before
    
    def remove(self, amount):
        """
        Remove from resource amount.
        
        Args:
            amount: Amount to remove
            
        Returns:
            Amount actually removed (may be limited by available amount)
        """
        before = self.amount
        self.amount = max(0, self.amount - amount)
        return before - self.amount
    
    def update(self, hours):
        """
        Update resource based on production and consumption rates.
        
        Args:
            hours: Game hours elapsed
        """
        # Calculate net production
        net_production = (self.production_rate - self.consumption_rate) * hours
        
        if net_production > 0:
            self.add(net_production)
        elif net_production < 0:
            self.remove(abs(net_production))
    
    def to_dict(self):
        """Convert to dictionary for serialization."""
        return {
            'resource_type': self.resource_type.value,
            'amount': self.amount,
            'max_amount': self.max_amount,
            'production_rate': self.production_rate,
            'consumption_rate': self.consumption_rate
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create from dictionary."""
        resource = cls(
            ResourceType(data['resource_type']),
            data['amount'],
            data['max_amount']
        )
        resource.production_rate = data['production_rate']
        resource.consumption_rate = data['consumption_rate']
        return resource

class Building:
    """A building in the base."""
    
    def __init__(self, building_type, x, y, level=1, health=100):
        """
        Initialize a building.
        
        Args:
            building_type: Type from BuildingType enum
            x: Grid X position
            y: Grid Y position
            level: Building level (1+)
            health: Building health points
        """
        self.building_type = building_type
        self.x = x
        self.y = y
        self.level = level
        self.max_health = 100 * level
        self.health = health if health is not None else self.max_health
        self.construction_progress = 1.0  # 0.0 to 1.0 (1.0 = complete)
        self.assigned_workers = 0
        self.size = self._get_size()
        self.production = {}  # Resource production rates
        self.consumption = {}  # Resource consumption rates
        self.special_abilities = []  # Special abilities granted
        
        # Set production/consumption based on building type and level
        self._update_production_rates()
    
    def _get_size(self):
        """
        Get the size of the building in grid cells.
        
        Returns:
            (width, height) tuple
        """
        if self.building_type == BuildingType.HOUSE:
            return (2, 2)
        elif self.building_type == BuildingType.FARM:
            return (3, 3)
        elif self.building_type == BuildingType.LUMBERMILL:
            return (3, 2)
        elif self.building_type == BuildingType.MINE:
            return (2, 3)
        elif self.building_type == BuildingType.BARRACKS:
            return (3, 3)
        elif self.building_type == BuildingType.WALL:
            return (1, 1)
        elif self.building_type == BuildingType.TOWER:
            return (2, 2)
        elif self.building_type == BuildingType.STORAGE:
            return (3, 3)
        elif self.building_type == BuildingType.WORKSHOP:
            return (3, 2)
        elif self.building_type == BuildingType.MARKET:
            return (3, 3)
        elif self.building_type == BuildingType.TEMPLE:
            return (3, 3)
        
        # Default
        return (2, 2)
    
    def _update_production_rates(self):
        """Update production and consumption rates based on type and level."""
        # Reset rates
        self.production = {}
        self.consumption = {}
        
        # Calculate base multiplier from level
        level_multiplier = math.sqrt(self.level)
        
        # Set rates based on building type
        if self.building_type == BuildingType.HOUSE:
            # Houses don't produce resources but affect population cap
            pass
            
        elif self.building_type == BuildingType.FARM:
            # Farms produce food
            base_rate = 5.0 * level_multiplier * (1.0 + self.assigned_workers * 0.5)
            self.production[ResourceType.FOOD] = base_rate
            
        elif self.building_type == BuildingType.LUMBERMILL:
            # Lumbermills produce wood
            base_rate = 3.0 * level_multiplier * (1.0 + self.assigned_workers * 0.5)
            self.production[ResourceType.WOOD] = base_rate
            
        elif self.building_type == BuildingType.MINE:
            # Mines produce stone and iron
            stone_rate = 2.0 * level_multiplier * (1.0 + self.assigned_workers * 0.5)
            iron_rate = 1.0 * level_multiplier * (1.0 + self.assigned_workers * 0.5)
            self.production[ResourceType.STONE] = stone_rate
            self.production[ResourceType.IRON] = iron_rate
            
        elif self.building_type == BuildingType.BARRACKS:
            # Barracks consume food to train defenders
            food_consumption = 1.0 * level_multiplier * self.assigned_workers
            self.consumption[ResourceType.FOOD] = food_consumption
            
        elif self.building_type == BuildingType.WORKSHOP:
            # Workshops consume wood and iron
            wood_consumption = 0.5 * level_multiplier * self.assigned_workers
            iron_consumption = 0.2 * level_multiplier * self.assigned_workers
            self.consumption[ResourceType.WOOD] = wood_consumption
            self.consumption[ResourceType.IRON] = iron_consumption
            
        elif self.building_type == BuildingType.MARKET:
            # Markets produce gold
            gold_rate = 1.0 * level_multiplier * (1.0 + self.assigned_workers * 0.5)
            self.production[ResourceType.GOLD] = gold_rate
    
    def upgrade(self):
        """
        Upgrade the building to the next level.
        
        Returns:
            Boolean indicating if upgrade was successful
        """
        # Increase level
        self.level += 1
        
        # Update health
        old_health_percentage = self.health / self.max_health
        self.max_health = 100 * self.level
        self.health = self.max_health * old_health_percentage
        
        # Update production rates
        self._update_production_rates()
        
        logger.info(f"Upgraded {self.building_type.name} to level {self.level}")
        return True
    
    def repair(self, amount):
        """
        Repair the building.
        
        Args:
            amount: Amount of health to repair
            
        Returns:
            Actual amount repaired
        """
        before = self.health
        self.health = min(self.max_health, self.health + amount)
        return self.health - before
    
    def damage(self, amount):
        """
        Damage the building.
        
        Args:
            amount: Amount of damage to apply
            
        Returns:
            Actual amount of damage applied
        """
        before = self.health
        self.health = max(0, self.health - amount)
        return before - self.health
    
    def assign_worker(self):
        """
        Assign a worker to the building.
        
        Returns:
            Boolean indicating success
        """
        # Buildings have different worker capacities based on type and level
        max_workers = self._get_max_workers()
        
        if self.assigned_workers < max_workers:
            self.assigned_workers += 1
            self._update_production_rates()
            return True
        
        return False
    
    def remove_worker(self):
        """
        Remove a worker from the building.
        
        Returns:
            Boolean indicating success
        """
        if self.assigned_workers > 0:
            self.assigned_workers -= 1
            self._update_production_rates()
            return True
        
        return False
    
    def _get_max_workers(self):
        """
        Get the maximum number of workers for this building.
        
        Returns:
            Maximum worker capacity
        """
        if self.building_type == BuildingType.HOUSE:
            return 0  # Houses don't have workers
        elif self.building_type == BuildingType.FARM:
            return 4 * self.level
        elif self.building_type == BuildingType.LUMBERMILL:
            return 3 * self.level
        elif self.building_type == BuildingType.MINE:
            return 5 * self.level
        elif self.building_type == BuildingType.BARRACKS:
            return 6 * self.level
        elif self.building_type == BuildingType.WALL:
            return 0  # Walls don't have workers
        elif self.building_type == BuildingType.TOWER:
            return 2 * self.level
        elif self.building_type == BuildingType.STORAGE:
            return 2 * self.level
        elif self.building_type == BuildingType.WORKSHOP:
            return 4 * self.level
        elif self.building_type == BuildingType.MARKET:
            return 3 * self.level
        elif self.building_type == BuildingType.TEMPLE:
            return 2 * self.level
        
        # Default
        return 2 * self.level
    
    def get_grid_cells(self):
        """
        Get all grid cells occupied by this building.
        
        Returns:
            List of (x, y) tuples for each cell occupied
        """
        width, height = self.size
        cells = []
        
        for dy in range(height):
            for dx in range(width):
                cells.append((self.x + dx, self.y + dy))
        
        return cells
    
    def to_dict(self):
        """Convert to dictionary for serialization."""
        return {
            'building_type': self.building_type.value,
            'x': self.x,
            'y': self.y,
            'level': self.level,
            'health': self.health,
            'max_health': self.max_health,
            'construction_progress': self.construction_progress,
            'assigned_workers': self.assigned_workers,
            'size': self.size,
            'production': {k.value: v for k, v in self.production.items()},
            'consumption': {k.value: v for k, v in self.consumption.items()},
            'special_abilities': self.special_abilities
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create from dictionary."""
        building = cls(
            BuildingType(data['building_type']),
            data['x'],
            data['y'],
            data['level'],
            data['health']
        )
        building.max_health = data['max_health']
        building.construction_progress = data['construction_progress']
        building.assigned_workers = data['assigned_workers']
        building.size = data['size']
        
        # Restore production/consumption
        building.production = {ResourceType(int(k)): v for k, v in data['production'].items()}
        building.consumption = {ResourceType(int(k)): v for k, v in data['consumption'].items()}
        
        building.special_abilities = data['special_abilities']
        
        return building

class Npc:
    """An NPC in the base."""
    
    def __init__(self, name, role, efficiency=1.0):
        """
        Initialize an NPC.
        
        Args:
            name: NPC name
            role: Role from NpcRole enum
            efficiency: Work efficiency multiplier (0.5-2.0)
        """
        self.name = name
        self.role = role
        self.efficiency = efficiency
        self.assigned_building = None
        self.health = 100
        self.max_health = 100
        self.happiness = 100  # 0-100
        self.experience = 0
        self.level = 1
    
    def assign_to_building(self, building):
        """
        Assign NPC to a building.
        
        Args:
            building: Building to assign to
            
        Returns:
            Boolean indicating success
        """
        # Check if building can take another worker
        if building and building.assign_worker():
            self.assigned_building = building
            return True
        
        return False
    
    def unassign(self):
        """
        Unassign NPC from current building.
        
        Returns:
            Boolean indicating success
        """
        if self.assigned_building:
            if self.assigned_building.remove_worker():
                old_building = self.assigned_building
                self.assigned_building = None
                return True
        
        return False
    
    def gain_experience(self, amount):
        """
        Add experience and handle level ups.
        
        Args:
            amount: Amount of experience to add
            
        Returns:
            Boolean indicating if level up occurred
        """
        self.experience += amount
        
        # Check for level up (simple formula: 100 * level^2)
        next_level_exp = 100 * (self.level ** 2)
        
        if self.experience >= next_level_exp:
            self.level += 1
            
            # Increase efficiency with level
            self.efficiency += 0.1
            
            return True
        
        return False
    
    def update_happiness(self, food_availability):
        """
        Update happiness based on conditions.
        
        Args:
            food_availability: Food availability ratio (0.0-1.0)
        """
        # Happiness factors
        # Food is a major factor
        if food_availability >= 0.9:
            self.happiness = min(100, self.happiness + 5)
        elif food_availability >= 0.7:
            self.happiness = min(100, self.happiness + 1)
        elif food_availability >= 0.5:
            self.happiness = max(0, self.happiness - 1)
        elif food_availability >= 0.3:
            self.happiness = max(0, self.happiness - 5)
        else:
            self.happiness = max(0, self.happiness - 10)
    
    def to_dict(self):
        """Convert to dictionary for serialization."""
        return {
            'name': self.name,
            'role': self.role.value,
            'efficiency': self.efficiency,
            'assigned_building': None if self.assigned_building is None else {
                'building_type': self.assigned_building.building_type.value,
                'x': self.assigned_building.x,
                'y': self.assigned_building.y
            },
            'health': self.health,
            'max_health': self.max_health,
            'happiness': self.happiness,
            'experience': self.experience,
            'level': self.level
        }
    
    @classmethod
    def from_dict(cls, data, buildings=None):
        """Create from dictionary."""
        npc = cls(
            data['name'],
            NpcRole(data['role']),
            data['efficiency']
        )
        npc.health = data['health']
        npc.max_health = data['max_health']
        npc.happiness = data['happiness']
        npc.experience = data['experience']
        npc.level = data['level']
        
        # Restore assigned building if possible
        if data['assigned_building'] and buildings:
            building_data = data['assigned_building']
            for building in buildings:
                if (building.building_type.value == building_data['building_type'] and
                    building.x == building_data['x'] and building.y == building_data['y']):
                    npc.assigned_building = building
                    break
        
        return npc

class Base:
    """Player's base with buildings, NPCs, and resources."""
    
    def __init__(self, width=20, height=20, name="Base"):
        """
        Initialize a base.
        
        Args:
            width: Base width in grid cells
            height: Base height in grid cells
            name: Base name
        """
        self.width = width
        self.height = height
        self.name = name
        self.buildings = []
        self.npcs = []
        self.resources = {
            ResourceType.WOOD: Resource(ResourceType.WOOD, 50),
            ResourceType.STONE: Resource(ResourceType.STONE, 50),
            ResourceType.FOOD: Resource(ResourceType.FOOD, 100),
            ResourceType.GOLD: Resource(ResourceType.GOLD, 20),
            ResourceType.IRON: Resource(ResourceType.IRON, 10),
            ResourceType.CRYSTAL: Resource(ResourceType.CRYSTAL, 0)
        }
        self.grid = [[None for _ in range(width)] for _ in range(height)]
        self.attack_strength = 0  # Current attack strength
        self.defense_strength = 0  # Current defense strength
        self.population = 0
        self.max_population = 10  # Starting max population
        self.happiness = 100  # Overall base happiness
        self.attack_cooldown = 0  # Time until next attack
        self.prosperity = 0  # Overall base prosperity level
        self.discovered_techs = []  # Techs that have been researched
    
    def add_building(self, building_type, x, y):
        """
        Add a building to the base.
        
        Args:
            building_type: Type from BuildingType enum
            x: Grid X position
            y: Grid Y position
            
        Returns:
            Newly created Building instance or None if failed
        """
        # Check if position is valid
        if not self.is_position_valid(building_type, x, y):
            logger.warning(f"Cannot place {building_type.name} at ({x}, {y}): position invalid")
            return None
        
        # Check resource requirements
        requirements = self.get_building_requirements(building_type)
        
        for resource_type, amount in requirements.items():
            if self.resources[resource_type].amount < amount:
                logger.warning(f"Cannot afford {building_type.name}: need {amount} {resource_type.name}")
                return None
        
        # Deduct resources
        for resource_type, amount in requirements.items():
            self.resources[resource_type].remove(amount)
        
        # Create building
        building = Building(building_type, x, y)
        
        # New buildings start at 0% progress
        building.construction_progress = 0.0
        
        # Add to buildings list
        self.buildings.append(building)
        
        # Update grid occupancy
        self._update_grid_occupancy(building)
        
        # Update base stats
        self._update_base_stats()
        
        logger.info(f"Added {building_type.name} at ({x}, {y})")
        return building
    
    def remove_building(self, building):
        """
        Remove a building from the base.
        
        Args:
            building: Building instance to remove
            
        Returns:
            Boolean indicating success
        """
        if building not in self.buildings:
            return False
        
        # Remove from buildings list
        self.buildings.remove(building)
        
        # Clear grid occupancy
        for x, y in building.get_grid_cells():
            if 0 <= x < self.width and 0 <= y < self.height:
                self.grid[y][x] = None
        
        # Update base stats
        self._update_base_stats()
        
        logger.info(f"Removed {building.building_type.name} at ({building.x}, {building.y})")
        return True
    
    def upgrade_building(self, building):
        """
        Upgrade a building.
        
        Args:
            building: Building instance to upgrade
            
        Returns:
            Boolean indicating success
        """
        if building not in self.buildings:
            return False
        
        # Check resource requirements
        requirements = self.get_upgrade_requirements(building)
        
        for resource_type, amount in requirements.items():
            if self.resources[resource_type].amount < amount:
                logger.warning(f"Cannot afford upgrade: need {amount} {resource_type.name}")
                return False
        
        # Deduct resources
        for resource_type, amount in requirements.items():
            self.resources[resource_type].remove(amount)
        
        # Upgrade building
        building.upgrade()
        
        # Update base stats
        self._update_base_stats()
        
        logger.info(f"Upgraded {building.building_type.name} to level {building.level}")
        return True
    
    def add_npc(self, name, role):
        """
        Add an NPC to the base.
        
        Args:
            name: NPC name
            role: Role from NpcRole enum
            
        Returns:
            Newly created NPC instance or None if failed
        """
        # Check if population cap is reached
        if self.population >= self.max_population:
            logger.warning(f"Cannot add NPC: population cap reached")
            return None
        
        # Create NPC
        npc = Npc(name, role)
        
        # Add to NPCs list
        self.npcs.append(npc)
        
        # Update population
        self.population += 1
        
        # Update base stats
        self._update_base_stats()
        
        logger.info(f"Added NPC {name} with role {role.name}")
        return npc
    
    def remove_npc(self, npc):
        """
        Remove an NPC from the base.
        
        Args:
            npc: NPC instance to remove
            
        Returns:
            Boolean indicating success
        """
        if npc not in self.npcs:
            return False
        
        # Unassign from building first
        if npc.assigned_building:
            npc.unassign()
        
        # Remove from NPCs list
        self.npcs.remove(npc)
        
        # Update population
        self.population -= 1
        
        # Update base stats
        self._update_base_stats()
        
        logger.info(f"Removed NPC {npc.name}")
        return True
    
    def assign_npc(self, npc, building):
        """
        Assign an NPC to a building.
        
        Args:
            npc: NPC instance to assign
            building: Building to assign to
            
        Returns:
            Boolean indicating success
        """
        if npc not in self.npcs or building not in self.buildings:
            return False
        
        # Unassign from current building first
        if npc.assigned_building:
            npc.unassign()
        
        # Assign to new building
        if npc.assign_to_building(building):
            logger.info(f"Assigned {npc.name} to {building.building_type.name}")
            return True
        
        return False
    
    def update(self, hours):
        """
        Update base for elapsed time.
        
        Args:
            hours: Game hours elapsed
        """
        # Update building construction
        self._update_construction(hours)
        
        # Update resource production
        self._update_resources(hours)
        
        # Update NPC happiness
        self._update_npcs(hours)
        
        # Update defense values
        self._update_defenses()
        
        # Update attack cooldown
        if self.attack_cooldown > 0:
            self.attack_cooldown = max(0, self.attack_cooldown - hours)
            
            # If cooldown expired, trigger attack
            if self.attack_cooldown == 0 and self.prosperity > 10:
                self._trigger_attack()
        elif self.attack_cooldown == 0 and random.random() < 0.01 * hours and self.prosperity > 10:
            # Small chance of attack every hour if prosperity is high enough
            self._trigger_attack()
    
    def _update_construction(self, hours):
        """
        Update building construction progress.
        
        Args:
            hours: Game hours elapsed
        """
        # Find builder NPCs
        builders = [npc for npc in self.npcs if npc.role == NpcRole.BUILDER and not npc.assigned_building]
        builder_count = len(builders)
        
        # Calculate construction speed factor
        speed_factor = 0.02 * hours  # Base speed
        if builder_count > 0:
            # Each builder adds 0.03 (with efficiency multiplier)
            builder_efficiency = sum(builder.efficiency for builder in builders)
            speed_factor += 0.03 * builder_efficiency * hours
        
        # Update all incomplete buildings
        for building in self.buildings:
            if building.construction_progress < 1.0:
                building.construction_progress = min(1.0, building.construction_progress + speed_factor)
                
                if building.construction_progress >= 1.0:
                    logger.info(f"Completed construction of {building.building_type.name}")
                    
                    # Update base stats when building is complete
                    self._update_base_stats()
    
    def _update_resources(self, hours):
        """
        Update resource production and consumption.
        
        Args:
            hours: Game hours elapsed
        """
        # Calculate production and consumption from buildings
        production_rates = {resource_type: 0 for resource_type in ResourceType}
        consumption_rates = {resource_type: 0 for resource_type in ResourceType}
        
        for building in self.buildings:
            # Only consider completed buildings
            if building.construction_progress >= 1.0:
                # Add production
                for resource_type, rate in building.production.items():
                    production_rates[resource_type] += rate
                
                # Add consumption
                for resource_type, rate in building.consumption.items():
                    consumption_rates[resource_type] += rate
        
        # Update resource amounts
        for resource_type, resource in self.resources.items():
            # Set current rates
            resource.production_rate = production_rates[resource_type]
            resource.consumption_rate = consumption_rates[resource_type]
            
            # Update resource
            resource.update(hours)
    
    def _update_npcs(self, hours):
        """
        Update NPCs.
        
        Args:
            hours: Game hours elapsed
        """
        # Calculate food availability ratio
        food_resource = self.resources[ResourceType.FOOD]
        food_needed = self.population * 1.0 * hours  # Each NPC needs 1 food per hour
        
        if food_needed > 0:
            food_availability = min(1.0, food_resource.amount / food_needed)
        else:
            food_availability = 1.0
        
        # Consume food
        food_to_consume = min(food_resource.amount, food_needed)
        food_resource.remove(food_to_consume)
        
        # Update each NPC
        for npc in self.npcs:
            # Update happiness
            npc.update_happiness(food_availability)
            
            # Gain experience if working
            if npc.assigned_building and npc.assigned_building.construction_progress >= 1.0:
                npc.gain_experience(hours * 0.5)
        
        # Overall base happiness is average of NPC happiness
        if self.npcs:
            self.happiness = sum(npc.happiness for npc in self.npcs) / len(self.npcs)
        else:
            self.happiness = 100
    
    def _update_defenses(self):
        """Update base attack and defense strength."""
        # Reset values
        self.attack_strength = 0
        self.defense_strength = 0
        
        # Calculate from buildings and NPCs
        for building in self.buildings:
            # Only consider completed buildings
            if building.construction_progress >= 1.0:
                if building.building_type == BuildingType.WALL:
                    self.defense_strength += 5 * building.level
                elif building.building_type == BuildingType.TOWER:
                    self.defense_strength += 10 * building.level
                    self.attack_strength += 5 * building.level
                elif building.building_type == BuildingType.BARRACKS:
                    self.defense_strength += 3 * building.level * building.assigned_workers
                    self.attack_strength += 5 * building.level * building.assigned_workers
        
        # Add NPC contribution
        for npc in self.npcs:
            if npc.role == NpcRole.DEFENDER:
                self.defense_strength += 10 * npc.level * npc.efficiency
                self.attack_strength += 5 * npc.level * npc.efficiency
    
    def _trigger_attack(self):
        """Trigger a random attack on the base."""
        # Calculate attack strength based on base prosperity
        enemy_strength = 10 + (self.prosperity * 0.5) + random.randint(0, 20)
        
        logger.info(f"Attack triggered! Enemy strength: {enemy_strength}, Base defense: {self.defense_strength}")
        
        # Set new cooldown
        self.attack_cooldown = 24 + random.randint(0, 48)  # 1-3 days
        
        # Check if defense is sufficient
        if self.defense_strength >= enemy_strength:
            logger.info("Attack repelled successfully!")
            
            # Reward for defending
            reward = max(5, int(enemy_strength * 0.2))
            self.resources[ResourceType.GOLD].add(reward)
            
            # TODO: Show success notification
            
        else:
            # Calculate damage based on defense ratio
            defense_ratio = self.defense_strength / enemy_strength
            damage_factor = 1.0 - min(0.9, defense_ratio)  # Maximum 90% reduction
            
            logger.info(f"Base defenses breached! Damage factor: {damage_factor:.2f}")
            
            # Apply damage to random buildings
            damaged_buildings = []
            
            # Target around 3 buildings based on damage factor
            target_buildings = max(1, int(3 * damage_factor))
            
            # Only select completed buildings
            valid_buildings = [b for b in self.buildings if b.construction_progress >= 1.0]
            
            if valid_buildings:
                chosen_buildings = random.sample(valid_buildings, min(target_buildings, len(valid_buildings)))
                
                for building in chosen_buildings:
                    damage_amount = random.randint(10, 30) * damage_factor
                    actual_damage = building.damage(damage_amount)
                    damaged_buildings.append((building, actual_damage))
            
            # Steal some resources
            for resource_type, resource in self.resources.items():
                steal_amount = int(resource.amount * 0.1 * damage_factor)
                if steal_amount > 0:
                    resource.remove(steal_amount)
            
            # TODO: Show failure notification with damage report
    
    def _update_grid_occupancy(self, building):
        """
        Update grid to mark cells occupied by a building.
        
        Args:
            building: Building instance
        """
        for x, y in building.get_grid_cells():
            if 0 <= x < self.width and 0 <= y < self.height:
                self.grid[y][x] = building
    
    def _update_base_stats(self):
        """Update base stats based on buildings and NPCs."""
        # Reset certain values
        old_max_population = self.max_population
        self.max_population = 10  # Base value
        
        # Calculate from buildings
        for building in self.buildings:
            # Only consider completed buildings
            if building.construction_progress >= 1.0:
                # Building specific effects
                if building.building_type == BuildingType.HOUSE:
                    self.max_population += 5 * building.level
                elif building.building_type == BuildingType.STORAGE:
                    # Increase resource storage capacity
                    for resource in self.resources.values():
                        resource.max_amount = 100 * (1 + (building.level * 0.5))
        
        # Calculate prosperity based on various factors
        self.prosperity = (
            len(self.buildings) * 2 +
            sum(b.level for b in self.buildings) * 3 +
            self.population * 1 +
            sum(r.amount for r in self.resources.values()) * 0.01 +
            self.happiness * 0.1
        )
        
        # If max population decreased, might need to remove NPCs
        if self.max_population < old_max_population and self.population > self.max_population:
            overflow = self.population - self.max_population
            logger.warning(f"Population cap decreased! Need to remove {overflow} NPCs")
            
            # Find NPCs to remove (prioritize unassigned ones)
            to_remove = [npc for npc in self.npcs if npc.assigned_building is None]
            
            # If still need more, select random ones
            if len(to_remove) < overflow:
                remaining = list(set(self.npcs) - set(to_remove))
                to_remove.extend(random.sample(remaining, overflow - len(to_remove)))
            
            # Remove overflow NPCs
            for npc in to_remove[:overflow]:
                self.remove_npc(npc)
    
    def is_position_valid(self, building_type, x, y):
        """
        Check if a building can be placed at a position.
        
        Args:
            building_type: Type from BuildingType enum
            x: Grid X position
            y: Grid Y position
            
        Returns:
            Boolean indicating if position is valid
        """
        # Create temporary building to get size
        temp_building = Building(building_type, x, y)
        
        # Check if all grid cells are within bounds and empty
        for cell_x, cell_y in temp_building.get_grid_cells():
            if not (0 <= cell_x < self.width and 0 <= cell_y < self.height):
                return False
            
            if self.grid[cell_y][cell_x] is not None:
                return False
        
        return True
    
    def get_building_at(self, x, y):
        """
        Get the building at a grid position.
        
        Args:
            x: Grid X position
            y: Grid Y position
            
        Returns:
            Building instance or None if no building
        """
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.grid[y][x]
        
        return None
    
    def get_building_requirements(self, building_type):
        """
        Get resource requirements for a new building.
        
        Args:
            building_type: Type from BuildingType enum
            
        Returns:
            Dictionary mapping ResourceType to amount needed
        """
        requirements = {}
        
        if building_type == BuildingType.HOUSE:
            requirements[ResourceType.WOOD] = 30
            requirements[ResourceType.STONE] = 20
            
        elif building_type == BuildingType.FARM:
            requirements[ResourceType.WOOD] = 20
            requirements[ResourceType.STONE] = 10
            
        elif building_type == BuildingType.LUMBERMILL:
            requirements[ResourceType.WOOD] = 25
            requirements[ResourceType.STONE] = 15
            
        elif building_type == BuildingType.MINE:
            requirements[ResourceType.WOOD] = 15
            requirements[ResourceType.STONE] = 30
            
        elif building_type == BuildingType.BARRACKS:
            requirements[ResourceType.WOOD] = 40
            requirements[ResourceType.STONE] = 30
            requirements[ResourceType.IRON] = 10
            
        elif building_type == BuildingType.WALL:
            requirements[ResourceType.STONE] = 15
            
        elif building_type == BuildingType.TOWER:
            requirements[ResourceType.WOOD] = 15
            requirements[ResourceType.STONE] = 25
            requirements[ResourceType.IRON] = 5
            
        elif building_type == BuildingType.STORAGE:
            requirements[ResourceType.WOOD] = 35
            requirements[ResourceType.STONE] = 25
            
        elif building_type == BuildingType.WORKSHOP:
            requirements[ResourceType.WOOD] = 30
            requirements[ResourceType.STONE] = 20
            requirements[ResourceType.IRON] = 15
            
        elif building_type == BuildingType.MARKET:
            requirements[ResourceType.WOOD] = 40
            requirements[ResourceType.STONE] = 30
            requirements[ResourceType.GOLD] = 20
            
        elif building_type == BuildingType.TEMPLE:
            requirements[ResourceType.WOOD] = 50
            requirements[ResourceType.STONE] = 50
            requirements[ResourceType.GOLD] = 30
            requirements[ResourceType.CRYSTAL] = 5
        
        # Ensure all resource types are included with at least 0
        for resource_type in ResourceType:
            if resource_type not in requirements:
                requirements[resource_type] = 0
        
        return requirements
    
    def get_upgrade_requirements(self, building):
        """
        Get resource requirements for upgrading a building.
        
        Args:
            building: Building instance to upgrade
            
        Returns:
            Dictionary mapping ResourceType to amount needed
        """
        # Base requirements from building type
        base_reqs = self.get_building_requirements(building.building_type)
        
        # Scale with current level (linear increase)
        requirements = {}
        for resource_type, amount in base_reqs.items():
            requirements[resource_type] = int(amount * 0.7 * building.level)
        
        return requirements
    
    def to_dict(self):
        """Convert to dictionary for serialization."""
        return {
            'width': self.width,
            'height': self.height,
            'name': self.name,
            'buildings': [b.to_dict() for b in self.buildings],
            'npcs': [n.to_dict() for n in self.npcs],
            'resources': {r.value: res.to_dict() for r, res in self.resources.items()},
            'population': self.population,
            'max_population': self.max_population,
            'happiness': self.happiness,
            'attack_strength': self.attack_strength,
            'defense_strength': self.defense_strength,
            'attack_cooldown': self.attack_cooldown,
            'prosperity': self.prosperity,
            'discovered_techs': self.discovered_techs
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create from dictionary."""
        base = cls(
            data['width'],
            data['height'],
            data['name']
        )
        
        # Restore resources
        for resource_type_val, resource_data in data['resources'].items():
            resource_type = ResourceType(int(resource_type_val))
            base.resources[resource_type] = Resource.from_dict(resource_data)
        
        # Restore buildings
        for building_data in data['buildings']:
            building = Building.from_dict(building_data)
            base.buildings.append(building)
            base._update_grid_occupancy(building)
        
        # Restore NPCs
        for npc_data in data['npcs']:
            npc = Npc.from_dict(npc_data, base.buildings)
            base.npcs.append(npc)
        
        # Restore base stats
        base.population = data['population']
        base.max_population = data['max_population']
        base.happiness = data['happiness']
        base.attack_strength = data['attack_strength']
        base.defense_strength = data['defense_strength']
        base.attack_cooldown = data['attack_cooldown']
        base.prosperity = data['prosperity']
        base.discovered_techs = data['discovered_techs']
        
        return base

class BaseBuildingState(GameState):
    """
    Game state for base building mode.
    
    This state handles:
    - Resource gathering and management
    - Structure construction and placement
    - NPC recruitment and management
    - Base upgrades and expansion
    """
    
    def __init__(self, state_manager, event_bus, settings):
        """Initialize the base building state."""
        super().__init__(state_manager, event_bus, settings)
        
        # Base data
        self.base = None
        
        # UI elements
        self.font_small = None
        self.font_medium = None
        self.font_large = None
        self.colors = {
            'background': (0, 100, 0),
            'grid': (0, 50, 0),
            'ui_bg': (50, 50, 50, 180),
            'ui_border': (200, 200, 200),
            'ui_highlight': (100, 200, 100),
            'text': (255, 255, 255),
            'text_highlight': (255, 255, 100),
            'building': {
                BuildingType.HOUSE: (150, 150, 200),
                BuildingType.FARM: (100, 200, 100),
                BuildingType.LUMBERMILL: (150, 100, 50),
                BuildingType.MINE: (100, 100, 100),
                BuildingType.BARRACKS: (200, 100, 100),
                BuildingType.WALL: (150, 150, 150),
                BuildingType.TOWER: (100, 100, 200),
                BuildingType.STORAGE: (200, 200, 100),
                BuildingType.WORKSHOP: (200, 150, 50),
                BuildingType.MARKET: (200, 200, 200),
                BuildingType.TEMPLE: (200, 100, 200)
            },
            'resource': {
                ResourceType.WOOD: (150, 100, 50),
                ResourceType.STONE: (150, 150, 150),
                ResourceType.FOOD: (100, 200, 100),
                ResourceType.GOLD: (255, 215, 0),
                ResourceType.IRON: (100, 100, 100),
                ResourceType.CRYSTAL: (100, 200, 255)
            }
        }
        
        # Grid display
        self.tile_size = 40
        self.grid_offset_x = 20
        self.grid_offset_y = 20
        
        # View state
        self.view_mode = "normal"  # normal, building, npc, attack
        self.selected_building_type = None
        self.selected_entity = None
        self.show_grid = True
        self.time_speed = 1  # 1x speed
        
        # UI state
        self.ui_panels = {
            'resources': pygame.Rect(0, 0, 0, 0),  # Will be sized in render
            'building_menu': pygame.Rect(0, 0, 0, 0),
            'npc_menu': pygame.Rect(0, 0, 0, 0),
            'info_panel': pygame.Rect(0, 0, 0, 0)
        }
        self.ui_buttons = {}
        
        # Hover information
        self.hover_x = None
        self.hover_y = None
        
        # Time tracking
        self.game_time = 0
        self.real_time_accumulator = 0
        
        logger.info("BaseBuildingState initialized")
    
    def enter(self, data=None):
        """Set up the state when entered."""
        super().enter(data)
        
        # Initialize fonts
        pygame.font.init()
        self.font_small = pygame.font.SysFont(None, 18)
        self.font_medium = pygame.font.SysFont(None, 24)
        self.font_large = pygame.font.SysFont(None, 32)
        
        # Get base from persistent data or create a new one
        base_data = self.state_manager.get_persistent_data("player_base")
        if base_data:
            self.base = Base.from_dict(base_data)
            logger.info(f"Loaded existing base: {self.base.name}")
        else:
            # Create new base
            self.base = Base(20, 20, "Player Base")
            
            # Add initial resources
            self.base.resources[ResourceType.WOOD].add(100)
            self.base.resources[ResourceType.STONE].add(50)
            self.base.resources[ResourceType.FOOD].add(100)
            self.base.resources[ResourceType.GOLD].add(20)
            
            # Add initial buildings
            if self.base.add_building(BuildingType.HOUSE, 5, 5):
                house = self.base.buildings[0]
                house.construction_progress = 1.0  # Start with a complete house
            
            if self.base.add_building(BuildingType.FARM, 8, 5):
                farm = self.base.buildings[1]
                farm.construction_progress = 1.0  # Start with a complete farm
            
            # Add initial NPCs
            self.base.add_npc("Builder", NpcRole.BUILDER)
            self.base.add_npc("Farmer", NpcRole.FARMER)
            
            # Assign farmer to farm
            if len(self.base.buildings) > 1 and len(self.base.npcs) > 1:
                self.base.assign_npc(self.base.npcs[1], self.base.buildings[1])
            
            logger.info("Created new base")
        
        # Set up UI
        self._setup_ui()
        
        logger.info("Entered base building state")
    
    def exit(self):
        """Clean up when leaving the state."""
        # Save base to persistent data
        self.state_manager.set_persistent_data("player_base", self.base.to_dict())
        
        super().exit()
        logger.info("Exited base building state")
    
    def handle_event(self, event):
        """Handle pygame events."""
        if not self.active:
            return
        
        if event.type == pygame.MOUSEBUTTONDOWN:
            # Get mouse position
            pos = pygame.mouse.get_pos()
            
            # Handle UI clicks first
            if self._handle_ui_click(pos):
                return
            
            # Handle grid clicks
            if event.button == 1:  # Left click
                self._handle_grid_left_click(pos)
            elif event.button == 3:  # Right click
                self._handle_grid_right_click(pos)
        
        elif event.type == pygame.MOUSEMOTION:
            # Update hover position
            pos = pygame.mouse.get_pos()
            self._update_hover_position(pos)
        
        elif event.type == pygame.KEYDOWN:
            # Handle keyboard input
            if event.key == pygame.K_ESCAPE:
                # Cancel building placement or selection
                if self.view_mode == "building":
                    self.view_mode = "normal"
                    self.selected_building_type = None
                elif self.selected_entity:
                    self.selected_entity = None
                else:
                    # Exit to world map
                    self._exit_base_building()
            
            elif event.key == pygame.K_g:
                # Toggle grid
                self.show_grid = not self.show_grid
            
            elif event.key in [pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4]:
                # Change time speed
                if event.key == pygame.K_1:
                    self.time_speed = 1
                elif event.key == pygame.K_2:
                    self.time_speed = 2
                elif event.key == pygame.K_3:
                    self.time_speed = 5
                elif event.key == pygame.K_4:
                    self.time_speed = 10
                
                logger.debug(f"Time speed set to {self.time_speed}x")
    
    def update(self, dt):
        """Update game state."""
        if not self.active:
            return
        
        # Accumulate real time and update at intervals
        self.real_time_accumulator += dt
        
        # Update every 0.25 seconds of real time
        if self.real_time_accumulator >= 0.25:
            # Calculate game time elapsed (hours)
            # 1 real second = 1 game minute at 1x speed
            game_hours = (self.real_time_accumulator * self.time_speed) / 60
            
            # Update base
            self.base.update(game_hours)
            
            # Update game time
            self.game_time += game_hours
            
            # Reset accumulator
            self.real_time_accumulator = 0
    
    def render(self, screen):
        """Render the game state."""
        if not self.visible:
            return
        
        # Fill background
        screen.fill(self.colors['background'])
        
        # Render base grid
        self._render_grid(screen)
        
        # Render UI
        self._render_ui(screen)
        
        # Render hover info
        self._render_hover_info(screen)
        
        # Render building preview when placing
        if self.view_mode == "building" and self.selected_building_type and self.hover_x is not None:
            self._render_building_preview(screen)
    
    def _setup_ui(self):
        """Set up UI elements."""
        # Get screen dimensions
        screen_width, screen_height = pygame.display.get_surface().get_size()
        
        # Resource panel at top
        self.ui_panels['resources'] = pygame.Rect(
            screen_width - 300, 10, 290, 100
        )
        
        # Building menu on right
        self.ui_panels['building_menu'] = pygame.Rect(
            screen_width - 300, 120, 290, 250
        )
        
        # NPC menu on right
        self.ui_panels['npc_menu'] = pygame.Rect(
            screen_width - 300, 380, 290, 200
        )
        
        # Info panel at bottom
        self.ui_panels['info_panel'] = pygame.Rect(
            10, screen_height - 110, screen_width - 320, 100
        )
        
        # Create buttons
        self.ui_buttons = {}
        
        # Building buttons
        building_types = [
            BuildingType.HOUSE, BuildingType.FARM, BuildingType.LUMBERMILL,
            BuildingType.MINE, BuildingType.BARRACKS, BuildingType.WALL,
            BuildingType.TOWER, BuildingType.STORAGE, BuildingType.WORKSHOP,
            BuildingType.MARKET, BuildingType.TEMPLE
        ]
        
        # Create a grid of building buttons
        button_width = 60
        button_height = 60
        button_spacing = 10
        buttons_per_row = 4
        
        for i, building_type in enumerate(building_types):
            row = i // buttons_per_row
            col = i % buttons_per_row
            
            button_x = self.ui_panels['building_menu'].x + col * (button_width + button_spacing) + 10
            button_y = self.ui_panels['building_menu'].y + row * (button_height + button_spacing) + 40
            
            self.ui_buttons[f"build_{building_type.name}"] = pygame.Rect(
                button_x, button_y, button_width, button_height
            )
        
        # Add close button
        self.ui_buttons["exit"] = pygame.Rect(
            screen_width - 100, 10, 80, 30
        )
        
        # Add time control buttons
        self.ui_buttons["time_1x"] = pygame.Rect(
            10, 10, 50, 30
        )
        self.ui_buttons["time_2x"] = pygame.Rect(
            70, 10, 50, 30
        )
        self.ui_buttons["time_5x"] = pygame.Rect(
            130, 10, 50, 30
        )
        self.ui_buttons["time_10x"] = pygame.Rect(
            190, 10, 50, 30
        )
    
    def _handle_ui_click(self, pos):
        """
        Handle clicks on UI elements.
        
        Args:
            pos: (x, y) mouse position
            
        Returns:
            Boolean indicating if click was handled
        """
        # Check buttons
        for button_id, button_rect in self.ui_buttons.items():
            if button_rect.collidepoint(pos):
                # Building buttons
                if button_id.startswith("build_"):
                    building_type_name = button_id.split("_")[1]
                    
                    try:
                        building_type = BuildingType[building_type_name]
                        self.view_mode = "building"
                        self.selected_building_type = building_type
                        logger.debug(f"Selected building type: {building_type.name}")
                    except KeyError:
                        logger.error(f"Invalid building type: {building_type_name}")
                
                # Exit button
                elif button_id == "exit":
                    self._exit_base_building()
                
                # Time control buttons
                elif button_id == "time_1x":
                    self.time_speed = 1
                elif button_id == "time_2x":
                    self.time_speed = 2
                elif button_id == "time_5x":
                    self.time_speed = 5
                elif button_id == "time_10x":
                    self.time_speed = 10
                
                return True
        
        # Check if clicking a panel
        for panel_id, panel_rect in self.ui_panels.items():
            if panel_rect.collidepoint(pos):
                return True
        
        return False
    
    def _handle_grid_left_click(self, pos):
        """
        Handle left clicks on the grid.
        
        Args:
            pos: (x, y) mouse position
        """
        # Convert screen position to grid coordinates
        grid_x, grid_y = self._screen_to_grid(pos)
        
        if grid_x is None or grid_y is None:
            return
        
        # Different handling based on view mode
        if self.view_mode == "normal":
            # Select entity at position
            building = self.base.get_building_at(grid_x, grid_y)
            
            if building:
                self.selected_entity = building
                logger.debug(f"Selected building: {building.building_type.name} at ({grid_x}, {grid_y})")
            else:
                self.selected_entity = None
        
        elif self.view_mode == "building" and self.selected_building_type:
            # Attempt to place building
            if self.base.is_position_valid(self.selected_building_type, grid_x, grid_y):
                building = self.base.add_building(self.selected_building_type, grid_x, grid_y)
                
                if building:
                    # Successfully placed building
                    logger.info(f"Placed {self.selected_building_type.name} at ({grid_x}, {grid_y})")
                    
                    # Return to normal mode if placing multiple buildings is not needed
                    self.view_mode = "normal"
                    self.selected_building_type = None
                    self.selected_entity = building
            else:
                logger.warning(f"Cannot place {self.selected_building_type.name} at ({grid_x}, {grid_y})")
    
    def _handle_grid_right_click(self, pos):
        """
        Handle right clicks on the grid.
        
        Args:
            pos: (x, y) mouse position
        """
        # Convert screen position to grid coordinates
        grid_x, grid_y = self._screen_to_grid(pos)
        
        if grid_x is None or grid_y is None:
            return
        
        # Right click cancels building placement
        if self.view_mode == "building":
            self.view_mode = "normal"
            self.selected_building_type = None
            logger.debug("Canceled building placement")
    
    def _update_hover_position(self, pos):
        """
        Update hover position for grid highlighting.
        
        Args:
            pos: (x, y) mouse position
        """
        # Convert screen position to grid coordinates
        grid_x, grid_y = self._screen_to_grid(pos)
        
        self.hover_x = grid_x
        self.hover_y = grid_y
    
    def _screen_to_grid(self, pos):
        """
        Convert screen coordinates to grid coordinates.
        
        Args:
            pos: (x, y) screen position
            
        Returns:
            (grid_x, grid_y) tuple or (None, None) if outside grid
        """
        x, y = pos
        
        # Adjust for grid offset
        x -= self.grid_offset_x
        y -= self.grid_offset_y
        
        # Convert to grid coordinates
        grid_x = x // self.tile_size
        grid_y = y // self.tile_size
        
        # Check if within grid bounds
        if 0 <= grid_x < self.base.width and 0 <= grid_y < self.base.height:
            return grid_x, grid_y
        
        return None, None
    
    def _grid_to_screen(self, grid_x, grid_y):
        """
        Convert grid coordinates to screen coordinates.
        
        Args:
            grid_x: Grid X position
            grid_y: Grid Y position
            
        Returns:
            (screen_x, screen_y) tuple
        """
        screen_x = self.grid_offset_x + grid_x * self.tile_size
        screen_y = self.grid_offset_y + grid_y * self.tile_size
        
        return screen_x, screen_y
    
    def _render_grid(self, screen):
        """
        Render the base grid.
        
        Args:
            screen: Pygame surface to render to
        """
        # Render ground
        grid_width = self.base.width * self.tile_size
        grid_height = self.base.height * self.tile_size
        
        pygame.draw.rect(
            screen,
            (50, 120, 50),
            (self.grid_offset_x, self.grid_offset_y, grid_width, grid_height)
        )
        
        # Render grid lines
        if self.show_grid:
            for x in range(self.base.width + 1):
                pygame.draw.line(
                    screen,
                    self.colors['grid'],
                    (self.grid_offset_x + x * self.tile_size, self.grid_offset_y),
                    (self.grid_offset_x + x * self.tile_size, self.grid_offset_y + grid_height),
                    1
                )
            
            for y in range(self.base.height + 1):
                pygame.draw.line(
                    screen,
                    self.colors['grid'],
                    (self.grid_offset_x, self.grid_offset_y + y * self.tile_size),
                    (self.grid_offset_x + grid_width, self.grid_offset_y + y * self.tile_size),
                    1
                )
        
        # Render buildings
        for building in self.base.buildings:
            self._render_building(screen, building)
        
        # Highlight hover tile
        if self.hover_x is not None and self.hover_y is not None:
            screen_x, screen_y = self._grid_to_screen(self.hover_x, self.hover_y)
            
            pygame.draw.rect(
                screen,
                (255, 255, 255, 100),
                (screen_x, screen_y, self.tile_size, self.tile_size),
                2
            )
    
    def _render_building(self, screen, building):
        """
        Render a building on the grid.
        
        Args:
            screen: Pygame surface to render to
            building: Building instance to render
        """
        screen_x, screen_y = self._grid_to_screen(building.x, building.y)
        width, height = building.size
        
        # Calculate dimensions
        width_pixels = width * self.tile_size
        height_pixels = height * self.tile_size
        
        # Get building color
        color = self.colors['building'].get(building.building_type, (150, 150, 150))
        
        # If under construction, darken color
        if building.construction_progress < 1.0:
            color = tuple(int(c * 0.7) for c in color)
        
        # Draw building rectangle
        pygame.draw.rect(
            screen,
            color,
            (screen_x, screen_y, width_pixels, height_pixels)
        )
        
        # Draw border (thicker for selected building)
        border_width = 3 if building == self.selected_entity else 1
        pygame.draw.rect(
            screen,
            (0, 0, 0),
            (screen_x, screen_y, width_pixels, height_pixels),
            border_width
        )
        
        # Draw building type
        type_text = self.font_small.render(
            building.building_type.name,
            True,
            (0, 0, 0)
        )
        screen.blit(
            type_text,
            (screen_x + 5, screen_y + 5)
        )
        
        # Draw level
        level_text = self.font_small.render(
            f"Lvl {building.level}",
            True,
            (0, 0, 0)
        )
        screen.blit(
            level_text,
            (screen_x + 5, screen_y + 20)
        )
        
        # If under construction, draw progress bar
        if building.construction_progress < 1.0:
            progress_width = int(width_pixels * building.construction_progress)
            
            pygame.draw.rect(
                screen,
                (0, 255, 0),
                (screen_x, screen_y + height_pixels - 5, progress_width, 5)
            )
            
            progress_text = self.font_small.render(
                f"{int(building.construction_progress * 100)}%",
                True,
                (0, 0, 0)
            )
            screen.blit(
                progress_text,
                (screen_x + 5, screen_y + height_pixels - 20)
            )
    
    def _render_building_preview(self, screen):
        """
        Render a preview of a building being placed.
        
        Args:
            screen: Pygame surface to render to
        """
        if self.hover_x is None or self.hover_y is None:
            return
        
        # Create temporary building to get size
        temp_building = Building(self.selected_building_type, self.hover_x, self.hover_y)
        
        screen_x, screen_y = self._grid_to_screen(self.hover_x, self.hover_y)
        width, height = temp_building.size
        
        # Calculate dimensions
        width_pixels = width * self.tile_size
        height_pixels = height * self.tile_size
        
        # Get building color
        color = self.colors['building'].get(self.selected_building_type, (150, 150, 150))
        
        # Check if position is valid
        is_valid = self.base.is_position_valid(self.selected_building_type, self.hover_x, self.hover_y)
        
        # Make semi-transparent
        color = color + (100,)  # Add alpha channel
        
        # Make red if invalid
        if not is_valid:
            color = (255, 0, 0, 100)
        
        # Draw building rectangle
        surface = pygame.Surface((width_pixels, height_pixels), pygame.SRCALPHA)
        surface.fill(color)
        screen.blit(surface, (screen_x, screen_y))
        
        # Draw border
        pygame.draw.rect(
            screen,
            (255, 255, 255) if is_valid else (255, 0, 0),
            (screen_x, screen_y, width_pixels, height_pixels),
            2
        )
        
        # Draw building type
        type_text = self.font_small.render(
            self.selected_building_type.name,
            True,
            (255, 255, 255)
        )
        screen.blit(
            type_text,
            (screen_x + 5, screen_y + 5)
        )
        
        # Draw resource requirements below grid
        self._render_building_requirements(screen, self.selected_building_type)
    
    def _render_building_requirements(self, screen, building_type):
        """
        Render resource requirements for a building.
        
        Args:
            screen: Pygame surface to render to
            building_type: BuildingType to show requirements for
        """
        requirements = self.base.get_building_requirements(building_type)
        
        # Draw at fixed position below grid
        screen_width, screen_height = screen.get_size()
        
        req_x = 10
        req_y = self.grid_offset_y + self.base.height * self.tile_size + 10
        
        # Draw header
        header_text = self.font_medium.render(
            f"Requirements for {building_type.name}:",
            True,
            self.colors['text']
        )
        screen.blit(header_text, (req_x, req_y))
        
        # Draw each resource requirement
        req_y += 25
        for resource_type, amount in requirements.items():
            if amount > 0:
                color = self.colors['resource'].get(resource_type, (255, 255, 255))
                
                # Check if player has enough
                has_enough = self.base.resources[resource_type].amount >= amount
                
                text_color = self.colors['text'] if has_enough else (255, 0, 0)
                
                resource_text = self.font_small.render(
                    f"{resource_type.name}: {amount} / {self.base.resources[resource_type].amount}",
                    True,
                    text_color
                )
                screen.blit(resource_text, (req_x + 10, req_y))
                
                # Draw small colored square for resource type
                pygame.draw.rect(
                    screen,
                    color,
                    (req_x, req_y + 2, 8, 8)
                )
                
                req_y += 20
    
    def _render_ui(self, screen):
        """
        Render UI elements.
        
        Args:
            screen: Pygame surface to render to
        """
        # Render panels
        for panel_id, panel_rect in self.ui_panels.items():
            # Draw panel background
            pygame.draw.rect(
                screen,
                self.colors['ui_bg'],
                panel_rect
            )
            
            # Draw panel border
            pygame.draw.rect(
                screen,
                self.colors['ui_border'],
                panel_rect,
                2
            )
            
            # Draw panel content
            if panel_id == 'resources':
                self._render_resources_panel(screen, panel_rect)
            elif panel_id == 'building_menu':
                self._render_building_menu(screen, panel_rect)
            elif panel_id == 'npc_menu':
                self._render_npc_menu(screen, panel_rect)
            elif panel_id == 'info_panel':
                self._render_info_panel(screen, panel_rect)
        
        # Render buttons
        for button_id, button_rect in self.ui_buttons.items():
            # Draw button background
            if button_id.startswith("build_") and self.view_mode == "building":
                # Check if this is the selected building type
                building_type_name = button_id.split("_")[1]
                
                try:
                    building_type = BuildingType[building_type_name]
                    is_selected = building_type == self.selected_building_type
                except KeyError:
                    is_selected = False
                
                button_color = self.colors['ui_highlight'] if is_selected else self.colors['ui_bg']
            elif button_id.startswith("time_"):
                # Highlight current time speed
                speed = int(button_id.split("_")[1].replace("x", ""))
                button_color = self.colors['ui_highlight'] if speed == self.time_speed else self.colors['ui_bg']
            else:
                button_color = self.colors['ui_bg']
            
            pygame.draw.rect(
                screen,
                button_color,
                button_rect
            )
            
            # Draw button border
            pygame.draw.rect(
                screen,
                self.colors['ui_border'],
                button_rect,
                2
            )
            
            # Draw button text
            if button_id.startswith("build_"):
                # Get building type from button ID
                building_type_name = button_id.split("_")[1]
                
                try:
                    building_type = BuildingType[building_type_name]
                    text = building_type.name
                    
                    # Draw colored building icon
                    color = self.colors['building'].get(building_type, (150, 150, 150))
                    pygame.draw.rect(
                        screen,
                        color,
                        (button_rect.x + 5, button_rect.y + 5, 20, 20)
                    )
                    
                    # Draw small text
                    button_text = self.font_small.render(
                        text if len(text) < 8 else text[:6] + "..",
                        True,
                        self.colors['text']
                    )
                    screen.blit(
                        button_text,
                        (button_rect.x + 28, button_rect.y + 8)
                    )
                except KeyError:
                    pass
            elif button_id == "exit":
                button_text = self.font_small.render(
                    "Exit Base",
                    True,
                    self.colors['text']
                )
                text_rect = button_text.get_rect(center=button_rect.center)
                screen.blit(button_text, text_rect)
            elif button_id.startswith("time_"):
                speed = button_id.split("_")[1]
                button_text = self.font_small.render(
                    speed,
                    True,
                    self.colors['text']
                )
                text_rect = button_text.get_rect(center=button_rect.center)
                screen.blit(button_text, text_rect)
    
    def _render_resources_panel(self, screen, panel_rect):
        """
        Render the resources panel.
        
        Args:
            screen: Pygame surface to render to
            panel_rect: Rectangle for the panel
        """
        # Draw panel title
        title_text = self.font_medium.render(
            "Resources",
            True,
            self.colors['text']
        )
        screen.blit(
            title_text,
            (panel_rect.x + 10, panel_rect.y + 5)
        )
        
        # Draw each resource
        resource_x = panel_rect.x + 10
        resource_y = panel_rect.y + 30
        
        for resource_type, resource in self.base.resources.items():
            # Skip if resource isn't discovered yet
            if resource_type == ResourceType.CRYSTAL and resource.amount == 0:
                continue
                
            # Draw resource name
            color = self.colors['resource'].get(resource_type, (255, 255, 255))
            
            resource_text = self.font_small.render(
                f"{resource_type.name}: {int(resource.amount)}/{int(resource.max_amount)}",
                True,
                color
            )
            screen.blit(resource_text, (resource_x, resource_y))
            
            # Draw production rate if non-zero
            if resource.production_rate > 0 or resource.consumption_rate > 0:
                net_rate = resource.production_rate - resource.consumption_rate
                sign = "+" if net_rate >= 0 else ""
                
                rate_text = self.font_small.render(
                    f"({sign}{net_rate:.1f}/h)",
                    True,
                    (0, 255, 0) if net_rate >= 0 else (255, 0, 0)
                )
                screen.blit(rate_text, (resource_x + 150, resource_y))
            
            resource_y += 20
    
    def _render_building_menu(self, screen, panel_rect):
        """
        Render the building menu panel.
        
        Args:
            screen: Pygame surface to render to
            panel_rect: Rectangle for the panel
        """
        # Draw panel title
        title_text = self.font_medium.render(
            "Buildings",
            True,
            self.colors['text']
        )
        screen.blit(
            title_text,
            (panel_rect.x + 10, panel_rect.y + 5)
        )
        
        # Building buttons are rendered in _render_ui
    
    def _render_npc_menu(self, screen, panel_rect):
        """
        Render the NPC menu panel.
        
        Args:
            screen: Pygame surface to render to
            panel_rect: Rectangle for the panel
        """
        # Draw panel title
        title_text = self.font_medium.render(
            f"Population: {self.base.population}/{self.base.max_population}",
            True,
            self.colors['text']
        )
        screen.blit(
            title_text,
            (panel_rect.x + 10, panel_rect.y + 5)
        )
        
        # Draw happiness
        happiness_text = self.font_small.render(
            f"Happiness: {int(self.base.happiness)}%",
            True,
            (0, 255, 0) if self.base.happiness >= 70 else
            (255, 255, 0) if self.base.happiness >= 40 else
            (255, 0, 0)
        )
        screen.blit(
            happiness_text,
            (panel_rect.x + 10, panel_rect.y + 25)
        )
        
        # Draw defense strength
        defense_text = self.font_small.render(
            f"Defense: {int(self.base.defense_strength)}",
            True,
            self.colors['text']
        )
        screen.blit(
            defense_text,
            (panel_rect.x + 10, panel_rect.y + 45)
        )
        
        # Draw attack strength
        attack_text = self.font_small.render(
            f"Attack: {int(self.base.attack_strength)}",
            True,
            self.colors['text']
        )
        screen.blit(
            attack_text,
            (panel_rect.x + 150, panel_rect.y + 45)
        )
        
        # Draw attack cooldown if active
        if self.base.attack_cooldown > 0:
            cooldown_text = self.font_small.render(
                f"Next attack: {int(self.base.attack_cooldown)}h",
                True,
                self.colors['text']
            )
            screen.blit(
                cooldown_text,
                (panel_rect.x + 10, panel_rect.y + 65)
            )
        
        # Draw NPC list (showing workers by role)
        roles = {}
        for npc in self.base.npcs:
            if npc.role in roles:
                roles[npc.role] += 1
            else:
                roles[npc.role] = 1
        
        roles_y = panel_rect.y + 85
        
        # Display role counts
        for role, count in roles.items():
            role_text = self.font_small.render(
                f"{role.name}: {count}",
                True,
                self.colors['text']
            )
            screen.blit(
                role_text,
                (panel_rect.x + 10, roles_y)
            )
            
            roles_y += 20
    
    def _render_info_panel(self, screen, panel_rect):
        """
        Render the information panel.
        
        Args:
            screen: Pygame surface to render to
            panel_rect: Rectangle for the panel
        """
        if self.selected_entity:
            if isinstance(self.selected_entity, Building):
                self._render_building_info(screen, panel_rect, self.selected_entity)
        else:
            # Draw default info
            title_text = self.font_medium.render(
                f"Base: {self.base.name}",
                True,
                self.colors['text']
            )
            screen.blit(
                title_text,
                (panel_rect.x + 10, panel_rect.y + 5)
            )
            
            # Draw prosperity
            prosperity_text = self.font_small.render(
                f"Prosperity: {int(self.base.prosperity)}",
                True,
                self.colors['text']
            )
            screen.blit(
                prosperity_text,
                (panel_rect.x + 10, panel_rect.y + 30)
            )
            
            # Draw stats
            stats_text = self.font_small.render(
                f"Buildings: {len(self.base.buildings)} | NPCs: {self.base.population} | Storage: {sum(r.max_amount for r in self.base.resources.values())}",
                True,
                self.colors['text']
            )
            screen.blit(
                stats_text,
                (panel_rect.x + 10, panel_rect.y + 50)
            )
            
            # Draw help text
            help_text = self.font_small.render(
                "Click on a building to select it. Right click to cancel.",
                True,
                self.colors['text']
            )
            screen.blit(
                help_text,
                (panel_rect.x + 10, panel_rect.y + 70)
            )
    
    def _render_building_info(self, screen, panel_rect, building):
        """
        Render building information in the info panel.
        
        Args:
            screen: Pygame surface to render to
            panel_rect: Rectangle for the panel
            building: Building instance to show info for
        """
        # Draw building type and level
        title_text = self.font_medium.render(
            f"{building.building_type.name} (Level {building.level})",
            True,
            self.colors['text']
        )
        screen.blit(
            title_text,
            (panel_rect.x + 10, panel_rect.y + 5)
        )
        
        # Draw health
        health_text = self.font_small.render(
            f"Health: {int(building.health)}/{int(building.max_health)}",
            True,
            self.colors['text']
        )
        screen.blit(
            health_text,
            (panel_rect.x + 10, panel_rect.y + 30)
        )
        
        # Draw construction progress if incomplete
        if building.construction_progress < 1.0:
            progress_text = self.font_small.render(
                f"Construction: {int(building.construction_progress * 100)}%",
                True,
                self.colors['text']
            )
            screen.blit(
                progress_text,
                (panel_rect.x + 150, panel_rect.y + 30)
            )
        
        # Draw workers
        workers_text = self.font_small.render(
            f"Workers: {building.assigned_workers}/{building._get_max_workers()}",
            True,
            self.colors['text']
        )
        screen.blit(
            workers_text,
            (panel_rect.x + 10, panel_rect.y + 50)
        )
        
        # Draw production/consumption if any
        if building.production or building.consumption:
            # Production
            if building.production:
                production_y = panel_rect.y + 70
                production_text = self.font_small.render(
                    "Production:",
                    True,
                    self.colors['text']
                )
                screen.blit(
                    production_text,
                    (panel_rect.x + 10, production_y)
                )
                
                for resource_type, rate in building.production.items():
                    if rate > 0:
                        resource_text = self.font_small.render(
                            f"{resource_type.name}: +{rate:.1f}/h",
                            True,
                            self.colors['resource'].get(resource_type, (255, 255, 255))
                        )
                        screen.blit(
                            resource_text,
                            (panel_rect.x + 100, production_y)
                        )
                        production_y += 15
            
            # Consumption
            if building.consumption:
                consumption_y = panel_rect.y + 70 + (15 * len([r for r, v in building.production.items() if v > 0]))
                consumption_text = self.font_small.render(
                    "Consumption:",
                    True,
                    self.colors['text']
                )
                screen.blit(
                    consumption_text,
                    (panel_rect.x + 10, consumption_y)
                )
                
                for resource_type, rate in building.consumption.items():
                    if rate > 0:
                        resource_text = self.font_small.render(
                            f"{resource_type.name}: -{rate:.1f}/h",
                            True,
                            self.colors['resource'].get(resource_type, (255, 255, 255))
                        )
                        screen.blit(
                            resource_text,
                            (panel_rect.x + 100, consumption_y)
                        )
                        consumption_y += 15
        
        # Draw upgrade button
        upgrade_button_rect = pygame.Rect(
            panel_rect.x + panel_rect.width - 100,
            panel_rect.y + panel_rect.height - 40,
            90,
            30
        )
        
        # Only show upgrade button for completed buildings
        if building.construction_progress >= 1.0:
            pygame.draw.rect(
                screen,
                self.colors['ui_bg'],
                upgrade_button_rect
            )
            
            pygame.draw.rect(
                screen,
                self.colors['ui_border'],
                upgrade_button_rect,
                2
            )
            
            upgrade_text = self.font_small.render(
                "Upgrade",
                True,
                self.colors['text']
            )
            text_rect = upgrade_text.get_rect(center=upgrade_button_rect.center)
            screen.blit(upgrade_text, text_rect)
            
            # Add to UI buttons
            self.ui_buttons["upgrade_building"] = upgrade_button_rect
        
        # Draw demolish button
        demolish_button_rect = pygame.Rect(
            panel_rect.x + panel_rect.width - 200,
            panel_rect.y + panel_rect.height - 40,
            90,
            30
        )
        
        pygame.draw.rect(
            screen,
            self.colors['ui_bg'],
            demolish_button_rect
        )
        
        pygame.draw.rect(
            screen,
            self.colors['ui_border'],
            demolish_button_rect,
            2
        )
        
        demolish_text = self.font_small.render(
            "Demolish",
            True,
            self.colors['text']
        )
        text_rect = demolish_text.get_rect(center=demolish_button_rect.center)
        screen.blit(demolish_text, text_rect)
        
        # Add to UI buttons
        self.ui_buttons["demolish_building"] = demolish_button_rect
    
    def _render_hover_info(self, screen):
        """
        Render information about hovered grid cell.
        
        Args:
            screen: Pygame surface to render to
        """
        if self.hover_x is None or self.hover_y is None:
            return
        
        # Draw coordinates
        coord_text = self.font_small.render(
            f"({self.hover_x}, {self.hover_y})",
            True,
            self.colors['text']
        )
        
        # Display at fixed position (top left)
        screen.blit(
            coord_text,
            (10, 50)
        )
    
    def _exit_base_building(self):
        """Exit base building mode and return to world exploration."""
        logger.info("Exiting base building mode")
        
        # Save base to persistent data
        self.state_manager.set_persistent_data("player_base", self.base.to_dict())
        
        # Return to world exploration
        self.change_state("world_exploration")
