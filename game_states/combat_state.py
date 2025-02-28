import pygame
import logging
from game_state import GameState

logger = logging.getLogger("combat")

class CombatGameState(GameState):
    """
    Game state for turn-based combat.
    
    This state handles:
    - Turn-based combat system
    - Combat UI and animations
    - Combat rewards and progression
    """
    
    def __init__(self, state_manager, event_bus, settings):
        """
        Initialize combat state.
        
        Args:
            state_manager: StateManager instance
            event_bus: EventBus for communication
            settings: Game settings
        """
        super().__init__(state_manager, event_bus, settings)
        # We'll implement the combat manager later
        # self.combat_manager = CombatManager(event_bus, settings)
        logger.info("CombatGameState initialized")
    
    def enter(self, data=None):
        """
        Enter the combat state.
        
        Args:
            data: Optional data dictionary with:
                - player_entities: List of player entities
                - enemy_entities: List of enemy entities
                - background: Optional background image
        """
        super().enter(data)
        
        try:
            # Get player character from game data
            player_character = self.state_manager.get_persistent_data("player_character")
            if not player_character:
                # Create a default player character if not found
                player_character = {
                    "name": "Hero",
                    "level": 1
                }
            
            # For now, just show a placeholder combat screen
            logger.info(f"Started combat with player: {player_character.get('name', 'Unknown')}")
            
            # Show notification
            self.event_bus.publish("show_notification", {
                "title": "Combat Started",
                "message": "You've entered combat mode!",
                "duration": 3.0
            })
            
            # Subscribe to combat events
            # self.event_bus.subscribe("combat_ended", self._handle_combat_end)
            
            logger.info("Entered combat state")
        except Exception as e:
            logger.error(f"Error entering combat state: {e}", exc_info=True)
    
    def exit(self):
        """Exit the combat state."""
        super().exit()
        
        # Unsubscribe from events
        # self.event_bus.unsubscribe("combat_ended", self._handle_combat_end)
        
        logger.info("Exited combat state")
    
    def handle_event(self, event):
        """
        Handle pygame events.
        
        Args:
            event: Pygame event
            
        Returns:
            Boolean indicating if event was handled
        """
        # Handle escape key to exit combat (for debugging/testing)
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                # End combat and return to previous state
                self.change_state("world_exploration")
                return True
            elif event.key == pygame.K_SPACE:
                # Simulate combat victory
                self._handle_combat_victory()
                return True
        
        return super().handle_event(event)
    
    def update(self, dt):
        """
        Update state.
        
        Args:
            dt: Time delta in seconds
        """
        super().update(dt)
        
        # Update combat manager
        # self.combat_manager.update(dt)
    
    def render(self, screen):
        """
        Render state.
        
        Args:
            screen: Pygame surface to render on
        """
        # Clear screen with dark background
        screen.fill((20, 20, 40))
        
        # Draw placeholder combat UI
        font = pygame.font.SysFont(None, 36)
        
        # Title
        title_text = font.render("COMBAT MODE", True, (255, 255, 255))
        screen.blit(title_text, (screen.get_width() // 2 - title_text.get_width() // 2, 50))
        
        # Instructions
        font_small = pygame.font.SysFont(None, 24)
        instr1 = font_small.render("Press SPACE to win combat", True, (200, 200, 200))
        instr2 = font_small.render("Press ESC to flee", True, (200, 200, 200))
        
        screen.blit(instr1, (screen.get_width() // 2 - instr1.get_width() // 2, 120))
        screen.blit(instr2, (screen.get_width() // 2 - instr2.get_width() // 2, 150))
        
        # Player area
        pygame.draw.rect(screen, (50, 50, 80), (50, 200, screen.get_width() - 100, 100))
        player_text = font.render("Player", True, (255, 255, 255))
        screen.blit(player_text, (100, 230))
        
        # Enemy area
        pygame.draw.rect(screen, (80, 50, 50), (50, 350, screen.get_width() - 100, 100))
        enemy_text = font.render("Enemy", True, (255, 255, 255))
        screen.blit(enemy_text, (100, 380))
    
    def _handle_combat_victory(self):
        """Handle combat victory."""
        # Publish notification of victory
        self.event_bus.publish("show_notification", {
            "title": "Victory!",
            "message": "You won the battle!",
            "duration": 3.0
        })
        
        # Return to previous state
        self.change_state("world_exploration")
