import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
import pygame
import sys
import logging
from state_manager import StateManager
from game_states.main_menu_state import MainMenuState
from game_states.world_exploration_state import WorldExplorationState
from game_states.investigation_state import InvestigationState
from game_states.dungeon_state import DungeonState
from game_states.base_building_state import BaseBuildingState
from game_states.combat_state import CombatGameState
from game_states.pause_menu_state import PauseMenuState
from game_states.town_state import TownState
from event_bus import EventBus
from settings import Settings
from save_system import SaveSystem
from quest_system import QuestManager, QuestNotificationManager, QuestMarkerManager, create_test_quests

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Change from INFO to DEBUG for more detailed logs
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("game.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("main")

class Game:
    """Main game class that initializes systems and runs the game loop."""
    
    def __init__(self):
        # Initialize Pygame
        pygame.init()
        pygame.display.set_caption("Multi-Genre RPG")
        
        # Game settings
        self.settings = Settings()
        
        # Set up the display
        if self.settings.fullscreen:
            self.screen = pygame.display.set_mode(
                (self.settings.screen_width, self.settings.screen_height),
                pygame.FULLSCREEN
            )
        else:
            self.screen = pygame.display.set_mode(
                (self.settings.screen_width, self.settings.screen_height)
            )
        
        # Initialize systems
        self.event_bus = EventBus()
        self.save_system = SaveSystem()
        
        # Add notification system
        from notification_system import NotificationManager
        self.notification_manager = NotificationManager(self.event_bus)
        
        # Initialize quest system
        self.quest_manager = QuestManager(self.event_bus)
        self.quest_notification_manager = QuestNotificationManager(self.event_bus)
        self.quest_marker_manager = QuestMarkerManager(self.quest_manager)
        
        # Load quest data
        try:
            self.quest_manager.load_quests_from_file("data/quests.json")
            # Create some example test quests if needed
            create_test_quests(self.quest_manager)
            logger.info("Quests loaded successfully")
        except Exception as e:
            logger.error(f"Error loading quests: {e}")
        
        # Make save system available to all states
        self.state_manager = StateManager(self.screen, self.event_bus)
        self.state_manager.set_persistent_data("save_system", self.save_system)
        self.state_manager.set_persistent_data("quest_manager", self.quest_manager)
        
        # Set up quest UI for all states to access
        from quest_system import QuestUI
        self.quest_ui = QuestUI(self.screen, self.quest_manager, self.event_bus)
        self.state_manager.set_persistent_data("quest_ui", self.quest_ui)
        # State manager already created above when setting persistent data
        self._register_game_states()
        
        # Set initial state to main menu
        self.state_manager.change_state("main_menu")
        
        # Set up clock for controlling frame rate
        self.clock = pygame.time.Clock()
        
        # Flag to track if the game is running
        self.running = True
        
        logger.info("Game initialized successfully")
    
    def _register_game_states(self):
        """Register all game states with the state manager."""
        self.state_manager.register_state("main_menu", MainMenuState(self.state_manager, self.event_bus, self.settings))
        self.state_manager.register_state("world_exploration", WorldExplorationState(self.state_manager, self.event_bus, self.settings))
        self.state_manager.register_state("investigation", InvestigationState(self.state_manager, self.event_bus, self.settings))
        self.state_manager.register_state("dungeon", DungeonState(self.state_manager, self.event_bus, self.settings))
        self.state_manager.register_state("base_building", BaseBuildingState(self.state_manager, self.event_bus, self.settings))
        self.state_manager.register_state("town", TownState(self.state_manager, self.event_bus, self.settings))
        self.state_manager.register_state("combat", CombatGameState(self.state_manager, self.event_bus, self.settings))
        self.state_manager.register_state("pause_menu", PauseMenuState(self.state_manager, self.event_bus, self.settings))
    
    def handle_events(self):
        """Process all game events."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            
            # Forward event to current state
            self.state_manager.handle_event(event)
    
    def update(self, dt):
        """Update game state."""
        self.state_manager.update(dt)
        self.notification_manager.update(dt)
        self.quest_notification_manager.update(dt)
        self.quest_marker_manager.update_markers(dt)

        # Update quest UI so it is accessible in all states
        if hasattr(self, "quest_ui"):
            self.quest_ui.update(dt)
    
    def render(self):
        """Render the current game state."""
        self.state_manager.render()
        # Render quest markers after the main state but before notifications
        # Get current state to get camera position
        current_state = self.state_manager.current_state if hasattr(self.state_manager, "current_state") else None
        camera_offset = (0, 0)
        if current_state and hasattr(current_state, "camera_x") and hasattr(current_state, "camera_y"):
            camera_offset = (current_state.camera_x, current_state.camera_y)
        self.quest_marker_manager.draw_markers(self.screen, camera_offset)
        
        # Draw quest UI if it exists and is visible
        if hasattr(self, "quest_ui"):
            self.quest_ui.draw()
            
        self.notification_manager.render(self.screen)
        self.quest_notification_manager.draw(self.screen)
        pygame.display.flip()
    
    def run(self):
        """Main game loop."""
        logger.info("Starting game loop")
        
        try:
            while self.running:
                # Calculate delta time (time since last frame) in seconds
                dt = self.clock.tick(self.settings.fps) / 1000.0
                
                # Handle events, update game state, and render
                self.handle_events()
                self.update(dt)
                self.render()
        except Exception as e:
            logger.error(f"Exception in main game loop: {e}", exc_info=True)
            
            # Handle specific errors
            error_message = str(e)
            if "noise" in error_message.lower() or "module" in error_message.lower():
                logger.error("This might be a dependency issue. Make sure to install the required packages:")
                logger.error("pip install noise numpy")
            elif "numpy" in error_message.lower():
                logger.error("This may be related to NumPy. Make sure you've installed it with: pip install numpy")
                
            # Display error to user
            if self.screen:
                font = pygame.font.SysFont(None, 24)
                text = font.render(f"Error: {str(e)}", True, (255, 0, 0))
                self.screen.fill((0, 0, 0))
                self.screen.blit(text, (10, 10))
                pygame.display.flip()
                pygame.time.wait(5000)  # Show error for 5 seconds
        finally:
            self._cleanup()
    
    def _cleanup(self):
        """Clean up resources before exiting."""
        logger.info("Cleaning up resources")
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    try:
        game = Game()
        game.run()
    except Exception as e:
        logger.error(f"Unhandled exception: {e}", exc_info=True)
        pygame.quit()
        sys.exit(1)