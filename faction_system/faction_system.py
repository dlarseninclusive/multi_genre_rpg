# faction.py
from enum import Enum, auto
import json
from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple, Optional
import random

class RelationshipStatus(Enum):
    ALLIED = auto()
    FRIENDLY = auto()
    NEUTRAL = auto()
    UNFRIENDLY = auto()
    HOSTILE = auto()

class FactionType(Enum):
    GOVERNMENT = auto()
    CRIMINAL = auto()
    MERCHANT = auto()
    RELIGIOUS = auto()
    MILITARY = auto()
    GUILD = auto()
    TRIBAL = auto()

@dataclass
class Faction:
    id: str
    name: str
    faction_type: FactionType
    description: str
    primary_color: Tuple[int, int, int]
    secondary_color: Tuple[int, int, int]
    
    # Territory and control
    controlled_locations: Set[str] = field(default_factory=set)
    headquarters: Optional[str] = None
    
    # Special properties
    can_arrest: bool = False
    has_slavery: bool = False
    
    # Internal state
    is_hidden: bool = False
    power_level: int = 50  # 0-100 scale of faction power
    
    def __post_init__(self):
        # Ensure colors are valid RGB tuples
        for color in [self.primary_color, self.secondary_color]:
            assert all(0 <= c <= 255 for c in color), f"Invalid color value: {color}"
    
    def to_dict(self):
        """Convert faction to dictionary for serialization"""
        return {
            "id": self.id,
            "name": self.name,
            "faction_type": self.faction_type.name,
            "description": self.description,
            "primary_color": self.primary_color,
            "secondary_color": self.secondary_color,
            "controlled_locations": list(self.controlled_locations),
            "headquarters": self.headquarters,
            "can_arrest": self.can_arrest,
            "has_slavery": self.has_slavery,
            "is_hidden": self.is_hidden,
            "power_level": self.power_level
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create faction from dictionary data"""
        return cls(
            id=data["id"],
            name=data["name"],
            faction_type=FactionType[data["faction_type"]],
            description=data["description"],
            primary_color=tuple(data["primary_color"]),
            secondary_color=tuple(data["secondary_color"]),
            controlled_locations=set(data["controlled_locations"]),
            headquarters=data["headquarters"],
            can_arrest=data["can_arrest"],
            has_slavery=data["has_slavery"],
            is_hidden=data["is_hidden"],
            power_level=data["power_level"]
        )


class FactionManager:
    def __init__(self):
        self.factions: Dict[str, Faction] = {}
        self.relationships: Dict[Tuple[str, str], RelationshipStatus] = {}
        self.player_reputation: Dict[str, int] = {}  # -100 to 100 scale
        
        # Cache of location to controlling faction mapping
        self._location_control_cache: Dict[str, str] = {}
    
    def add_faction(self, faction: Faction) -> None:
        """Add a new faction to the game world"""
        if faction.id in self.factions:
            raise ValueError(f"Faction with ID {faction.id} already exists")
        
        self.factions[faction.id] = faction
        self.player_reputation[faction.id] = 0  # Start neutral
        
        # Set default relationships with existing factions
        for existing_id in self.factions:
            if existing_id != faction.id:
                # Default to neutral relationships
                self.set_relationship(faction.id, existing_id, RelationshipStatus.NEUTRAL)
        
        # Update location control cache
        for location in faction.controlled_locations:
            self._location_control_cache[location] = faction.id
    
    def get_faction(self, faction_id: str) -> Faction:
        """Get a faction by ID"""
        if faction_id not in self.factions:
            raise KeyError(f"Faction {faction_id} not found")
        return self.factions[faction_id]
    
    def set_relationship(self, faction1_id: str, faction2_id: str, status: RelationshipStatus) -> None:
        """Set the relationship between two factions"""
        if faction1_id not in self.factions or faction2_id not in self.factions:
            raise KeyError("One or both factions do not exist")
        
        # Store relationship both ways (symmetric)
        self.relationships[(faction1_id, faction2_id)] = status
        self.relationships[(faction2_id, faction1_id)] = status
    
    def get_relationship(self, faction1_id: str, faction2_id: str) -> RelationshipStatus:
        """Get the relationship status between two factions"""
        if (faction1_id, faction2_id) in self.relationships:
            return self.relationships[(faction1_id, faction2_id)]
        return RelationshipStatus.NEUTRAL  # Default to neutral
    
    def modify_player_reputation(self, faction_id: str, amount: int) -> int:
        """Change player's reputation with a faction and return new value"""
        if faction_id not in self.factions:
            raise KeyError(f"Faction {faction_id} not found")
        
        current = self.player_reputation.get(faction_id, 0)
        new_value = max(-100, min(100, current + amount))  # Clamp to -100 to 100 range
        self.player_reputation[faction_id] = new_value
        
        # TODO: Trigger reputation-based events here
        return new_value
    
    def get_controlling_faction(self, location_id: str) -> Optional[str]:
        """Determine which faction controls a location"""
        # Use cached value if available
        if location_id in self._location_control_cache:
            return self._location_control_cache[location_id]
        
        # Otherwise determine control
        for faction_id, faction in self.factions.items():
            if location_id in faction.controlled_locations:
                self._location_control_cache[location_id] = faction_id
                return faction_id
        
        return None  # No faction controls this location
    
    def get_factions_by_type(self, faction_type: FactionType) -> List[Faction]:
        """Get all factions of a specific type"""
        return [f for f in self.factions.values() if f.faction_type == faction_type]
    
    def get_player_faction_status(self, faction_id: str) -> RelationshipStatus:
        """Determine relationship status based on player reputation"""
        if faction_id not in self.factions:
            raise KeyError(f"Faction {faction_id} not found")
        
        rep = self.player_reputation.get(faction_id, 0)
        
        if rep >= 75:
            return RelationshipStatus.ALLIED
        elif rep >= 25:
            return RelationshipStatus.FRIENDLY
        elif rep >= -25:
            return RelationshipStatus.NEUTRAL
        elif rep >= -75:
            return RelationshipStatus.UNFRIENDLY
        else:
            return RelationshipStatus.HOSTILE
    
    def transfer_location_control(self, location_id: str, new_faction_id: str) -> None:
        """Transfer control of a location from current faction to new faction"""
        current_controller = self.get_controlling_faction(location_id)
        
        # Remove from previous controller if any
        if current_controller:
            self.factions[current_controller].controlled_locations.discard(location_id)
        
        # Add to new controller
        if new_faction_id in self.factions:
            self.factions[new_faction_id].controlled_locations.add(location_id)
            self._location_control_cache[location_id] = new_faction_id
    
    def save_to_file(self, filename: str) -> None:
        """Save faction system state to a JSON file"""
        data = {
            "factions": {f_id: faction.to_dict() for f_id, faction in self.factions.items()},
            "relationships": {f"{f1}:{f2}": status.name for (f1, f2), status in self.relationships.items()},
            "player_reputation": self.player_reputation
        }
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
    
    def load_from_file(self, filename: str) -> None:
        """Load faction system state from a JSON file"""
        with open(filename, 'r') as f:
            data = json.load(f)
        
        # Clear current state
        self.factions = {}
        self.relationships = {}
        self.player_reputation = {}
        self._location_control_cache = {}
        
        # Load factions
        for f_id, f_data in data["factions"].items():
            self.factions[f_id] = Faction.from_dict(f_data)
            
        # Load relationships
        for rel_key, status_name in data["relationships"].items():
            f1, f2 = rel_key.split(":")
            self.relationships[(f1, f2)] = RelationshipStatus[status_name]
            
        # Load player reputation
        self.player_reputation = data["player_reputation"]
        
        # Rebuild location control cache
        for faction in self.factions.values():
            for location in faction.controlled_locations:
                self._location_control_cache[location] = faction.id
