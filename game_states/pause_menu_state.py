import pygame
import logging
from game_state import GameState

logger = logging.getLogger("pause_menu")

class PauseMenuState(GameState):
    """
    Game state for pause menu.
    
    This state handles:
    - Pausing the game
    - Resuming the game
    - Returning to main menu
    - Saving the game
    """
    
    def __init__(self, state_manager, event_bus, settings):
        """Initialize pause menu state."""
        super().__init__(state_manager, event_bus, settings)
        self.font = None
        self.buttons = []
        self.selected_button = 0
        logger.info("PauseMenuState initialized")
    
    def enter(self, data=None):
        """Set up the state when entered."""
        super().enter(data)
        
        # Initialize font
        pygame.font.init()
        self.font = pygame.font.SysFont(None, 36)
        
        # Set up buttons
        self.buttons = [
            {"text": "Resume", "action": self._resume_game},
            {"text": "Save Game", "action": self._save_game},
            {"text": "Main Menu", "action": self._return_to_main_menu},
            {"text": "Quit Game", "action": self._quit_game}
        ]
        
        self.selected_button = 0
        
        logger.info("Entered pause menu")
    
    def exit(self):
        """Clean up when leaving the state."""
        super().exit()
        logger.info("Exited pause menu")
    
    def handle_event(self, event):
        """Handle pygame events."""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                # Return to game
                self._resume_game()
                return True
            
            # Navigate menu
            elif event.key == pygame.K_UP:
                self.selected_button = (self.selected_button - 1) % len(self.buttons)
                return True
            
            elif event.key == pygame.K_DOWN:
                self.selected_button = (self.selected_button + 1) % len(self.buttons)
                return True
            
            # Select button
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                # Execute button action
                self.buttons[self.selected_button]["action"]()
                return True
        
        return super().handle_event(event)
    
    def update(self, dt):
        """Update state."""
        super().update(dt)
    
    def render(self, screen):
        """Render the pause menu."""
        # Create semi-transparent overlay
        overlay = pygame.Surface((screen.get_width(), screen.get_height()), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))  # Semi-transparent black
        screen.blit(overlay, (0, 0))
        
        # Draw title
        title_surface = self.font.render("Game Paused", True, (255, 255, 255))
        title_rect = title_surface.get_rect(center=(screen.get_width() // 2, 100))
        screen.blit(title_surface, title_rect)
        
        # Draw buttons
        button_y = 200
        for i, button in enumerate(self.buttons):
            # Highlight selected button
            color = (255, 255, 0) if i == self.selected_button else (255, 255, 255)
            
            # Create button text
            button_surface = self.font.render(button["text"], True, color)
            button_rect = button_surface.get_rect(center=(screen.get_width() // 2, button_y))
            
            # Draw button
            screen.blit(button_surface, button_rect)
            
            # Move to next position
            button_y += 50
    
    def _resume_game(self):
        """Resume the game."""
        logger.info("Resuming game")
        self.pop_state()
    
    def _save_game(self):
        """Save the current game."""
        try:
            # Get persistent data for saving
            world = self.state_manager.get_persistent_data("world")
            player_pos = self.state_manager.get_persistent_data("player_world_position")
            player_character = self.state_manager.get_persistent_data("player_character")
            
            logger.debug(f"Preparing to save: world={type(world)}, player_pos={player_pos}")
            
            # Create game state to save
            game_state = {
                "world": world,
                "player_world_position": player_pos,
                "player_character": player_character
            }
            
            # Get save system
            save_system = self.state_manager.get_persistent_data("save_system")
            if save_system:
                # Use slot 1 for now
                success = save_system.save_game(1, game_state)
                
                if success:
                    self.event_bus.publish("show_notification", {
                        "title": "Game Saved",
                        "message": "Your game has been saved successfully.",
                        "duration": 2.0
                    })
                    logger.info("Game saved successfully")
                else:
                    self.event_bus.publish("show_notification", {
                        "title": "Save Failed",
                        "message": "Failed to save the game.",
                        "duration": 2.0
                    })
                    logger.error("Failed to save game")
            else:
                logger.error("Save system not found")
                self.event_bus.publish("show_notification", {
                    "title": "Save Error",
                    "message": "Save system not available.",
                    "duration": 2.0
                })
        except Exception as e:
            logger.error(f"Error in save game: {e}", exc_info=True)
            self.event_bus.publish("show_notification", {
                "title": "Save Error",
                "message": f"An error occurred: {str(e)}",
                "duration": 3.0
            })
    
    def _return_to_main_menu(self):
        """Return to the main menu."""
        logger.info("Returning to main menu")
        self.change_state("main_menu")
    
    def _quit_game(self):
        """Quit the game."""
        logger.info("Quitting game")
        pygame.event.post(pygame.event.Event(pygame.QUIT))
