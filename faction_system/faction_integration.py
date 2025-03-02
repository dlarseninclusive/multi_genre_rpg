# faction_integration.py
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from enum import Enum, auto
import random

from faction_system.faction_system import Faction, FactionManager, FactionType, RelationshipStatus

# -----------------------------------------------------------------------------
# NPC Faction Integration
# -----------------------------------------------------------------------------

@dataclass
class NPCFactionData:
    """Faction-related data for NPCs"""
    faction_id: str
    rank: int = 1  # 1-10 scale of importance within faction
    loyalty: int = 50  # 0-100 scale of loyalty to faction
    is_leader: bool = False
    
    # History of actions and consequences
    criminal_record: Dict[str, int] = field(default_factory=dict)  # faction_id -> severity
    hidden_faction_ids: List[str] = field(default_factory=list)  # Secret faction affiliations
    
    # Relationships with other NPCs in faction
    npc_relationships: Dict[str, int] = field(default_factory=dict)  # npc_id -> relationship value

class NPCFactionIntegration:
    """Handles integration between NPCs and the faction system"""
    
    def __init__(self, faction_manager: FactionManager):
        self.faction_manager = faction_manager
        self.npc_faction_data: Dict[str, NPCFactionData] = {}  # npc_id -> faction data
    
    def add_npc_to_faction(self, npc_id: str, faction_id: str, rank: int = 1, loyalty: int = 50, 
                          is_leader: bool = False) -> None:
        """Add an NPC to a faction"""
        if faction_id not in self.faction_manager.factions:
            raise KeyError(f"Faction {faction_id} not found")
        
        if npc_id in self.npc_faction_data and self.npc_faction_data[npc_id].faction_id != faction_id:
            # NPC is changing factions - handle this case
            old_faction_id = self.npc_faction_data[npc_id].faction_id
            # Could trigger events, update reputation, etc.
        
        self.npc_faction_data[npc_id] = NPCFactionData(
            faction_id=faction_id,
            rank=max(1, min(10, rank)),  # Clamp to 1-10
            loyalty=max(0, min(100, loyalty)),  # Clamp to 0-100
            is_leader=is_leader
        )
        
        # If this NPC is a leader, ensure only one leader per faction
        if is_leader:
            for other_npc_id, data in self.npc_faction_data.items():
                if other_npc_id != npc_id and data.faction_id == faction_id and data.is_leader:
                    data.is_leader = False
    
    def add_secret_faction_affiliation(self, npc_id: str, faction_id: str) -> None:
        """Add a secret faction affiliation for an NPC (e.g., spies, double agents)"""
        if faction_id not in self.faction_manager.factions:
            raise KeyError(f"Faction {faction_id} not found")
        
        if npc_id not in self.npc_faction_data:
            raise KeyError(f"NPC {npc_id} not found in faction system")
        
        if faction_id != self.npc_faction_data[npc_id].faction_id:
            self.npc_faction_data[npc_id].hidden_faction_ids.append(faction_id)
    
    def get_npc_faction(self, npc_id: str) -> Optional[str]:
        """Get the main faction ID for an NPC"""
        if npc_id in self.npc_faction_data:
            return self.npc_faction_data[npc_id].faction_id
        return None
    
    def get_npc_rank_title(self, npc_id: str) -> str:
        """Get a descriptive rank title based on NPC's position in faction"""
        if npc_id not in self.npc_faction_data:
            return "Civilian"
        
        data = self.npc_faction_data[npc_id]
        faction = self.faction_manager.get_faction(data.faction_id)
        
        # Rank titles by faction type
        rank_titles = {
            FactionType.GOVERNMENT: [
                "Citizen", "Clerk", "Officer", "Magistrate", "Minister", 
                "Councilor", "Governor", "Chancellor", "Regent", "Sovereign"
            ],
            FactionType.CRIMINAL: [
                "Associate", "Lookout", "Soldier", "Enforcer", "Lieutenant", 
                "Captain", "Underboss", "Consigliere", "Boss", "Godfather"
            ],
            FactionType.MERCHANT: [
                "Apprentice", "Journeyman", "Merchant", "Senior Merchant", "Trader",
                "Master Trader", "Commerce Master", "Director", "Guild Master", "Commerce Lord" 
            ],
            FactionType.RELIGIOUS: [
                "Acolyte", "Initiate", "Priest", "Elder", "Keeper",
                "High Priest", "Patriarch", "Blessed One", "Prophet", "Divine Avatar"
            ],
            FactionType.MILITARY: [
                "Recruit", "Soldier", "Sergeant", "Lieutenant", "Captain",
                "Major", "Colonel", "General", "Commander", "Warlord"
            ],
            FactionType.GUILD: [
                "Apprentice", "Novice", "Journeyman", "Craftsman", "Artisan",
                "Expert", "Master Craftsman", "Guildsman", "Guild Master", "Grand Master"
            ],
            FactionType.TRIBAL: [
                "Member", "Hunter", "Warrior", "Protector", "Elder",
                "Shaman", "Sage", "Council Member", "Chief", "Great Chief"
            ]
        }
        
        # If they're a leader, always use the top title
        if data.is_leader:
            return rank_titles[faction.faction_type][-1]
        
        # Otherwise use rank-based title
        idx = min(data.rank - 1, len(rank_titles[faction.faction_type]) - 1)
        return rank_titles[faction.faction_type][idx]
    
    def get_faction_leader(self, faction_id: str) -> Optional[str]:
        """Find the NPC ID of the faction leader, if any"""
        for npc_id, data in self.npc_faction_data.items():
            if data.faction_id == faction_id and data.is_leader:
                return npc_id
        return None
    
    def get_faction_members(self, faction_id: str, min_rank: int = 1) -> List[str]:
        """Get all NPCs in a faction, optionally filtered by minimum rank"""
        members = []
        for npc_id, data in self.npc_faction_data.items():
            if data.faction_id == faction_id and data.rank >= min_rank:
                members.append(npc_id)
        return members
    
    def get_loyalty_probability(self, npc_id: str) -> float:
        """Calculate probability an NPC will follow faction orders (0.0-1.0)"""
        if npc_id not in self.npc_faction_data:
            return 0.0
        
        data = self.npc_faction_data[npc_id]
        base_probability = data.loyalty / 100.0
        
        # Adjust for rank - higher rank NPCs are more loyal
        rank_modifier = data.rank / 20.0  # 0.05 to 0.5 boost
        
        # Leaders are extremely loyal
        if data.is_leader:
            rank_modifier = 0.8
            
        # Could add other modifiers based on game state
        
        return min(1.0, base_probability + rank_modifier)
    
    def handle_faction_crime(self, npc_id: str, target_faction_id: str, 
                           severity: int) -> Tuple[bool, Dict[str, Any]]:
        """
        Handle when an NPC commits a crime against a faction
        Returns: (was_witnessed, consequences_dict)
        """
        if npc_id not in self.npc_faction_data:
            npc_faction_id = None
        else:
            npc_faction_id = self.npc_faction_data[npc_id].faction_id
        
        # Record crime in NPC's criminal record
        if npc_id in self.npc_faction_data:
            criminal_record = self.npc_faction_data[npc_id].criminal_record
            if target_faction_id in criminal_record:
                criminal_record[target_faction_id] += severity
            else:
                criminal_record[target_faction_id] = severity
        
        # Determine if crime was witnessed
        witness_chance = min(0.9, severity / 10.0)  # More severe crimes are more likely to be witnessed
        was_witnessed = random.random() < witness_chance
        
        # Determine consequences
        consequences = {
            "reputation_change": -severity,
            "bounty": severity * 10 if was_witnessed else 0,
            "faction_response": None,
            "guards_alerted": False
        }
        
        # Adjust relationships between factions if the criminal belongs to a faction
        if was_witnessed and npc_faction_id is not None and npc_faction_id != target_faction_id:
            current_rel = self.faction_manager.get_relationship(npc_faction_id, target_faction_id)
            
            # Minor crimes don't affect faction relationships as much
            if severity >= 5 and current_rel != RelationshipStatus.HOSTILE:
                # Determine new relationship based on severity
                new_rel = current_rel
                if severity >= 8:  # Major crimes
                    if current_rel == RelationshipStatus.FRIENDLY or current_rel == RelationshipStatus.ALLIED:
                        new_rel = RelationshipStatus.NEUTRAL
                    elif current_rel == RelationshipStatus.NEUTRAL:
                        new_rel = RelationshipStatus.UNFRIENDLY
                    elif current_rel == RelationshipStatus.UNFRIENDLY:
                        new_rel = RelationshipStatus.HOSTILE
                
                # Update relationship if it changed
                if new_rel != current_rel:
                    self.faction_manager.set_relationship(npc_faction_id, target_faction_id, new_rel)
                    consequences["faction_response"] = f"Relations between {npc_faction_id} and {target_faction_id} worsened to {new_rel.name}"
        
        # Determine if guards are alerted
        if was_witnessed and severity >= 3:
            target_faction = self.faction_manager.get_faction(target_faction_id)
            if target_faction.can_arrest:
                consequences["guards_alerted"] = True
        
        # Return results
        return was_witnessed, consequences
    
    def generate_faction_task(self, faction_id: str, difficulty: int = 5) -> Dict[str, Any]:
        """Generate a random task that faction might assign to a member or player"""
        faction = self.faction_manager.get_faction(faction_id)
        
        # List of possible task types based on faction type
        task_types = {
            FactionType.GOVERNMENT: ["tax_collection", "law_enforcement", "infrastructure", "diplomacy"],
            FactionType.CRIMINAL: ["theft", "smuggling", "protection", "intimidation"],
            FactionType.MERCHANT: ["trade", "acquisition", "escort", "investment"],
            FactionType.RELIGIOUS: ["conversion", "pilgrimage", "artifact", "ceremony"],
            FactionType.MILITARY: ["patrol", "training", "scouting", "defense"],
            FactionType.GUILD: ["crafting", "gathering", "training", "quality_control"],
            FactionType.TRIBAL: ["hunting", "gathering", "ritual", "defense"]
        }
        
        # Generate task details
        task_type = random.choice(task_types[faction.faction_type])
        
        # Find possible targets (other factions)
        possible_targets = []
        for other_id, other_faction in self.faction_manager.factions.items():
            if other_id != faction_id:
                rel = self.faction_manager.get_relationship(faction_id, other_id)
                # Targets depend on relationship
                if rel == RelationshipStatus.HOSTILE or rel == RelationshipStatus.UNFRIENDLY:
                    possible_targets.append(other_id)
        
        # If no hostile targets, use neutral ones for non-aggressive tasks
        if not possible_targets:
            for other_id, other_faction in self.faction_manager.factions.items():
                if other_id != faction_id:
                    rel = self.faction_manager.get_relationship(faction_id, other_id)
                    if rel == RelationshipStatus.NEUTRAL:
                        possible_targets.append(other_id)
        
        # If still no targets, just pick randomly
        if not possible_targets:
            possible_targets = [f_id for f_id in self.faction_manager.factions.keys() if f_id != faction_id]
        
        # Pick a random target
        target_faction_id = random.choice(possible_targets) if possible_targets else None
        
        # Create task data
        task = {
            "faction_id": faction_id,
            "task_type": task_type,
            "difficulty": difficulty,
            "target_faction_id": target_faction_id,
            "reward_reputation": difficulty * 5,
            "reward_gold": difficulty * 10 * random.randint(5, 15),
            "description": self._generate_task_description(faction, task_type, target_faction_id, difficulty)
        }
        
        return task
    
    def _generate_task_description(self, faction: Faction, task_type: str, 
                                  target_faction_id: Optional[str], difficulty: int) -> str:
        """Generate a description for a faction task"""
        # This would ideally be a more complex text generation system
        # For now, use templates
        
        target_name = "a rival faction"
        if target_faction_id:
            target_faction = self.faction_manager.get_faction(target_faction_id)
            target_name = target_faction.name
        
        templates = {
            "tax_collection": [
                f"Collect {difficulty * 10} gold in taxes from the citizens in our territory.",
                f"Recover unpaid taxes from merchants who are avoiding their duties."
            ],
            "law_enforcement": [
                f"Apprehend criminals associated with {target_name}.",
                f"Investigate reports of illegal activities in our territory."
            ],
            "infrastructure": [
                f"Oversee repairs to key buildings in our territory.",
                f"Secure resources needed for expanding our influence."
            ],
            "diplomacy": [
                f"Deliver a message to representatives of {target_name}.",
                f"Negotiate a trade agreement with {target_name}."
            ],
            "theft": [
                f"Steal valuable items from {target_name} without being caught.",
                f"Break into a secure location and retrieve documents for us."
            ],
            "smuggling": [
                f"Move contraband goods through {target_name}'s territory undetected.",
                f"Establish a new smuggling route for our operations."
            ],
            "protection": [
                f"Collect protection money from businesses in our territory.",
                f"Deal with anyone refusing to pay for our protection."
            ],
            "intimidation": [
                f"Send a message to {target_name} by making an example of one of their members.",
                f"Convince a local business owner to reconsider their allegiance to {target_name}."
            ],
            "trade": [
                f"Secure a trade deal with merchants from {target_name}.",
                f"Deliver valuable goods to one of our trading partners."
            ],
            "acquisition": [
                f"Acquire rare resources needed for our business ventures.",
                f"Purchase land or property that will strengthen our position against {target_name}."
            ],
            "escort": [
                f"Protect one of our caravans traveling through dangerous territory.",
                f"Ensure the safe passage of important goods through {target_name}'s territory."
            ],
            "investment": [
                f"Invest in a promising business venture to increase our influence.",
                f"Undermine {target_name}'s economic interests in the region."
            ],
            "conversion": [
                f"Spread our faith to new followers in territories controlled by {target_name}.",
                f"Establish a new shrine or temple to strengthen our presence."
            ],
            "pilgrimage": [
                f"Escort faithful followers on a pilgrimage through dangerous lands.",
                f"Recover sacred relics from an ancient site now controlled by {target_name}."
            ],
            "artifact": [
                f"Retrieve a sacred artifact that rightfully belongs to our faith.",
                f"Protect a holy relic from those who would seek to destroy it."
            ],
            "ceremony": [
                f"Prepare for an important religious ceremony by gathering necessary components.",
                f"Ensure a sacred ritual is not disrupted by agents of {target_name}."
            ],
            "patrol": [
                f"Patrol our borders to prevent incursions from {target_name}.",
                f"Clear dangerous monsters from an area under our protection."
            ],
            "training": [
                f"Train new recruits in combat techniques essential for our operations.",
                f"Test new weapons or tactics against {target_name}'s forces."
            ],
            "scouting": [
                f"Gather intelligence on {target_name}'s movements and strengths.",
                f"Map out territory that we plan to claim in the future."
            ],
            "defense": [
                f"Reinforce our defenses against expected attacks from {target_name}.",
                f"Eliminate threats to our security before they can strike."
            ],
            "crafting": [
                f"Craft specialized items that only our guild knows how to make.",
                f"Create superior goods that will outperform those made by {target_name}."
            ],
            "gathering": [
                f"Gather rare materials needed for our finest crafts.",
                f"Secure a source of materials before {target_name} can claim it."
            ],
            "quality_control": [
                f"Ensure all goods bearing our guild's mark meet our high standards.",
                f"Identify and deal with counterfeit items being produced by {target_name}."
            ],
            "hunting": [
                f"Hunt game to feed our people during the coming season.",
                f"Track and eliminate a dangerous predator threatening our territory."
            ],
            "gathering": [
                f"Gather medicinal herbs from lands claimed by {target_name}.",
                f"Collect resources from sacred grounds for an important tribal ritual."
            ],
            "ritual": [
                f"Perform a ritual to ensure good fortune for our tribe.",
                f"Conduct a ceremony to appease the spirits of our ancestors."
            ],
            "defense": [
                f"Defend our tribal lands from encroachment by {target_name}.",
                f"Prepare our warriors for possible conflict with neighboring tribes."
            ]
        }
        
        # Select a random template for the task type
        if task_type in templates and templates[task_type]:
            return random.choice(templates[task_type])
        else:
            return f"Assist {faction.name} with an important task involving {target_name}."

