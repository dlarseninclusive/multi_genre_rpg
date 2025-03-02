import pygame
import logging
import random
import math
from enum import Enum
from game_state import GameState
from world_generator import Location, LocationType
from ui_system import UIManager, UIButton, UILabel, UIPanel, UIImage, UIProgressBar
from quest_system import QuestManager, QuestStatus, QuestType, ObjectiveType, Quest
from character import Character

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
        self.current_quest = None  # Current quest being offered
        
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
        
        # Initialize town if not already done
        if not self.buildings:
            self._generate_town()
        
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
                pygame.draw.circle(self.screen, (200, 200, 0), (int(screen_x), int(screen_y)), 10)
            
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
        
        # Create dialog options based on NPC type
        option_y = 100
        
        # Check for quests if this is a quest giver
        if npc.npc_type == NpcType.QUEST_GIVER:
            # Use a closure for the callback to avoid late binding issues
            def create_offer_quest_callback(specific_npc):
                def callback(_):
                    self._offer_quest(specific_npc)
                return callback
            
            # Offer quest button
            quest_button = self.ui_manager.create_button(
                pygame.Rect(20, option_y, 150, 30),
                "Ask about quests",
                create_offer_quest_callback(npc),
                self.dialog_panel
            )
            self.dialog_options.append(quest_button)
            option_y += 40
        
        # Add shop option for merchants
        if npc.npc_type == NpcType.MERCHANT or npc.npc_type == NpcType.BLACKSMITH:
            # Use a closure for the callback
            def create_shop_callback(specific_npc):
                def callback(_):
                    self._open_shop(specific_npc)
                return callback
            
            shop_button = self.ui_manager.create_button(
                pygame.Rect(180, option_y - 40, 150, 30),
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
            player = Character("Player", "Human", "Warrior")
        
        # Get available quests from the quest manager
        if self.quest_manager:
            try:
                available_quests = self.quest_manager.get_available_quests(player)
                
                if not available_quests:
                    self.dialog_text.set_text(f"{npc.name}: I don't have any quests for you right now.")
                    return
                
                # Find a quest for this NPC
                self.current_quest = None
                npc_id = f"{npc.npc_type.name.lower()}_{npc.name.lower().replace(' ', '_')}"
                
                for quest in available_quests:
                    if hasattr(quest, 'quest_giver') and quest.quest_giver == npc_id:
                        self.current_quest = quest
                        break
                
                if not self.current_quest and available_quests:
                    # If no specific quest for this NPC, just use the first one
                    self.current_quest = available_quests[0]
                
                if not self.current_quest:
                    self.dialog_text.set_text(f"{npc.name}: I don't have any quests for you right now.")
                    return
                    
                # Update dialog text with quest description
                self.dialog_text.set_text(f"{npc.name}: {self.current_quest.description}")
                
                # Update dialog options
                for button in self.dialog_options:
                    self.ui_manager.remove_element(button)
                
                self.dialog_options = []
                
                # Create closures for the callbacks to avoid Python's late binding issues
                def create_accept_callback(the_npc, the_quest_id, the_player):
                    def callback(_):
                        self._accept_quest(the_npc, the_quest_id, the_player)
                    return callback
                
                def create_decline_callback(the_npc, dialog_key):
                    def callback(_):
                        self._continue_dialog(the_npc, dialog_key)
                    return callback
                
                # Add accept button
                accept_button = self.ui_manager.create_button(
                    pygame.Rect(20, 100, 150, 30),
                    "Accept Quest",
                    create_accept_callback(npc, self.current_quest.id, player),
                    self.dialog_panel
                )
                self.dialog_options.append(accept_button)
                
                # Add decline button
                decline_button = self.ui_manager.create_button(
                    pygame.Rect(180, 100, 150, 30),
                    "Decline",
                    create_decline_callback(npc, "quest_declined"),
                    self.dialog_panel
                )
                self.dialog_options.append(decline_button)
            except Exception as e:
                logger.error(f"Error offering quest: {e}")
                self.dialog_text.set_text(f"{npc.name}: I'm having trouble with my quest ledger. Check back later.")
        else:
            # Fallback if quest manager not available
            self.dialog_text.set_text(f"{npc.name}: I'm sorry, I don't have any quests for you.")
    
    def _accept_quest(self, npc, quest_id, player):
        """
        Accept a quest from an NPC.
        
        Args:
            npc: Npc instance
            quest_id: Quest ID string
            player: Player character
        """
        try:
            if quest_id:
                logger.info(f"Accepted quest: {quest_id}")
                
                # Find the quest object from the ID if needed
                quest_name = quest_id  # Fallback for logging
                quest_obj = None
                if self.quest_manager:
                    # Try to get the quest object by ID from the quest manager
                    available_quests = self.quest_manager.get_available_quests(player)
                    for quest in available_quests:
                        if quest.id == quest_id:
                            quest_obj = quest
                            quest_name = quest.title
                            break
                
                    logger.info(f"Activating quest: {quest_name}")
                    # Activate the quest in the quest manager using the ID
                    self.quest_manager.activate_quest(quest_id, player)
                
                # Add response dialog
                npc.add_dialog("quest_accepted", 
                              "Excellent! Come back when you've completed the task.")
                
                # Update dialog
                self.dialog_text.set_text(f"{npc.name}: {npc.get_dialog('quest_accepted')}")
                
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
                logger.error("Attempted to accept a quest, but quest ID is invalid")
                self._close_dialog()
        except Exception as e:
            logger.error(f"Error accepting quest: {e}")
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
        
        # TODO: Implement quest journal UI
        if self.quest_manager:
            # This would create or destroy the quest journal UI
            pass
