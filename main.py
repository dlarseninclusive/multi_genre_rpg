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
from event_bus import EventBus
from settings import Settings
from save_system import SaveSystem

# Configure logging
logging.basicConfig(
    level=logging.INFO,
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
        
        # Create state manager and register game states
        self.state_manager = StateManager(self.screen, self.event_bus)
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
    
    def render(self):
        """Render the current game state."""
        self.state_manager.render()
        self.notification_manager.render(self.screen)
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
