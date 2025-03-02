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
        self._resuming = False
        self.show_character_sheet = False
        self.show_character_sheet = False
        
        # Get screen dimensions
        screen_width, screen_height = pygame.display.get_surface().get_size()
        
        # Initialize UI manager if not already done
        if not hasattr(self, 'ui_manager'):
            from ui_system import UIManager
            self.ui_manager = UIManager(pygame.display.get_surface())
        
        # Create pause menu UI
        menu_width = 300
        menu_height = 400
        menu_x = (screen_width - menu_width) // 2
        menu_y = (screen_height - menu_height) // 2
        
        # Create background panel
        self.menu_panel = self.ui_manager.create_panel(
            pygame.Rect(menu_x, menu_y, menu_width, menu_height)
        )
        
        # Add title
        self.ui_manager.create_label(
            pygame.Rect(0, 20, menu_width, 40),
            "Game Paused",
            self.menu_panel
        )
        
        # Add buttons
        button_width = 200
        button_height = 40
        button_x = (menu_width - button_width) // 2
        
        # Resume button
        self.resume_button = self.ui_manager.create_button(
            pygame.Rect(button_x, 100, button_width, button_height),
            "Resume Game",
            lambda btn: self._resume_game(btn),
            self.menu_panel
        )
        
        # Save button
        self.save_button = self.ui_manager.create_button(
            pygame.Rect(button_x, 160, button_width, button_height),
            "Save Game",
            self._save_game,
            self.menu_panel
        )
        
        # Settings button
        self.settings_button = self.ui_manager.create_button(
            pygame.Rect(button_x, 220, button_width, button_height),
            "Settings",
            self._open_settings,
            self.menu_panel
        )
        
        # Character sheet button
        self.char_sheet_button = self.ui_manager.create_button(
            pygame.Rect(button_x, 280, button_width, button_height),
            "Character Sheet",
            self._toggle_character_sheet,
            self.menu_panel
        )
        
        # Main menu button
        self.main_menu_button = self.ui_manager.create_button(
            pygame.Rect(button_x, 340, button_width, button_height),
            "Return to Main Menu",
            self._return_to_main_menu,
            self.menu_panel
        )
        
        # Quit button
        self.quit_button = self.ui_manager.create_button(
            pygame.Rect(button_x, 400, button_width, button_height),
            "Quit Game",
            self._quit_game,
            self.menu_panel
        )
        
        logger.info("Entered pause menu")
    
    def exit(self):
        """Clean up when leaving the state."""
        if hasattr(self, 'ui_manager'):
            self.ui_manager.clear()
        super().exit()
        logger.info("Exited pause menu")
    
    def handle_event(self, event):
        """Handle pygame events."""
        # Let the UI manager handle the event first
        if self.ui_manager.handle_event(event):
            return True
            
        # Original keyboard controls can remain
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                # Return to game
                self._resume_game(None)
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
        self.ui_manager.update(dt)
    
    def render(self, screen):
        """Render the pause menu."""
        # Draw previous state in background
        if len(self.state_manager.state_stack) > 1:
            prev_state = self.state_manager.state_stack[-2]
            prev_state.render(screen)
        
        # Darken the screen a bit
        overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 128))  # Semi-transparent black
        screen.blit(overlay, (0, 0))
        
        # Initialize character sheet flag if not present
        if not hasattr(self, 'show_character_sheet'):
            self.show_character_sheet = False
        
        # Render UI
        self.ui_manager.render()
        
        # Character info if available
        player = self.state_manager.get_persistent_data("player_character")
        if player and self.show_character_sheet:
            self._render_character_sheet(screen, player)
    
    def _resume_game(self, button):
        """Resume the game."""
        # Prevent double-execution
        if not hasattr(self, '_resuming') or not self._resuming:
            self._resuming = True
            logger.info("Resuming game")
            self.state_manager.pop_state()
    
    def _toggle_character_sheet(self, button):
        """Toggle the character sheet."""
        self.show_character_sheet = not self.show_character_sheet
        logger.info(f"Character sheet toggled: {self.show_character_sheet}")
    
    def _render_character_sheet(self, screen, character):
        """Render the character sheet."""
        # Create a semi-transparent background
        sheet_surface = pygame.Surface((400, 500))
        sheet_surface.set_alpha(230)
        sheet_surface.fill((30, 30, 40))
        
        # Position in center of screen
        sheet_rect = sheet_surface.get_rect(center=(screen.get_width() // 2, screen.get_height() // 2))
        
        # Render character info
        title_font = pygame.font.Font(None, 36)
        label_font = pygame.font.Font(None, 24)
        value_font = pygame.font.Font(None, 24)
        
        # Character name and class
        name_text = title_font.render(f"{character.name} - Level {character.level} {character.race.name} {character.character_class.name}", True, (220, 220, 220))
        sheet_surface.blit(name_text, (20, 20))
        
        # Stats
        y_pos = 70
        for stat_name, stat in character.stats.items():
            stat_label = label_font.render(f"{stat_name.capitalize()}:", True, (180, 180, 180))
            stat_value = value_font.render(f"{stat.value}", True, (220, 220, 220))
            sheet_surface.blit(stat_label, (30, y_pos))
            sheet_surface.blit(stat_value, (150, y_pos))
            y_pos += 30
        
        # Health and Mana
        y_pos += 10
        health_label = label_font.render("Health:", True, (180, 180, 180))
        health_value = value_font.render(f"{character.health}/{character.max_health}", True, (220, 100, 100))
        sheet_surface.blit(health_label, (30, y_pos))
        sheet_surface.blit(health_value, (150, y_pos))
        
        y_pos += 30
        mana_label = label_font.render("Mana:", True, (180, 180, 180))
        mana_value = value_font.render(f"{character.mana}/{character.max_mana}", True, (100, 100, 220))
        sheet_surface.blit(mana_label, (30, y_pos))
        sheet_surface.blit(mana_value, (150, y_pos))
        
        # Experience
        y_pos += 30
        exp_label = label_font.render("Experience:", True, (180, 180, 180))
        exp_value = value_font.render(f"{character.experience}/{character.next_level_exp}", True, (220, 220, 100))
        sheet_surface.blit(exp_label, (30, y_pos))
        sheet_surface.blit(exp_value, (150, y_pos))
        
        # Skills
        y_pos += 50
        skills_label = title_font.render("Skills:", True, (220, 220, 220))
        sheet_surface.blit(skills_label, (20, y_pos))
        
        y_pos += 30
        for skill in character.skills:
            skill_text = label_font.render(f"• {skill}", True, (180, 180, 180))
            sheet_surface.blit(skill_text, (40, y_pos))
            y_pos += 25
        
        # Draw the surface to the screen
        screen.blit(sheet_surface, sheet_rect.topleft)
    
    def _save_game(self, button):
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
    
    def _open_settings(self, button):
        """Open settings menu."""
        # TODO: Implement settings menu
        self.event_bus.publish("show_notification", {
            "title": "Not Implemented",
            "message": "Settings menu not yet implemented.",
            "duration": 2.0
        })
        
    def _return_to_main_menu(self, button):
        """Return to the main menu."""
        logger.info("Returning to main menu")
        self.state_manager.change_state("main_menu")
    
    def _quit_game(self, button):
        """Quit the game."""
        logger.info("Quitting game")
        pygame.event.post(pygame.event.Event(pygame.QUIT))