# -----------------------------------------------------------------------------
# Territory Control Integration
# -----------------------------------------------------------------------------

@dataclass
class TerritoryData:
    """Data for a territory controlled by a faction"""
    location_id: str
    controlling_faction_id: str
    control_level: int = 50  # 0-100 scale of how firmly controlled
    contested: bool = False
    contesting_factions: List[str] = field(default_factory=list)
    tax_rate: int = 10  # Percentage
    crime_rate: int = 5  # 0-100 scale
    prosperity: int = 50  # 0-100 scale, affects tax income
    
    # Special territory attributes
    has_guards: bool = True
    has_prison: bool = False
    has_slavery: bool = False
    
    # Resource production
    resources: Dict[str, int] = field(default_factory=dict)  # resource_type -> production value

class TerritoryManager:
    """Manages territory control and related mechanics"""
    
    def __init__(self, faction_manager: FactionManager):
        self.faction_manager = faction_manager
        self.territories: Dict[str, TerritoryData] = {}
        
        # Cache of territory resource production
        self._resource_cache: Dict[str, Dict[str, int]] = {}  # faction_id -> resource_type -> amount
    
    def add_territory(self, location_id: str, controlling_faction_id: str, 
                     control_level: int = 50, tax_rate: int = 10) -> None:
        """Add a territory under faction control"""
        if controlling_faction_id not in self.faction_manager.factions:
            raise KeyError(f"Faction {controlling_faction_id} not found")
        
        # Create territory data
        territory = TerritoryData(
            location_id=location_id,
            controlling_faction_id=controlling_faction_id,
            control_level=max(0, min(100, control_level)),
            tax_rate=max(0, min(30, tax_rate)),  # Cap tax rate at 30%
        )
        
        # Add to territories
        self.territories[location_id] = territory
        
        # Update faction's controlled locations
        faction = self.faction_manager.get_faction(controlling_faction_id)
        faction.controlled_locations.add(location_id)
        
        # Invalidate resource cache
        if controlling_faction_id in self._resource_cache:
            del self._resource_cache[controlling_faction_id]
    
    def transfer_control(self, location_id: str, new_faction_id: str, 
                        control_level: int = 30) -> None:
        """Transfer control of a territory to a new faction"""
        if location_id not in self.territories:
            raise KeyError(f"Territory {location_id} not found")
        
        if new_faction_id not in self.faction_manager.factions:
            raise KeyError(f"Faction {new_faction_id} not found")
        
        # Update territory data
        territory = self.territories[location_id]
        old_faction_id = territory.controlling_faction_id
        territory.controlling_faction_id = new_faction_id
        territory.control_level = max(0, min(100, control_level))
        territory.contested = False
        territory.contesting_factions = []
        
        # Update faction controlled locations
        old_faction = self.faction_manager.get_faction(old_faction_id)
        new_faction = self.faction_manager.get_faction(new_faction_id)
        
        old_faction.controlled_locations.discard(location_id)
        new_faction.controlled_locations.add(location_id)
        
        # Update faction manager's location control cache
        self.faction_manager.transfer_location_control(location_id, new_faction_id)
        
        # Invalidate resource cache for both factions
        for faction_id in [old_faction_id, new_faction_id]:
            if faction_id in self._resource_cache:
                del self._resource_cache[faction_id]
    
    def contest_territory(self, location_id: str, contesting_faction_id: str) -> None:
        """Mark a territory as contested by another faction"""
        if location_id not in self.territories:
            raise KeyError(f"Territory {location_id} not found")
        
        if contesting_faction_id not in self.faction_manager.factions:
            raise KeyError(f"Faction {contesting_faction_id} not found")
        
        territory = self.territories[location_id]
        
        # Can't contest your own territory
        if territory.controlling_faction_id == contesting_faction_id:
            return
        
        territory.contested = True
        if contesting_faction_id not in territory.contesting_factions:
            territory.contesting_factions.append(contesting_faction_id)
    
    def resolve_contest(self, location_id: str) -> Optional[str]:
        """
        Resolve a territory contest based on faction power and control level
        Returns faction_id of the winner or None if no change
        """
        if location_id not in self.territories:
            raise KeyError(f"Territory {location_id} not found")
        
        territory = self.territories[location_id]
        
        if not territory.contested or not territory.contesting_factions:
            return None
        
        # Get current controller details
        controlling_faction = self.faction_manager.get_faction(territory.controlling_faction_id)
        defense_strength = controlling_faction.power_level * (territory.control_level / 100)
        
        # Find strongest contender
        strongest_contender = None
        strongest_power = 0
        
        for contender_id in territory.contesting_factions:
            contender = self.faction_manager.get_faction(contender_id)
            
            # Base contender strength on faction power
            contender_strength = contender.power_level
            
            # Modify based on relationship to other factions
            for other_id, other_faction in self.faction_manager.factions.items():
                if other_id not in [territory.controlling_faction_id, contender_id]:
                    rel = self.faction_manager.get_relationship(contender_id, other_id)
                    
                    # Allied factions boost strength
                    if rel == RelationshipStatus.ALLIED:
                        contender_strength += other_faction.power_level * 0.2
            
            if contender_strength > strongest_power:
                strongest_contender = contender
                strongest_power = contender_strength
        
        # Determine if control changes
        if strongest_contender and strongest_power > defense_strength:
            # Transfer control
            self.transfer_control(location_id, strongest_contender.id, int(strongest_power - defense_strength))
            return strongest_contender.id
        
        # No change, but increase control level for successful defense
        territory.control_level = min(100, territory.control_level + 5)
        return None
    
    def update_resources(self, location_id: str, resources: Dict[str, int]) -> None:
        """Update resource production values for a territory"""
        if location_id not in self.territories:
            raise KeyError(f"Territory {location_id} not found")
        
        territory = self.territories[location_id]
        territory.resources = resources.copy()
        
        # Invalidate resource cache for controlling faction
        if territory.controlling_faction_id in self._resource_cache:
            del self._resource_cache[territory.controlling_faction_id]
    
    def calculate_faction_resources(self, faction_id: str) -> Dict[str, int]:
        """Calculate total resources produced by all territories a faction controls"""
        if faction_id in self._resource_cache:
            return self._resource_cache[faction_id].copy()
        
        total_resources = {}
        
        for location_id, territory in self.territories.items():
            if territory.controlling_faction_id == faction_id:
                for resource_type, amount in territory.resources.items():
                    if resource_type in total_resources:
                        total_resources[resource_type] += amount
                    else:
                        total_resources[resource_type] = amount
        
        # Cache the result
        self._resource_cache[faction_id] = total_resources.copy()
        return total_resources
    
    def calculate_tax_income(self, faction_id: str) -> int:
        """Calculate tax income from all territories a faction controls"""
        total_income = 0
        
        for location_id, territory in self.territories.items():
            if territory.controlling_faction_id == faction_id:
                # Base tax is prosperity * tax_rate
                base_tax = territory.prosperity * territory.tax_rate // 10
                
                # Modify based on control level - better control means better tax collection
                collection_efficiency = territory.control_level / 100
                
                # High crime reduces tax income
                crime_modifier = 1.0 - (territory.crime_rate / 200)  # Max 50% reduction
                
                territory_income = int(base_tax * collection_efficiency * crime_modifier)
                total_income += territory_income
        
        return total_income
    
    def update_territory_attributes(self, location_id: str, prosperity_change: int = 0, 
                                  crime_change: int = 0, control_change: int = 0) -> None:
        """Update territory attributes and handle the consequences"""
        if location_id not in self.territories:
            raise KeyError(f"Territory {location_id} not found")
        
        territory = self.territories[location_id]
        
        # Apply changes with bounds checking
        territory.prosperity = max(0, min(100, territory.prosperity + prosperity_change))
        territory.crime_rate = max(0, min(100, territory.crime_rate + crime_change))
        territory.control_level = max(0, min(100, territory.control_level + control_change))
        
        # Handle consequences of changes
        
        # High crime reduces prosperity
        if territory.crime_rate > 70 and random.random() < 0.2:
            territory.prosperity = max(0, territory.prosperity - random.randint(1, 3))
        
        # Low control increases crime
        if territory.control_level < 30 and random.random() < 0.3:
            territory.crime_rate = min(100, territory.crime_rate + random.randint(1, 3))
        
        # High prosperity with high taxes reduces control
        if territory.prosperity > 70 and territory.tax_rate > 20 and random.random() < 0.2:
            territory.control_level = max(0, territory.control_level - random.randint(1, 2))
        
        # Very low control might trigger territory contest
        if territory.control_level < 20 and not territory.contested and random.random() < 0.1:
            # Find a faction that might contest this territory
            for other_id, other_faction in self.faction_manager.factions.items():
                if other_id != territory.controlling_faction_id:
                    rel = self.faction_manager.get_relationship(territory.controlling_faction_id, other_id)
                    if rel in [RelationshipStatus.UNFRIENDLY, RelationshipStatus.HOSTILE]:
                        self.contest_territory(location_id, other_id)
                        break

