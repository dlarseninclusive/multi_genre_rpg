# slavery_system.py
from typing import Dict, List, Tuple, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum, auto
import random
import uuid

from faction_system.faction_system import Faction, FactionManager, FactionType, RelationshipStatus
from faction_system.faction_integration import FactionSystemIntegration, CrimeSeverity, NPCFactionData

class SlaveType(Enum):
    LABOR = auto()      # Manual labor (mining, farming, etc.)
    DOMESTIC = auto()   # Household work
    GLADIATOR = auto()  # Fighting for entertainment
    SKILLED = auto()    # Craftsmen, scholars, etc.
    PLEASURE = auto()   # Adult-appropriate abstraction

@dataclass
class SlaveData:
    """Data for a slave in the game world"""
    slave_id: str
    original_entity_id: str  # NPC or player ID before enslavement
    owner_id: str  # Faction or NPC ID
    slave_type: SlaveType
    value: int  # Base market value
    skills: Dict[str, int] = field(default_factory=dict)  # skill_name -> level
    health: int = 100  # 0-100 scale
    morale: int = 50  # 0-100 scale
    escape_attempts: int = 0
    days_enslaved: int = 0
    
    # Special attributes
    is_branded: bool = False  # Makes escaped slaves more recognizable
    is_chained: bool = False  # Reduces escape chance but lowers productivity
    is_for_sale: bool = False

class SlaveMarket:
    """Represents a slave market in a specific location"""
    def __init__(self, location_id: str, controlling_faction_id: str):
        self.location_id = location_id
        self.controlling_faction_id = controlling_faction_id
        self.slaves_for_sale: List[str] = []  # List of slave_ids
        self.tax_rate: int = 10  # Percentage tax on sales
        
        # Market prices fluctuate
        self.price_modifier: float = 1.0  # Base price multiplier
    
    def update_price_modifier(self):
        """Update market price modifier based on random factors"""
        # Fluctuate between 0.8 and 1.2
        self.price_modifier = 0.8 + (random.random() * 0.4)

