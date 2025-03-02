# faction_ui.py
import pygame
from typing import Dict, List, Tuple, Optional
from faction_system.faction_system import Faction, FactionManager, RelationshipStatus

class FactionUI:
    """UI component for displaying faction information"""
    
    def __init__(self, screen: pygame.Surface, faction_manager: FactionManager, fonts: Dict):
        self.screen = screen
        self.faction_manager = faction_manager
        self.fonts = fonts
        
        # UI state
        self.selected_faction: Optional[str] = None
        self.scroll_offset = 0
        self.max_scroll = 0
        self.show_relationships = False
        
        # UI settings
        self.padding = 20
        self.item_height = 40
        self.reputation_bar_width = 200
        self.reputation_bar_height = 20
        
        # UI colors
        self.text_color = (240, 240, 240)
        self.bg_color = (40, 40, 50, 220)  # With alpha for transparency
        self.highlight_color = (60, 100, 160)
        self.button_color = (80, 80, 100)
        self.button_hover_color = (100, 100, 140)
        
        # Reputation bar colors
        self.rep_colors = {
            RelationshipStatus.ALLIED: (50, 200, 100),      # Green
            RelationshipStatus.FRIENDLY: (100, 180, 80),    # Light green
            RelationshipStatus.NEUTRAL: (180, 180, 80),     # Yellow
            RelationshipStatus.UNFRIENDLY: (200, 100, 50),  # Orange
            RelationshipStatus.HOSTILE: (200, 50, 50)       # Red
        }
        
        # UI elements
        self.buttons = {}
        self._create_buttons()
    
    def _create_buttons(self):
        """Create UI button elements"""
        self.buttons = {
            "close": pygame.Rect(0, 0, 100, 30),  # Will position dynamically
            "relationships": pygame.Rect(0, 0, 180, 30),  # Will position dynamically
            "scroll_up": pygame.Rect(0, 0, 30, 30),  # Will position dynamically
            "scroll_down": pygame.Rect(0, 0, 30, 30)  # Will position dynamically
        }
    
    def draw(self, player_pos: Tuple[int, int] = None):
        """Draw the faction UI panel"""
        if player_pos is None:
            # Default to center of screen if no position provided
            player_pos = (self.screen.get_width() // 2, self.screen.get_height() // 2)
        
        # Determine panel size and position
        panel_width = 500
        panel_height = 400
        panel_x = max(10, min(self.screen.get_width() - panel_width - 10, 
                             player_pos[0] - panel_width // 2))
        panel_y = max(10, min(self.screen.get_height() - panel_height - 10, 
                             player_pos[1] - panel_height // 2))
        
        # Create a transparent surface for the panel
        panel_surface = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
        pygame.draw.rect(panel_surface, self.bg_color, (0, 0, panel_width, panel_height), border_radius=10)
        
        # Draw panel title
        title_text = self.fonts["title"].render("Factions", True, self.text_color)
        panel_surface.blit(title_text, (self.padding, self.padding))
        
        # Position and draw buttons
        button_y = self.padding
        self.buttons["close"] = pygame.Rect(panel_width - 100 - self.padding, button_y, 100, 30)
        pygame.draw.rect(panel_surface, self.button_color, self.buttons["close"], border_radius=5)
        close_text = self.fonts["button"].render("Close", True, self.text_color)
        panel_surface.blit(close_text, (self.buttons["close"].x + 10, self.buttons["close"].y + 5))
        
        self.buttons["relationships"] = pygame.Rect(self.buttons["close"].x - 180 - 10, button_y, 180, 30)
        rel_button_text = "Hide Relationships" if self.show_relationships else "Show Relationships"
        pygame.draw.rect(panel_surface, self.button_color, self.buttons["relationships"], border_radius=5)
        rel_text = self.fonts["button"].render(rel_button_text, True, self.text_color)
        panel_surface.blit(rel_text, (self.buttons["relationships"].x + 10, self.buttons["relationships"].y + 5))
        
        # Draw faction list
        content_y = self.padding + 50
        content_height = panel_height - content_y - self.padding
        self._draw_faction_list(panel_surface, self.padding, content_y, panel_width - self.padding * 2, content_height)
        
        # Draw scroll buttons
        scroll_button_size = 30
        self.buttons["scroll_up"] = pygame.Rect(panel_width - scroll_button_size - self.padding, 
                                               content_y, scroll_button_size, scroll_button_size)
        self.buttons["scroll_down"] = pygame.Rect(panel_width - scroll_button_size - self.padding, 
                                                 content_y + content_height - scroll_button_size, 
                                                 scroll_button_size, scroll_button_size)
        
        pygame.draw.rect(panel_surface, self.button_color, self.buttons["scroll_up"], border_radius=5)
        pygame.draw.rect(panel_surface, self.button_color, self.buttons["scroll_down"], border_radius=5)
        
        # Draw scroll button arrows
        # Up arrow
        pygame.draw.polygon(panel_surface, self.text_color, [
            (self.buttons["scroll_up"].centerx, self.buttons["scroll_up"].y + 8),
            (self.buttons["scroll_up"].x + 8, self.buttons["scroll_up"].y + 18),
            (self.buttons["scroll_up"].right - 8, self.buttons["scroll_up"].y + 18)
        ])
        
        # Down arrow
        pygame.draw.polygon(panel_surface, self.text_color, [
            (self.buttons["scroll_down"].centerx, self.buttons["scroll_down"].bottom - 8),
            (self.buttons["scroll_down"].x + 8, self.buttons["scroll_down"].y + 12),
            (self.buttons["scroll_down"].right - 8, self.buttons["scroll_down"].y + 12)
        ])
        
        # Finally, draw the panel to the screen
        self.screen.blit(panel_surface, (panel_x, panel_y))
        
        # Update button rects to screen coordinates for event handling
        for button_name, button_rect in self.buttons.items():
            self.buttons[button_name] = pygame.Rect(button_rect.x + panel_x, button_rect.y + panel_y, 
                                                   button_rect.width, button_rect.height)
    
    def _draw_faction_list(self, surface, x, y, width, height):
        """Draw the scrollable list of factions"""
        # Calculate visible factions
        factions_list = list(self.faction_manager.factions.values())
        faction_item_height = 60 if not self.show_relationships else 120
        visible_factions = height // faction_item_height
        
        # Update max scroll value
        self.max_scroll = max(0, len(factions_list) - visible_factions)
        self.scroll_offset = min(self.scroll_offset, self.max_scroll)
        
        # Draw each visible faction
        for i in range(self.scroll_offset, min(self.scroll_offset + visible_factions, len(factions_list))):
            faction = factions_list[i]
            item_y = y + (i - self.scroll_offset) * faction_item_height
            
            # Highlight selected faction
            if self.selected_faction == faction.id:
                pygame.draw.rect(surface, self.highlight_color, 
                                (x, item_y, width, faction_item_height), border_radius=5)
            
            # Draw faction name with its colors
            name_bg_rect = pygame.Rect(x + 10, item_y + 10, width - 20, 30)
            pygame.draw.rect(surface, faction.primary_color, name_bg_rect, border_radius=5)
            pygame.draw.rect(surface, faction.secondary_color, name_bg_rect, border_radius=5, width=3)
            
            name_text = self.fonts["faction_name"].render(faction.name, True, self.text_color)
            surface.blit(name_text, (name_bg_rect.x + 10, name_bg_rect.y + 5))
            
            # Draw faction type
            type_text = self.fonts["small"].render(f"Type: {faction.faction_type.name}", True, self.text_color)
            surface.blit(type_text, (x + 20, item_y + 45))
            
            # Draw player reputation with this faction
            rep_value = self.faction_manager.player_reputation.get(faction.id, 0)
            rep_status = self.faction_manager.get_player_faction_status(faction.id)
            
            # Draw reputation bar background
            rep_bar_x = x + width - self.reputation_bar_width - 20
            rep_bar_y = item_y + 45
            pygame.draw.rect(surface, (60, 60, 60), 
                            (rep_bar_x, rep_bar_y, self.reputation_bar_width, self.reputation_bar_height), 
                            border_radius=3)
            
            # Draw reputation value
            rep_width = int(((rep_value + 100) / 200) * self.reputation_bar_width)
            pygame.draw.rect(surface, self.rep_colors[rep_status], 
                            (rep_bar_x, rep_bar_y, rep_width, self.reputation_bar_height), 
                            border_radius=3)
            
            # Draw reputation text
            rep_text = self.fonts["small"].render(f"{rep_status.name}: {rep_value}", True, self.text_color)
            surface.blit(rep_text, (rep_bar_x + 5, rep_bar_y - 20))
            
            # Draw relationships if enabled
            if self.show_relationships and faction.id == self.selected_faction:
                self._draw_faction_relationships(surface, faction, x, item_y + 80, width - 20)
    
    def _draw_faction_relationships(self, surface, faction, x, y, width):
        """Draw relationship information for the selected faction"""
        # Title for relationships section
        rel_title = self.fonts["small"].render("Relationships with other factions:", True, self.text_color)
        surface.blit(rel_title, (x + 10, y))
        
        # Find all relationships for this faction
        rel_y = y + 25
        rel_height = 20
        rel_per_row = 2
        rel_width = width // rel_per_row - 10
        
        row = 0
        col = 0
        
        for other_id, other_faction in self.faction_manager.factions.items():
            if other_id == faction.id:
                continue
                
            status = self.faction_manager.get_relationship(faction.id, other_id)
            
            # Calculate position
            rel_x = x + 10 + col * (rel_width + 10)
            current_rel_y = rel_y + row * (rel_height + 5)
            
            # Draw relationship indicator
            pygame.draw.rect(surface, self.rep_colors[status], 
                            (rel_x, current_rel_y, 10, rel_height), border_radius=2)
            
            # Draw faction name
            other_name = other_faction.name[:20] + "..." if len(other_faction.name) > 20 else other_faction.name
            rel_text = self.fonts["small"].render(f"{other_name}: {status.name}", True, self.text_color)
            surface.blit(rel_text, (rel_x + 15, current_rel_y))
            
            # Update position for next relationship
            col += 1
            if col >= rel_per_row:
                col = 0
                row += 1
    
    def handle_event(self, event: pygame.event.Event, mouse_pos: Tuple[int, int]) -> bool:
        """Handle UI events, return True if event was consumed"""
        if event.type == pygame.MOUSEBUTTONDOWN:
            # Check button clicks
            for button_name, button_rect in self.buttons.items():
                if button_rect.collidepoint(mouse_pos):
                    self._handle_button_click(button_name)
                    return True
            
            # Check faction list clicks
            panel_width = 500
            panel_height = 400
            panel_x = mouse_pos[0] - (mouse_pos[0] % panel_width)
            panel_y = mouse_pos[1] - (mouse_pos[1] % panel_height)
            
            content_y = panel_y + self.padding + 50
            content_width = panel_width - self.padding * 2
            
            # If click is in faction list area
            faction_item_height = 60 if not self.show_relationships else 120
            rel_x = panel_x + self.padding
            
            if (rel_x <= mouse_pos[0] <= rel_x + content_width and
                content_y <= mouse_pos[1]):
                
                # Calculate which faction was clicked
                idx = self.scroll_offset + (mouse_pos[1] - content_y) // faction_item_height
                factions_list = list(self.faction_manager.factions.values())
                
                if 0 <= idx < len(factions_list):
                    self.selected_faction = factions_list[idx].id
                    return True
        
        # Scrolling with mousewheel
        elif event.type == pygame.MOUSEWHEEL:
            if event.y > 0:  # Scroll up
                self.scroll_offset = max(0, self.scroll_offset - 1)
                return True
            elif event.y < 0:  # Scroll down
                self.scroll_offset = min(self.max_scroll, self.scroll_offset + 1)
                return True
                
        return False
    
    def _handle_button_click(self, button_name: str):
        """Handle UI button clicks"""
        if button_name == "close":
            # Signal to close the UI
            self.selected_faction = None
            # This would be handled by the state manager
        
        elif button_name == "relationships":
            self.show_relationships = not self.show_relationships
        
        elif button_name == "scroll_up":
            self.scroll_offset = max(0, self.scroll_offset - 1)
        
        elif button_name == "scroll_down":
            self.scroll_offset = min(self.max_scroll, self.scroll_offset + 1)


# Example usage
if __name__ == "__main__":
    import sys
    from faction_system.faction_generator import FactionGenerator
    
    # Initialize pygame
    pygame.init()
    screen = pygame.display.set_mode((1024, 768))
    pygame.display.set_caption("Faction UI Test")
    
    # Create fonts
    fonts = {
        "title": pygame.font.SysFont('Arial', 24, bold=True),
        "button": pygame.font.SysFont('Arial', 18),
        "faction_name": pygame.font.SysFont('Arial', 20, bold=True),
        "normal": pygame.font.SysFont('Arial', 16),
        "small": pygame.font.SysFont('Arial', 14)
    }
    
    # Generate factions
    faction_manager = FactionGenerator.generate_default_factions()
    
    # Create UI
    faction_ui = FactionUI(screen, faction_manager, fonts)
    
    # Main loop
    clock = pygame.time.Clock()
    running = True
    
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            # Pass events to UI
            faction_ui.handle_event(event, pygame.mouse.get_pos())
        
        # Draw
        screen.fill((30, 30, 40))
        faction_ui.draw()
        pygame.display.flip()
        
        clock.tick(60)
    
    pygame.quit()
    sys.exit()