# -----------------------------------------------------------------------------
# Crime and Law Enforcement Integration
# -----------------------------------------------------------------------------

class CrimeSeverity(Enum):
    MINOR = auto()  # Petty theft, trespassing
    MODERATE = auto()  # Assault, major theft
    SERIOUS = auto()  # Armed robbery, arson
    SEVERE = auto()  # Murder, treason, slavery crimes

@dataclass
class CrimeRecord:
    """Record of a crime committed in the game world"""
    crime_id: str
    crime_type: str
    severity: CrimeSeverity
    location_id: str
    perpetrator_id: Optional[str]  # NPC or player ID, None if unknown
    faction_id: str  # Faction against which the crime was committed
    witnesses: List[str] = field(default_factory=list)  # NPC IDs who witnessed
    bounty: int = 0
    is_solved: bool = False
    punishment_served: bool = False

class CrimeManager:
    """Manages crime, bounties, and law enforcement"""
    
    def __init__(self, faction_manager: FactionManager, npc_integration: NPCFactionIntegration):
        self.faction_manager = faction_manager
        self.npc_integration = npc_integration
        self.crimes: Dict[str, CrimeRecord] = {}
        self.bounties: Dict[str, int] = {}  # entity_id -> total bounty
        
        # Track crimes by location and faction for efficient lookup
        self._crimes_by_location: Dict[str, List[str]] = {}  # location_id -> list of crime_ids
        self._crimes_by_faction: Dict[str, List[str]] = {}  # faction_id -> list of crime_ids
        self._crimes_by_perpetrator: Dict[str, List[str]] = {}  # perpetrator_id -> list of crime_ids
    
    def report_crime(self, crime_type: str, severity: CrimeSeverity, location_id: str, 
                    faction_id: str, perpetrator_id: Optional[str] = None, 
                    witnesses: List[str] = None) -> str:
        """
        Report a crime that occurred in the game world
        Returns the crime_id
        """
        if faction_id not in self.faction_manager.factions:
            raise KeyError(f"Faction {faction_id} not found")
        
        # Generate a unique crime ID
        crime_id = f"crime_{len(self.crimes) + 1}_{crime_type}_{location_id}"
        
        # Create crime record
        crime = CrimeRecord(
            crime_id=crime_id,
            crime_type=crime_type,
            severity=severity,
            location_id=location_id,
            perpetrator_id=perpetrator_id,
            faction_id=faction_id,
            witnesses=witnesses or []
        )
        
        # Save crime record
        self.crimes[crime_id] = crime
        
        # Update lookup dictionaries
        if location_id not in self._crimes_by_location:
            self._crimes_by_location[location_id] = []
        self._crimes_by_location[location_id].append(crime_id)
        
        if faction_id not in self._crimes_by_faction:
            self._crimes_by_faction[faction_id] = []
        self._crimes_by_faction[faction_id].append(crime_id)
        
        if perpetrator_id:
            if perpetrator_id not in self._crimes_by_perpetrator:
                self._crimes_by_perpetrator[perpetrator_id] = []
            self._crimes_by_perpetrator[perpetrator_id].append(crime_id)
        
        # Set bounty if perpetrator is known and crime is witnessed
        if perpetrator_id and witnesses:
            self._set_bounty(crime, perpetrator_id)
        
        # Adjust faction reputation if perpetrator belongs to a faction
        if perpetrator_id:
            # Get perpetrator's faction if they have one
            perp_faction_id = self.npc_integration.get_npc_faction(perpetrator_id)
            
            if perp_faction_id and perp_faction_id != faction_id:
                # How much reputation is lost depends on severity
                rep_loss = {
                    CrimeSeverity.MINOR: -2,
                    CrimeSeverity.MODERATE: -5,
                    CrimeSeverity.SERIOUS: -10,
                    CrimeSeverity.SEVERE: -20
                }[severity]
                
                # Apply reputation change
                self.faction_manager.modify_player_reputation(faction_id, rep_loss)
        
        return crime_id
    
    def _set_bounty(self, crime: CrimeRecord, perpetrator_id: str) -> None:
        """Set bounty for a perpetrator based on crime severity"""
        # Base bounty values by severity
        base_bounties = {
            CrimeSeverity.MINOR: 50,
            CrimeSeverity.MODERATE: 150,
            CrimeSeverity.SERIOUS: 400,
            CrimeSeverity.SEVERE: 1000
        }
        
        # Calculate bounty based on severity and number of witnesses
        base_amount = base_bounties[crime.severity]
        witness_multiplier = min(3.0, 1.0 + (len(crime.witnesses) * 0.2))  # Max 3x for many witnesses
        bounty_amount = int(base_amount * witness_multiplier)
        
        # Update crime record
        crime.bounty = bounty_amount
        
        # Update total bounty for perpetrator
        if perpetrator_id in self.bounties:
            self.bounties[perpetrator_id] += bounty_amount
        else:
            self.bounties[perpetrator_id] = bounty_amount
    
    def get_bounty(self, entity_id: str) -> int:
        """Get the total bounty for an entity"""
        return self.bounties.get(entity_id, 0)
    
    def pay_bounty(self, entity_id: str, faction_id: str) -> int:
        """
        Pay a bounty to the capturing entity
        Returns the amount paid
        """
        if entity_id not in self.bounties or self.bounties[entity_id] <= 0:
            return 0
        
        bounty_amount = self.bounties[entity_id]
        self.bounties[entity_id] = 0
        
        # Mark relevant crimes as solved
        if entity_id in self._crimes_by_perpetrator:
            for crime_id in self._crimes_by_perpetrator[entity_id]:
                crime = self.crimes[crime_id]
                if crime.faction_id == faction_id:
                    crime.is_solved = True
        
        return bounty_amount
    
    def get_crimes_in_location(self, location_id: str, unsolved_only: bool = True) -> List[CrimeRecord]:
        """Get all crimes in a specific location"""
        if location_id not in self._crimes_by_location:
            return []
        
        result = []
        for crime_id in self._crimes_by_location[location_id]:
            crime = self.crimes[crime_id]
            if not unsolved_only or not crime.is_solved:
                result.append(crime)
        
        return result
    
    def get_crimes_against_faction(self, faction_id: str, unsolved_only: bool = True) -> List[CrimeRecord]:
        """Get all crimes against a specific faction"""
        if faction_id not in self._crimes_by_faction:
            return []
        
        result = []
        for crime_id in self._crimes_by_faction[faction_id]:
            crime = self.crimes[crime_id]
            if not unsolved_only or not crime.is_solved:
                result.append(crime)
        
        return result
    
    def get_criminal_record(self, entity_id: str) -> List[CrimeRecord]:
        """Get criminal record for an entity"""
        if entity_id not in self._crimes_by_perpetrator:
            return []
        
        return [self.crimes[crime_id] for crime_id in self._crimes_by_perpetrator[entity_id]]
    
    def add_witness(self, crime_id: str, witness_id: str) -> None:
        """Add a witness to a crime"""
        if crime_id not in self.crimes:
            raise KeyError(f"Crime {crime_id} not found")
        
        crime = self.crimes[crime_id]
        if witness_id not in crime.witnesses:
            crime.witnesses.append(witness_id)
            
            # If perpetrator is known, update bounty
            if crime.perpetrator_id:
                self._set_bounty(crime, crime.perpetrator_id)
    
    def punish_criminal(self, entity_id: str, faction_id: str) -> Dict[str, Any]:
        """
        Apply punishment for crimes against a faction
        Returns details of punishment
        """
        if faction_id not in self.faction_manager.factions:
            raise KeyError(f"Faction {faction_id} not found")
        
        faction = self.faction_manager.get_faction(faction_id)
        
        # Find crimes against this faction
        relevant_crimes = []
        if entity_id in self._crimes_by_perpetrator:
            for crime_id in self._crimes_by_perpetrator[entity_id]:
                crime = self.crimes[crime_id]
                if crime.faction_id == faction_id and not crime.punishment_served:
                    relevant_crimes.append(crime)
        
        if not relevant_crimes:
            return {"result": "no_crimes", "details": "No unpunished crimes found"}
        
        # Calculate total severity
        severities = {
            CrimeSeverity.MINOR: 1,
            CrimeSeverity.MODERATE: 3,
            CrimeSeverity.SERIOUS: 6,
            CrimeSeverity.SEVERE: 10
        }
        
        total_severity = sum(severities[crime.severity] for crime in relevant_crimes)
        
        # Determine punishment based on faction type and total severity
        punishment = {"gold_fine": 0, "jail_time": 0, "enslavement": False, "reputation_change": 0}
        
        # Government and military factions use jail time
        if faction.faction_type in [FactionType.GOVERNMENT, FactionType.MILITARY]:
            punishment["gold_fine"] = total_severity * 50
            punishment["jail_time"] = total_severity * 4  # Hours
        
        # Criminal factions might enslave for serious crimes
        elif faction.faction_type == FactionType.CRIMINAL and faction.has_slavery and total_severity >= 10:
            punishment["enslavement"] = True
        
        # Merchant factions use heavy fines
        elif faction.faction_type == FactionType.MERCHANT:
            punishment["gold_fine"] = total_severity * 100
        
        # Religious factions use a mix of fines and penalties
        elif faction.faction_type == FactionType.RELIGIOUS:
            punishment["gold_fine"] = total_severity * 30
            punishment["reputation_change"] = -total_severity * 2
        
        # Tribal factions have their own justice systems
        elif faction.faction_type == FactionType.TRIBAL:
            if faction.has_slavery and total_severity >= 15:
                punishment["enslavement"] = True
            else:
                punishment["gold_fine"] = total_severity * 40
                punishment["reputation_change"] = -total_severity
        
        # Guild factions focus on reputation and fines
        elif faction.faction_type == FactionType.GUILD:
            punishment["gold_fine"] = total_severity * 70
            punishment["reputation_change"] = -total_severity
        
        # Mark crimes as punished
        for crime in relevant_crimes:
            crime.punishment_served = True
        
        # Clear bounty
        if entity_id in self.bounties:
            self.bounties[entity_id] = 0
        
        # Apply reputation change
        if punishment["reputation_change"] != 0:
            self.faction_manager.modify_player_reputation(faction_id, punishment["reputation_change"])
        
        punishment["result"] = "punishment_applied"
        punishment["details"] = f"Punished for {len(relevant_crimes)} crimes with total severity {total_severity}"
        
        return punishment

