import logging
import os
import pygame
from typing import Dict, List, Optional, Any, Tuple

from faction_system.faction_system import Faction, FactionManager, FactionType, RelationshipStatus
from faction_system.faction_generator import FactionGenerator
from faction_system.faction_integration import FactionSystemIntegration
from faction_system.slavery_system import SlaveSystem

logger = logging.getLogger("faction_manager")

class GameFactionManager:
    """
    Central manager for all faction-related systems.
    
    This class provides unified access to all faction subsystems and handles 
    integration with the main game through the event bus.
    """
    
    def __init__(self, event_bus):
        """
        Initialize the faction manager.
        
        Args:
            event_bus: EventBus instance for communication
        """
        self.event_bus = event_bus
        
        # Initialize the core faction integration system
        self.faction_integration = FactionSystemIntegration()
        
        # Initialize with default factions
        self.faction_integration.initialize_default_factions()
        
        # Initialize slavery system
        self.slavery_system = SlaveSystem(self.faction_integration)
        
        # Shorthand references to subsystems for convenience
        self.faction_manager = self.faction_integration.faction_manager
        self.npc_integration = self.faction_integration.npc_integration
        self.territory_manager = self.faction_integration.territory_manager
        self.crime_manager = self.faction_integration.crime_manager
        
        # Register event handlers
        self.register_events()
        
        logger.info("GameFactionManager initialized")
    
    def register_events(self):
        """Register event handlers for faction system."""
        # General faction events
        self.event_bus.subscribe("faction_reputation_change", self.handle_reputation_change)
        self.event_bus.subscribe("faction_task_complete", self.handle_task_complete)
        self.event_bus.subscribe("faction_join_request", self.handle_join_request)
        
        # Criminal events
        self.event_bus.subscribe("crime_reported", self.handle_crime_reported)
        self.event_bus.subscribe("bounty_paid", self.handle_bounty_paid)
        
        # Territory events
        self.event_bus.subscribe("territory_contested", self.handle_territory_contested)
        self.event_bus.subscribe("territory_entered", self.handle_territory_entered)
        
        # Slavery events
        self.event_bus.subscribe("slave_captured", self.handle_slave_captured)
        self.event_bus.subscribe("slave_market_transaction", self.handle_slave_market_transaction)
        
        # World exploration integration
        self.event_bus.subscribe("location_discovered", self.handle_location_discovered)
    
    def handle_reputation_change(self, data):
        """
        Handle reputation change event.
        
        Args:
            data: Dictionary with faction_id and amount
        """
        faction_id = data.get("faction_id")
        amount = data.get("amount", 0)
        reason = data.get("reason", "unspecified")
        
        if faction_id and faction_id in self.faction_manager.factions:
            old_rep = self.faction_manager.player_reputation.get(faction_id, 0)
            new_rep = self.faction_manager.modify_player_reputation(faction_id, amount)
            
            old_status = self.faction_manager.get_player_faction_status(faction_id)
            new_status = self.faction_manager.get_player_faction_status(faction_id)
            
            # If status changed, publish status change event
            if old_status != new_status:
                self.event_bus.publish("faction_status_changed", {
                    "faction_id": faction_id,
                    "faction_name": self.faction_manager.factions[faction_id].name,
                    "old_status": old_status.name,
                    "new_status": new_status.name,
                    "reputation": new_rep
                })
            
            # Publish notification about reputation change
            faction_name = self.faction_manager.factions[faction_id].name
            message = f"Your reputation with {faction_name} has "
            if amount > 0:
                message += f"increased by {amount}."
            else:
                message += f"decreased by {abs(amount)}."
            
            self.event_bus.publish("show_notification", {
                "title": "Reputation Changed",
                "message": message,
                "duration": 3.0
            })
            
            logger.info(f"Player reputation with {faction_name} changed from {old_rep} to {new_rep} ({reason})")
    
    def handle_task_complete(self, data):
        """
        Handle faction task completion event.
        
        Args:
            data: Dictionary with task details
        """
        task = data.get("task")
        success = data.get("success", True)
        
        if task:
            result = self.faction_integration.complete_faction_task(task, success)
            
            # Publish notification
            faction_name = self.faction_manager.factions[task["faction_id"]].name
            if success:
                message = f"Task completed for {faction_name}. Gained {result['reputation_change']} reputation."
            else:
                message = f"Task failed for {faction_name}. Lost {abs(result['reputation_change'])} reputation."
            
            self.event_bus.publish("show_notification", {
                "title": "Task Complete" if success else "Task Failed",
                "message": message,
                "duration": 3.0
            })
            
            logger.info(f"Player {'completed' if success else 'failed'} task for {faction_name}")
    
    def handle_join_request(self, data):
        """
        Handle player request to join a faction.
        
        Args:
            data: Dictionary with faction_id
        """
        faction_id = data.get("faction_id")
        player_id = data.get("player_id", "player")
        
        if faction_id and faction_id in self.faction_manager.factions:
            faction = self.faction_manager.factions[faction_id]
            
            # Check current reputation
            current_rep = self.faction_manager.player_reputation.get(faction_id, 0)
            required_rep = 50  # Base requirement to join
            
            if current_rep >= required_rep:
                # Player can join
                self.npc_integration.add_npc_to_faction(
                    npc_id=player_id,
                    faction_id=faction_id,
                    rank=1,
                    loyalty=50
                )
                
                # Publish notification
                rank_title = self.npc_integration.get_npc_rank_title(player_id)
                self.event_bus.publish("show_notification", {
                    "title": "Faction Joined",
                    "message": f"You have joined {faction.name} as a {rank_title}.",
                    "duration": 3.0
                })
                
                # Publish joined event for other systems
                self.event_bus.publish("faction_joined", {
                    "faction_id": faction_id,
                    "faction_name": faction.name,
                    "player_id": player_id,
                    "rank": 1,
                    "rank_title": rank_title
                })
                
                logger.info(f"Player joined faction: {faction.name}")
                return True
            else:
                # Not enough reputation
                self.event_bus.publish("show_notification", {
                    "title": "Cannot Join Faction",
                    "message": f"{faction.name} does not accept you yet. Reputation: {current_rep}/{required_rep}",
                    "duration": 3.0
                })
                
                logger.info(f"Player denied faction membership in {faction.name} (rep: {current_rep}/{required_rep})")
                return False
    
    def handle_crime_reported(self, data):
        """
        Handle crime reported event.
        
        Args:
            data: Dictionary with crime details
        """
        crime_type = data.get("crime_type", "theft")
        severity = data.get("severity")
        location_id = data.get("location_id", "unknown")
        faction_id = data.get("faction_id")
        perpetrator_id = data.get("perpetrator_id", "player")
        witnesses = data.get("witnesses", [])
        
        if not faction_id or faction_id not in self.faction_manager.factions:
            logger.error(f"Invalid faction ID for crime report: {faction_id}")
            return
        
        # Report crime
        crime_id = self.crime_manager.report_crime(
            crime_type=crime_type,
            severity=severity,
            location_id=location_id,
            faction_id=faction_id,
            perpetrator_id=perpetrator_id,
            witnesses=witnesses
        )
        
        # Get bounty
        bounty = self.crime_manager.get_bounty(perpetrator_id)
        
        # Publish notification if the player is the perpetrator
        if perpetrator_id == "player" and witnesses:
            faction_name = self.faction_manager.factions[faction_id].name
            self.event_bus.publish("show_notification", {
                "title": "Crime Witnessed!",
                "message": f"Your {crime_type} against {faction_name} was witnessed. Bounty: {bounty}",
                "duration": 3.0
            })
        
        logger.info(f"Crime reported: {crime_type} against {faction_id} - Bounty: {bounty}")
    
    def handle_bounty_paid(self, data):
        """
        Handle bounty payment event.
        
        Args:
            data: Dictionary with entity_id and faction_id
        """
        entity_id = data.get("entity_id", "player")
        faction_id = data.get("faction_id")
        
        if faction_id and faction_id in self.faction_manager.factions:
            bounty_amount = self.crime_manager.pay_bounty(entity_id, faction_id)
            
            if bounty_amount > 0:
                # Publish notification
                faction_name = self.faction_manager.factions[faction_id].name
                self.event_bus.publish("show_notification", {
                    "title": "Bounty Paid",
                    "message": f"Paid {bounty_amount} gold to {faction_name} for your crimes.",
                    "duration": 3.0
                })
                
                logger.info(f"Bounty of {bounty_amount} paid to {faction_name}")
    
    def handle_territory_contested(self, data):
        """
        Handle territory contested event.
        
        Args:
            data: Dictionary with location_id and contesting_faction_id
        """
        location_id = data.get("location_id")
        contesting_faction_id = data.get("contesting_faction_id")
        
        if location_id and contesting_faction_id:
            if location_id in self.territory_manager.territories:
                self.territory_manager.contest_territory(location_id, contesting_faction_id)
                
                # Get faction names for notification
                controlling_faction_id = self.territory_manager.territories[location_id].controlling_faction_id
                controlling_name = self.faction_manager.factions[controlling_faction_id].name
                contesting_name = self.faction_manager.factions[contesting_faction_id].name
                
                # Publish notification
                self.event_bus.publish("show_notification", {
                    "title": "Territory Contested",
                    "message": f"{contesting_name} is contesting {controlling_name}'s control of {location_id}.",
                    "duration": 3.0
                })
                
                logger.info(f"Territory {location_id} contested by {contesting_name}")
    
    def handle_territory_entered(self, data):
        """
        Handle territory entered event.
        
        Args:
            data: Dictionary with location_id
        """
        location_id = data.get("location_id")
        
        if location_id and location_id in self.territory_manager.territories:
            territory = self.territory_manager.territories[location_id]
            faction_id = territory.controlling_faction_id
            faction = self.faction_manager.factions[faction_id]
            
            # Publish notification
            self.event_bus.publish("show_notification", {
                "title": "Entered Territory",
                "message": f"You've entered territory controlled by {faction.name}.",
                "duration": 3.0
            })
            
            # Check player's status with this faction
            status = self.faction_manager.get_player_faction_status(faction_id)
            player_in_faction = self.npc_integration.get_npc_faction("player") == faction_id
            
            if not player_in_faction and status == RelationshipStatus.HOSTILE:
                # Show warning for hostile territory
                self.event_bus.publish("show_notification", {
                    "title": "Warning!",
                    "message": f"{faction.name} is hostile toward you! You may be attacked on sight.",
                    "duration": 5.0
                })
            
            logger.info(f"Player entered {faction.name} territory ({status.name})")
    
    def handle_slave_captured(self, data):
        """
        Handle slave captured event.
        
        Args:
            data: Dictionary with slave details
        """
        entity_id = data.get("entity_id")
        owner_id = data.get("owner_id")
        slave_type = data.get("slave_type")
        reason = data.get("reason", "crime")
        
        if entity_id and owner_id:
            slave_id = self.slavery_system.enslave_entity(
                entity_id=entity_id,
                owner_id=owner_id,
                slave_type=slave_type,
                reason=reason
            )
            
            if slave_id:
                # If owner is a faction, get name
                if owner_id in self.faction_manager.factions:
                    owner_name = self.faction_manager.factions[owner_id].name
                else:
                    owner_name = "an individual"
                
                # Publish notification if player enslaved
                if entity_id == "player":
                    self.event_bus.publish("show_notification", {
                        "title": "Enslaved!",
                        "message": f"You have been enslaved by {owner_name}.",
                        "duration": 5.0
                    })
                    
                    # Publish player enslaved event
                    self.event_bus.publish("player_enslaved", {
                        "slave_id": slave_id,
                        "owner_id": owner_id,
                        "owner_name": owner_name,
                        "reason": reason
                    })
                
                logger.info(f"Entity {entity_id} enslaved by {owner_id} as {slave_id}")
    
    def handle_slave_market_transaction(self, data):
        """
        Handle slave market transaction event.
        
        Args:
            data: Dictionary with transaction details
        """
        slave_id = data.get("slave_id")
        buyer_id = data.get("buyer_id")
        market_location_id = data.get("market_location_id")
        
        if slave_id and buyer_id and market_location_id:
            result = self.slavery_system.purchase_slave(
                slave_id=slave_id,
                buyer_id=buyer_id,
                market_location_id=market_location_id
            )
            
            if result["success"]:
                # Publish notification
                self.event_bus.publish("show_notification", {
                    "title": "Slave Purchased",
                    "message": f"Slave purchased for {result['price']} gold.",
                    "duration": 3.0
                })
                
                logger.info(f"Slave {slave_id} purchased by {buyer_id} for {result['price']}")
    
    def handle_location_discovered(self, data):
        """
        Handle location discovered event - integrate with territory system.
        
        Args:
            data: Dictionary with location details
        """
        location_id = data.get("location_id")
        location_name = data.get("name", location_id)
        
        # Check if this location is a controlled territory
        controlling_faction_id = self.faction_manager.get_controlling_faction(location_id)
        
        if controlling_faction_id:
            faction = self.faction_manager.factions[controlling_faction_id]
            
            # Publish notification about faction control
            self.event_bus.publish("show_notification", {
                "title": "Territory Information",
                "message": f"{location_name} is controlled by {faction.name}.",
                "duration": 3.0
            })
            
            logger.info(f"Player discovered {location_name} controlled by {faction.name}")
    
    def get_faction_ui_data(self, faction_id):
        """
        Get faction data for UI display.
        
        Args:
            faction_id: ID of faction to get data for
            
        Returns:
            Dictionary with UI data
        """
        if faction_id not in self.faction_manager.factions:
            return None
        
        faction = self.faction_manager.factions[faction_id]
        
        # Calculate territory count
        territory_count = len(faction.controlled_locations)
        
        # Calculate resources
        resources = self.territory_manager.calculate_faction_resources(faction_id)
        
        # Get faction leader if any
        leader_id = self.npc_integration.get_faction_leader(faction_id)
        leader_name = "None"
        if leader_id:
            # Would get actual NPC name
            leader_name = f"NPC {leader_id}"
        
        # Get player status with this faction
        reputation = self.faction_manager.player_reputation.get(faction_id, 0)
        status = self.faction_manager.get_player_faction_status(faction_id)
        
        # Check if player is a member
        is_member = self.npc_integration.get_npc_faction("player") == faction_id
        rank = 0
        rank_title = "Non-member"
        
        if is_member:
            rank = self.npc_integration.npc_faction_data["player"].rank
            rank_title = self.npc_integration.get_npc_rank_title("player")
        
        # Check for slavery
        has_slavery = faction.has_slavery
        slave_count = 0
        if faction_id in self.slavery_system.faction_slaves:
            slave_count = len(self.slavery_system.faction_slaves[faction_id])
        
        # Return UI data
        return {
            "id": faction_id,
            "name": faction.name,
            "type": faction.faction_type.name,
            "description": faction.description,
            "colors": {
                "primary": faction.primary_color,
                "secondary": faction.secondary_color
            },
            "territories": {
                "count": territory_count,
                "names": list(faction.controlled_locations)
            },
            "resources": resources,
            "leader": {
                "id": leader_id,
                "name": leader_name
            },
            "player_status": {
                "reputation": reputation,
                "status": status.name,
                "is_member": is_member,
                "rank": rank,
                "rank_title": rank_title
            },
            "has_slavery": has_slavery,
            "slave_count": slave_count,
            "can_arrest": faction.can_arrest,
            "is_hidden": faction.is_hidden,
            "power_level": faction.power_level
        }
    
    def get_all_factions_data(self):
        """
        Get data for all factions.
        
        Returns:
            List of faction data dictionaries
        """
        return [
            self.get_faction_ui_data(faction_id) 
            for faction_id in self.faction_manager.factions
            if not self.faction_manager.factions[faction_id].is_hidden
        ]
    
    def get_territory_data(self, location_id):
        """
        Get territory data for a location.
        
        Args:
            location_id: Location ID to get territory data for
            
        Returns:
            Dictionary with territory data or None
        """
        if location_id not in self.territory_manager.territories:
            return None
        
        territory = self.territory_manager.territories[location_id]
        controlling_faction = self.faction_manager.factions[territory.controlling_faction_id]
        
        return {
            "location_id": location_id,
            "controlling_faction": {
                "id": territory.controlling_faction_id,
                "name": controlling_faction.name,
                "type": controlling_faction.faction_type.name
            },
            "control_level": territory.control_level,
            "contested": territory.contested,
            "contesting_factions": [
                {
                    "id": faction_id,
                    "name": self.faction_manager.factions[faction_id].name
                }
                for faction_id in territory.contesting_factions
            ],
            "tax_rate": territory.tax_rate,
            "crime_rate": territory.crime_rate,
            "prosperity": territory.prosperity,
            "has_guards": territory.has_guards,
            "has_prison": territory.has_prison,
            "has_slavery": territory.has_slavery,
            "resources": territory.resources
        }
    
    def get_player_crime_data(self):
        """
        Get data about player's crimes and bounties.
        
        Returns:
            Dictionary with crime data
        """
        player_id = "player"
        
        # Get bounty
        bounty = self.crime_manager.get_bounty(player_id)
        
        # Get crimes
        crimes = self.crime_manager.get_criminal_record(player_id)
        
        # Organize crimes by faction
        crimes_by_faction = {}
        
        for crime in crimes:
            faction_id = crime.faction_id
            
            if faction_id not in crimes_by_faction:
                faction_name = self.faction_manager.factions[faction_id].name
                crimes_by_faction[faction_id] = {
                    "faction_name": faction_name,
                    "total_bounty": 0,
                    "crimes": []
                }
            
            # Add crime details
            crimes_by_faction[faction_id]["crimes"].append({
                "crime_id": crime.crime_id,
                "crime_type": crime.crime_type,
                "severity": crime.severity.name,
                "location_id": crime.location_id,
                "bounty": crime.bounty,
                "is_solved": crime.is_solved,
                "punishment_served": crime.punishment_served
            })
            
            # Add to total bounty if not solved
            if not crime.is_solved:
                crimes_by_faction[faction_id]["total_bounty"] += crime.bounty
        
        return {
            "total_bounty": bounty,
            "crimes_by_faction": crimes_by_faction
        }
    
    def save_state(self, save_dir):
        """
        Save faction system state.
        
        Args:
            save_dir: Directory to save state to
        """
        # Create faction save directory
        faction_save_dir = os.path.join(save_dir, "faction_system")
        os.makedirs(faction_save_dir, exist_ok=True)
        
        # Save main faction system state
        self.faction_integration.save_state(faction_save_dir)
        
        # Save slavery system state
        self.slavery_system.save_state(faction_save_dir)
        
        logger.info(f"Faction system state saved to {faction_save_dir}")
    
    def load_state(self, save_dir):
        """
        Load faction system state.
        
        Args:
            save_dir: Directory to load state from
        """
        # Create faction save directory path
        faction_save_dir = os.path.join(save_dir, "faction_system")
        
        # Check if directory exists
        if not os.path.exists(faction_save_dir):
            logger.warning(f"Faction save directory not found: {faction_save_dir}")
            return
        
        # Load main faction system state
        self.faction_integration.load_state(faction_save_dir)
        
        # Load slavery system state
        self.slavery_system.load_state(faction_save_dir)
        
        logger.info(f"Faction system state loaded from {faction_save_dir}")
    
    def update(self, game_time):
        """
        Update faction systems based on game time.
        
        Args:
            game_time: Current game time
        """
        # Update core faction integration
        self.faction_integration.update(game_time)
        
        # Update slavery system
        self.slavery_system.update_slaves(game_time)