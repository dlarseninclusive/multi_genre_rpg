import pygame
import json
import random
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Any, Callable

from event_bus import EventBus
from character import Character


class QuestStatus(Enum):
    """Status of a quest."""
    NOT_STARTED = auto()
    ACTIVE = auto()
    COMPLETED = auto()
    FAILED = auto()


class QuestType(Enum):
    """Types of quests."""
    MAIN = auto()      # Main storyline quest
    SIDE = auto()      # Optional side quest
    WORLD = auto()     # World event quest
    FACTION = auto()   # Faction-specific quest
    DAILY = auto()     # Daily repeatable quest
    SPECIAL = auto()   # Special event quest


class ObjectiveType(Enum):
    """Types of quest objectives."""
    KILL = auto()      # Kill specific enemies
    COLLECT = auto()   # Collect items
    TALK = auto()      # Talk to NPCs
    LOCATION = auto()  # Visit a location
    ESCORT = auto()    # Escort an NPC
    DELIVER = auto()   # Deliver items
    CRAFT = auto()     # Craft items
    INVESTIGATE = auto()  # Investigate a scene (detective mode)
    BUILD = auto()     # Build structures (base building)
    DEFEND = auto()    # Defend a location
    BOSS = auto()      # Defeat a boss
    PUZZLE = auto()    # Solve a puzzle
    MINIGAME = auto()  # Complete a minigame


@dataclass
class QuestObjective:
    """An objective that must be completed as part of a quest."""
    id: str
    type: ObjectiveType
    description: str
    target: str  # Entity to interact with (enemy type, item id, npc id, location id)
    required_amount: int = 1
    current_amount: int = 0
    completed: bool = False
    
    # Optional data for specific objective types
    coordinates: Optional[Tuple[int, int]] = None  # For LOCATION objectives
    time_limit: Optional[int] = None  # For timed objectives (in seconds)
    special_conditions: Dict[str, Any] = field(default_factory=dict)  # Additional conditions
    
    def is_complete(self) -> bool:
        """Check if the objective is completed."""
        if self.completed:
            return True
        
        if self.current_amount >= self.required_amount:
            self.completed = True
            return True
        return False
    
    def update_progress(self, amount: int = 1):
        """Update the progress of this objective."""
        if not self.completed:
            self.current_amount = min(self.required_amount, self.current_amount + amount)
            if self.current_amount >= self.required_amount:
                self.completed = True
    
    def reset(self):
        """Reset objective progress."""
        self.current_amount = 0
        self.completed = False


@dataclass
class QuestReward:
    """Rewards for completing a quest."""
    xp: int = 0
    gold: int = 0
    items: List[Dict[str, Any]] = field(default_factory=list)  # List of item definitions
    reputation: Dict[str, int] = field(default_factory=dict)  # Faction name -> reputation amount
    stats: Dict[str, int] = field(default_factory=dict)  # Stat name -> bonus amount
    unlock_quests: List[str] = field(default_factory=list)  # IDs of quests to unlock
    unlock_locations: List[str] = field(default_factory=list)  # IDs of locations to unlock
    unlock_items: List[str] = field(default_factory=list)  # IDs of items to unlock for shops/crafting


@dataclass
class Quest:
    """A quest that can be undertaken by the player."""
    id: str
    title: str
    description: str
    type: QuestType
    level: int
    status: QuestStatus = QuestStatus.NOT_STARTED
    objectives: List[QuestObjective] = field(default_factory=list)
    rewards: QuestReward = field(default_factory=QuestReward)
    
    # Quest requirements
    required_level: int = 1
    required_quests: List[str] = field(default_factory=list)  # IDs of quests that must be completed
    required_faction: Optional[str] = None  # Required faction
    required_reputation: int = 0  # Required reputation level with faction
    
    # Quest properties
    is_repeatable: bool = False
    is_hidden: bool = False  # Hidden until requirements met
    is_timed: bool = False
    time_limit: Optional[int] = None  # Time limit in seconds
    
    # Quest NPCs
    quest_giver: Optional[str] = None  # NPC ID
    quest_receiver: Optional[str] = None  # NPC ID to turn in to (if different)
    
    # Dialog entries
    dialog_start: Optional[str] = None  # Dialog ID
    dialog_incomplete: Optional[str] = None  # Dialog ID
    dialog_complete: Optional[str] = None  # Dialog ID
    
    def is_complete(self) -> bool:
        """Check if all objectives are completed."""
        return all(objective.is_complete() for objective in self.objectives)
    
    def get_progress(self) -> float:
        """Get the overall completion percentage of the quest."""
        if not self.objectives:
            return 1.0 if self.status == QuestStatus.COMPLETED else 0.0
        
        total_required = sum(obj.required_amount for obj in self.objectives)
        total_current = sum(min(obj.current_amount, obj.required_amount) for obj in self.objectives)
        
        return total_current / total_required if total_required > 0 else 0.0
    
    def get_objective_by_id(self, objective_id: str) -> Optional[QuestObjective]:
        """Get an objective by its ID."""
        for objective in self.objectives:
            if objective.id == objective_id:
                return objective
        return None
    
    def activate(self):
        """Activate the quest, setting its status to active."""
        self.status = QuestStatus.ACTIVE
    
    def complete(self):
        """Mark the quest as completed."""
        self.status = QuestStatus.COMPLETED
    
    def fail(self):
        """Mark the quest as failed."""
        self.status = QuestStatus.FAILED
    
    def reset(self):
        """Reset the quest to its initial state."""
        self.status = QuestStatus.NOT_STARTED
        for objective in self.objectives:
            objective.reset()