# -----------------------------------------------------------------------------
# Faction System Integration (Main Class)
# -----------------------------------------------------------------------------

class FactionSystemIntegration:
    """Main integration class that combines all faction-related systems"""
    
    def __init__(self):
        # Create component systems
        self.faction_manager = FactionManager()
        self.npc_integration = NPCFactionIntegration(self.faction_manager)
        self.territory_manager = TerritoryManager(self.faction_manager)
        self.crime_manager = CrimeManager(self.faction_manager, self.npc_integration)
    
    def initialize_default_factions(self):
        """Initialize the system with default factions"""
        from faction_system.faction_generator import FactionGenerator
        self.faction_manager = FactionGenerator.generate_default_factions()
        
        # Update references in other components
        self.npc_integration.faction_manager = self.faction_manager
        self.territory_manager.faction_manager = self.faction_manager
        self.crime_manager.faction_manager = self.faction_manager
    
    def save_state(self, save_dir: str):
        """Save all faction system state to files"""
        import os
        import json
        
        # Create save directory if it doesn't exist
        os.makedirs(save_dir, exist_ok=True)
        
        # Save faction data
        self.faction_manager.save_to_file(os.path.join(save_dir, "factions.json"))
        
        # Save NPC faction data
        npc_data = {
            npc_id: {
                "faction_id": data.faction_id,
                "rank": data.rank,
                "loyalty": data.loyalty,
                "is_leader": data.is_leader,
                "criminal_record": data.criminal_record,
                "hidden_faction_ids": data.hidden_faction_ids,
                "npc_relationships": data.npc_relationships
            }
            for npc_id, data in self.npc_integration.npc_faction_data.items()
        }
        
        with open(os.path.join(save_dir, "npc_factions.json"), 'w') as f:
            json.dump(npc_data, f, indent=2)
        
        # Save territory data
        territory_data = {
            location_id: {
                "controlling_faction_id": territory.controlling_faction_id,
                "control_level": territory.control_level,
                "contested": territory.contested,
                "contesting_factions": territory.contesting_factions,
                "tax_rate": territory.tax_rate,
                "crime_rate": territory.crime_rate,
                "prosperity": territory.prosperity,
                "has_guards": territory.has_guards,
                "has_prison": territory.has_prison,
                "has_slavery": territory.has_slavery,
                "resources": territory.resources
            }
            for location_id, territory in self.territory_manager.territories.items()
        }
        
        with open(os.path.join(save_dir, "territories.json"), 'w') as f:
            json.dump(territory_data, f, indent=2)
        
        # Save crime data
        crime_data = {
            crime_id: {
                "crime_type": crime.crime_type,
                "severity": crime.severity.name,
                "location_id": crime.location_id,
                "perpetrator_id": crime.perpetrator_id,
                "faction_id": crime.faction_id,
                "witnesses": crime.witnesses,
                "bounty": crime.bounty,
                "is_solved": crime.is_solved,
                "punishment_served": crime.punishment_served
            }
            for crime_id, crime in self.crime_manager.crimes.items()
        }
        
        with open(os.path.join(save_dir, "crimes.json"), 'w') as f:
            json.dump(crime_data, f, indent=2)
        
        # Save bounties
        with open(os.path.join(save_dir, "bounties.json"), 'w') as f:
            json.dump(self.crime_manager.bounties, f, indent=2)
    
    def load_state(self, save_dir: str):
        """Load all faction system state from files"""
        import os
        import json
        
        # Load faction data
        self.faction_manager.load_from_file(os.path.join(save_dir, "factions.json"))
        
        # Update references in other components
        self.npc_integration.faction_manager = self.faction_manager
        self.territory_manager.faction_manager = self.faction_manager
        self.crime_manager.faction_manager = self.faction_manager
        
        # Load NPC faction data
        with open(os.path.join(save_dir, "npc_factions.json"), 'r') as f:
            npc_data = json.load(f)
        
        for npc_id, data in npc_data.items():
            self.npc_integration.npc_faction_data[npc_id] = NPCFactionData(
                faction_id=data["faction_id"],
                rank=data["rank"],
                loyalty=data["loyalty"],
                is_leader=data["is_leader"],
                criminal_record=data["criminal_record"],
                hidden_faction_ids=data["hidden_faction_ids"],
                npc_relationships=data["npc_relationships"]
            )
        
        # Load territory data
        with open(os.path.join(save_dir, "territories.json"), 'r') as f:
            territory_data = json.load(f)
        
        for location_id, data in territory_data.items():
            self.territory_manager.territories[location_id] = TerritoryData(
                location_id=location_id,
                controlling_faction_id=data["controlling_faction_id"],
                control_level=data["control_level"],
                contested=data["contested"],
                contesting_factions=data["contesting_factions"],
                tax_rate=data["tax_rate"],
                crime_rate=data["crime_rate"],
                prosperity=data["prosperity"],
                has_guards=data["has_guards"],
                has_prison=data["has_prison"],
                has_slavery=data["has_slavery"],
                resources=data["resources"]
            )
        
        # Load crime data
        with open(os.path.join(save_dir, "crimes.json"), 'r') as f:
            crime_data = json.load(f)
        
        for crime_id, data in crime_data.items():
            crime = CrimeRecord(
                crime_id=crime_id,
                crime_type=data["crime_type"],
                severity=CrimeSeverity[data["severity"]],
                location_id=data["location_id"],
                perpetrator_id=data["perpetrator_id"],
                faction_id=data["faction_id"],
                witnesses=data["witnesses"],
                bounty=data["bounty"],
                is_solved=data["is_solved"],
                punishment_served=data["punishment_served"]
            )
            
            self.crime_manager.crimes[crime_id] = crime
            
            # Rebuild lookup dictionaries
            if crime.location_id not in self.crime_manager._crimes_by_location:
                self.crime_manager._crimes_by_location[crime.location_id] = []
            self.crime_manager._crimes_by_location[crime.location_id].append(crime_id)
            
            if crime.faction_id not in self.crime_manager._crimes_by_faction:
                self.crime_manager._crimes_by_faction[crime.faction_id] = []
            self.crime_manager._crimes_by_faction[crime.faction_id].append(crime_id)
            
            if crime.perpetrator_id:
                if crime.perpetrator_id not in self.crime_manager._crimes_by_perpetrator:
                    self.crime_manager._crimes_by_perpetrator[crime.perpetrator_id] = []
                self.crime_manager._crimes_by_perpetrator[crime.perpetrator_id].append(crime_id)
        
        # Load bounties
        with open(os.path.join(save_dir, "bounties.json"), 'r') as f:
            self.crime_manager.bounties = json.load(f)
    
    def update(self, game_time):
        """Update faction system state based on game time"""
        # Update territory control
        self._update_territories(game_time)
        
        # Update faction relationships
        self._update_faction_relationships(game_time)
    
    def _update_territories(self, game_time):
        """Update territory control and resolve contests"""
        # Only update every in-game day
        if game_time.hour == 0 and game_time.minute == 0:
            # Resolve contested territories
            for location_id, territory in list(self.territory_manager.territories.items()):
                if territory.contested:
                    self.territory_manager.resolve_contest(location_id)
            
            # Natural territory changes
            for location_id, territory in list(self.territory_manager.territories.items()):
                # Random prosperity changes
                prosperity_change = random.randint(-2, 3)
                
                # Crime rate slowly decreases in high-control areas
                crime_change = -1 if territory.control_level > 70 and territory.crime_rate > 10 else 0
                
                # Control level might change based on random events
                control_change = 0
                
                # Apply changes
                self.territory_manager.update_territory_attributes(
                    location_id, prosperity_change, crime_change, control_change
                )
    
    def _update_faction_relationships(self, game_time):
        """Update relationships between factions over time"""
        # Only update relationships occasionally
        if game_time.day % 7 == 0 and game_time.hour == 0 and game_time.minute == 0:
            factions = list(self.faction_manager.factions.values())
            
            # Randomly select some faction pairs to update
            pairs_to_update = min(len(factions) // 2, 3)
            
            for _ in range(pairs_to_update):
                # Pick two random factions
                f1 = random.choice(factions)
                f2 = random.choice([f for f in factions if f.id != f1.id])
                
                # Get current relationship
                current_rel = self.faction_manager.get_relationship(f1.id, f2.id)
                
                # Determine if relationship should change
                should_change = random.random() < 0.3  # 30% chance
                
                if should_change:
                    # List possible relationships in order
                    rel_order = [
                        RelationshipStatus.HOSTILE,
                        RelationshipStatus.UNFRIENDLY,
                        RelationshipStatus.NEUTRAL,
                        RelationshipStatus.FRIENDLY,
                        RelationshipStatus.ALLIED
                    ]
                    
                    current_idx = rel_order.index(current_rel)
                    
                    # Determine direction of change (more likely to worsen than improve)
                    if random.random() < 0.6:  # 60% chance to worsen
                        new_idx = max(0, current_idx - 1)
                    else:  # 40% chance to improve
                        new_idx = min(len(rel_order) - 1, current_idx + 1)
                    
                    new_rel = rel_order[new_idx]
                    
                    # Only update if relationship actually changed
                    if new_rel != current_rel:
                        self.faction_manager.set_relationship(f1.id, f2.id, new_rel)
    
    def handle_player_faction_interaction(self, player, faction_id, interaction_type, **kwargs):
        """Handle player interactions with factions and their consequences"""
        if faction_id not in self.faction_manager.factions:
            raise KeyError(f"Faction {faction_id} not found")
        
        faction = self.faction_manager.get_faction(faction_id)
        current_rep = self.faction_manager.player_reputation.get(faction_id, 0)
        
        result = {
            "success": False,
            "reputation_change": 0,
            "message": "",
            "rewards": {}
        }
        
        # Handle different interaction types
        if interaction_type == "quest_complete":
            quest_id = kwargs.get("quest_id")
            difficulty = kwargs.get("difficulty", 5)
            
            # Calculate reputation gain
            rep_gain = difficulty * 3
            
            # Apply reputation change
            new_rep = self.faction_manager.modify_player_reputation(faction_id, rep_gain)
            
            result.update({
                "success": True,
                "reputation_change": rep_gain,
                "message": f"Quest completed for {faction.name}. Reputation increased.",
                "rewards": {
                    "gold": difficulty * random.randint(10, 20),
                    "items": []  # Would contain actual items in real implementation
                }
            })
        
        elif interaction_type == "crime_committed":
            severity = kwargs.get("severity", CrimeSeverity.MINOR)
            location_id = kwargs.get("location_id", "unknown")
            crime_type = kwargs.get("crime_type", "theft")
            witnesses = kwargs.get("witnesses", [])
            
            # Create crime record
            crime_id = self.crime_manager.report_crime(
                crime_type=crime_type,
                severity=severity,
                location_id=location_id,
                faction_id=faction_id,
                perpetrator_id=player.id,
                witnesses=witnesses
            )
            
            # Calculate reputation loss based on severity
            severity_values = {
                CrimeSeverity.MINOR: 5,
                CrimeSeverity.MODERATE: 10,
                CrimeSeverity.SERIOUS: 20,
                CrimeSeverity.SEVERE: 40
            }
            
            rep_loss = -severity_values[severity]
            
            # Apply reputation change
            new_rep = self.faction_manager.modify_player_reputation(faction_id, rep_loss)
            
            # Get bounty
            bounty = self.crime_manager.get_bounty(player.id)
            
            result.update({
                "success": True,
                "reputation_change": rep_loss,
                "message": f"Crime reported against {faction.name}. Reputation decreased.",
                "bounty": bounty,
                "witnesses": len(witnesses)
            })
        
        elif interaction_type == "turn_self_in":
            # Apply punishment
            punishment = self.crime_manager.punish_criminal(player.id, faction_id)
            
            # Small reputation gain for turning self in
            rep_gain = 5 if punishment["result"] == "punishment_applied" else 0
            new_rep = self.faction_manager.modify_player_reputation(faction_id, rep_gain)
            
            result.update({
                "success": punishment["result"] == "punishment_applied",
                "reputation_change": rep_gain,
                "message": punishment["details"],
                "punishment": punishment
            })
        
        elif interaction_type == "join_faction":
            min_rep_to_join = 50
            
            if current_rep >= min_rep_to_join:
                # Add player to faction at low rank
                self.npc_integration.add_npc_to_faction(
                    npc_id=player.id,
                    faction_id=faction_id,
                    rank=1,
                    loyalty=50
                )
                
                result.update({
                    "success": True,
                    "message": f"You have joined {faction.name} as a {self.npc_integration.get_npc_rank_title(player.id)}.",
                    "rank": 1
                })
            else:
                result.update({
                    "success": False,
                    "message": f"{faction.name} does not accept you yet. Improve your reputation with them first.",
                    "required_reputation": min_rep_to_join,
                    "current_reputation": current_rep
                })
        
        elif interaction_type == "leave_faction":
            if self.npc_integration.get_npc_faction(player.id) == faction_id:
                # Check if leaving on good terms
                loyalty = self.npc_integration.npc_faction_data[player.id].loyalty
                
                # Remove from faction
                del self.npc_integration.npc_faction_data[player.id]
                
                # Reputation penalty depends on loyalty
                rep_change = -max(0, (loyalty // 10))
                new_rep = self.faction_manager.modify_player_reputation(faction_id, rep_change)
                
                result.update({
                    "success": True,
                    "reputation_change": rep_change,
                    "message": f"You have left {faction.name}.",
                })
            else:
                result.update({
                    "success": False,
                    "message": f"You are not a member of {faction.name}."
                })
        
        elif interaction_type == "promote":
            if self.npc_integration.get_npc_faction(player.id) == faction_id:
                current_rank = self.npc_integration.npc_faction_data[player.id].rank
                
                if current_rank < 10:
                    # Promote player
                    self.npc_integration.npc_faction_data[player.id].rank += 1
                    new_rank = self.npc_integration.npc_faction_data[player.id].rank
                    
                    result.update({
                        "success": True,
                        "message": f"You have been promoted to {self.npc_integration.get_npc_rank_title(player.id)} in {faction.name}.",
                        "old_rank": current_rank,
                        "new_rank": new_rank
                    })
                else:
                    result.update({
                        "success": False,
                        "message": f"You have already reached the highest rank in {faction.name}."
                    })
            else:
                result.update({
                    "success": False,
                    "message": f"You are not a member of {faction.name}."
                })
        
        elif interaction_type == "donate":
            amount = kwargs.get("amount", 0)
            
            if amount > 0:
                # Calculate reputation gain (diminishing returns)
                rep_gain = min(20, max(1, amount // 50))
                
                # Apply reputation change
                new_rep = self.faction_manager.modify_player_reputation(faction_id, rep_gain)
                
                result.update({
                    "success": True,
                    "reputation_change": rep_gain,
                    "message": f"You donated {amount} gold to {faction.name}. Reputation increased.",
                })
            else:
                result.update({
                    "success": False,
                    "message": "Invalid donation amount."
                })
        
        return result

    def get_faction_task(self, faction_id, player_rank=1):
        """Get a task for the player from a faction"""
        if faction_id not in self.faction_manager.factions:
            raise KeyError(f"Faction {faction_id} not found")
        
        # Task difficulty scales with player rank
        difficulty = min(10, player_rank + 2)
        
        # Generate the task
        return self.npc_integration.generate_faction_task(faction_id, difficulty)
    
    def complete_faction_task(self, task, success=True):
        """Handle completion of a faction task"""
        faction_id = task["faction_id"]
        
        if faction_id not in self.faction_manager.factions:
            raise KeyError(f"Faction {faction_id} not found")
        
        result = {
            "reputation_change": 0,
            "gold_reward": 0,
            "message": ""
        }
        
        if success:
            # Apply reputation gain
            rep_gain = task["reward_reputation"]
            new_rep = self.faction_manager.modify_player_reputation(faction_id, rep_gain)
            
            # Gold reward
            gold_reward = task["reward_gold"]
            
            result.update({
                "reputation_change": rep_gain,
                "gold_reward": gold_reward,
                "message": f"Task completed successfully for {self.faction_manager.factions[faction_id].name}."
            })
        else:
            # Reputation penalty for failure
            rep_loss = -task["reward_reputation"] // 2
            new_rep = self.faction_manager.modify_player_reputation(faction_id, rep_loss)
            
            result.update({
                "reputation_change": rep_loss,
                "gold_reward": 0,
                "message": f"Task failed for {self.faction_manager.factions[faction_id].name}."
            })
        
        return result


# Example usage
if __name__ == "__main__":
    import time
    from datetime import datetime
    
    # Create integration
    integration = FactionSystemIntegration()
    
    # Initialize default factions
    integration.initialize_default_factions()
    
    # Print faction info
    print("Generated Factions:")
    for faction_id, faction in integration.faction_manager.factions.items():
        print(f"- {faction.name} ({faction.faction_type.name})")
        print(f"  Description: {faction.description}")
        print()
    
    # Add territories
    print("\nAdding territories...")
    for i, faction in enumerate(integration.faction_manager.factions.values()):
        for j in range(2):  # Add 2 territories per faction
            territory_id = f"territory_{i}_{j}"
            integration.territory_manager.add_territory(
                location_id=territory_id,
                controlling_faction_id=faction.id,
                control_level=random.randint(40, 80),
                tax_rate=random.randint(5, 15)
            )
            print(f"Added {territory_id} under control of {faction.name}")
    
    # Add NPCs
    print("\nAdding NPCs to factions...")
    for i, faction in enumerate(integration.faction_manager.factions.values()):
        # Add a leader
        leader_id = f"npc_leader_{i}"
        integration.npc_integration.add_npc_to_faction(
            npc_id=leader_id,
            faction_id=faction.id,
            rank=10,
            loyalty=90,
            is_leader=True
        )
        print(f"Added {leader_id} as leader of {faction.name}")
        
        # Add some members
        for j in range(5):
            member_id = f"npc_member_{i}_{j}"
            integration.npc_integration.add_npc_to_faction(
                npc_id=member_id,
                faction_id=faction.id,
                rank=random.randint(1, 8),
                loyalty=random.randint(50, 90)
            )
            print(f"Added {member_id} to {faction.name}")
    
    # Simulate some crimes
    print("\nSimulating crimes...")
    for i in range(5):
        criminal_id = f"criminal_{i}"
        victim_faction = random.choice(list(integration.faction_manager.factions.values()))
        crime_location = random.choice(list(integration.territory_manager.territories.keys()))
        severity = random.choice(list(CrimeSeverity))
        
        witnesses = []
        if random.random() < 0.7:  # 70% chance of witnesses
            for j in range(random.randint(1, 3)):
                witnesses.append(f"witness_{i}_{j}")
        
        crime_id = integration.crime_manager.report_crime(
            crime_type="theft",
            severity=severity,
            location_id=crime_location,
            faction_id=victim_faction.id,
            perpetrator_id=criminal_id,
            witnesses=witnesses
        )
        
        print(f"Crime reported: {severity.name} theft by {criminal_id} against {victim_faction.name}")
        
        # Check bounty
        if witnesses:
            bounty = integration.crime_manager.get_bounty(criminal_id)
            print(f"  Bounty set: {bounty} gold")
    
    # Save state
    print("\nSaving state...")
    integration.save_state("faction_save")
    
    # Simulate time passing
    print("\nSimulating time passage and updates...")
    game_time = datetime.now()
    
    for _ in range(3):
        # Advance time by a day
        game_time = datetime.fromtimestamp(game_time.timestamp() + 86400)
        
        # Update faction system
        integration.update(game_time)
        print(f"Updated to game time: {game_time}")
        
        # Check territory status
        contested = [t for t in integration.territory_manager.territories.values() if t.contested]
        if contested:
            print(f"  {len(contested)} territories are currently contested")
        
        # Report resource production
        for faction_id, faction in integration.faction_manager.factions.items():
            resources = integration.territory_manager.calculate_faction_resources(faction_id)
            if resources:
                print(f"  {faction.name} is producing: {resources}")
            
            tax_income = integration.territory_manager.calculate_tax_income(faction_id)
            print(f"  {faction.name} tax income: {tax_income} gold")
    
    print("\nFaction System Integration Test Complete")
