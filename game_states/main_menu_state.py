import pygame
import logging
import os
from game_state import GameState
from save_system import SaveSystem
from settings import Settings

logger = logging.getLogger("main_menu")

class MainMenuState(GameState):
    """
    Game state for the main menu.
    
    This state handles:
    - New game creation
    - Loading saved games
    - Settings menu
    - Credits and game exit
    """
    
    def __init__(self, state_manager, event_bus, settings):
        """Initialize the main menu state."""
        super().__init__(state_manager, event_bus, settings)
        
        # UI elements
        self.font_title = None
        self.font_large = None
        self.font_medium = None
        self.font_small = None
        
        # Menu state
        self.current_menu = "main"  # main, new_game, load_game, settings, credits
        self.selected_save_slot = None
        self.character_creation_data = {}
        
        # UI colors
        self.colors = {
            'background': (20, 20, 40),
            'title': (255, 255, 100),
            'text': (255, 255, 255),
            'button': (50, 50, 80),
            'button_hover': (80, 80, 120),
            'button_text': (255, 255, 255),
            'highlight': (100, 150, 255),
            'input_bg': (30, 30, 50),
            'input_text': (255, 255, 255),
            'disabled': (100, 100, 100)
        }
        
        # Save system
        self.save_system = SaveSystem()
        
        # Buttons
        self.buttons = {}
        
        # Input fields
        self.input_fields = {}
        self.active_input = None
        
        # Animation properties
        self.title_offset = 0
        self.animate_title = True
        
        logger.info("MainMenuState initialized")
    
    def enter(self, data=None):
        """Set up the state when entered."""
        super().enter(data)
        
        # Initialize fonts
        pygame.font.init()
        try:
            self.font_title = pygame.font.Font(None, 72)
            self.font_large = pygame.font.Font(None, 48)
            self.font_medium = pygame.font.Font(None, 36)
            self.font_small = pygame.font.Font(None, 24)
        except:
            # Fallback to system font
            self.font_title = pygame.font.SysFont(None, 72)
            self.font_large = pygame.font.SysFont(None, 48)
            self.font_medium = pygame.font.SysFont(None, 36)
            self.font_small = pygame.font.SysFont(None, 24)
        
        # Set up buttons
        self._setup_buttons()
        
        # Initialize character creation data
        self.character_creation_data = {
            'name': 'Adventurer',
            'race': 'Human',
            'class': 'Warrior'
        }
        
        logger.info("Entered main menu state")
    
    def exit(self):
        """Clean up when leaving the state."""
        super().exit()
        logger.info("Exited main menu state")
    
    def handle_event(self, event):
        """Handle pygame events."""
        if not self.active:
            return
        
        if event.type == pygame.MOUSEBUTTONDOWN:
            # Handle button clicks
            pos = pygame.mouse.get_pos()
            self._handle_button_click(pos)
            
            # Handle input field clicks
            self._handle_input_field_click(pos)
            
        elif event.type == pygame.KEYDOWN:
            # Handle keyboard input
            if event.key == pygame.K_ESCAPE:
                if self.current_menu != "main":
                    self.current_menu = "main"
                    self._setup_buttons()
            
            # Handle input field text input
            if self.active_input is not None:
                if event.key == pygame.K_BACKSPACE:
                    self.input_fields[self.active_input]['text'] = self.input_fields[self.active_input]['text'][:-1]
                elif event.key == pygame.K_RETURN:
                    # Deactivate current input
                    self.active_input = None
                else:
                    # Add character to input
                    if len(self.input_fields[self.active_input]['text']) < self.input_fields[self.active_input]['max_length']:
                        self.input_fields[self.active_input]['text'] += event.unicode
                        
                        # Update character creation data if this is a character field
                        if self.active_input == 'character_name':
                            self.character_creation_data['name'] = self.input_fields[self.active_input]['text']
    
    def update(self, dt):
        """Update game state."""
        if not self.active:
            return
        
        # Update title animation
        if self.animate_title:
            self.title_offset = 5 * math.sin(pygame.time.get_ticks() / 500)
    
    def render(self, screen):
        """Render the game state."""
        if not self.visible:
            return
        
        # Fill background
        screen.fill(self.colors['background'])
        
        # Render current menu
        if self.current_menu == "main":
            self._render_main_menu(screen)
        elif self.current_menu == "new_game":
            self._render_new_game_menu(screen)
        elif self.current_menu == "load_game":
            self._render_load_game_menu(screen)
        elif self.current_menu == "settings":
            self._render_settings_menu(screen)
        elif self.current_menu == "credits":
            self._render_credits_menu(screen)
    
    def _setup_buttons(self):
        """Set up menu buttons based on current menu."""
        # Clear existing buttons
        self.buttons = {}
        
        # Screen dimensions
        screen_width, screen_height = pygame.display.get_surface().get_size()
        
        button_width = 250
        button_height = 60
        button_spacing = 20
        
        if self.current_menu == "main":
            # Main menu buttons
            buttons = ["New Game", "Load Game", "Settings", "Credits", "Exit"]
            
            for i, text in enumerate(buttons):
                button_y = screen_height // 2 + i * (button_height + button_spacing)
                
                self.buttons[text] = {
                    'rect': pygame.Rect((screen_width - button_width) // 2, button_y, button_width, button_height),
                    'text': text,
                    'hover': False,
                    'enabled': True
                }
        
        elif self.current_menu == "new_game":
            # New game menu buttons
            self.buttons["Start Game"] = {
                'rect': pygame.Rect((screen_width - button_width) // 2, screen_height - button_height - 50, button_width, button_height),
                'text': "Start Game",
                'hover': False,
                'enabled': True
            }
            
            self.buttons["Back"] = {
                'rect': pygame.Rect(50, screen_height - button_height - 50, 120, button_height),
                'text': "Back",
                'hover': False,
                'enabled': True
            }
            
            # Race selection buttons
            races = ["Human", "Elf", "Dwarf", "Orc"]
            race_button_width = 120
            race_button_spacing = 10
            
            for i, race in enumerate(races):
                button_x = (screen_width - (race_button_width * len(races) + race_button_spacing * (len(races) - 1))) // 2 + i * (race_button_width + race_button_spacing)
                
                self.buttons[f"race_{race}"] = {
                    'rect': pygame.Rect(button_x, 250, race_button_width, 40),
                    'text': race,
                    'hover': False,
                    'enabled': True,
                    'selected': self.character_creation_data['race'] == race
                }
            
            # Class selection buttons
            classes = ["Warrior", "Mage", "Rogue", "Cleric"]
            class_button_width = 120
            class_button_spacing = 10
            
            for i, cls in enumerate(classes):
                button_x = (screen_width - (class_button_width * len(classes) + class_button_spacing * (len(classes) - 1))) // 2 + i * (class_button_width + class_button_spacing)
                
                self.buttons[f"class_{cls}"] = {
                    'rect': pygame.Rect(button_x, 350, class_button_width, 40),
                    'text': cls,
                    'hover': False,
                    'enabled': True,
                    'selected': self.character_creation_data['class'] == cls
                }
            
            # Set up input fields
            self.input_fields = {
                'character_name': {
                    'rect': pygame.Rect((screen_width - 300) // 2, 150, 300, 40),
                    'text': self.character_creation_data['name'],
                    'placeholder': 'Enter character name',
                    'max_length': 20
                }
            }
        
        elif self.current_menu == "load_game":
            # Load game menu buttons
            self.buttons["Load Selected"] = {
                'rect': pygame.Rect((screen_width - button_width) // 2, screen_height - button_height - 50, button_width, button_height),
                'text': "Load Selected",
                'hover': False,
                'enabled': self.selected_save_slot is not None
            }
            
            self.buttons["Back"] = {
                'rect': pygame.Rect(50, screen_height - button_height - 50, 120, button_height),
                'text': "Back",
                'hover': False,
                'enabled': True
            }
            
            # Save slot buttons
            slot_width = 400
            slot_height = 80
            slot_spacing = 10
            
            save_info = self.save_system.get_save_info()
            
            for i, info in enumerate(save_info):
                slot_y = 150 + i * (slot_height + slot_spacing)
                
                self.buttons[f"save_slot_{i+1}"] = {
                    'rect': pygame.Rect((screen_width - slot_width) // 2, slot_y, slot_width, slot_height),
                    'text': f"Slot {i+1}" + (f": {info['datetime']}" if info['exists'] else ": Empty"),
                    'hover': False,
                    'enabled': info['exists'],
                    'selected': self.selected_save_slot == i+1,
                    'save_info': info
                }
        
        elif self.current_menu == "settings":
            # Settings menu buttons
            self.buttons["Apply"] = {
                'rect': pygame.Rect((screen_width - button_width) // 2, screen_height - button_height - 50, button_width, button_height),
                'text': "Apply",
                'hover': False,
                'enabled': True
            }
            
            self.buttons["Back"] = {
                'rect': pygame.Rect(50, screen_height - button_height - 50, 120, button_height),
                'text': "Back",
                'hover': False,
                'enabled': True
            }
            
            # Toggle buttons for settings
            self.buttons["Fullscreen"] = {
                'rect': pygame.Rect((screen_width - 200) // 2, 150, 200, 40),
                'text': "Fullscreen: " + ("ON" if self.settings.fullscreen else "OFF"),
                'hover': False,
                'enabled': True,
                'selected': self.settings.fullscreen
            }
            
            self.buttons["Sound"] = {
                'rect': pygame.Rect((screen_width - 200) // 2, 200, 200, 40),
                'text': "Sound: " + ("ON" if self.settings.sound_enabled else "OFF"),
                'hover': False,
                'enabled': True,
                'selected': self.settings.sound_enabled
            }
            
            self.buttons["Music"] = {
                'rect': pygame.Rect((screen_width - 200) // 2, 250, 200, 40),
                'text': "Music: " + ("ON" if self.settings.music_enabled else "OFF"),
                'hover': False,
                'enabled': True,
                'selected': self.settings.music_enabled
            }
            
            # Resolution buttons
            resolutions = [
                (800, 600),
                (1024, 768),
                (1280, 720),
                (1366, 768),
                (1600, 900),
                (1920, 1080)
            ]
            
            for i, res in enumerate(resolutions):
                col = i % 3
                row = i // 3
                
                button_width = 200
                button_height = 40
                button_spacing = 10
                
                button_x = (screen_width - (button_width * 3 + button_spacing * 2)) // 2 + col * (button_width + button_spacing)
                button_y = 320 + row * (button_height + button_spacing)
                
                res_text = f"{res[0]}x{res[1]}"
                self.buttons[f"resolution_{res_text}"] = {
                    'rect': pygame.Rect(button_x, button_y, button_width, button_height),
                    'text': res_text,
                    'hover': False,
                    'enabled': True,
                    'selected': (self.settings.screen_width, self.settings.screen_height) == res
                }
        
        elif self.current_menu == "credits":
            # Credits menu buttons
            self.buttons["Back"] = {
                'rect': pygame.Rect(50, screen_height - button_height - 50, 120, button_height),
                'text': "Back",
                'hover': False,
                'enabled': True
            }
    
    def _handle_button_click(self, pos):
        """
        Handle button clicks.
        
        Args:
            pos: (x, y) mouse position
        """
        for button_id, button in self.buttons.items():
            if button['rect'].collidepoint(pos) and button['enabled']:
                logger.debug(f"Clicked button: {button_id}")
                
                # Main menu buttons
                if self.current_menu == "main":
                    if button_id == "New Game":
                        self.current_menu = "new_game"
                        self._setup_buttons()
                    elif button_id == "Load Game":
                        self.current_menu = "load_game"
                        self._setup_buttons()
                    elif button_id == "Settings":
                        self.current_menu = "settings"
                        self._setup_buttons()
                    elif button_id == "Credits":
                        self.current_menu = "credits"
                        self._setup_buttons()
                    elif button_id == "Exit":
                        self._exit_game()
                
                # New game menu buttons
                elif self.current_menu == "new_game":
                    if button_id == "Start Game":
                        self._start_new_game()
                    elif button_id == "Back":
                        self.current_menu = "main"
                        self._setup_buttons()
                    elif button_id.startswith("race_"):
                        race = button_id.split("_")[1]
                        self.character_creation_data['race'] = race
                        self._setup_buttons()  # Refresh buttons to show selection
                    elif button_id.startswith("class_"):
                        cls = button_id.split("_")[1]
                        self.character_creation_data['class'] = cls
                        self._setup_buttons()  # Refresh buttons to show selection
                
                # Load game menu buttons
                elif self.current_menu == "load_game":
                    if button_id == "Load Selected":
                        self._load_selected_game()
                    elif button_id == "Back":
                        self.current_menu = "main"
                        self._setup_buttons()
                    elif button_id.startswith("save_slot_"):
                        slot = int(button_id.split("_")[2])
                        self.selected_save_slot = slot
                        self._setup_buttons()  # Refresh buttons to show selection
                
                # Settings menu buttons
                elif self.current_menu == "settings":
                    if button_id == "Apply":
                        self._apply_settings()
                    elif button_id == "Back":
                        self.current_menu = "main"
                        self._setup_buttons()
                    elif button_id == "Fullscreen":
                        self.settings.fullscreen = not self.settings.fullscreen
                        self._setup_buttons()  # Refresh buttons to show new setting
                    elif button_id == "Sound":
                        self.settings.sound_enabled = not self.settings.sound_enabled
                        self._setup_buttons()  # Refresh buttons to show new setting
                    elif button_id == "Music":
                        self.settings.music_enabled = not self.settings.music_enabled
                        self._setup_buttons()  # Refresh buttons to show new setting
                    elif button_id.startswith("resolution_"):
                        res_text = button_id.split("_")[1]
                        width, height = map(int, res_text.split("x"))
                        self.settings.screen_width = width
                        self.settings.screen_height = height
                        self._setup_buttons()  # Refresh buttons to show selection
                
                # Credits menu buttons
                elif self.current_menu == "credits":
                    if button_id == "Back":
                        self.current_menu = "main"
                        self._setup_buttons()
    
    def _handle_input_field_click(self, pos):
        """
        Handle clicks on input fields.
        
        Args:
            pos: (x, y) mouse position
        """
        # Deactivate current input
        self.active_input = None
        
        # Check if clicked on an input field
        for input_id, input_field in self.input_fields.items():
            if input_field['rect'].collidepoint(pos):
                self.active_input = input_id
                break
    
    def _render_main_menu(self, screen):
        """
        Render the main menu.
        
        Args:
            screen: Pygame surface to render to
        """
        screen_width, screen_height = screen.get_size()
        
        # Render title
        title_text = self.font_title.render("Multi-Genre RPG", True, self.colors['title'])
        title_rect = title_text.get_rect(center=(screen_width // 2, 120 + self.title_offset))
        screen.blit(title_text, title_rect)
        
        # Render subtitle
        subtitle_text = self.font_medium.render("A Pygame RPG Adventure", True, self.colors['text'])
        subtitle_rect = subtitle_text.get_rect(center=(screen_width // 2, 180))
        screen.blit(subtitle_text, subtitle_rect)
        
        # Render buttons
        self._render_buttons(screen)
        
        # Render version info
        version_text = self.font_small.render("Version 1.0", True, self.colors['text'])
        version_rect = version_text.get_rect(bottomright=(screen_width - 20, screen_height - 20))
        screen.blit(version_text, version_rect)
    
    def _render_new_game_menu(self, screen):
        """
        Render the new game menu.
        
        Args:
            screen: Pygame surface to render to
        """
        screen_width, screen_height = screen.get_size()
        
        # Render title
        title_text = self.font_large.render("Create New Character", True, self.colors['title'])
        title_rect = title_text.get_rect(center=(screen_width // 2, 60))
        screen.blit(title_text, title_rect)
        
        # Render name label
        name_label = self.font_medium.render("Character Name:", True, self.colors['text'])
        name_label_rect = name_label.get_rect(center=(screen_width // 2, 120))
        screen.blit(name_label, name_label_rect)
        
        # Render name input field
        name_input = self.input_fields['character_name']
        pygame.draw.rect(screen, self.colors['input_bg'], name_input['rect'])
        
        # Draw input border (highlighted if active)
        border_color = self.colors['highlight'] if self.active_input == 'character_name' else self.colors['button']
        pygame.draw.rect(screen, border_color, name_input['rect'], 2)
        
        # Draw input text or placeholder
        if name_input['text']:
            text_surface = self.font_medium.render(name_input['text'], True, self.colors['input_text'])
        else:
            text_surface = self.font_medium.render(name_input['placeholder'], True, self.colors['disabled'])
        
        text_rect = text_surface.get_rect(midleft=(name_input['rect'].left + 10, name_input['rect'].centery))
        screen.blit(text_surface, text_rect)
        
        # Render race label
        race_label = self.font_medium.render("Race:", True, self.colors['text'])
        race_label_rect = race_label.get_rect(center=(screen_width // 2, 220))
        screen.blit(race_label, race_label_rect)
        
        # Race buttons are rendered in _render_buttons
        
        # Render class label
        class_label = self.font_medium.render("Class:", True, self.colors['text'])
        class_label_rect = class_label.get_rect(center=(screen_width // 2, 320))
        screen.blit(class_label, class_label_rect)
        
        # Class buttons are rendered in _render_buttons
        
        # Render preview
        preview_label = self.font_medium.render("Preview:", True, self.colors['text'])
        preview_label_rect = preview_label.get_rect(center=(screen_width // 2, 420))
        screen.blit(preview_label, preview_label_rect)
        
        # Render character preview
        preview_rect = pygame.Rect((screen_width - 150) // 2, 450, 150, 150)
        pygame.draw.rect(screen, self.colors['input_bg'], preview_rect)
        pygame.draw.rect(screen, self.colors['button'], preview_rect, 2)
        
        # Draw character info
        preview_text = self.font_small.render(
            f"{self.character_creation_data['name']}",
            True, self.colors['text']
        )
        preview_text_rect = preview_text.get_rect(center=(preview_rect.centerx, preview_rect.top + 20))
        screen.blit(preview_text, preview_text_rect)
        
        race_text = self.font_small.render(
            f"Race: {self.character_creation_data['race']}",
            True, self.colors['text']
        )
        race_text_rect = race_text.get_rect(center=(preview_rect.centerx, preview_rect.top + 50))
        screen.blit(race_text, race_text_rect)
        
        class_text = self.font_small.render(
            f"Class: {self.character_creation_data['class']}",
            True, self.colors['text']
        )
        class_text_rect = class_text.get_rect(center=(preview_rect.centerx, preview_rect.top + 80))
        screen.blit(class_text, class_text_rect)
        
        # Render buttons
        self._render_buttons(screen)
    
    def _render_load_game_menu(self, screen):
        """
        Render the load game menu.
        
        Args:
            screen: Pygame surface to render to
        """
        screen_width, screen_height = screen.get_size()
        
        # Render title
        title_text = self.font_large.render("Load Game", True, self.colors['title'])
        title_rect = title_text.get_rect(center=(screen_width // 2, 60))
        screen.blit(title_text, title_rect)
        
        # Render instructions
        instructions = self.font_medium.render("Select a save slot to load:", True, self.colors['text'])
        instructions_rect = instructions.get_rect(center=(screen_width // 2, 120))
        screen.blit(instructions, instructions_rect)
        
        # Render buttons (including save slots)
        self._render_buttons(screen)
    
    def _render_settings_menu(self, screen):
        """
        Render the settings menu.
        
        Args:
            screen: Pygame surface to render to
        """
        screen_width, screen_height = screen.get_size()
        
        # Render title
        title_text = self.font_large.render("Settings", True, self.colors['title'])
        title_rect = title_text.get_rect(center=(screen_width // 2, 60))
        screen.blit(title_text, title_rect)
        
        # Resolution section
        resolution_title = self.font_medium.render("Resolution:", True, self.colors['text'])
        resolution_rect = resolution_title.get_rect(midtop=(screen_width // 2, 300))
        screen.blit(resolution_title, resolution_rect)
        
        # Render buttons
        self._render_buttons(screen)
    
    def _render_credits_menu(self, screen):
        """
        Render the credits menu.
        
        Args:
            screen: Pygame surface to render to
        """
        screen_width, screen_height = screen.get_size()
        
        # Render title
        title_text = self.font_large.render("Credits", True, self.colors['title'])
        title_rect = title_text.get_rect(center=(screen_width // 2, 60))
        screen.blit(title_text, title_rect)
        
        # Render credits content
        credits = [
            "Multi-Genre RPG",
            "",
            "A Pygame RPG Adventure",
            "",
            "Created by: Your Name",
            "",
            "Programming:",
            "Your Name",
            "",
            "Art:",
            "Your Name",
            "",
            "Sound:",
            "Your Name",
            "",
            "Special Thanks:",
            "Pygame Community",
            "Python Community",
            "",
            "Created with Pygame"
        ]
        
        y_pos = 120
        for line in credits:
            if line:
                text_surface = self.font_medium.render(line, True, self.colors['text'])
                text_rect = text_surface.get_rect(center=(screen_width // 2, y_pos))
                screen.blit(text_surface, text_rect)
            y_pos += 30
        
        # Render buttons
        self._render_buttons(screen)
    
    def _render_buttons(self, screen):
        """
        Render all menu buttons.
        
        Args:
            screen: Pygame surface to render to
        """
        # Get mouse position for hover effect
        mouse_pos = pygame.mouse.get_pos()
        
        for button_id, button in self.buttons.items():
            # Check hover state
            button['hover'] = button['rect'].collidepoint(mouse_pos) and button['enabled']
            
            # Determine button color
            if 'selected' in button and button['selected']:
                button_color = self.colors['highlight']
            elif button['hover']:
                button_color = self.colors['button_hover']
            else:
                button_color = self.colors['button']
            
            # Draw button
            pygame.draw.rect(
                screen,
                button_color,
                button['rect']
            )
            
            # Draw border
            pygame.draw.rect(
                screen,
                self.colors['highlight'] if 'selected' in button and button['selected'] else self.colors['button_text'],
                button['rect'],
                2
            )
            
            # Draw text
            text_color = self.colors['button_text'] if button['enabled'] else self.colors['disabled']
            text_surface = self.font_medium.render(button['text'], True, text_color)
            text_rect = text_surface.get_rect(center=button['rect'].center)
            screen.blit(text_surface, text_rect)
            
            # Draw additional info for save slots
            if button_id.startswith("save_slot_") and 'save_info' in button and button['save_info']['exists']:
                info = button['save_info']
                
                # Display date in small font
                date_text = self.font_small.render(f"{info['datetime']}", True, text_color)
                date_rect = date_text.get_rect(midtop=(button['rect'].centerx, button['rect'].top + 10))
                screen.blit(date_text, date_rect)
                
                # Display metadata
                if 'metadata' in info and info['metadata']:
                    metadata = info['metadata']
                    
                    if 'character_name' in metadata:
                        char_text = self.font_small.render(
                            f"Character: {metadata['character_name']}",
                            True, text_color
                        )
                        char_rect = char_text.get_rect(midtop=(button['rect'].centerx, button['rect'].top + 30))
                        screen.blit(char_text, char_rect)
                    
                    if 'play_time' in metadata:
                        time_text = self.font_small.render(
                            f"Time: {metadata['play_time']}",
                            True, text_color
                        )
                        time_rect = time_text.get_rect(midtop=(button['rect'].centerx, button['rect'].top + 50))
                        screen.blit(time_text, time_rect)
    
    def _start_new_game(self):
        """Start a new game with the created character."""
        logger.info("Starting new game")
        
        # Create character data
        character_data = {
            'name': self.character_creation_data['name'],
            'race': self.character_creation_data['race'],
            'class': self.character_creation_data['class']
        }
        
        # Store in persistent data
        self.state_manager.set_persistent_data("player_character_template", character_data)
        
        # Reset any existing world data
        self.state_manager.set_persistent_data("world", None)
        self.state_manager.set_persistent_data("player_character", None)
        self.state_manager.set_persistent_data("player_world_position", None)
        
        # Start the game by transitioning to world exploration state
        self.change_state("world_exploration")
    
    def _load_selected_game(self):
        """Load the selected save game."""
        if self.selected_save_slot is None:
            return
        
        logger.info(f"Loading game from slot {self.selected_save_slot}")
        
        # Load game state from save slot
        game_state = self.save_system.load_game(self.selected_save_slot)
        
        if game_state:
            # Store loaded data in persistent storage
            for key, value in game_state.items():
                self.state_manager.set_persistent_data(key, value)
            
            # Transition to appropriate state
            # Usually this would be world exploration
            self.change_state("world_exploration")
        else:
            logger.error(f"Failed to load game from slot {self.selected_save_slot}")
            # TODO: Show error message
    
    def _apply_settings(self):
        """Apply the selected settings."""
        logger.info("Applying settings")
        
        # Store settings
        self.settings.save_settings()
        
        # Apply fullscreen setting immediately
        if self.settings.fullscreen:
            pygame.display.set_mode(
                (self.settings.screen_width, self.settings.screen_height),
                pygame.FULLSCREEN
            )
        else:
            pygame.display.set_mode(
                (self.settings.screen_width, self.settings.screen_height)
            )
        
        # Return to main menu
        self.current_menu = "main"
        self._setup_buttons()
    
    def _exit_game(self):
        """Exit the game."""
        logger.info("Exiting game")
        pygame.quit()
        import sys
        sys.exit()

# Import here to avoid circular import
import math