class QuestManager:
    """Manages all quests in the game."""
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.quests: Dict[str, Quest] = {}
        self.active_quests: List[str] = []
        self.completed_quests: List[str] = []
        self.failed_quests: List[str] = []
        
        # Subscribe to events
        self.event_bus.subscribe("enemy_killed", self.handle_enemy_killed)
        self.event_bus.subscribe("item_collected", self.handle_item_collected)
        self.event_bus.subscribe("npc_talked", self.handle_npc_talked)
        self.event_bus.subscribe("location_visited", self.handle_location_visited)
        self.event_bus.subscribe("item_crafted", self.handle_item_crafted)
        self.event_bus.subscribe("item_delivered", self.handle_item_delivered)
        self.event_bus.subscribe("structure_built", self.handle_structure_built)
        self.event_bus.subscribe("boss_defeated", self.handle_boss_defeated)
        self.event_bus.subscribe("puzzle_solved", self.handle_puzzle_solved)
        self.event_bus.subscribe("minigame_completed", self.handle_minigame_completed)
    
    def load_quests_from_file(self, filename: str):
        """Load quests from a JSON file."""
        try:
            with open(filename, 'r') as file:
                quest_data = json.load(file)
                
                for quest_info in quest_data:
                    quest_id = quest_info.get("id")
                    if quest_id:
                        # Convert objectives data
                        objectives = []
                        for obj_data in quest_info.get("objectives", []):
                            objective = QuestObjective(
                                id=obj_data.get("id"),
                                type=ObjectiveType[obj_data.get("type")],
                                description=obj_data.get("description"),
                                target=obj_data.get("target"),
                                required_amount=obj_data.get("required_amount", 1),
                                coordinates=tuple(obj_data.get("coordinates")) if "coordinates" in obj_data else None,
                                time_limit=obj_data.get("time_limit"),
                                special_conditions=obj_data.get("special_conditions", {})
                            )
                            objectives.append(objective)
                        
                        # Convert rewards data
                        rewards_data = quest_info.get("rewards", {})
                        rewards = QuestReward(
                            xp=rewards_data.get("xp", 0),
                            gold=rewards_data.get("gold", 0),
                            items=rewards_data.get("items", []),
                            reputation=rewards_data.get("reputation", {}),
                            stats=rewards_data.get("stats", {}),
                            unlock_quests=rewards_data.get("unlock_quests", []),
                            unlock_locations=rewards_data.get("unlock_locations", []),
                            unlock_items=rewards_data.get("unlock_items", [])
                        )
                        
                        # Create quest
                        quest = Quest(
                            id=quest_id,
                            title=quest_info.get("title", "Unnamed Quest"),
                            description=quest_info.get("description", ""),
                            type=QuestType[quest_info.get("type", "SIDE")],
                            level=quest_info.get("level", 1),
                            required_level=quest_info.get("required_level", 1),
                            required_quests=quest_info.get("required_quests", []),
                            required_faction=quest_info.get("required_faction"),
                            required_reputation=quest_info.get("required_reputation", 0),
                            is_repeatable=quest_info.get("is_repeatable", False),
                            is_hidden=quest_info.get("is_hidden", False),
                            is_timed=quest_info.get("is_timed", False),
                            time_limit=quest_info.get("time_limit"),
                            quest_giver=quest_info.get("quest_giver"),
                            quest_receiver=quest_info.get("quest_receiver"),
                            dialog_start=quest_info.get("dialog_start"),
                            dialog_incomplete=quest_info.get("dialog_incomplete"),
                            dialog_complete=quest_info.get("dialog_complete"),
                            objectives=objectives,
                            rewards=rewards
                        )
                        
                        self.quests[quest_id] = quest
                
                print(f"Loaded {len(self.quests)} quests from {filename}")
        except Exception as e:
            print(f"Error loading quests: {e}")
    
    def save_quest_progress(self, filename: str):
        """Save quest progress to a file."""
        quest_progress = {
            "active_quests": self.active_quests,
            "completed_quests": self.completed_quests,
            "failed_quests": self.failed_quests,
            "quest_states": {}
        }
        
        # Save state of each quest (status and objective progress)
        for quest_id, quest in self.quests.items():
            quest_progress["quest_states"][quest_id] = {
                "status": quest.status.name,
                "objectives": [
                    {
                        "id": obj.id,
                        "current_amount": obj.current_amount,
                        "completed": obj.completed
                    }
                    for obj in quest.objectives
                ]
            }
        
        try:
            with open(filename, 'w') as file:
                json.dump(quest_progress, file, indent=2)
            print(f"Saved quest progress to {filename}")
        except Exception as e:
            print(f"Error saving quest progress: {e}")
    
    def load_quest_progress(self, filename: str):
        """Load quest progress from a file."""
        try:
            with open(filename, 'r') as file:
                progress = json.load(file)
                
                self.active_quests = progress.get("active_quests", [])
                self.completed_quests = progress.get("completed_quests", [])
                self.failed_quests = progress.get("failed_quests", [])
                
                # Restore quest states
                quest_states = progress.get("quest_states", {})
                for quest_id, state in quest_states.items():
                    if quest_id in self.quests:
                        quest = self.quests[quest_id]
                        quest.status = QuestStatus[state.get("status", "NOT_STARTED")]
                        
                        # Restore objective progress
                        objectives_progress = state.get("objectives", [])
                        for obj_progress in objectives_progress:
                            obj_id = obj_progress.get("id")
                            objective = quest.get_objective_by_id(obj_id)
                            if objective:
                                objective.current_amount = obj_progress.get("current_amount", 0)
                                objective.completed = obj_progress.get("completed", False)
                
                print(f"Loaded quest progress from {filename}")
        except Exception as e:
            print(f"Error loading quest progress: {e}")
    
    def get_available_quests(self, player: Character) -> List[Quest]:
        """Get a list of quests available to the player."""
        available_quests = []
        
        for quest_id, quest in self.quests.items():
            # Skip quests that are already active, completed, or failed
            if (quest_id in self.active_quests or 
                quest_id in self.completed_quests or 
                quest_id in self.failed_quests):
                continue
            
            # Check requirements
            if self.can_accept_quest(quest, player):
                available_quests.append(quest)
        
        return available_quests
    
    def can_accept_quest(self, quest: Quest, player: Character) -> bool:
        """Check if a player can accept a quest."""
        # Check level requirement
        if player.level < quest.required_level:
            return False
        
        # Check prerequisite quests
        for required_quest_id in quest.required_quests:
            if required_quest_id not in self.completed_quests:
                return False
        
        # Check faction requirements (would require a faction system)
        if quest.required_faction and quest.required_reputation > 0:
            # This would check player's reputation with the required faction
            # For now, just assume player meets faction requirements
            pass
        
        return True
    
    def activate_quest(self, quest_id: str, player: Character) -> bool:
        """Activate a quest for the player."""
        if quest_id not in self.quests:
            print(f"Quest {quest_id} not found")
            return False
        
        quest = self.quests[quest_id]
        
        # Check if quest can be activated
        if quest_id in self.active_quests:
            print(f"Quest {quest_id} is already active")
            return False
        
        if quest_id in self.completed_quests and not quest.is_repeatable:
            print(f"Quest {quest_id} is already completed and not repeatable")
            return False
        
        if not self.can_accept_quest(quest, player):
            print(f"Cannot accept quest {quest_id}: requirements not met")
            return False
        
        # Activate the quest
        quest.activate()
        self.active_quests.append(quest_id)
        
        # If quest was previously failed, remove from failed list
        if quest_id in self.failed_quests:
            self.failed_quests.remove(quest_id)
        
        # Notify about quest activation
        self.event_bus.publish("quest_activated", {
            "quest_id": quest_id,
            "quest": quest
        })
        
        print(f"Activated quest: {quest.title}")
        return True
    
    def complete_quest(self, quest_id: str, player: Character) -> bool:
        """Complete a quest and give rewards."""
        if quest_id not in self.quests or quest_id not in self.active_quests:
            return False
        
        quest = self.quests[quest_id]
        
        # Check if all objectives are complete
        if not quest.is_complete():
            return False
        
        # Update quest status
        quest.complete()
        self.active_quests.remove(quest_id)
        self.completed_quests.append(quest_id)
        
        # Award rewards
        self._award_quest_rewards(quest, player)
        
        # Notify about quest completion
        self.event_bus.publish("quest_completed", {
            "quest_id": quest_id,
            "quest": quest,
            "rewards": quest.rewards
        })
        
        # Check for any quests that might now be available
        self._check_unlocked_quests(player)
        
        print(f"Completed quest: {quest.title}")
        return True
    
    def fail_quest(self, quest_id: str) -> bool:
        """Fail a quest."""
        if quest_id not in self.quests or quest_id not in self.active_quests:
            return False
        
        quest = self.quests[quest_id]
        
        # Update quest status
        quest.fail()
        self.active_quests.remove(quest_id)
        self.failed_quests.append(quest_id)
        
        # Notify about quest failure
        self.event_bus.publish("quest_failed", {
            "quest_id": quest_id,
            "quest": quest
        })
        
        print(f"Failed quest: {quest.title}")
        return True
    
    def _award_quest_rewards(self, quest: Quest, player: Character):
        """Award the rewards for completing a quest."""
        rewards = quest.rewards
        
        # Award XP
        if rewards.xp > 0:
            player.gain_xp(rewards.xp)
        
        # Award gold
        if rewards.gold > 0:
            player.gold += rewards.gold
        
        # Award items
        for item_data in rewards.items:
            # This would create and add the item to player's inventory
            # Requires item creation system
            pass
        
        # Award reputation
        for faction, amount in rewards.reputation.items():
            # This would update player's reputation with factions
            # Requires faction system
            pass
        
        # Award stat bonuses
        for stat, amount in rewards.stats.items():
            # This would update player's stats
            # Requires stat system that can handle permanent bonuses
            pass
        
        # Unlock quest locations
        for location_id in rewards.unlock_locations:
            self.event_bus.publish("location_unlocked", {
                "location_id": location_id,
                "quest_id": quest.id
            })
        
        # Unlock items
        for item_id in rewards.unlock_items:
            self.event_bus.publish("item_unlocked", {
                "item_id": item_id,
                "quest_id": quest.id
            })
    
    def _check_unlocked_quests(self, player: Character):
        """Check for quests that might be unlocked by completing others."""
        for quest_id, quest in self.quests.items():
            # If quest is not started and all required quests are completed
            if (quest.status == QuestStatus.NOT_STARTED and
                all(req_quest in self.completed_quests for req_quest in quest.required_quests)):
                
                # Notify about newly available quest
                if self.can_accept_quest(quest, player):
                    self.event_bus.publish("quest_available", {
                        "quest_id": quest_id,
                        "quest": quest
                    })
    
    def update_quest_objectives(self, objective_type: ObjectiveType, target: str, amount: int = 1):
        """Update progress on objectives of a certain type and target."""
        updated_quests = []
        
        for quest_id in self.active_quests:
            quest = self.quests[quest_id]
            quest_updated = False
            
            for objective in quest.objectives:
                if objective.type == objective_type and objective.target == target and not objective.is_complete():
                    objective.update_progress(amount)
                    quest_updated = True
            
            if quest_updated:
                updated_quests.append(quest)
                
                # Check if quest is now complete
                if quest.is_complete():
                    self.event_bus.publish("quest_objectives_complete", {
                        "quest_id": quest_id,
                        "quest": quest
                    })
                else:
                    self.event_bus.publish("quest_updated", {
                        "quest_id": quest_id,
                        "quest": quest
                    })
        
        return updated_quests
    
    # Event handlers for different objective types
    def handle_enemy_killed(self, data):
        """Handle enemy killed event."""
        enemy_type = data.get("enemy_type")
        if enemy_type:
            self.update_quest_objectives(ObjectiveType.KILL, enemy_type)
    
    def handle_item_collected(self, data):
        """Handle item collected event."""
        item_id = data.get("item_id")
        amount = data.get("amount", 1)
        if item_id:
            self.update_quest_objectives(ObjectiveType.COLLECT, item_id, amount)
    
    def handle_npc_talked(self, data):
        """Handle NPC talked event."""
        npc_id = data.get("npc_id")
        if npc_id:
            self.update_quest_objectives(ObjectiveType.TALK, npc_id)
    
    def handle_location_visited(self, data):
        """Handle location visited event."""
        location_id = data.get("location_id")
        if location_id:
            self.update_quest_objectives(ObjectiveType.LOCATION, location_id)
    
    def handle_item_crafted(self, data):
        """Handle item crafted event."""
        item_id = data.get("item_id")
        amount = data.get("amount", 1)
        if item_id:
            self.update_quest_objectives(ObjectiveType.CRAFT, item_id, amount)
    
    def handle_item_delivered(self, data):
        """Handle item delivered event."""
        item_id = data.get("item_id")
        npc_id = data.get("npc_id")
        if item_id and npc_id:
            # For delivery quests, the target might be a combination of item and NPC
            self.update_quest_objectives(ObjectiveType.DELIVER, f"{item_id}:{npc_id}")
    
    def handle_structure_built(self, data):
        """Handle structure built event."""
        structure_id = data.get("structure_id")
        if structure_id:
            self.update_quest_objectives(ObjectiveType.BUILD, structure_id)
    
    def handle_boss_defeated(self, data):
        """Handle boss defeated event."""
        boss_id = data.get("boss_id")
        if boss_id:
            self.update_quest_objectives(ObjectiveType.BOSS, boss_id)
    
    def handle_puzzle_solved(self, data):
        """Handle puzzle solved event."""
        puzzle_id = data.get("puzzle_id")
        if puzzle_id:
            self.update_quest_objectives(ObjectiveType.PUZZLE, puzzle_id)
    
    def handle_minigame_completed(self, data):
        """Handle minigame completed event."""
        minigame_id = data.get("minigame_id")
        score = data.get("score", 0)
        success = data.get("success", False)
        
        if minigame_id and success:
            self.update_quest_objectives(ObjectiveType.MINIGAME, minigame_id)


