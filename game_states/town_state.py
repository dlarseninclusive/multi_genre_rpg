import pygame
import logging
import random
import math
from enum import Enum
from game_state import GameState
from world_generator import Location, LocationType
from ui_system import UIManager, UIButton, UILabel, UIPanel, UIImage, UIProgressBar
from quest_system import QuestManager, QuestStatus, QuestType, ObjectiveType, Quest, QuestUI
from character import Character, Race, CharacterClass
from faction_system.faction_system import RelationshipStatus, FactionType

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
        Initialize a building.
        
        Args:
            building_type: Type from BuildingType enum
            name: Building name
            position: (x, y) tuple for grid position
            size: (width, height) tuple for grid size
        """
        self.building_type = building_type
        self.name = name
        self.position = position
        self.size = size
        self.npcs = []
        self.accessible = True
        self.services = []
        self.entrance = None
        self.interior_map = None
        self.is_player_inside = False
        self.discovered = False
        
        # Calculate entrance position (middle of bottom edge)
        x = position[0] + (size[0] // 2)
        y = position[1] + size[1]
        self.entrance = (x, y)
    
    def get_rect(self, tile_size):
        """
        Get building rectangle.
        
        Args:
            tile_size: Size of each tile
        
        Returns:
            Pygame Rect
        """
        x = self.position[0] * tile_size
        y = self.position[1] * tile_size
        width = self.size[0] * tile_size
        height = self.size[1] * tile_size
        return pygame.Rect(x, y, width, height)
    
    def add_npc(self, npc):
        """
        Add an NPC to this building.
        
        Args:
            npc: Npc instance
        """
        self.npcs.append(npc)
        npc.building = self

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
        self.faction_id = None  # Added for faction system integration
    
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
        # For collision detection
        size = 20
        x = self.position[0] - size // 2
        y = self.position[1] - size // 2
        return pygame.Rect(x, y, size, size)

class TownState(GameState):
    """Game state for town exploration."""
    
    def __init__(self, state_manager, event_bus, settings):
        """
        Initialize town state.
        
        Args:
            state_manager: StateManager instance
            event_bus: EventBus instance
            settings: Settings instance
        """
        super().__init__(state_manager, event_bus, settings)
        
        self.font = pygame.font.Font(None, 36)
        self.small_font = pygame.font.Font(None, 24)
        
        # Town grid properties
        self.grid_width = 40
        self.grid_height = 30
        self.tile_size = 30
        
        # Town generation properties
        self.town_name = "Unnamed Town"
        self.town_type = None
        self.buildings = []
        self.npcs = []
        self.map_tiles = []  # 2D grid of tile types
        
        # Camera and player position
        self.camera_offset = [0, 0]
        self.player_grid_pos = [10, 10]  # Starting position in grid coordinates
        self.player_moving = False
        self.player_target = None
        self.player_path = []
        
        # UI elements
        self.screen = None  # Will be set in render
        self.ui_manager = None  # Will be initialized when we have a screen
        self.status_panel = None
        self.dialog_panel = None
        self.dialog_text = None
        self.dialog_npc = None
        self.dialog_options = []
        
        # Quest system
        self.quest_manager = None
        self.quest_ui = None  # Initialize the quest UI reference
        self.quest_journal_visible = False  # To track if the journal is visible
        self.current_quest = None  # Current quest being offered
        
        # Faction system
        self.faction_manager = None
        self.town_faction_id = None  # Controlling faction for the town
        self.laws_panel = None
        self.faction_info_visible = False
        
        # Load tile graphics
        self._load_graphics()
        
        logger.info("TownState initialized")
    
    def _load_graphics(self):
        """Load game graphics."""
        try:
            # Try to load tiles from assets folder
            self.tile_images = {
                'grass': pygame.image.load('assets/tiles/grass.png').convert_alpha(),
                'road': pygame.image.load('assets/tiles/road.png').convert_alpha(),
                'water': pygame.image.load('assets/tiles/water.png').convert_alpha(),
                'building': pygame.image.load('assets/tiles/building.png').convert_alpha(),
                'roof': pygame.image.load('assets/tiles/roof.png').convert_alpha(),
                'player': pygame.image.load('assets/characters/player.png').convert_alpha(),
                'npc': pygame.image.load('assets/characters/npc.png').convert_alpha(),
            }
        except (pygame.error, FileNotFoundError) as e:
            # If graphics loading fails, fall back to simple rendering
            logger.warning(f"Failed to load graphics: {e}. Using simple rendering.")
            self.tile_images = {}
    
    def enter(self, previous_state=None):
        """Enter this state."""
        super().enter(previous_state)
        
        # Get the quest manager from persistent data
        self.quest_manager = self.state_manager.get_persistent_data("quest_manager")
        
        # Get the faction manager from persistent data
        self.faction_manager = self.state_manager.get_persistent_data("faction_manager")
        
        # Initialize town if not already done
        if not self.buildings:
            self._generate_town()
        
        # Set up quest NPCs with available quests
        self._setup_npc_quests()
        
        # Update town's faction information
        self._update_town_faction_info()
        
        # Notify faction system that player entered this territory
        if self.town_faction_id and self.faction_manager:
            self.event_bus.publish("territory_entered", {
                "location_id": self.town_name.lower().replace(" ", "_"),
                "name": self.town_name
            })
        
        logger.info(f"Entered town: {self.town_name}")
    
    def exit(self):
        """Exit this state."""
        # Clean up UI elements
        if self.ui_manager:
            self.ui_manager.clear()
        super().exit()
    
    def update(self, dt):
        """
        Update town state.
        
        Args:
            dt: Time delta in seconds
        """
        # Update UI if available
        if self.ui_manager:
            self.ui_manager.update(dt)
        
        # Update player movement
        self._update_player_movement(dt)
        
        # Update camera position to follow player
        self._update_camera()
    
    def handle_event(self, event):
        """
        Handle events.
        
        Args:
            event: Pygame event
        """
        # If quest journal is open, let it handle events first
        if self.quest_journal_visible and self.quest_ui:
            self.quest_ui.handle_event(event)
            
            # Close journal on ESC key
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.quest_journal_visible = False
                return
            
            # Don't let other UI elements handle events while journal is open
            return
        
        # If faction info is visible, handle ESC key to close it
        if self.faction_info_visible:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.faction_info_visible = False
                return
        
        # Handle UI events if UI manager exists
        if self.ui_manager and self.ui_manager.handle_event(event):
            return
        
        # Handle mouse clicks
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Convert screen coordinates to world coordinates
            world_x = event.pos[0] + self.camera_offset[0]
            world_y = event.pos[1] + self.camera_offset[1]
            
            # Check for NPC clicks
            for npc in self.npcs:
                npc_rect = npc.get_rect()
                if npc_rect.collidepoint(world_x, world_y):
                    self._interact_with_npc(npc)
                    return
            
            # Check for building clicks
            for building in self.buildings:
                building_rect = building.get_rect(self.tile_size)
                if building_rect.collidepoint(world_x, world_y):
                    self._interact_with_building(building)
                    return
            
            # Otherwise, move player to clicked position
            grid_x = world_x // self.tile_size
            grid_y = world_y // self.tile_size
            
            # Ensure we're within the map bounds
            if 0 <= grid_x < self.grid_width and 0 <= grid_y < self.grid_height:
                self.player_target = [grid_x, grid_y]
                self.player_moving = True
        
        # Handle keyboard events
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                # Open pause menu
                self.state_manager.push_state("pause_menu")
            elif event.key == pygame.K_j:
                # Toggle quest journal
                self._toggle_quest_journal()
            elif event.key == pygame.K_f:
                # Toggle faction info
                self._toggle_faction_info()
            elif event.key == pygame.K_w:
                # Return to world map
                self.state_manager.change_state("world_exploration")
    
    def render(self, screen):
        """Render the town."""
        # Store screen for future use if we don't have it yet
        if not hasattr(self, 'screen') or self.screen is None:
            self.screen = screen
            
            # Initialize UI if we now have a screen
            if self.ui_manager is None:
                self.ui_manager = UIManager(self.screen)
                self._create_status_panel()
    
        # Clear screen
        screen.fill((0, 0, 0))
        
        # Render town grid
        self._render_town_grid()
        
        # Render buildings
        self._render_buildings()
        
        # Render NPCs
        self._render_npcs()
        
        # Render player
        self._render_player()
        
        # Render UI if available
        if self.ui_manager:
            self.ui_manager.render()
        
        # Render the quest journal if visible
        if self.quest_journal_visible and self.quest_ui:
            self.quest_ui.draw()
            
        # Render faction information if visible
        if self.faction_info_visible:
            self._render_faction_info()
    
    def _create_status_panel(self):
        """Create the status panel UI."""
        if self.ui_manager is None:
            return
            
        panel_rect = pygame.Rect(10, 10, 300, 80)
        self.status_panel = self.ui_manager.create_panel(panel_rect)
        
        # Town name label
        self.ui_manager.create_label(
            pygame.Rect(10, 10, 280, 30),
            self.town_name,
            self.status_panel
        )
        
        # If we have faction information, show it
        if self.town_faction_id and self.faction_manager:
            faction = self.faction_manager.get_faction(self.town_faction_id)
            faction_label_text = f"Controlled by: {faction.name}"
            
            faction_label = self.ui_manager.create_label(
                pygame.Rect(10, 45, 280, 25),
                faction_label_text,
                self.status_panel
            )
            
            # Set the label color to match the faction's primary color
            faction_label.text_color = faction.primary_color
    
    def _generate_town(self):
        """Generate a random town."""
        self.town_name = "Riverdale"  # TODO: Generate random name
        self.town_type = LocationType.TOWN
        
        # Create grid
        self.map_tiles = [[0 for _ in range(self.grid_width)] for _ in range(self.grid_height)]
        
        # Create some buildings
        self._generate_buildings()
        
        # Create some NPCs
        self._generate_npcs()
        
        # Assign a faction to control the town
        if self.faction_manager:
            factions = list(self.faction_manager.factions.values())
            if factions:
                # For now, randomly select a faction
                controlling_faction = random.choice(factions)
                self.town_faction_id = controlling_faction.id
                
                # Add this town to the faction's controlled territories
                location_id = self.town_name.lower().replace(" ", "_")
                controlling_faction.controlled_locations.add(location_id)
                
                logger.info(f"Town {self.town_name} is controlled by faction: {controlling_faction.name}")
            else:
                logger.warning("No factions available to control town")
    
    def _update_town_faction_info(self):
        """Update town information based on controlling faction."""
        if not self.faction_manager or not self.town_faction_id:
            return
            
        try:
            # Get the controlling faction
            faction = self.faction_manager.get_faction(self.town_faction_id)
            
            # Get the player's status with this faction
            player_status = self.faction_manager.get_player_faction_status(self.town_faction_id)
            
            # Check if the player has a bounty with this faction
            player_bounty = 0
            if hasattr(self.faction_manager, 'crime_manager'):
                player_bounty = self.faction_manager.crime_manager.get_bounty("player")
            
            # Update town law enforcement based on faction type
            has_guards = faction.faction_type in [FactionType.GOVERNMENT, FactionType.MILITARY]
            
            # Update NPC dialog based on faction
            for npc in self.npcs:
                # Assign NPCs to the controlling faction
                npc.faction_id = self.town_faction_id
                
                # Special dialog for guards based on player status and bounty
                if npc.npc_type == NpcType.GUARD:
                    if player_bounty > 0:
                        npc.add_dialog("greeting", f"Halt! You have a bounty of {player_bounty} gold in {faction.name} territory.")
                        npc.add_dialog("bounty", f"Pay your {player_bounty} gold bounty or face the consequences!")
                    elif player_status == RelationshipStatus.HOSTILE:
                        npc.add_dialog("greeting", f"You're not welcome in {self.town_name}. The {faction.name} has marked you as an enemy.")
                    elif player_status == RelationshipStatus.UNFRIENDLY:
                        npc.add_dialog("greeting", f"I'm watching you. The {faction.name} doesn't trust outsiders like you.")
                    else:
                        npc.add_dialog("greeting", f"Greetings, traveler. Obey the laws of {faction.name} while in {self.town_name}.")
                
                # Add faction-specific dialog to quest givers
                elif npc.npc_type == NpcType.QUEST_GIVER:
                    npc.add_dialog("faction", f"The {faction.name} controls this town. You'd do well to stay on their good side.")
            
            logger.info(f"Updated town faction info: {faction.name} controlling {self.town_name}")
            
        except Exception as e:
            logger.error(f"Error updating town faction info: {e}")
    
    def _render_faction_info(self):
        """Render faction information panel."""
        if not self.faction_manager or not self.town_faction_id:
            return
        
        try:
            faction = self.faction_manager.get_faction(self.town_faction_id)
            
            # Create a semi-transparent panel
            panel_width = 500
            panel_height = 400
            panel_x = (self.screen.get_width() - panel_width) // 2
            panel_y = (self.screen.get_height() - panel_height) // 2
            
            # Create panel surface
            panel_surface = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
            panel_surface.fill((40, 40, 50, 220))  # Semi-transparent dark background
            
            # Draw faction header with faction colors
            header_rect = pygame.Rect(0, 0, panel_width, 60)
            pygame.draw.rect(panel_surface, faction.primary_color, header_rect)
            pygame.draw.rect(panel_surface, faction.secondary_color, header_rect, 2)
            
            # Draw faction name
            name_text = self.font.render(faction.name, True, (255, 255, 255))
            panel_surface.blit(name_text, (20, 15))
            
            # Draw faction type
            type_text = self.small_font.render(f"Type: {faction.faction_type.name}", True, (255, 255, 255))
            panel_surface.blit(type_text, (20, 70))
            
            # Draw faction description
            desc_lines = self._wrap_text(faction.description, panel_width - 40, self.small_font)
            for i, line in enumerate(desc_lines):
                line_text = self.small_font.render(line, True, (255, 255, 255))
                panel_surface.blit(line_text, (20, 100 + i * 25))
            
            # Draw player reputation
            reputation = self.faction_manager.player_reputation.get(faction.id, 0)
            status = self.faction_manager.get_player_faction_status(faction.id)
            
            # Reputation color based on status
            status_colors = {
                RelationshipStatus.ALLIED: (50, 200, 100),
                RelationshipStatus.FRIENDLY: (100, 180, 80),
                RelationshipStatus.NEUTRAL: (180, 180, 80),
                RelationshipStatus.UNFRIENDLY: (200, 100, 50),
                RelationshipStatus.HOSTILE: (200, 50, 50)
            }
            
            # Draw reputation bar
            bar_y = 180
            bar_width = 300
            pygame.draw.rect(panel_surface, (80, 80, 80), (100, bar_y, bar_width, 20))
            
            # Calculate fill width (-100 to +100 -> 0 to bar_width)
            fill_width = int((reputation + 100) / 200 * bar_width)
            pygame.draw.rect(panel_surface, status_colors[status], (100, bar_y, fill_width, 20))
            
            # Draw reputation text
            rep_text = self.small_font.render(f"Reputation: {reputation} ({status.name})", True, (255, 255, 255))
            panel_surface.blit(rep_text, (20, bar_y - 25))
            
            # Draw laws and rules
            laws_y = 230
            laws_text = self.small_font.render("Local Laws and Customs:", True, (255, 255, 255))
            panel_surface.blit(laws_text, (20, laws_y))
            
            # Generate laws based on faction type
            laws = self._get_faction_laws(faction)
            for i, law in enumerate(laws):
                law_text = self.small_font.render(f"• {law}", True, (255, 255, 255))
                panel_surface.blit(law_text, (30, laws_y + 30 + i * 25))
            
            # Draw close instructions
            close_text = self.small_font.render("Press ESC to close", True, (200, 200, 200))
            panel_surface.blit(close_text, (panel_width - 150, panel_height - 30))
            
            # Draw panel to screen
            self.screen.blit(panel_surface, (panel_x, panel_y))
            
        except Exception as e:
            logger.error(f"Error rendering faction info: {e}")
    
    def _get_faction_laws(self, faction):
        """Generate laws based on faction type."""
        laws = []
        
        if faction.faction_type == FactionType.GOVERNMENT:
            laws = [
                "All visitors must register at the town hall",
                "Tax of 10% on all transactions",
                "Weapons must be peace-bonded in public",
                "Curfew in effect from midnight to dawn"
            ]
        elif faction.faction_type == FactionType.MILITARY:
            laws = [
                "Martial law is in effect - obey all guard orders",
                "No unauthorized gatherings of more than 3 people",
                "All weapons must be declared upon entry",
                "Travel papers required for entry/exit after dark"
            ]
        elif faction.faction_type == FactionType.MERCHANT:
            laws = [
                "Guild membership required for commercial activity",
                "15% sales tax on all transactions",
                "Price fixing is punishable by heavy fines",
                "All disputes settled by merchant council"
            ]
        elif faction.faction_type == FactionType.CRIMINAL:
            laws = [
                "Pay protection fee to avoid 'accidents'",
                "Don't ask too many questions",
                "All disputes settled by the boss",
                "No law enforcement allowed"
            ]
        elif faction.faction_type == FactionType.RELIGIOUS:
            laws = [
                "Respect holy sites and temples",
                "Mandatory prayer times for all residents",
                "Blasphemy is a serious offense",
                "Tithe of 10% expected from visitors"
            ]
        elif faction.faction_type == FactionType.GUILD:
            laws = [
                "Guild membership required for specialized work",
                "Apprenticeship system strictly enforced",
                "Trade secrets are protected by law",
                "Quality standards must be maintained"
            ]
        elif faction.faction_type == FactionType.TRIBAL:
            laws = [
                "Outsiders must be vouched for by a tribe member",
                "Respect tribal customs and traditions",
                "Natural resources are communally owned",
                "Elders' decisions are final in all matters"
            ]
            
        # Add law about slavery if applicable
        if faction.has_slavery:
            laws.append("Slavery is legal and practiced openly")
            
        # Add law about arrest powers
        if faction.can_arrest:
            laws.append("Guards have authority to arrest criminals on sight")
            
        return laws
    
    def _wrap_text(self, text, max_width, font):
        """Wrap text to fit within a certain width."""
        words = text.split(' ')
        lines = []
        current_line = []
        
        for word in words:
            # Try adding this word to the current line
            test_line = ' '.join(current_line + [word])
            width, _ = font.size(test_line)
            
            if width <= max_width:
                current_line.append(word)
            else:
                # If the line is too long, start a new line
                lines.append(' '.join(current_line))
                current_line = [word]
        
        # Add the last line
        if current_line:
            lines.append(' '.join(current_line))
            
        return lines
    
    def _toggle_faction_info(self):
        """Toggle the faction information panel."""
        self.faction_info_visible = not self.faction_info_visible
        
        # Close other panels when showing faction info
        if self.faction_info_visible:
            self.quest_journal_visible = False
            if self.dialog_panel:
                self._close_dialog()
    
    def _generate_buildings(self):
        """Generate town buildings."""
        # Create a town center
        center_building = TownBuilding(
            BuildingType.TOWNHALL,
            "Town Hall",
            (18, 12),
            (4, 4)
        )
        self.buildings.append(center_building)
        
        # Create a tavern
        tavern = TownBuilding(
            BuildingType.TAVERN,
            "The Dancing Dragon",
            (12, 8),
            (3, 3)
        )
        self.buildings.append(tavern)
        
        # Create a blacksmith
        blacksmith = TownBuilding(
            BuildingType.BLACKSMITH,
            "Forge & Anvil",
            (24, 8),
            (3, 2)
        )
        self.buildings.append(blacksmith)
        
        # Create a shop
        shop = TownBuilding(
            BuildingType.SHOP,
            "General Store",
            (8, 16),
            (3, 3)
        )
        self.buildings.append(shop)
        
        # Create a temple
        temple = TownBuilding(
            BuildingType.TEMPLE,
            "Temple of Light",
            (28, 16),
            (4, 4)
        )
        self.buildings.append(temple)
    
    def _generate_npcs(self):
        """Generate town NPCs."""
        # Create a quest giver
        quest_giver = Npc(
            NpcType.QUEST_GIVER,
            "Elder Thorne",
            (self.buildings[0].entrance[0] * self.tile_size, 
             self.buildings[0].entrance[1] * self.tile_size - 20)
        )
        quest_giver.add_dialog("greeting", "Welcome, traveler. The town is in need of your help.")
        quest_giver.add_dialog("quest_offer", "We've been having trouble with wolves attacking our livestock. Could you help us?")
        quest_giver.add_dialog("quest_declined", "I understand. Come back if you change your mind.")
        quest_giver.add_dialog("quest_accepted", "Excellent! Come back when you've completed the task.")
        # We will assign quests to this NPC later in _setup_npc_quests
        self.npcs.append(quest_giver)
        self.buildings[0].add_npc(quest_giver)
        
        # Create a blacksmith
        blacksmith = Npc(
            NpcType.BLACKSMITH,
            "Gareth Ironarm",
            (self.buildings[2].entrance[0] * self.tile_size, 
             self.buildings[2].entrance[1] * self.tile_size - 20)
        )
        blacksmith.add_dialog("greeting", "Need some new equipment, adventurer?")
        self.npcs.append(blacksmith)
        self.buildings[2].add_npc(blacksmith)
        
        # Create a merchant
        merchant = Npc(
            NpcType.MERCHANT,
            "Lydia Coinpurse",
            (self.buildings[3].entrance[0] * self.tile_size, 
             self.buildings[3].entrance[1] * self.tile_size - 20)
        )
        merchant.add_dialog("greeting", "Browse my wares! I have everything you need.")
        self.npcs.append(merchant)
        self.buildings[3].add_npc(merchant)
        
        # Create an innkeeper
        innkeeper = Npc(
            NpcType.INNKEEPER,
            "Bram Goodale",
            (self.buildings[1].entrance[0] * self.tile_size, 
             self.buildings[1].entrance[1] * self.tile_size - 20)
        )
        innkeeper.add_dialog("greeting", "Welcome to the Dancing Dragon! Food, drink, and a warm bed await.")
        self.npcs.append(innkeeper)
        self.buildings[1].add_npc(innkeeper)
        
        # Add a guard for faction system integration
        if self.town_faction_id and self.faction_manager:
            # Position near town entrance
            guard = Npc(
                NpcType.GUARD,
                "Town Guard",
                (15 * self.tile_size, 25 * self.tile_size)
            )
            guard.add_dialog("greeting", "Halt! State your business in town.")
            self.npcs.append(guard)
    
    def _update_player_movement(self, dt):
        """
        Update player movement.
        
        Args:
            dt: Time delta in seconds
        """
        if self.player_moving and self.player_target:
            # Simple direct movement for now
            speed = 5 * dt  # Grid cells per second
            
            # Calculate direction
            dx = self.player_target[0] - self.player_grid_pos[0]
            dy = self.player_target[1] - self.player_grid_pos[1]
            distance = math.sqrt(dx**2 + dy**2)
            
            if distance <= speed:
                # Arrived at target
                self.player_grid_pos = self.player_target
                self.player_moving = False
                self.player_target = None
            else:
                # Move towards target
                self.player_grid_pos[0] += dx / distance * speed
                self.player_grid_pos[1] += dy / distance * speed
    
    def _update_camera(self):
        """Update camera position to follow player."""
        if not hasattr(self, 'screen') or self.screen is None:
            return
            
        target_x = int(self.player_grid_pos[0] * self.tile_size - self.screen.get_width() // 2)
        target_y = int(self.player_grid_pos[1] * self.tile_size - self.screen.get_height() // 2)
        
        # Smoothly move camera towards target
        self.camera_offset[0] += (target_x - self.camera_offset[0]) * 0.1
        self.camera_offset[1] += (target_y - self.camera_offset[1]) * 0.1
        
        # Ensure camera doesn't go beyond map bounds
        self.camera_offset[0] = max(0, min(self.camera_offset[0], 
                                          self.grid_width * self.tile_size - self.screen.get_width()))
        self.camera_offset[1] = max(0, min(self.camera_offset[1], 
                                          self.grid_height * self.tile_size - self.screen.get_height()))
    
    def _render_town_grid(self):
        """Render the town grid."""
        # Calculate visible range
        start_x = int(self.camera_offset[0] // self.tile_size)
        start_y = int(self.camera_offset[1] // self.tile_size)
        end_x = start_x + self.screen.get_width() // self.tile_size + 2
        end_y = start_y + self.screen.get_height() // self.tile_size + 2
        
        # Ensure we're within bounds
        start_x = max(0, start_x)
        start_y = max(0, start_y)
        end_x = min(self.grid_width, end_x)
        end_y = min(self.grid_height, end_y)
        
        # Draw grid
        for y in range(start_y, end_y):
            for x in range(start_x, end_x):
                rect = pygame.Rect(
                    x * self.tile_size - self.camera_offset[0],
                    y * self.tile_size - self.camera_offset[1],
                    self.tile_size,
                    self.tile_size
                )
                
                # Use sprite if available, otherwise draw a simple rectangle
                if 'grass' in self.tile_images:
                    self.screen.blit(self.tile_images['grass'], rect)
                else:
                    # Draw grass tile
                    pygame.draw.rect(self.screen, (50, 150, 50), rect)
                    pygame.draw.rect(self.screen, (40, 120, 40), rect, 1)
    
    def _render_buildings(self):
        """Render town buildings."""
        for building in self.buildings:
            building_rect = pygame.Rect(
                building.position[0] * self.tile_size - self.camera_offset[0],
                building.position[1] * self.tile_size - self.camera_offset[1],
                building.size[0] * self.tile_size,
                building.size[1] * self.tile_size
            )
            
            # Skip if not visible
            if (building_rect.right < 0 or building_rect.bottom < 0 or
                building_rect.left > self.screen.get_width() or
                building_rect.top > self.screen.get_height()):
                continue
            
            # Use sprites if available, otherwise draw simple shapes
            if 'building' in self.tile_images and 'roof' in self.tile_images:
                # Draw building base
                for y in range(building.size[1]):
                    for x in range(building.size[0]):
                        pos = (
                            (building.position[0] + x) * self.tile_size - self.camera_offset[0],
                            (building.position[1] + y) * self.tile_size - self.camera_offset[1]
                        )
                        self.screen.blit(self.tile_images['building'], pos)
                
                # Draw roof on top half
                roof_rect = pygame.Rect(
                    building_rect.left,
                    building_rect.top,
                    building_rect.width,
                    building_rect.height // 2
                )
                pygame.transform.scale(self.tile_images['roof'], (roof_rect.width, roof_rect.height))
                self.screen.blit(pygame.transform.scale(self.tile_images['roof'], 
                                                      (roof_rect.width, roof_rect.height)), roof_rect)
            else:
                # Draw building (simple rectangle)
                pygame.draw.rect(self.screen, (150, 100, 50), building_rect)
                pygame.draw.rect(self.screen, (120, 70, 30), building_rect, 2)
                
                # Draw roof (simple rectangle)
                roof_rect = pygame.Rect(
                    building_rect.left,
                    building_rect.top,
                    building_rect.width,
                    building_rect.height // 2
                )
                pygame.draw.rect(self.screen, (180, 50, 50), roof_rect)
            
            # Draw name
            name_text = self.small_font.render(building.name, True, (255, 255, 255))
            self.screen.blit(name_text, (
                building_rect.centerx - name_text.get_width() // 2,
                building_rect.bottom + 5
            ))
    
    def _render_npcs(self):
        """Render town NPCs."""
        for npc in self.npcs:
            # Convert NPC position to screen coordinates
            screen_x = npc.position[0] - self.camera_offset[0]
            screen_y = npc.position[1] - self.camera_offset[1]
            
            # Skip if not visible
            if (screen_x < -20 or screen_y < -20 or
                screen_x > self.screen.get_width() + 20 or
                screen_y > self.screen.get_height() + 20):
                continue
            
            # Draw NPC sprite if available, otherwise a circle
            if 'npc' in self.tile_images:
                sprite_rect = pygame.Rect(
                    screen_x - self.tile_size // 2,
                    screen_y - self.tile_size // 2,
                    self.tile_size,
                    self.tile_size
                )
                self.screen.blit(self.tile_images['npc'], sprite_rect)
            else:
                # Draw NPC as a circle
                npc_color = (200, 200, 0)  # Default yellow
                
                # Use faction colors for NPCs if available
                if npc.faction_id and self.faction_manager:
                    try:
                        faction = self.faction_manager.get_faction(npc.faction_id)
                        if npc.npc_type == NpcType.GUARD:
                            npc_color = faction.secondary_color
                        else:
                            npc_color = faction.primary_color
                    except:
                        pass
                
                pygame.draw.circle(self.screen, npc_color, (int(screen_x), int(screen_y)), 10)
            
            # Draw NPC name
            name_text = self.small_font.render(npc.name, True, (255, 255, 255))
            self.screen.blit(name_text, (
                screen_x - name_text.get_width() // 2,
                screen_y - 30
            ))
            
            # If this is a quest giver with available quests, show an indicator
            if npc.npc_type == NpcType.QUEST_GIVER and self.quest_manager and npc.quests:
                pygame.draw.polygon(self.screen, (255, 255, 0), [
                    (screen_x, screen_y - 20),
                    (screen_x - 5, screen_y - 30),
                    (screen_x + 5, screen_y - 30)
                ])
    
    def _render_player(self):
        """Render player character."""
        # Convert grid position to screen coordinates
        screen_x = int(self.player_grid_pos[0] * self.tile_size - self.camera_offset[0])
        screen_y = int(self.player_grid_pos[1] * self.tile_size - self.camera_offset[1])
        
        # Draw player sprite if available, otherwise a circle
        if 'player' in self.tile_images:
            sprite_rect = pygame.Rect(
                screen_x - self.tile_size // 2,
                screen_y - self.tile_size // 2,
                self.tile_size,
                self.tile_size
            )
            self.screen.blit(self.tile_images['player'], sprite_rect)
        else:
            # Draw player as a circle
            pygame.draw.circle(self.screen, (0, 100, 255), (screen_x, screen_y), 12)
            pygame.draw.circle(self.screen, (0, 50, 200), (screen_x, screen_y), 12, 2)
    
    def _interact_with_npc(self, npc):
        """
        Interact with an NPC.
        
        Args:
            npc: Npc instance
        """
        logger.info(f"Interacting with NPC: {npc.name}")
        
        # Open dialog panel
        self._open_dialog(npc)
        
        # Publish event for NPC talk (which quest system listens for)
        npc_id = f"{npc.npc_type.name.lower()}_{npc.name.lower().replace(' ', '_')}"
        self.event_bus.publish("npc_talked", {"npc_id": npc_id, "npc": npc})
    
    def _interact_with_building(self, building):
        """
        Interact with a building.
        
        Args:
            building: TownBuilding instance
        """
        logger.info(f"Interacting with building: {building.name}")
        
        # For now, just move player to building entrance
        self.player_target = list(building.entrance)
        self.player_moving = True
    
    def _setup_npc_quests(self):
        """Set up quests for NPCs based on quest manager data."""
        if not self.quest_manager:
            logger.warning("No quest manager available to set up NPC quests")
            return
            
        # Get player character from state manager (for checking quest requirements)
        player = self.state_manager.get_persistent_data("player_character")
        if not player:
            player = Character("Player", Race.HUMAN, CharacterClass.WARRIOR)
            
        # First, set up quest givers
        for quest_id, quest in self.quest_manager.quests.items():
            # If a quest doesn't have a quest giver, assign it to the Elder Thorne for now
            if not hasattr(quest, 'quest_giver') or not quest.quest_giver:
                # Simple heuristic: low-level quests go to Elder Thorne, but this could be more sophisticated
                if quest.level <= 3:
                    quest.quest_giver = "quest_giver_elder_thorne"
                    logger.info(f"Auto-assigned quest '{quest.title}' to Elder Thorne")
                    
        # Now, assign quests to NPCs
        for npc in self.npcs:
            npc_id = f"{npc.npc_type.name.lower()}_{npc.name.lower().replace(' ', '_')}"
            
            # Clear existing quests first
            npc.quests = []
            
            # Add quests where this NPC is the quest giver
            for quest_id, quest in self.quest_manager.quests.items():
                if hasattr(quest, 'quest_giver') and quest.quest_giver == npc_id:
                    # Check if the player meets the requirements
                    if self.quest_manager.can_accept_quest(quest, player):
                        npc.quests.append(quest_id)
                        logger.info(f"Assigned quest '{quest.title}' to NPC {npc.name}")
            
            # Also add active quests to NPCs (for turning in completed quests)
            for quest_id in self.quest_manager.active_quests:
                quest = self.quest_manager.quests.get(quest_id)
                if quest and quest.is_complete() and hasattr(quest, 'quest_receiver') and quest.quest_receiver == npc_id:
                    if quest_id not in npc.quests:
                        npc.quests.append(quest_id)
                        logger.info(f"Added completed quest '{quest.title}' to NPC {npc.name} for turn-in")
                        
        # Log the results for debugging
        for npc in self.npcs:
            if npc.quests:
                quest_names = [self.quest_manager.quests[qid].title for qid in npc.quests if qid in self.quest_manager.quests]
                logger.info(f"NPC {npc.name} has {len(npc.quests)} quests: {quest_names}")
    
    def _open_dialog(self, npc):
        """
        Open dialog with NPC.
        
        Args:
            npc: Npc instance
        """
        # Create dialog panel if it doesn't exist
        if not self.dialog_panel:
            panel_rect = pygame.Rect(
                self.screen.get_width() // 2 - 300,
                self.screen.get_height() - 200,
                600,
                180
            )
            self.dialog_panel = self.ui_manager.create_panel(panel_rect)
            
            # Add dialog text label
            text_rect = pygame.Rect(20, 20, 560, 60)
            self.dialog_text = self.ui_manager.create_label(
                text_rect,
                "",
                self.dialog_panel
            )
        
        # Store current NPC
        self.dialog_npc = npc
        
        # Set initial dialog text
        self.dialog_text.set_text(f"{npc.name}: {npc.get_dialog('greeting')}")
        
        # Clear existing dialog options
        for button in self.dialog_options:
            self.ui_manager.remove_element(button)
        
        self.dialog_options = []
        
        # Get player character from state manager
        player = self.state_manager.get_persistent_data("player_character")
        if not player:
            player = Character("Player", Race.HUMAN, CharacterClass.WARRIOR)
        
        # Create dialog options based on NPC type
        option_y = 100
        
        # Check for quests if this is a quest giver
        if npc.npc_type == NpcType.QUEST_GIVER:
            # If the NPC has quests, add a 'Quest' button
            if npc.quests:
                def create_quest_callback(specific_npc):
                    def callback(_):
                        self._offer_quest(specific_npc)
                    return callback
                
                quest_button = self.ui_manager.create_button(
                    pygame.Rect(20, option_y, 150, 30),
                    "Ask about quests",
                    create_quest_callback(npc),
                    self.dialog_panel
                )
                self.dialog_options.append(quest_button)
                option_y += 40
        
        # Add faction info button if NPC belongs to a faction
        if npc.faction_id and self.faction_manager:
            def create_faction_callback(specific_npc):
                def callback(_):
                    self._show_faction_dialog(specific_npc)
                return callback
            
            faction_button = self.ui_manager.create_button(
                pygame.Rect(180, option_y - 40, 150, 30),
                "Ask about faction",
                create_faction_callback(npc),
                self.dialog_panel
            )
            self.dialog_options.append(faction_button)
        
        # Add specific guard options for bounty payment
        if npc.npc_type == NpcType.GUARD and self.faction_manager:
            try:
                player_bounty = 0
                if hasattr(self.faction_manager, 'crime_manager'):
                    player_bounty = self.faction_manager.crime_manager.get_bounty("player")
                
                if player_bounty > 0:
                    def create_pay_bounty_callback():
                        def callback(_):
                            self._pay_bounty(npc)
                        return callback
                    
                    bounty_button = self.ui_manager.create_button(
                        pygame.Rect(340, option_y - 40, 150, 30),
                        f"Pay bounty ({player_bounty}g)",
                        create_pay_bounty_callback(),
                        self.dialog_panel
                    )
                    self.dialog_options.append(bounty_button)
            except Exception as e:
                logger.error(f"Error creating bounty button: {e}")
        
        # Add shop option for merchants
        if npc.npc_type == NpcType.MERCHANT or npc.npc_type == NpcType.BLACKSMITH:
            # Use a closure for the callback
            def create_shop_callback(specific_npc):
                def callback(_):
                    self._open_shop(specific_npc)
                return callback
            
            shop_button = self.ui_manager.create_button(
                pygame.Rect(340, option_y - 40, 150, 30) if "faction_button" in locals() else pygame.Rect(180, option_y - 40, 150, 30),
                "Shop",
                create_shop_callback(npc),
                self.dialog_panel
            )
            self.dialog_options.append(shop_button)
        
        # Add close button with closure
        def create_close_callback():
            def callback(_):
                self._close_dialog()
            return callback
        
        close_button = self.ui_manager.create_button(
            pygame.Rect(430, option_y - 40, 150, 30),
            "Close",
            create_close_callback(),
            self.dialog_panel
        )
        self.dialog_options.append(close_button)
    
    def _show_faction_dialog(self, npc):
        """Show dialog about the NPC's faction."""
        if not npc.faction_id or not self.faction_manager:
            self._continue_dialog(npc, "greeting")
            return
        
        try:
            faction = self.faction_manager.get_faction(npc.faction_id)
            player_status = self.faction_manager.get_player_faction_status(npc.faction_id)
            
            # Different dialog based on NPC type and player status
            dialog_key = "faction"
            
            if "faction" not in npc.dialog:
                if npc.npc_type == NpcType.GUARD:
                    if player_status == RelationshipStatus.HOSTILE:
                        npc.add_dialog("faction", f"The {faction.name} considers you an enemy. You're lucky I don't arrest you on sight.")
                    elif player_status == RelationshipStatus.UNFRIENDLY:
                        npc.add_dialog("faction", f"The {faction.name} controls this town. Watch your step - we're keeping an eye on you.")
                    elif player_status == RelationshipStatus.NEUTRAL:
                        npc.add_dialog("faction", f"The {faction.name} maintains order here. Obey our laws and you won't have trouble.")
                    elif player_status == RelationshipStatus.FRIENDLY:
                        npc.add_dialog("faction", f"The {faction.name} appreciates your past cooperation. You're welcome in our town.")
                    else:  # ALLIED
                        npc.add_dialog("faction", f"You're a trusted friend of the {faction.name}. Let me know if you need anything.")
                else:
                    npc.add_dialog("faction", f"The {faction.name} controls this town. It's best to stay on their good side.")
            
            # Update dialog with faction information
            self._continue_dialog(npc, dialog_key)
            
        except Exception as e:
            logger.error(f"Error showing faction dialog: {e}")
            self._continue_dialog(npc, "greeting")
    
    def _pay_bounty(self, npc):
        """Pay bounty to a guard NPC."""
        if not npc.faction_id or not self.faction_manager or not hasattr(self.faction_manager, 'crime_manager'):
            self._continue_dialog(npc, "greeting")
            return
        
        try:
            player_bounty = self.faction_manager.crime_manager.get_bounty("player")
            
            if player_bounty <= 0:
                npc.add_dialog("bounty_paid", "You have no bounty to pay.")
                self._continue_dialog(npc, "bounty_paid")
                return
            
            # For now, automatically pay the bounty - in a real game you'd check player gold
            faction = self.faction_manager.get_faction(npc.faction_id)
            
            # Pay the bounty
            self.event_bus.publish("bounty_paid", {
                "entity_id": "player",
                "faction_id": npc.faction_id
            })
            
            # Add dialog for paid bounty
            npc.add_dialog("bounty_paid", f"Your bounty of {player_bounty} gold has been paid. You're free to go... for now.")
            self._continue_dialog(npc, "bounty_paid")
            
        except Exception as e:
            logger.error(f"Error paying bounty: {e}")
            self._continue_dialog(npc, "greeting")
    
    def _close_dialog(self):
        """Close dialog panel."""
        if self.dialog_panel:
            self.ui_manager.remove_element(self.dialog_panel)
            self.dialog_panel = None
            self.dialog_text = None
            self.dialog_npc = None
            self.dialog_options = []
            self.current_quest = None
    
    def _offer_quest(self, npc):
        """
        Offer a quest from an NPC.
        
        Args:
            npc: Npc instance
        """
        # Get player character
        player = self.state_manager.get_persistent_data("player_character")
        if not player:
            player = Character("Player", Race.HUMAN, CharacterClass.WARRIOR)
        
        # Check if NPC has any quests assigned
        if not npc.quests:
            self.dialog_text.set_text(f"{npc.name}: I don't have any quests for you right now.")
            return
            
        # Get available quests from the quest manager
        if self.quest_manager:
            try:
                logger.info(f"NPC {npc.name} has quests: {npc.quests}")
                
                # Find a quest for this NPC from their quest list
                self.current_quest = None
                
                for quest_id in npc.quests:
                    # Get the quest object from the quest manager
                    quest = self.quest_manager.quests.get(quest_id)
                    if quest and self.quest_manager.can_accept_quest(quest, player):
                        self.current_quest = quest
                        break
                        
                if not self.current_quest:
                    self.dialog_text.set_text(f"{npc.name}: I don't have any quests for you right now.")
                    return
                    
                # Get the quest ID properly
                quest_id = self.current_quest.id
                logger.info(f"Offering quest: {quest_id} - {self.current_quest.title}")
                
                # Update dialog text with quest description
                self.dialog_text.set_text(f"{npc.name}: {self.current_quest.description}")
                
                # Update dialog options
                for button in self.dialog_options:
                    self.ui_manager.remove_element(button)
                
                self.dialog_options = []
                
                # Create closures for the callbacks
                def create_accept_callback(the_npc, the_quest_id, the_player):
                    logger.info(f"Creating accept callback with quest_id: {the_quest_id}")
                    def callback(_):
                        logger.info(f"Accept callback called with quest_id: {the_quest_id}")
                        self._accept_quest(the_npc, the_quest_id, the_player)
                    return callback
                
                # Add accept button 
                accept_button = self.ui_manager.create_button(
                    pygame.Rect(20, 100, 150, 30),
                    "Accept Quest",
                    create_accept_callback(npc, quest_id, player),
                    self.dialog_panel
                )
                self.dialog_options.append(accept_button)
                
                # Add decline button
                def create_decline_callback(the_npc, dialog_key):
                    def callback(_):
                        self._continue_dialog(the_npc, dialog_key)
                    return callback
                
                decline_button = self.ui_manager.create_button(
                    pygame.Rect(180, 100, 150, 30),
                    "Decline",
                    create_decline_callback(npc, "quest_declined"),
                    self.dialog_panel
                )
            except Exception as e:
                logger.error(f"Error offering quest: {e}")
                self.dialog_text.set_text(f"{npc.name}: I'm having trouble with my quest ledger. Check back later.")
        else:
            # Fallback if quest manager not available
            self.dialog_text.set_text(f"{npc.name}: I'm sorry, I don't have any quests for you.")
    
    def _accept_quest(self, npc, quest_id, player):
        """Accept a quest from an NPC."""
        logger.info(f"Accepting quest: {quest_id}")
        
        try:
            if not self.quest_manager:
                logger.error("No quest manager available")
                self.dialog_text.set_text(f"{npc.name}: I'm sorry, there seems to be a problem with the quest system.")
                return
                
            if quest_id:
                # Find the quest object from the ID if needed
                quest_name = quest_id  # Fallback for logging
                quest_obj = None
                
                if self.quest_manager:
                    logger.info("Getting quests from quest manager")
                    # Try to get the quest object by ID from the quest manager
                    try:
                        available_quests = self.quest_manager.get_available_quests(player)
                        logger.info(f"Found {len(available_quests)} available quests")
                        
                        for quest in available_quests:
                            logger.info(f"Checking quest: {quest.id}, {quest.title}")
                            if getattr(quest, 'id', None) == quest_id:
                                quest_obj = quest
                                quest_name = quest.title
                                logger.info(f"Found matching quest object: {quest_name}")
                                break
                        
                        if not quest_obj:
                            logger.warning(f"Could not find quest object with ID: {quest_id}")
                            
                        logger.info(f"Activating quest ID: {quest_id}")
                        # Activate the quest in the quest manager using the ID
                        self.quest_manager.activate_quest(quest_id, player)
                        logger.info("Quest activated successfully")
                    except Exception as e:
                        logger.error(f"Error finding or activating quest: {e}", exc_info=True)
                
                # Add response dialog
                logger.info("Setting quest accepted dialog")
                npc.add_dialog("quest_accepted", "Excellent! Come back when you've completed the task.")
                
                # Update dialog
                logger.info("Updating dialog text")
                self.dialog_text.set_text(f"{npc.name}: {npc.get_dialog('quest_accepted')}")
                
                # Update dialog options
                logger.info("Updating dialog options")
                for button in self.dialog_options:
                    self.ui_manager.remove_element(button)
                
                self.dialog_options = []
                
                # Add close button with closure
                def create_close_callback():
                    def callback(_):
                        self._close_dialog()
                    return callback
                
                close_button = self.ui_manager.create_button(
                    pygame.Rect(20, 100, 150, 30),
                    "Close",
                    create_close_callback(),
                    self.dialog_panel
                )
                self.dialog_options.append(close_button)
            else:
                logger.error("Attempted to accept a quest, but quest ID is invalid")
                self._close_dialog()
        except Exception as e:
            logger.error(f"Error accepting quest: {e}", exc_info=True)
            if self.dialog_text:
                self.dialog_text.set_text(f"{npc.name}: There seems to be a problem with this quest. Let's talk later.")
    
    def _continue_dialog(self, npc, dialog_key):
        """
        Continue dialog with an NPC.
        
        Args:
            npc: Npc instance
            dialog_key: Dialog key
        """
        if npc and dialog_key:
            self.dialog_text.set_text(f"{npc.name}: {npc.get_dialog(dialog_key)}")
            
            # Update dialog options
            for button in self.dialog_options:
                self.ui_manager.remove_element(button)
            
            self.dialog_options = []
            
            # Add close button with closure
            def create_close_callback():
                def callback(_):
                    self._close_dialog()
                return callback
            
            close_button = self.ui_manager.create_button(
                pygame.Rect(20, 100, 150, 30),
                "Close",
                create_close_callback(),
                self.dialog_panel
            )
            self.dialog_options.append(close_button)
        else:
            logger.error("Invalid parameters in _continue_dialog")
            self._close_dialog()
    
    def _open_shop(self, npc):
        """
        Open shop interface.
        
        Args:
            npc: Npc instance
        """
        logger.info(f"Opening shop with {npc.name}")
        
        # For now, just show a message
        self.dialog_text.set_text(f"{npc.name}: Welcome to my shop! (Shop interface not implemented yet)")
        
        # Update dialog options
        for button in self.dialog_options:
            self.ui_manager.remove_element(button)
        
        self.dialog_options = []
        
        # Add close button with closure
        def create_close_callback():
            def callback(_):
                self._close_dialog()
            return callback
        
        close_button = self.ui_manager.create_button(
            pygame.Rect(20, 100, 150, 30),
            "Close",
            create_close_callback(),
            self.dialog_panel
        )
        self.dialog_options.append(close_button)
    
    def _toggle_quest_journal(self):
        """Toggle the quest journal UI."""
        logger.info("Toggling quest journal")
        
        if not self.quest_manager:
            logger.warning("Cannot open quest journal: No quest manager available")
            return
        
        # Toggle visibility state
        self.quest_journal_visible = not self.quest_journal_visible
        
        if self.quest_journal_visible:
            # Create the quest UI if it doesn't exist
            if not self.quest_ui:
                self.quest_ui = QuestUI(self.screen, self.quest_manager, self.event_bus)
            
            # Close other UI panels when showing quest journal
            self.faction_info_visible = False
            if self.dialog_panel:
                self._close_dialog()
        else:
            # We'll keep the quest_ui instance, just not render it
            pass