class SlaveSystem:
    """Manages slavery mechanics in the game world"""
    
    def __init__(self, faction_integration: FactionSystemIntegration):
        self.faction_integration = faction_integration
        self.slaves: Dict[str, SlaveData] = {}
        self.markets: Dict[str, SlaveMarket] = {}
        
        # Track slave ownership
        self.faction_slaves: Dict[str, Set[str]] = {}  # faction_id -> set of slave_ids
        self.npc_slaves: Dict[str, Set[str]] = {}  # npc_id -> set of slave_ids
        
        # Slave escape tracking
        self.escaped_slaves: Dict[str, str] = {}  # slave_id -> location_id where they escaped to
    
    def enslave_entity(self, entity_id: str, owner_id: str, slave_type: SlaveType = None, 
                      reason: str = "crime") -> Optional[str]:
        """
        Enslave an entity (NPC or player)
        Returns slave_id if successful, None otherwise
        """
        # Check if entity is already a slave
        for slave in self.slaves.values():
            if slave.original_entity_id == entity_id:
                return None
        
        # Determine owner validity
        owner_is_faction = owner_id in self.faction_integration.faction_manager.factions
        owner_is_npc = owner_id in self.faction_integration.npc_integration.npc_faction_data
        
        if not (owner_is_faction or owner_is_npc):
            return None
        
        # If owner is a faction, check if they allow slavery
        if owner_is_faction:
            faction = self.faction_integration.faction_manager.get_faction(owner_id)
            if not faction.has_slavery:
                return None
        
        # If owner is an NPC, check their faction
        if owner_is_npc:
            npc_faction_id = self.faction_integration.npc_integration.get_npc_faction(owner_id)
            if npc_faction_id:
                faction = self.faction_integration.faction_manager.get_faction(npc_faction_id)
                if not faction.has_slavery:
                    return None
        
        # Determine slave type if not specified
        if slave_type is None:
            # Try to base it on entity skills (would use actual entity data in real implementation)
            slave_type = random.choice(list(SlaveType))
        
        # Generate slave ID
        slave_id = f"slave_{uuid.uuid4().hex[:8]}"
        
        # Determine base value based on type and random factors
        base_values = {
            SlaveType.LABOR: random.randint(50, 150),
            SlaveType.DOMESTIC: random.randint(100, 200),
            SlaveType.GLADIATOR: random.randint(200, 500),
            SlaveType.SKILLED: random.randint(300, 800),
            SlaveType.PLEASURE: random.randint(200, 600)
        }
        
        value = base_values[slave_type]
        
        # Create slave data
        slave = SlaveData(
            slave_id=slave_id,
            original_entity_id=entity_id,
            owner_id=owner_id,
            slave_type=slave_type,
            value=value,
            # Initial attributes
            morale=30 if reason == "crime" else 50,  # Lower morale if enslaved for crime
            health=random.randint(70, 100)
        )
        
        # Store slave data
        self.slaves[slave_id] = slave
        
        # Update ownership tracking
        if owner_is_faction:
            if owner_id not in self.faction_slaves:
                self.faction_slaves[owner_id] = set()
            self.faction_slaves[owner_id].add(slave_id)
        else:  # owner is NPC
            if owner_id not in self.npc_slaves:
                self.npc_slaves[owner_id] = set()
            self.npc_slaves[owner_id].add(slave_id)
        
        return slave_id
    
    def free_slave(self, slave_id: str, reason: str = "purchased_freedom") -> bool:
        """
        Free a slave
        Returns True if successful
        """
        if slave_id not in self.slaves:
            return False
        
        slave = self.slaves[slave_id]
        
        # Remove from ownership tracking
        owner_id = slave.owner_id
        
        if owner_id in self.faction_slaves and slave_id in self.faction_slaves[owner_id]:
            self.faction_slaves[owner_id].remove(slave_id)
        
        elif owner_id in self.npc_slaves and slave_id in self.npc_slaves[owner_id]:
            self.npc_slaves[owner_id].remove(slave_id)
        
        # Remove from any markets
        for market in self.markets.values():
            if slave_id in market.slaves_for_sale:
                market.slaves_for_sale.remove(slave_id)
        
        # Handle different freedom reasons
        if reason == "escaped":
            # Track escaped slave
            self.escaped_slaves[slave_id] = "unknown"  # Would be set to actual location
        else:
            # For legitimate freedom, remove slave data entirely
            del self.slaves[slave_id]
        
        return True
    
    def transfer_ownership(self, slave_id: str, new_owner_id: str) -> bool:
        """
        Transfer ownership of a slave to a new owner
        Returns True if successful
        """
        if slave_id not in self.slaves:
            return False
        
        # Check if new owner is valid
        owner_is_faction = new_owner_id in self.faction_integration.faction_manager.factions
        owner_is_npc = new_owner_id in self.faction_integration.npc_integration.npc_faction_data
        
        if not (owner_is_faction or owner_is_npc):
            return False
        
        # If owner is a faction, check if they allow slavery
        if owner_is_faction:
            faction = self.faction_integration.faction_manager.get_faction(new_owner_id)
            if not faction.has_slavery:
                return False
        
        # If owner is an NPC, check their faction
        if owner_is_npc:
            npc_faction_id = self.faction_integration.npc_integration.get_npc_faction(new_owner_id)
            if npc_faction_id:
                faction = self.faction_integration.faction_manager.get_faction(npc_faction_id)
                if not faction.has_slavery:
                    return False
        
        slave = self.slaves[slave_id]
        old_owner_id = slave.owner_id
        
        # Remove from old owner
        if old_owner_id in self.faction_slaves and slave_id in self.faction_slaves[old_owner_id]:
            self.faction_slaves[old_owner_id].remove(slave_id)
        elif old_owner_id in self.npc_slaves and slave_id in self.npc_slaves[old_owner_id]:
            self.npc_slaves[old_owner_id].remove(slave_id)
        
        # Update slave owner
        slave.owner_id = new_owner_id
        
        # Add to new owner
        if owner_is_faction:
            if new_owner_id not in self.faction_slaves:
                self.faction_slaves[new_owner_id] = set()
            self.faction_slaves[new_owner_id].add(slave_id)
        else:  # owner is NPC
            if new_owner_id not in self.npc_slaves:
                self.npc_slaves[new_owner_id] = set()
            self.npc_slaves[new_owner_id].add(slave_id)
        
        # Adjust morale for transfer
        slave.morale = max(10, slave.morale - 10)
        
        return True
    
    def attempt_escape(self, slave_id: str) -> Tuple[bool, str]:
        """
        Attempt to escape slavery
        Returns (success, message)
        """
        if slave_id not in self.slaves:
            return (False, "Invalid slave ID")
        
        slave = self.slaves[slave_id]
        slave.escape_attempts += 1
        
        # Base escape chance depends on health and morale
        base_chance = (slave.health + slave.morale) / 200  # 0.1 to 1.0
        
        # Adjustments
        if slave.is_chained:
            base_chance *= 0.5
        
        if slave.is_branded:
            base_chance *= 0.7
        
        # More difficult to escape with each failed attempt
        attempt_penalty = min(0.5, slave.escape_attempts * 0.1)
        escape_chance = max(0.05, base_chance - attempt_penalty)
        
        # Determine if escape succeeds
        success = random.random() < escape_chance
        
        if success:
            # Handle successful escape
            self.free_slave(slave_id, reason="escaped")
            return (True, "Escaped successfully")
        else:
            # Handle failed escape
            slave.morale = max(10, slave.morale - 20)
            slave.health = max(10, slave.health - 10)
            
            # Increase chance of being branded or chained
            if not slave.is_branded and random.random() < 0.3:
                slave.is_branded = True
                return (False, "Escape failed. You have been branded to mark you as a flight risk.")
            
            if not slave.is_chained and random.random() < 0.3:
                slave.is_chained = True
                return (False, "Escape failed. You have been chained to prevent further escape attempts.")
            
            return (False, "Escape failed. You have been punished and your conditions have worsened.")
    
    def create_market(self, location_id: str, controlling_faction_id: str) -> bool:
        """
        Create a slave market at a location
        Returns True if successful
        """
        if location_id in self.markets:
            return False
        
        # Check if faction allows slavery
        if controlling_faction_id not in self.faction_integration.faction_manager.factions:
            return False
        
        faction = self.faction_integration.faction_manager.get_faction(controlling_faction_id)
        if not faction.has_slavery:
            return False
        
        # Create market
        self.markets[location_id] = SlaveMarket(location_id, controlling_faction_id)
        return True
    
    def add_slave_to_market(self, slave_id: str, market_location_id: str) -> bool:
        """
        Put a slave up for sale at a market
        Returns True if successful
        """
        if slave_id not in self.slaves or market_location_id not in self.markets:
            return False
        
        slave = self.slaves[slave_id]
        market = self.markets[market_location_id]
        
        # Only the owner can sell a slave
        if slave.owner_id != market.controlling_faction_id and not self._is_authorized_agent(slave.owner_id, market.controlling_faction_id):
            return False
        
        # Mark slave for sale
        slave.is_for_sale = True
        
        # Add to market
        if slave_id not in market.slaves_for_sale:
            market.slaves_for_sale.append(slave_id)
        
        return True
    
    def _is_authorized_agent(self, npc_id: str, faction_id: str) -> bool:
        """Check if an NPC is authorized to act on behalf of a faction"""
        npc_faction_id = self.faction_integration.npc_integration.get_npc_faction(npc_id)
        return npc_faction_id == faction_id
    
    def remove_slave_from_market(self, slave_id: str, market_location_id: str) -> bool:
        """
        Remove a slave from sale at a market
        Returns True if successful
        """
        if slave_id not in self.slaves or market_location_id not in self.markets:
            return False
        
        market = self.markets[market_location_id]
        
        if slave_id in market.slaves_for_sale:
            market.slaves_for_sale.remove(slave_id)
            
            # Update slave status
            self.slaves[slave_id].is_for_sale = False
            
            return True
        
        return False
    
    def get_market_price(self, slave_id: str, market_location_id: str) -> int:
        """Calculate the market price for a slave"""
        if slave_id not in self.slaves or market_location_id not in self.markets:
            return 0
        
        slave = self.slaves[slave_id]
        market = self.markets[market_location_id]
        
        # Base price from slave value
        base_price = slave.value
        
        # Apply market modifier
        market_price = int(base_price * market.price_modifier)
        
        # Adjust for slave condition
        condition_modifier = (slave.health + slave.morale) / 200  # 0.1 to 1.0
        condition_price = int(market_price * (0.5 + condition_modifier))
        
        # Adjust for special conditions
        if slave.is_branded:
            condition_price = int(condition_price * 0.8)  # Branded slaves are worth less
        
        if slave.is_chained:
            condition_price = int(condition_price * 0.9)  # Chained slaves are worth less
        
        # Minimum price
        return max(10, condition_price)
    
    def purchase_slave(self, slave_id: str, buyer_id: str, market_location_id: str) -> Dict[str, Any]:
        """
        Purchase a slave from a market
        Returns result dictionary with success status and details
        """
        result = {
            "success": False,
            "message": "Transaction failed",
            "price": 0
        }
        
        if slave_id not in self.slaves or market_location_id not in self.markets:
            result["message"] = "Invalid slave or market"
            return result
        
        market = self.markets[market_location_id]
        
        if slave_id not in market.slaves_for_sale:
            result["message"] = "Slave not for sale at this market"
            return result
        
        # Check if buyer is valid
        buyer_is_faction = buyer_id in self.faction_integration.faction_manager.factions
        buyer_is_npc = buyer_id in self.faction_integration.npc_integration.npc_faction_data
        
        if not (buyer_is_faction or buyer_is_npc):
            result["message"] = "Invalid buyer"
            return result
        
        # If buyer is a faction, check if they allow slavery
        if buyer_is_faction:
            faction = self.faction_integration.faction_manager.get_faction(buyer_id)
            if not faction.has_slavery:
                result["message"] = f"{faction.name} does not practice slavery"
                return result
        
        # If buyer is an NPC, check their faction
        if buyer_is_npc:
            npc_faction_id = self.faction_integration.npc_integration.get_npc_faction(buyer_id)
            if npc_faction_id:
                faction = self.faction_integration.faction_manager.get_faction(npc_faction_id)
                if not faction.has_slavery:
                    result["message"] = f"{faction.name} does not allow its members to own slaves"
                    return result
        
        slave = self.slaves[slave_id]
        price = self.get_market_price(slave_id, market_location_id)
        
        # In a real implementation, check if buyer has enough money
        # For now, assume they do
        
        # Process the sale
        old_owner_id = slave.owner_id
        self.transfer_ownership(slave_id, buyer_id)
        
        # Calculate tax
        tax_amount = price * market.tax_rate // 100
        seller_amount = price - tax_amount
        
        # Remove from market
        self.remove_slave_from_market(slave_id, market_location_id)
        
        # Update result
        result["success"] = True
        result["message"] = "Purchase successful"
        result["price"] = price
        result["tax"] = tax_amount
        result["seller_amount"] = seller_amount
        result["old_owner"] = old_owner_id
        
        return result
    
    def get_slave_productivity(self, slave_id: str) -> float:
        """Calculate a slave's productivity (0.0 to 1.0)"""
        if slave_id not in self.slaves:
            return 0.0
        
        slave = self.slaves[slave_id]
        
        # Base productivity is a function of health and morale
        base_productivity = (slave.health + slave.morale) / 200  # 0.1 to 1.0
        
        # Adjust for conditions
        if slave.is_chained:
            base_productivity *= 0.7  # Chains reduce productivity
        
        # Skills could improve productivity for specific tasks
        # For now, just use a simple model
        
        return base_productivity
    
    def update_slaves(self, game_time):
        """Update all slaves (called periodically)"""
        # Process each slave
        for slave_id, slave in list(self.slaves.items()):
            # Increment days enslaved counter if it's a new day
            if game_time.hour == 0 and game_time.minute == 0:
                slave.days_enslaved += 1
            
            # Health slowly recovers if not too low
            if slave.health > 30 and slave.health < 100:
                slave.health += random.randint(0, 1)
            elif slave.health <= 30:
                # Health might deteriorate if very low
                if random.random() < 0.2:
                    slave.health -= 1
                    
                    # Slave might die if health reaches 0
                    if slave.health <= 0:
                        self.free_slave(slave_id, reason="death")
                        continue
            
            # Morale changes based on conditions and random factors
            morale_change = 0
            
            # Conditions affect morale
            if slave.is_chained:
                morale_change -= 1
            
            if slave.is_branded:
                morale_change -= 1
            
            # Random factor
            morale_change += random.randint(-1, 1)
            
            # Apply morale change
            slave.morale = max(10, min(100, slave.morale + morale_change))
            
            # Automatic escape attempts
            if slave.morale < 30 and random.random() < 0.05:
                self.attempt_escape(slave_id)
            
            # Update market prices occasionally
            if game_time.hour == 0 and game_time.minute == 0:
                for market in self.markets.values():
                    market.update_price_modifier()
    
    def generate_slave_labor_output(self, owner_id: str) -> Dict[str, int]:
        """
        Calculate resources generated by all slaves owned by an entity
        Returns dictionary of resource_type -> amount
        """
        output = {}
        
        # Get all slaves owned by this entity
        slave_ids = set()
        
        if owner_id in self.faction_slaves:
            slave_ids.update(self.faction_slaves[owner_id])
        
        if owner_id in self.npc_slaves:
            slave_ids.update(self.npc_slaves[owner_id])
        
        # No slaves, no output
        if not slave_ids:
            return output
        
        # Process each slave
        for slave_id in slave_ids:
            if slave_id not in self.slaves:
                continue
                
            slave = self.slaves[slave_id]
            productivity = self.get_slave_productivity(slave_id)
            
            # Different slave types generate different resources
            if slave.slave_type == SlaveType.LABOR:
                # Labor slaves generate raw materials
                resources = ["wood", "stone", "ore"]
                resource = random.choice(resources)
                amount = int(5 * productivity)
                
                if resource in output:
                    output[resource] += amount
                else:
                    output[resource] = amount
            
            elif slave.slave_type == SlaveType.DOMESTIC:
                # Domestic slaves improve living conditions and happiness
                # Could be used in a more complex game system
                pass
            
            elif slave.slave_type == SlaveType.GLADIATOR:
                # Gladiators generate entertainment value and potentially gold
                if "gold" in output:
                    output["gold"] += int(10 * productivity)
                else:
                    output["gold"] = int(10 * productivity)
            
            elif slave.slave_type == SlaveType.SKILLED:
                # Skilled slaves produce crafted items or intellectual work
                crafted_resources = ["cloth", "tools", "jewelry"]
                resource = random.choice(crafted_resources)
                amount = int(3 * productivity)
                
                if resource in output:
                    output[resource] += amount
                else:
                    output[resource] = amount
            
            elif slave.slave_type == SlaveType.PLEASURE:
                # Adult-appropriate abstraction
                if "gold" in output:
                    output["gold"] += int(8 * productivity)
                else:
                    output["gold"] = int(8 * productivity)
        
        return output
    
    def get_slave_info(self, slave_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a slave"""
        if slave_id not in self.slaves:
            return None
        
        slave = self.slaves[slave_id]
        
        # Get original entity name (would use actual entity data in real implementation)
        original_name = f"Entity {slave.original_entity_id}"
        
        # Get owner name
        owner_name = "Unknown"
        if slave.owner_id in self.faction_integration.faction_manager.factions:
            owner_name = self.faction_integration.faction_manager.get_faction(slave.owner_id).name
        elif slave.owner_id in self.faction_integration.npc_integration.npc_faction_data:
            # Would use actual NPC name in real implementation
            owner_name = f"NPC {slave.owner_id}"
        
        return {
            "id": slave.slave_id,
            "original_entity_id": slave.original_entity_id,
            "original_name": original_name,
            "owner_id": slave.owner_id,
            "owner_name": owner_name,
            "type": slave.slave_type.name,
            "value": slave.value,
            "health": slave.health,
            "morale": slave.morale,
            "days_enslaved": slave.days_enslaved,
            "is_branded": slave.is_branded,
            "is_chained": slave.is_chained,
            "is_for_sale": slave.is_for_sale,
            "productivity": self.get_slave_productivity(slave_id),
            "skills": slave.skills
        }
    
    def handle_player_crime_punishment(self, player_id: str, faction_id: str) -> Dict[str, Any]:
        """Handle crime punishment that might result in enslavement"""
        result = {
            "enslaved": False,
            "message": "",
            "slave_id": None
        }
        
        # Check if faction practices slavery
        if faction_id not in self.faction_integration.faction_manager.factions:
            result["message"] = "Invalid faction"
            return result
        
        faction = self.faction_integration.faction_manager.get_faction(faction_id)
        if not faction.has_slavery:
            result["message"] = f"{faction.name} does not practice slavery"
            return result
        
        # Get player's crimes against this faction
        crimes = self.faction_integration.crime_manager.get_crimes_against_faction(faction_id)
        player_crimes = [c for c in crimes if c.perpetrator_id == player_id and not c.punishment_served]
        
        if not player_crimes:
            result["message"] = "No unpunished crimes found"
            return result
        
        # Calculate total severity
        total_severity = 0
        for crime in player_crimes:
            severity_values = {
                CrimeSeverity.MINOR: 1,
                CrimeSeverity.MODERATE: 3,
                CrimeSeverity.SERIOUS: 6,
                CrimeSeverity.SEVERE: 10
            }
            total_severity += severity_values.get(crime.severity, 0)
        
        # Determine if severity warrants enslavement
        enslavement_threshold = 15  # High threshold for player enslavement
        
        if total_severity >= enslavement_threshold:
            # Determine slave type based on player characteristics
            # For now, just pick randomly
            slave_type = random.choice(list(SlaveType))
            
            # Enslave the player
            slave_id = self.enslave_entity(player_id, faction_id, slave_type, reason="crime")
            
            if slave_id:
                # Mark crimes as punished
                for crime in player_crimes:
                    crime.punishment_served = True
                
                result["enslaved"] = True
                result["message"] = f"You have been enslaved by {faction.name} for your crimes"
                result["slave_id"] = slave_id
            else:
                result["message"] = "Failed to process enslavement"
        else:
            result["message"] = f"Your crimes are not severe enough for enslavement by {faction.name}"
        
        return result
    
    def calculate_freedom_price(self, slave_id: str) -> int:
        """Calculate price to purchase freedom"""
        if slave_id not in self.slaves:
            return 0
        
        slave = self.slaves[slave_id]
        
        # Base price is higher than market value for freedom
        base_price = slave.value * 1.5
        
        # Adjust based on days enslaved - longer enslaved means cheaper freedom
        time_discount = min(0.5, slave.days_enslaved / 100)  # Up to 50% discount
        
        # Owner type affects price
        owner_id = slave.owner_id
        owner_modifier = 1.0
        
        if owner_id in self.faction_integration.faction_manager.factions:
            faction = self.faction_integration.faction_manager.get_faction(owner_id)
            
            # Different faction types have different attitudes toward freedom
            if faction.faction_type == FactionType.CRIMINAL:
                owner_modifier = 2.0  # Criminal factions charge more
            elif faction.faction_type == FactionType.MERCHANT:
                owner_modifier = 1.5  # Merchants are business-minded
            elif faction.faction_type == FactionType.RELIGIOUS:
                owner_modifier = 0.8  # Religious factions might be more lenient
        
        # Calculate final price
        price = int(base_price * (1 - time_discount) * owner_modifier)
        
        # Minimum price
        return max(50, price)
    
    def purchase_freedom(self, slave_id: str) -> Dict[str, Any]:
        """
        Purchase freedom for a slave (usually oneself)
        Returns result of transaction
        """
        result = {
            "success": False,
            "message": "Failed to purchase freedom",
            "price": 0
        }
        
        if slave_id not in self.slaves:
            result["message"] = "Invalid slave ID"
            return result
        
        slave = self.slaves[slave_id]
        price = self.calculate_freedom_price(slave_id)
        
        # In a real implementation, check if enough money is available
        # For now, assume it is
        
        # Process freedom purchase
        if self.free_slave(slave_id, reason="purchased_freedom"):
            result["success"] = True
            result["message"] = "Freedom purchased successfully"
            result["price"] = price
        
        return result

    def save_state(self, save_dir: str):
        """Save slavery system state to files"""
        import os
        import json
        
        # Create save directory if it doesn't exist
        os.makedirs(save_dir, exist_ok=True)
        
        # Save slave data
        slave_data = {}
        for slave_id, slave in self.slaves.items():
            slave_data[slave_id] = {
                "original_entity_id": slave.original_entity_id,
                "owner_id": slave.owner_id,
                "slave_type": slave.slave_type.name,
                "value": slave.value,
                "skills": slave.skills,
                "health": slave.health,
                "morale": slave.morale,
                "escape_attempts": slave.escape_attempts,
                "days_enslaved": slave.days_enslaved,
                "is_branded": slave.is_branded,
                "is_chained": slave.is_chained,
                "is_for_sale": slave.is_for_sale
            }
        
        with open(os.path.join(save_dir, "slaves.json"), 'w') as f:
            json.dump(slave_data, f, indent=2)
        
        # Save market data
        market_data = {}
        for location_id, market in self.markets.items():
            market_data[location_id] = {
                "controlling_faction_id": market.controlling_faction_id,
                "slaves_for_sale": market.slaves_for_sale,
                "tax_rate": market.tax_rate,
                "price_modifier": market.price_modifier
            }
        
        with open(os.path.join(save_dir, "slave_markets.json"), 'w') as f:
            json.dump(market_data, f, indent=2)
        
        # Save ownership tracking
        ownership_data = {
            "faction_slaves": {faction_id: list(slaves) for faction_id, slaves in self.faction_slaves.items()},
            "npc_slaves": {npc_id: list(slaves) for npc_id, slaves in self.npc_slaves.items()},
            "escaped_slaves": self.escaped_slaves
        }
        
        with open(os.path.join(save_dir, "slave_ownership.json"), 'w') as f:
            json.dump(ownership_data, f, indent=2)
    
    def load_state(self, save_dir: str):
        """Load slavery system state from files"""
        import os
        import json
        
        # Clear current state
        self.slaves = {}
        self.markets = {}
        self.faction_slaves = {}
        self.npc_slaves = {}
        self.escaped_slaves = {}
        
        # Load slave data
        try:
            with open(os.path.join(save_dir, "slaves.json"), 'r') as f:
                slave_data = json.load(f)
            
            for slave_id, data in slave_data.items():
                self.slaves[slave_id] = SlaveData(
                    slave_id=slave_id,
                    original_entity_id=data["original_entity_id"],
                    owner_id=data["owner_id"],
                    slave_type=SlaveType[data["slave_type"]],
                    value=data["value"],
                    skills=data["skills"],
                    health=data["health"],
                    morale=data["morale"],
                    escape_attempts=data["escape_attempts"],
                    days_enslaved=data["days_enslaved"],
                    is_branded=data["is_branded"],
                    is_chained=data["is_chained"],
                    is_for_sale=data["is_for_sale"]
                )
        except (FileNotFoundError, json.JSONDecodeError):
            pass
        
        # Load market data
        try:
            with open(os.path.join(save_dir, "slave_markets.json"), 'r') as f:
                market_data = json.load(f)
            
            for location_id, data in market_data.items():
                market = SlaveMarket(
                    location_id=location_id,
                    controlling_faction_id=data["controlling_faction_id"]
                )
                market.slaves_for_sale = data["slaves_for_sale"]
                market.tax_rate = data["tax_rate"]
                market.price_modifier = data["price_modifier"]
                
                self.markets[location_id] = market
        except (FileNotFoundError, json.JSONDecodeError):
            pass
        
        # Load ownership tracking
        try:
            with open(os.path.join(save_dir, "slave_ownership.json"), 'r') as f:
                ownership_data = json.load(f)
            
            # Convert list back to sets
            self.faction_slaves = {faction_id: set(slaves) for faction_id, slaves in ownership_data["faction_slaves"].items()}
            self.npc_slaves = {npc_id: set(slaves) for npc_id, slaves in ownership_data["npc_slaves"].items()}
            self.escaped_slaves = ownership_data["escaped_slaves"]
        except (FileNotFoundError, json.JSONDecodeError):
            pass


# Example usage
if __name__ == "__main__":
    import time
    from datetime import datetime
    
    # Create faction system
    faction_integration = FactionSystemIntegration()
    faction_integration.initialize_default_factions()
    
    # Create slavery system
    slave_system = SlaveSystem(faction_integration)
    
    # Find factions that allow slavery
    print("Factions that practice slavery:")
    slavery_factions = []
    for faction_id, faction in faction_integration.faction_manager.factions.items():
        if faction.has_slavery:
            slavery_factions.append(faction)
            print(f"- {faction.name} ({faction.faction_type.name})")
    
    if not slavery_factions:
        print("No factions practice slavery. Enabling it for testing.")
        # Enable slavery for one faction for testing
        test_faction = next(iter(faction_integration.faction_manager.factions.values()))
        test_faction.has_slavery = True
        slavery_factions.append(test_faction)
        print(f"- {test_faction.name} ({test_faction.faction_type.name}) (enabled for testing)")
    
    # Create a slave market
    test_faction = slavery_factions[0]
    market_location = f"market_{test_faction.id}"
    slave_system.create_market(market_location, test_faction.id)
    print(f"\nCreated slave market at {market_location} controlled by {test_faction.name}")
    
    # Enslave some NPCs for testing
    slave_ids = []
    for i in range(5):
        npc_id = f"test_npc_{i}"
        slave_type = random.choice(list(SlaveType))
        
        slave_id = slave_system.enslave_entity(npc_id, test_faction.id, slave_type)
        if slave_id:
            slave_ids.append(slave_id)
            print(f"Enslaved NPC {npc_id} as a {slave_type.name} slave (ID: {slave_id})")
    
    # Put some slaves on the market
    for slave_id in slave_ids[:3]:
        if slave_system.add_slave_to_market(slave_id, market_location):
            price = slave_system.get_market_price(slave_id, market_location)
            print(f"Added slave {slave_id} to market for {price} gold")
    
    # Create an NPC owner
    npc_owner_id = "npc_slaver"
    faction_integration.npc_integration.add_npc_to_faction(
        npc_id=npc_owner_id,
        faction_id=test_faction.id,
        rank=5
    )
    
    # Purchase a slave
    if slave_ids:
        slave_id = slave_ids[0]
        result = slave_system.purchase_slave(slave_id, npc_owner_id, market_location)
        if result["success"]:
            print(f"\nNPC {npc_owner_id} purchased slave {slave_id} for {result['price']} gold")
        else:
            print(f"\nFailed to purchase slave: {result['message']}")
    
    # Test slave labor
    if slave_ids:
        # Simulate a day passing
        for slave_id in slave_ids:
            if slave_id in slave_system.slaves:
                slave = slave_system.slaves[slave_id]
                print(f"\nSlave {slave_id} ({slave.slave_type.name}):")
                print(f"  Health: {slave.health}, Morale: {slave.morale}")
                print(f"  Productivity: {slave_system.get_slave_productivity(slave_id):.2f}")
        
        # Calculate labor output
        faction_output = slave_system.generate_slave_labor_output(test_faction.id)
        if faction_output:
            print(f"\n{test_faction.name} slave labor output:")
            for resource, amount in faction_output.items():
                print(f"  {resource}: {amount}")
        
        # Test escape attempt
        for slave_id in slave_ids:
            if slave_id in slave_system.slaves:
                success, message = slave_system.attempt_escape(slave_id)
                print(f"\nSlave {slave_id} escape attempt: {message}")
    
    # Save system state
    slave_system.save_state("slavery_save")
    print("\nSaved slavery system state to 'slavery_save' directory")
    
    print("\nSlavery System Test Complete")