class QuestUI:
    """User interface for the quest system."""
    def __init__(self, screen: pygame.Surface, event_bus: EventBus, quest_manager: QuestManager):
        self.screen = screen
        self.event_bus = event_bus
        self.quest_manager = quest_manager
        
        # UI properties
        self.font_title = pygame.font.Font(None, 32)
        self.font_subtitle = pygame.font.Font(None, 28)
        self.font_text = pygame.font.Font(None, 24)
        self.font_small = pygame.font.Font(None, 20)
        
        self.active_quests_tab_active = True
        self.completed_quests_tab_active = False
        self.quest_details_visible = False
        self.selected_quest_id = None
        
        # UI colors
        self.color_bg = (30, 30, 30)
        self.color_text = (255, 255, 255)
        self.color_highlight = (80, 120, 200)
        self.color_complete = (0, 255, 0)
        self.color_incomplete = (255, 200, 0)
        self.color_failed = (255, 50, 50)
        
        # UI elements
        self.quest_list_rect = pygame.Rect(50, 100, 300, 400)
        self.quest_details_rect = pygame.Rect(400, 100, 500, 400)
        
        self.active_tab_rect = pygame.Rect(50, 70, 150, 30)
        self.completed_tab_rect = pygame.Rect(201, 70, 150, 30)
        
        # Register for events
        self.event_bus.subscribe("quest_activated", self.handle_quest_activated)
        self.event_bus.subscribe("quest_completed", self.handle_quest_completed)
        self.event_bus.subscribe("quest_failed", self.handle_quest_failed)
        self.event_bus.subscribe("quest_updated", self.handle_quest_updated)
    
    def draw(self):
        """Draw the quest UI."""
        # Background
        pygame.draw.rect(self.screen, self.color_bg, pygame.Rect(30, 50, 900, 500))
        pygame.draw.rect(self.screen, (50, 50, 50), pygame.Rect(30, 50, 900, 500), 2)
        
        # Title
        title_text = self.font_title.render("Quest Journal", True, self.color_text)
        self.screen.blit(title_text, (50, 30))
        
        # Tabs
        active_color = self.color_highlight if self.active_quests_tab_active else (50, 50, 50)
        completed_color = self.color_highlight if self.completed_quests_tab_active else (50, 50, 50)
        
        pygame.draw.rect(self.screen, active_color, self.active_tab_rect)
        pygame.draw.rect(self.screen, completed_color, self.completed_tab_rect)
        
        active_text = self.font_text.render("Active Quests", True, self.color_text)
        completed_text = self.font_text.render("Completed Quests", True, self.color_text)
        
        self.screen.blit(active_text, (self.active_tab_rect.centerx - active_text.get_width()//2, 
                                      self.active_tab_rect.centery - active_text.get_height()//2))
        self.screen.blit(completed_text, (self.completed_tab_rect.centerx - completed_text.get_width()//2, 
                                         self.completed_tab_rect.centery - completed_text.get_height()//2))
        
        # Quest list
        pygame.draw.rect(self.screen, (40, 40, 40), self.quest_list_rect)
        pygame.draw.rect(self.screen, (100, 100, 100), self.quest_list_rect, 2)
        
        if self.active_quests_tab_active:
            self._draw_active_quests()
        else:
            self._draw_completed_quests()
        
        # Quest details
        if self.quest_details_visible and self.selected_quest_id:
            pygame.draw.rect(self.screen, (40, 40, 40), self.quest_details_rect)
            pygame.draw.rect(self.screen, (100, 100, 100), self.quest_details_rect, 2)
            
            self._draw_quest_details()
    
    def _draw_active_quests(self):
        """Draw the list of active quests."""
        y_offset = self.quest_list_rect.top + 10
        
        # Draw active quests
        if not self.quest_manager.active_quests:
            no_quests_text = self.font_text.render("No active quests", True, self.color_text)
            self.screen.blit(no_quests_text, (self.quest_list_rect.centerx - no_quests_text.get_width()//2, 
                                           self.quest_list_rect.centery - no_quests_text.get_height()//2))
            return
        
        for quest_id in self.quest_manager.active_quests:
            quest = self.quest_manager.quests.get(quest_id)
            if quest:
                # Quest title with highlight if selected
                if quest_id == self.selected_quest_id:
                    pygame.draw.rect(self.screen, self.color_highlight, 
                                    pygame.Rect(self.quest_list_rect.left + 5, y_offset - 5, 
                                               self.quest_list_rect.width - 10, 30))
                
                # Draw quest type icon or color indicator
                if quest.type == QuestType.MAIN:
                    pygame.draw.circle(self.screen, (255, 255, 0), 
                                       (self.quest_list_rect.left + 15, y_offset + 10), 8)
                elif quest.type == QuestType.SIDE:
                    pygame.draw.circle(self.screen, (0, 200, 255), 
                                       (self.quest_list_rect.left + 15, y_offset + 10), 8)
                else:
                    pygame.draw.circle(self.screen, (200, 200, 200), 
                                       (self.quest_list_rect.left + 15, y_offset + 10), 8)
                
                # Quest title
                title_text = self.font_text.render(quest.title, True, self.color_text)
                self.screen.blit(title_text, (self.quest_list_rect.left + 30, y_offset))
                
                # Progress
                progress = quest.get_progress() * 100
                progress_text = self.font_small.render(f"{progress:.0f}%", True, self.color_text)
                self.screen.blit(progress_text, (self.quest_list_rect.right - progress_text.get_width() - 10, y_offset))
                
                y_offset += 35
    
    def _draw_completed_quests(self):
        """Draw the list of completed quests."""
        y_offset = self.quest_list_rect.top + 10
        
        # Draw completed quests
        if not self.quest_manager.completed_quests:
            no_quests_text = self.font_text.render("No completed quests", True, self.color_text)
            self.screen.blit(no_quests_text, (self.quest_list_rect.centerx - no_quests_text.get_width()//2, 
                                           self.quest_list_rect.centery - no_quests_text.get_height()//2))
            return
        
        for quest_id in self.quest_manager.completed_quests:
            quest = self.quest_manager.quests.get(quest_id)
            if quest:
                # Quest title with highlight if selected
                if quest_id == self.selected_quest_id:
                    pygame.draw.rect(self.screen, self.color_highlight, 
                                    pygame.Rect(self.quest_list_rect.left + 5, y_offset - 5, 
                                               self.quest_list_rect.width - 10, 30))
                
                # Draw quest type icon or color indicator
                if quest.type == QuestType.MAIN:
                    pygame.draw.circle(self.screen, (255, 255, 0), 
                                       (self.quest_list_rect.left + 15, y_offset + 10), 8)
                elif quest.type == QuestType.SIDE:
                    pygame.draw.circle(self.screen, (0, 200, 255), 
                                       (self.quest_list_rect.left + 15, y_offset + 10), 8)
                else:
                    pygame.draw.circle(self.screen, (200, 200, 200), 
                                       (self.quest_list_rect.left + 15, y_offset + 10), 8)
                
                # Quest title
                title_text = self.font_text.render(quest.title, True, self.color_complete)
                self.screen.blit(title_text, (self.quest_list_rect.left + 30, y_offset))
                
                y_offset += 35
    
    def _draw_quest_details(self):
        """Draw the details of the selected quest."""
        if not self.selected_quest_id or self.selected_quest_id not in self.quest_manager.quests:
            return
        
        quest = self.quest_manager.quests[self.selected_quest_id]
        x_start = self.quest_details_rect.left + 20
        y_offset = self.quest_details_rect.top + 20
        
        # Quest title
        title_text = self.font_subtitle.render(quest.title, True, self.color_text)
        self.screen.blit(title_text, (x_start, y_offset))
        y_offset += 35
        
        # Quest level and type
        type_text = self.font_small.render(f"Level {quest.level} {quest.type.name} Quest", True, self.color_text)
        self.screen.blit(type_text, (x_start, y_offset))
        y_offset += 25
        
        # Quest description
        self._draw_wrapped_text(quest.description, x_start, y_offset, self.quest_details_rect.width - 40, self.font_text)
        y_offset += 60  # Adjust based on description length
        
        # Objectives header
        objectives_text = self.font_subtitle.render("Objectives", True, self.color_text)
        self.screen.blit(objectives_text, (x_start, y_offset))
        y_offset += 30
        
        # Objectives list
        for objective in quest.objectives:
            # Status icon
            if objective.is_complete():
                pygame.draw.rect(self.screen, self.color_complete, pygame.Rect(x_start, y_offset + 8, 10, 10))
            else:
                pygame.draw.rect(self.screen, self.color_incomplete, pygame.Rect(x_start, y_offset + 8, 10, 10))
            
            # Objective description
            obj_text = self.font_text.render(objective.description, True, 
                                           self.color_complete if objective.is_complete() else self.color_text)
            self.screen.blit(obj_text, (x_start + 20, y_offset))
            
            # Progress indicator for countable objectives
            if objective.required_amount > 1:
                progress_text = self.font_small.render(f"{objective.current_amount}/{objective.required_amount}", 
                                                    True, self.color_text)
                self.screen.blit(progress_text, (self.quest_details_rect.right - 50, y_offset))
            
            y_offset += 30
        
# Rewards header
        y_offset += 10
        rewards_text = self.font_subtitle.render("Rewards", True, self.color_text)
        self.screen.blit(rewards_text, (x_start, y_offset))
        y_offset += 30
        
        # Display rewards
        rewards = quest.rewards
        
        if rewards.xp > 0:
            xp_text = self.font_text.render(f"XP: {rewards.xp}", True, self.color_text)
            self.screen.blit(xp_text, (x_start, y_offset))
            y_offset += 25
        
        if rewards.gold > 0:
            gold_text = self.font_text.render(f"Gold: {rewards.gold}", True, self.color_text)
            self.screen.blit(gold_text, (x_start, y_offset))
            y_offset += 25
        
        if rewards.items:
            items_text = self.font_text.render("Items:", True, self.color_text)
            self.screen.blit(items_text, (x_start, y_offset))
            y_offset += 25
            
            for item in rewards.items:
                item_name = item.get("name", "Unknown Item")
                item_text = self.font_small.render(f"- {item_name}", True, self.color_text)
                self.screen.blit(item_text, (x_start + 20, y_offset))
                y_offset += 20
    
    def _draw_wrapped_text(self, text: str, x: int, y: int, max_width: int, font: pygame.font.Font, color=(255, 255, 255)):
        """Draw text that wraps if it exceeds the max width."""
        words = text.split(' ')
        lines = []
        current_line = []
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            test_width = font.size(test_line)[0]
            
            if test_width <= max_width:
                current_line.append(word)
            else:
                lines.append(' '.join(current_line))
                current_line = [word]
        
        if current_line:
            lines.append(' '.join(current_line))
        
        line_height = font.get_linesize()
        for i, line in enumerate(lines):
            rendered_line = font.render(line, True, color)
            self.screen.blit(rendered_line, (x, y + i * line_height))
    
    def handle_event(self, event):
        """Handle UI events."""
        if event.type == pygame.MOUSEBUTTONDOWN:
            # Handle tab clicks
            if self.active_tab_rect.collidepoint(event.pos):
                self.active_quests_tab_active = True
                self.completed_quests_tab_active = False
                self.selected_quest_id = None
                self.quest_details_visible = False
            
            elif self.completed_tab_rect.collidepoint(event.pos):
                self.active_quests_tab_active = False
                self.completed_quests_tab_active = True
                self.selected_quest_id = None
                self.quest_details_visible = False
            
            # Handle quest list clicks
            elif self.quest_list_rect.collidepoint(event.pos):
                self._handle_quest_selection(event.pos[1])
    
    def _handle_quest_selection(self, y_pos):
        """Handle selecting a quest from the list."""
        y_offset = self.quest_list_rect.top + 10
        quest_list = self.quest_manager.active_quests if self.active_quests_tab_active else self.quest_manager.completed_quests
        
        for quest_id in quest_list:
            # Check if click is within this quest's row
            if y_pos >= y_offset and y_pos < y_offset + 35:
                self.selected_quest_id = quest_id
                self.quest_details_visible = True
                break
            
            y_offset += 35
    
    def handle_quest_activated(self, data):
        """Handle quest activated event."""
        # Update the UI when a quest is activated
        if self.active_quests_tab_active:
            # If we're on the active quests tab, immediately select the new quest
            self.selected_quest_id = data.get("quest_id")
            self.quest_details_visible = True
    
    def handle_quest_completed(self, data):
        """Handle quest completed event."""
        quest_id = data.get("quest_id")
        
        # If the completed quest was selected, update the UI
        if quest_id == self.selected_quest_id and self.active_quests_tab_active:
            # Switch to completed quests tab and keep the quest selected
            self.active_quests_tab_active = False
            self.completed_quests_tab_active = True
    
    def handle_quest_failed(self, data):
        """Handle quest failed event."""
        quest_id = data.get("quest_id")
        
        # If the failed quest was selected, hide the details
        if quest_id == self.selected_quest_id:
            self.selected_quest_id = None
            self.quest_details_visible = False
    
    def handle_quest_updated(self, data):
        """Handle quest updated event."""
        # Update the UI when a quest's objectives are updated
        pass  # The UI will automatically show the updated status on next draw


class QuestMarker:
    """A visual indicator for quest-related locations on the map."""
    def __init__(self, position: Tuple[int, int], quest_id: str, marker_type: str):
        self.position = position
        self.quest_id = quest_id
        self.marker_type = marker_type  # 'start', 'objective', 'complete'
        
        # Appearance
        self.radius = 10
        self.pulsing = True
        self.pulse_speed = 0.05
        self.pulse_min = 0.7
        self.pulse_max = 1.3
        self.pulse_factor = 1.0
        self.pulse_direction = 1
        
        # Colors for different types
        self.colors = {
            'start': (255, 255, 0),       # Yellow for quest start
            'objective': (0, 200, 255),   # Blue for objectives
            'complete': (0, 255, 0),      # Green for completion
            'main': (255, 200, 0),        # Gold for main quests
            'side': (200, 200, 200)       # Silver for side quests
        }
    
    def update(self, dt: float):
        """Update the marker animation."""
        if self.pulsing:
            self.pulse_factor += self.pulse_direction * self.pulse_speed * dt
            
            if self.pulse_factor >= self.pulse_max:
                self.pulse_factor = self.pulse_max
                self.pulse_direction = -1
            elif self.pulse_factor <= self.pulse_min:
                self.pulse_factor = self.pulse_min
                self.pulse_direction = 1
    
    def draw(self, surface: pygame.Surface, camera_offset: Tuple[int, int] = (0, 0)):
        """Draw the marker on the surface."""
        # Apply camera offset
        x = self.position[0] - camera_offset[0]
        y = self.position[1] - camera_offset[1]
        
        # Base color
        color = self.colors.get(self.marker_type, (255, 255, 255))
        
        # Draw pulsing circle
        radius = int(self.radius * self.pulse_factor)
        
        # Draw outer glow
        glow_surf = pygame.Surface((radius * 2 + 4, radius * 2 + 4), pygame.SRCALPHA)
        for i in range(3):
            alpha = 100 - i * 30
            pygame.draw.circle(glow_surf, (*color, alpha), (radius + 2, radius + 2), radius - i)
        
        surface.blit(glow_surf, (x - radius - 2, y - radius - 2))
        
        # Draw main circle
        pygame.draw.circle(surface, color, (x, y), radius)
        pygame.draw.circle(surface, (255, 255, 255), (x, y), radius, 2)
        
        # Draw icon based on type
        if self.marker_type == 'start':
            # Exclamation mark
            pygame.draw.line(surface, (0, 0, 0), (x, y - 5), (x, y + 2), 2)
            pygame.draw.circle(surface, (0, 0, 0), (x, y + 5), 1)
        elif self.marker_type == 'objective':
            # Question mark
            pygame.draw.arc(surface, (0, 0, 0), (x - 3, y - 5, 6, 6), 0, 4.7, 2)
            pygame.draw.circle(surface, (0, 0, 0), (x, y + 3), 1)
        elif self.marker_type == 'complete':
            # Checkmark
            pygame.draw.line(surface, (0, 0, 0), (x - 3, y), (x, y + 3), 2)
            pygame.draw.line(surface, (0, 0, 0), (x, y + 3), (x + 4, y - 4), 2)


class QuestMarkerManager:
    """Manages all quest markers on the map."""
    def __init__(self, quest_manager: QuestManager):
        self.quest_manager = quest_manager
        self.markers: Dict[str, QuestMarker] = {}  # marker_id -> QuestMarker
        
        # Subscribe to events
        quest_manager.event_bus.subscribe("quest_activated", self.handle_quest_activated)
        quest_manager.event_bus.subscribe("quest_updated", self.handle_quest_updated)
        quest_manager.event_bus.subscribe("quest_completed", self.handle_quest_completed)
        quest_manager.event_bus.subscribe("quest_failed", self.handle_quest_failed)
    
    def add_marker(self, position: Tuple[int, int], quest_id: str, objective_id: str = None, marker_type: str = 'start'):
        """Add a new quest marker."""
        marker_id = f"{quest_id}:{objective_id}" if objective_id else quest_id
        self.markers[marker_id] = QuestMarker(position, quest_id, marker_type)
    
    def remove_marker(self, marker_id: str):
        """Remove a quest marker."""
        if marker_id in self.markers:
            del self.markers[marker_id]
    
    def update_markers(self, dt: float):
        """Update all markers."""
        for marker in self.markers.values():
            marker.update(dt)
    
    def draw_markers(self, surface: pygame.Surface, camera_offset: Tuple[int, int] = (0, 0)):
        """Draw all markers."""
        for marker in self.markers.values():
            marker.draw(surface, camera_offset)
    
    def handle_quest_activated(self, data):
        """Handle quest activation event."""
        quest_id = data.get("quest_id")
        quest = data.get("quest")
        
        # Add marker for quest giver if available
        # This would require a reference to the NPC's position
        # For now, we'll just add a placeholder marker
        self.add_marker((random.randint(100, 700), random.randint(100, 500)), quest_id, marker_type='start')
        
        # Add markers for initial objectives
        for objective in quest.objectives:
            if objective.coordinates:
                marker_id = f"{quest_id}:{objective.id}"
                self.add_marker(objective.coordinates, quest_id, objective.id, marker_type='objective')
    
    def handle_quest_updated(self, data):
        """Handle quest update event."""
        quest_id = data.get("quest_id")
        quest = data.get("quest")
        
        # Update markers for completed objectives
        for objective in quest.objectives:
            if objective.is_complete() and objective.coordinates:
                marker_id = f"{quest_id}:{objective.id}"
                if marker_id in self.markers:
                    self.markers[marker_id].marker_type = 'complete'
    
    def handle_quest_completed(self, data):
        """Handle quest completion event."""
        quest_id = data.get("quest_id")
        
        # Remove all markers for this quest
        markers_to_remove = [marker_id for marker_id in self.markers if marker_id.startswith(f"{quest_id}:")]
        for marker_id in markers_to_remove:
            self.remove_marker(marker_id)
        
        # Add a completion marker if quest receiver is available
        # Again, this would require NPC position data
        self.add_marker((random.randint(100, 700), random.randint(100, 500)), quest_id, marker_type='complete')
    
    def handle_quest_failed(self, data):
        """Handle quest failure event."""
        quest_id = data.get("quest_id")
        
        # Remove all markers for this quest
        markers_to_remove = [marker_id for marker_id in self.markers if marker_id.startswith(f"{quest_id}:")]
        for marker_id in markers_to_remove:
            self.remove_marker(marker_id)


class QuestNotification:
    """A notification that appears when quest status changes."""
    def __init__(self, message: str, quest_type: QuestType = None, duration: float = 5.0):
        self.message = message
        self.quest_type = quest_type
        self.duration = duration
        self.time_remaining = duration
        self.font = pygame.font.Font(None, 28)
        self.position = (50, 50)  # Default position
        self.alpha = 255  # For fade-in/out effects
        
        # Colors based on quest type
        self.colors = {
            QuestType.MAIN: (255, 215, 0),    # Gold for main quests
            QuestType.SIDE: (100, 149, 237),  # Cornflower blue for side quests
            QuestType.FACTION: (138, 43, 226), # Purple for faction quests
            QuestType.WORLD: (46, 139, 87),   # Sea green for world quests
            QuestType.DAILY: (255, 127, 80),  # Coral for daily quests
            QuestType.SPECIAL: (255, 105, 180)  # Hot pink for special quests
        }
        
        self.color = self.colors.get(quest_type, (255, 255, 255))
    
    def update(self, dt: float) -> bool:
        """Update the notification. Return False when expired."""
        self.time_remaining -= dt
        
        # Fade out in the last second
        if self.time_remaining < 1.0:
            self.alpha = int(255 * self.time_remaining)
        
        return self.time_remaining > 0
    
    def draw(self, surface: pygame.Surface):
        """Draw the notification."""
        # Background
        bg_rect = pygame.Rect(self.position[0], self.position[1], 400, 70)
        bg_surf = pygame.Surface((bg_rect.width, bg_rect.height), pygame.SRCALPHA)
        bg_surf.fill((0, 0, 0, 180))  # Semi-transparent black
        
        # Border
        border_surf = pygame.Surface((bg_rect.width, bg_rect.height), pygame.SRCALPHA)
        pygame.draw.rect(border_surf, (*self.color, 200), pygame.Rect(0, 0, bg_rect.width, bg_rect.height), 2)
        
        # Icon/indicator
        pygame.draw.rect(border_surf, (*self.color, 200), pygame.Rect(0, 0, 10, bg_rect.height))
        
        # Apply alpha for fading
        bg_surf.set_alpha(self.alpha)
        border_surf.set_alpha(self.alpha)
        
        surface.blit(bg_surf, bg_rect)
        surface.blit(border_surf, bg_rect)
        
        # Text with alpha
        text_surf = self.font.render(self.message, True, self.color)
        text_surf.set_alpha(self.alpha)
        surface.blit(text_surf, (bg_rect.x + 20, bg_rect.y + 20))


class QuestNotificationManager:
    """Manages quest notifications."""
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.notifications: List[QuestNotification] = []
        self.max_notifications = 3
        
        # Register event handlers
        self.event_bus.subscribe("quest_activated", self.handle_quest_activated)
        self.event_bus.subscribe("quest_objectives_complete", self.handle_quest_objectives_complete)
        self.event_bus.subscribe("quest_completed", self.handle_quest_completed)
        self.event_bus.subscribe("quest_failed", self.handle_quest_failed)
        self.event_bus.subscribe("quest_available", self.handle_quest_available)
    
    def add_notification(self, message: str, quest_type: QuestType = None, duration: float = 5.0):
        """Add a new notification."""
        notification = QuestNotification(message, quest_type, duration)
        
        # Limit number of notifications
        if len(self.notifications) >= self.max_notifications:
            self.notifications.pop(0)  # Remove oldest
        
        self.notifications.append(notification)
    
    def update(self, dt: float):
        """Update all notifications."""
        # Update and remove expired notifications
        self.notifications = [n for n in self.notifications if n.update(dt)]
        
        # Update positions
        for i, notification in enumerate(self.notifications):
            notification.position = (50, 50 + i * 80)
    
    def draw(self, surface: pygame.Surface):
        """Draw all notifications."""
        for notification in self.notifications:
            notification.draw(surface)
    
    # Event handlers
    def handle_quest_activated(self, data):
        """Handle quest activated event."""
        quest = data.get("quest")
        self.add_notification(f"Quest Started: {quest.title}", quest.type, 5.0)
    
    def handle_quest_objectives_complete(self, data):
        """Handle quest objectives completed event."""
        quest = data.get("quest")
        self.add_notification(f"Quest Objectives Complete: {quest.title}", quest.type, 5.0)
    
    def handle_quest_completed(self, data):
        """Handle quest completed event."""
        quest = data.get("quest")
        self.add_notification(f"Quest Completed: {quest.title}", quest.type, 7.0)
    
    def handle_quest_failed(self, data):
        """Handle quest failed event."""
        quest = data.get("quest")
        self.add_notification(f"Quest Failed: {quest.title}", quest.type, 5.0)
    
    def handle_quest_available(self, data):
        """Handle new quest available event."""
        quest = data.get("quest")
        self.add_notification(f"New Quest Available: {quest.title}", quest.type, 5.0)


# Example quest creation function for testing
def create_test_quests(quest_manager: QuestManager):
    """Create some test quests for development."""
    # Create a simple collection quest
    collection_objective = QuestObjective(
        id="collect_herbs",
        type=ObjectiveType.COLLECT,
        description="Collect medicinal herbs",
        target="herb_item",
        required_amount=5
    )
    
    collect_quest = Quest(
        id="herb_collection",
        title="Medicinal Needs",
        description="The village healer needs medicinal herbs to treat the sick. Collect 5 herbs from the forest.",
        type=QuestType.SIDE,
        level=1,
        objectives=[collection_objective],
        rewards=QuestReward(xp=100, gold=50)
    )
    
    # Create a kill quest
    kill_objective = QuestObjective(
        id="kill_wolves",
        type=ObjectiveType.KILL,
        description="Defeat the wolf pack",
        target="wolf_enemy",
        required_amount=3
    )
    
    kill_quest = Quest(
        id="wolf_hunt",
        title="Wolf Problem",
        description="Wolves have been attacking the village livestock. Defeat 3 wolves to protect the village.",
        type=QuestType.SIDE,
        level=2,
        objectives=[kill_objective],
        rewards=QuestReward(xp=150, gold=100)
    )
    
    # Create a multi-objective main quest
    talk_objective = QuestObjective(
        id="talk_to_elder",
        type=ObjectiveType.TALK,
        description="Speak with Village Elder",
        target="elder_npc"
    )
    
    location_objective = QuestObjective(
        id="find_ancient_temple",
        type=ObjectiveType.LOCATION,
        description="Locate the Ancient Temple",
        target="temple_location",
        coordinates=(500, 300)
    )
    
    artifact_objective = QuestObjective(
        id="retrieve_artifact",
        type=ObjectiveType.COLLECT,
        description="Retrieve the Ancient Artifact",
        target="ancient_artifact"
    )
    
    boss_objective = QuestObjective(
        id="defeat_guardian",
        type=ObjectiveType.BOSS,
        description="Defeat the Temple Guardian",
        target="temple_guardian"
    )
    
    main_quest = Quest(
        id="artifact_retrieval",
        title="The Ancient Artifact",
        description="The village is threatened by an ancient curse. You must retrieve an artifact from the Ancient Temple to break the curse.",
        type=QuestType.MAIN,
        level=5,
        objectives=[talk_objective, location_objective, artifact_objective, boss_objective],
        rewards=QuestReward(
            xp=500,
            gold=250,
            items=[{"id": "magic_amulet", "name": "Amulet of Protection"}],
            unlock_quests=["curse_removal"]
        )
    )
    
    # Add quests to quest manager
    quest_manager.quests[collect_quest.id] = collect_quest
    quest_manager.quests[kill_quest.id] = kill_quest
    quest_manager.quests[main_quest.id] = main_quest


# Example usage
if __name__ == "__main__":
    pygame.init()
    screen = pygame.display.set_mode((1024, 768))
    pygame.display.set_caption("Quest System Demo")
    clock = pygame.time.Clock()
    
    # Create systems
    event_bus = EventBus()
    quest_manager = QuestManager(event_bus)
    
    # Create test quests
    create_test_quests(quest_manager)
    
    # Create a mock player for testing
    from dataclasses import dataclass
    
    @dataclass
    class MockPlayer:
        level: int = 5
        gold: int = 100
        
        def gain_xp(self, amount):
            print(f"Player gained {amount} XP")
    
    player = MockPlayer()
    
    # Create UI systems
    quest_ui = QuestUI(screen, event_bus, quest_manager)
    marker_manager = QuestMarkerManager(quest_manager)
    notification_manager = QuestNotificationManager(event_bus)
    
    # Activate some quests for testing
    quest_manager.activate_quest("herb_collection", player)
    quest_manager.activate_quest("wolf_hunt", player)
    
    # Manually update some objectives for testing
    herb_quest = quest_manager.quests["herb_collection"]
    herb_objective = herb_quest.get_objective_by_id("collect_herbs")
    herb_objective.update_progress(2)  # Collected 2 herbs
    
    # Main loop
    running = True
    while running:
        dt = clock.tick(60) / 1000.0  # Delta time in seconds
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                # Test progress updates
                elif event.key == pygame.K_h:
                    # Update herb collection
                    event_bus.publish("item_collected", {"item_id": "herb_item", "amount": 1})
                elif event.key == pygame.K_w:
                    # Update wolf kills
                    event_bus.publish("enemy_killed", {"enemy_type": "wolf_enemy"})
                elif event.key == pygame.K_c:
                    # Complete selected quest
                    if quest_ui.selected_quest_id:
                        selected_quest = quest_manager.quests[quest_ui.selected_quest_id]
                        for objective in selected_quest.objectives:
                            objective.current_amount = objective.required_amount
                        quest_manager.complete_quest(quest_ui.selected_quest_id, player)
                elif event.key == pygame.K_n:
                    # Activate main quest
                    quest_manager.activate_quest("artifact_retrieval", player)
            
            # Handle UI events
            quest_ui.handle_event(event)
        
        # Update
        marker_manager.update_markers(dt)
        notification_manager.update(dt)
        
        # Draw
        screen.fill((20, 20, 30))
        
        # Draw markers (would normally be on the game world)
        marker_manager.draw_markers(screen)
        
        # Draw UI
        quest_ui.draw()
        notification_manager.draw(screen)
        
        # Draw instructions
        font = pygame.font.Font(None, 24)
        instructions = [
            "Controls:",
            "H - Collect herbs",
            "W - Kill wolves",
            "C - Complete selected quest",
            "N - Activate main quest",
            "Click tabs and quests to navigate"
        ]
        
        for i, instruction in enumerate(instructions):
            text = font.render(instruction, True, (200, 200, 200))
            screen.blit(text, (750, 50 + i * 25))
        
        pygame.display.flip()
    
    pygame.quit()