import pygame
import logging
from enum import Enum

logger = logging.getLogger("ui_system")

class UIElementType(Enum):
    """Types of UI elements."""
    PANEL = 0
    BUTTON = 1
    LABEL = 2
    IMAGE = 3
    INPUT = 4
    SLIDER = 5
    CHECKBOX = 6
    DROPDOWN = 7
    PROGRESSBAR = 8
    TOOLTIP = 9

class UIElement:
    """Base class for all UI elements."""
    
    def __init__(self, rect, element_type, parent=None):
        """
        Initialize UI element.
        
        Args:
            rect: Rectangle defining position and size
            element_type: Type from UIElementType enum
            parent: Optional parent element
        """
        self.rect = rect
        self.element_type = element_type
        self.parent = parent
        self.children = []
        self.visible = True
        self.enabled = True
        self.hover = False
        self.focus = False
        self.colors = {
            'background': (50, 50, 80, 200),
            'border': (150, 150, 200),
            'text': (255, 255, 255),
            'highlight': (100, 150, 255),
            'disabled': (100, 100, 100)
        }
        self.border_width = 1
        self.padding = 5
        self.font = None
        self.text = ""
        self.text_align = "center"  # left, center, right
        self.image = None
        self.callback = None
    
    def add_child(self, child):
        """
        Add a child element.
        
        Args:
            child: UIElement to add
        """
        child.parent = self
        self.children.append(child)
    
    def remove_child(self, child):
        """
        Remove a child element.
        
        Args:
            child: UIElement to remove
            
        Returns:
            Boolean indicating if child was removed
        """
        if child in self.children:
            self.children.remove(child)
            child.parent = None
            return True
        return False
    
    def get_absolute_rect(self):
        """
        Get absolute rectangle (accounting for parent position).
        
        Returns:
            Pygame Rect with absolute coordinates
        """
        if self.parent:
            parent_rect = self.parent.get_absolute_rect()
            return pygame.Rect(
                parent_rect.x + self.rect.x,
                parent_rect.y + self.rect.y,
                self.rect.width,
                self.rect.height
            )
        else:
            return self.rect.copy()
    
    def handle_event(self, event):
        """
        Handle a pygame event.
        
        Args:
            event: Pygame event
            
        Returns:
            Boolean indicating if event was handled
        """
        if not self.visible or not self.enabled:
            return False
        
        # Handle events for all children first
        for child in reversed(self.children):  # Reverse order for proper z-index
            if child.handle_event(event):
                return True
        
        # Mouse position tracking for hover state
        if event.type == pygame.MOUSEMOTION:
            old_hover = self.hover
            self.hover = self.get_absolute_rect().collidepoint(event.pos)
            
            # Return True if hover state changed (for UI updates)
            if old_hover != self.hover:
                return True
        
        # Handle mouse button events
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:  # Left click
            if self.get_absolute_rect().collidepoint(event.pos):
                self.focus = True
                
                # Execute callback if available
                if self.callback:
                    try:
                        self.callback(self)
                    except Exception as e:
                        logger.error(f"Error in UI element callback: {e}")
                
                return True
            else:
                self.focus = False
        
        return False
    
    def update(self, dt):
        """
        Update element state.
        
        Args:
            dt: Time delta in seconds
        """
        if not self.visible:
            return
        
        # Update hover state based on mouse position
        mouse_pos = pygame.mouse.get_pos()
        abs_rect = self.get_absolute_rect()
        self.hover = abs_rect.collidepoint(mouse_pos)
        
        # Check for mouse click
        mouse_pressed = pygame.mouse.get_pressed()[0]  # Left button
        if self.hover and mouse_pressed and not self._was_pressed:
            self.pressed = True
            if self.callback:
                try:
                    self.callback(self)
                except Exception as e:
                    logger.error(f"Error in button callback: {e}")
        elif not mouse_pressed:
            self.pressed = False
        
        self._was_pressed = mouse_pressed
        
        # Update all children
        for child in self.children:
            child.update(dt)
    
    def render(self, surface):
        """
        Render element to a surface.
        
        Args:
            surface: Pygame surface to render to
        """
        if not self.visible:
            return
        
        # Get absolute position
        rect = self.get_absolute_rect()
        
        # Draw element
        self._draw_element(surface, rect)
        
        # Render all children
        for child in self.children:
            child.render(surface)
    
    def _draw_element(self, surface, rect):
        """
        Draw the element.
        
        Args:
            surface: Pygame surface to render to
            rect: Absolute position rectangle
        """
        # Base implementation draws nothing
        pass
    
    def set_font(self, font):
        """
        Set the font for text rendering.
        
        Args:
            font: Pygame font object
        """
        self.font = font
    
    def set_text(self, text):
        """
        Set element text.
        
        Args:
            text: Text string
        """
        self.text = text
    
    def set_image(self, image):
        """
        Set element image.
        
        Args:
            image: Pygame surface
        """
        self.image = image
    
    def set_callback(self, callback):
        """
        Set callback function.
        
        Args:
            callback: Function to call when element is activated
        """
        self.callback = callback
    
    def set_position(self, x, y):
        """
        Set element position.
        
        Args:
            x: X position
            y: Y position
        """
        self.rect.x = x
        self.rect.y = y
    
    def set_size(self, width, height):
        """
        Set element size.
        
        Args:
            width: Width in pixels
            height: Height in pixels
        """
        self.rect.width = width
        self.rect.height = height
    
    def set_color(self, color_name, color):
        """
        Set element color.
        
        Args:
            color_name: Name of color property to set
            color: RGB or RGBA color tuple
        """
        if color_name in self.colors:
            self.colors[color_name] = color

class UIPanel(UIElement):
    """Panel UI element (container for other elements)."""
    
    def __init__(self, rect, parent=None):
        """
        Initialize panel.
        
        Args:
            rect: Rectangle defining position and size
            parent: Optional parent element
        """
        super().__init__(rect, UIElementType.PANEL, parent)
        self.transparent = False
    
    def _draw_element(self, surface, rect):
        """
        Draw the panel.
        
        Args:
            surface: Pygame surface to render to
            rect: Absolute position rectangle
        """
        if not self.transparent:
            # Draw background with alpha
            if len(self.colors['background']) == 4:
                # RGBA color
                bg_surface = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
                bg_surface.fill(self.colors['background'])
                surface.blit(bg_surface, rect)
            else:
                # RGB color
                pygame.draw.rect(surface, self.colors['background'], rect)
        
        # Draw border
        if self.border_width > 0:
            pygame.draw.rect(surface, self.colors['border'], rect, self.border_width)

class UIButton(UIElement):
    """Button UI element."""
    
    def __init__(self, rect, text="", parent=None):
        """
        Initialize button.
        
        Args:
            rect: Rectangle defining position and size
            text: Button text
            parent: Optional parent element
        """
        super().__init__(rect, UIElementType.BUTTON, parent)
        self.text = text
        self.pressed = False
        self.toggle = False
        self.toggled = False
        self._was_pressed = False  # Track previous press state
    
    def handle_event(self, event):
        """
        Handle a pygame event.
        
        Args:
            event: Pygame event
            
        Returns:
            Boolean indicating if event was handled
        """
        if not self.visible or not self.enabled:
            return False
        
        abs_rect = self.get_absolute_rect()
        
        # Handle mouse button events
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:  # Left click
            if abs_rect.collidepoint(event.pos):
                self.pressed = True
                return True
                
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:  # Left release
            was_pressed = self.pressed
            self.pressed = False
            
            if was_pressed and abs_rect.collidepoint(event.pos):
                if self.toggle:
                    # Toggle state
                    self.toggled = not self.toggled
                
                # Execute callback if available
                if self.callback:
                    try:
                        self.callback(self)
                    except Exception as e:
                        logger.error(f"Error in button callback: {e}")
                
                return True
                
        # Mouse movement for hover state
        elif event.type == pygame.MOUSEMOTION:
            self.hover = abs_rect.collidepoint(event.pos)
            if self.pressed and not self.hover:
                self.pressed = False
        
        return False
    
    def _draw_element(self, surface, rect):
        """
        Draw the button.
        
        Args:
            surface: Pygame surface to render to
            rect: Absolute position rectangle
        """
        # Determine button color based on state
        if not self.enabled:
            color = self.colors['disabled']
        elif self.pressed:
            color = self.colors['highlight']
        elif self.hover:
            color = (*self.colors['background'][:3], 255)  # Full opacity when hovering
        elif self.toggled:
            color = self.colors['highlight']
        else:
            color = self.colors['background']
        
        # Draw button background with alpha
        if len(color) == 4:
            bg_surface = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            bg_surface.fill(color)
            surface.blit(bg_surface, rect)
        else:
            pygame.draw.rect(surface, color, rect)
        
        # Draw border (highlighted when hovering or focused)
        border_color = self.colors['highlight'] if self.hover or self.focus else self.colors['border']
        pygame.draw.rect(surface, border_color, rect, self.border_width)
        
        # Draw text if font is available
        if self.font and self.text:
            text_color = self.colors['text'] if self.enabled else self.colors['disabled']
            text_surface = self.font.render(self.text, True, text_color)
            
            # Position text based on alignment
            if self.text_align == "left":
                text_pos = (rect.x + self.padding, rect.centery - text_surface.get_height() // 2)
            elif self.text_align == "right":
                text_pos = (rect.right - text_surface.get_width() - self.padding, 
                           rect.centery - text_surface.get_height() // 2)
            else:  # center
                text_pos = (rect.centerx - text_surface.get_width() // 2, 
                           rect.centery - text_surface.get_height() // 2)
            
            surface.blit(text_surface, text_pos)

class UILabel(UIElement):
    """Label UI element for displaying text."""
    
    def __init__(self, rect, text="", parent=None):
        """
        Initialize label.
        
        Args:
            rect: Rectangle defining position and size
            text: Label text
            parent: Optional parent element
        """
        super().__init__(rect, UIElementType.LABEL, parent)
        self.text = text
        self.transparent = True
    
    def _draw_element(self, surface, rect):
        """
        Draw the label.
        
        Args:
            surface: Pygame surface to render to
            rect: Absolute position rectangle
        """
        # Draw background if not transparent
        if not self.transparent:
            if len(self.colors['background']) == 4:
                # RGBA color
                bg_surface = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
                bg_surface.fill(self.colors['background'])
                surface.blit(bg_surface, rect)
            else:
                # RGB color
                pygame.draw.rect(surface, self.colors['background'], rect)
        
        # Draw text if font is available
        if self.font and self.text:
            text_color = self.colors['text'] if self.enabled else self.colors['disabled']
            text_surface = self.font.render(self.text, True, text_color)
            
            # Position text based on alignment
            if self.text_align == "left":
                text_pos = (rect.x, rect.centery - text_surface.get_height() // 2)
            elif self.text_align == "right":
                text_pos = (rect.right - text_surface.get_width(), 
                           rect.centery - text_surface.get_height() // 2)
            else:  # center
                text_pos = (rect.centerx - text_surface.get_width() // 2, 
                           rect.centery - text_surface.get_height() // 2)
            
            surface.blit(text_surface, text_pos)

class UIImage(UIElement):
    """Image UI element."""
    
    def __init__(self, rect, image=None, parent=None):
        """
        Initialize image element.
        
        Args:
            rect: Rectangle defining position and size
            image: Pygame surface
            parent: Optional parent element
        """
        super().__init__(rect, UIElementType.IMAGE, parent)
        self.image = image
        self.scale_mode = "fit"  # fit, fill, stretch
        self.transparent = True
    
    def _draw_element(self, surface, rect):
        """
        Draw the image.
        
        Args:
            surface: Pygame surface to render to
            rect: Absolute position rectangle
        """
        # Draw background if not transparent
        if not self.transparent:
            if len(self.colors['background']) == 4:
                # RGBA color
                bg_surface = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
                bg_surface.fill(self.colors['background'])
                surface.blit(bg_surface, rect)
            else:
                # RGB color
                pygame.draw.rect(surface, self.colors['background'], rect)
        
        # Draw image if available
        if self.image:
            # Scale image based on mode
            if self.scale_mode == "fit":
                # Preserve aspect ratio, fit within rect
                img_rect = self.image.get_rect()
                scale = min(rect.width / img_rect.width, rect.height / img_rect.height)
                new_width = int(img_rect.width * scale)
                new_height = int(img_rect.height * scale)
                
                scaled_image = pygame.transform.smoothscale(self.image, (new_width, new_height))
                
                # Center in rect
                pos = (
                    rect.x + (rect.width - new_width) // 2,
                    rect.y + (rect.height - new_height) // 2
                )
                
                surface.blit(scaled_image, pos)
                
            elif self.scale_mode == "fill":
                # Preserve aspect ratio, fill rect (may crop)
                img_rect = self.image.get_rect()
                scale = max(rect.width / img_rect.width, rect.height / img_rect.height)
                new_width = int(img_rect.width * scale)
                new_height = int(img_rect.height * scale)
                
                scaled_image = pygame.transform.smoothscale(self.image, (new_width, new_height))
                
                # Center in rect (cropping overflow)
                pos = (
                    rect.x + (rect.width - new_width) // 2,
                    rect.y + (rect.height - new_height) // 2
                )
                
                # Create a subsurface that fits within the rect
                crop_rect = pygame.Rect(0, 0, rect.width, rect.height)
                crop_rect.center = (new_width // 2, new_height // 2)
                
                cropped_image = scaled_image.subsurface(crop_rect)
                surface.blit(cropped_image, rect)
                
            else:  # stretch
                # Stretch to fill rect
                scaled_image = pygame.transform.smoothscale(self.image, (rect.width, rect.height))
                surface.blit(scaled_image, rect)
        
        # Draw border
        if self.border_width > 0:
            pygame.draw.rect(surface, self.colors['border'], rect, self.border_width)

class UIInputField(UIElement):
    """Input field UI element for text entry."""
    
    def __init__(self, rect, text="", placeholder="Enter text...", parent=None):
        """
        Initialize input field.
        
        Args:
            rect: Rectangle defining position and size
            text: Initial text
            placeholder: Placeholder text when empty
            parent: Optional parent element
        """
        super().__init__(rect, UIElementType.INPUT, parent)
        self.text = text
        self.placeholder = placeholder
        self.cursor_position = len(text)
        self.cursor_visible = True
        self.cursor_blink_timer = 0
        self.cursor_blink_rate = 0.5  # seconds
        self.max_length = 100
        self.text_offset = 0  # For horizontal scrolling
        self.password_mode = False
    
    def handle_event(self, event):
        """
        Handle a pygame event.
        
        Args:
            event: Pygame event
            
        Returns:
            Boolean indicating if event was handled
        """
        if not self.visible or not self.enabled:
            return False
        
        abs_rect = self.get_absolute_rect()
        
        # Handle mouse button events
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:  # Left click
            prev_focus = self.focus
            
            if abs_rect.collidepoint(event.pos):
                self.focus = True
                
                # Set cursor position based on click
                if self.font and self.text:
                    # Calculate character position from click
                    click_x = event.pos[0] - abs_rect.x - self.padding + self.text_offset
                    
                    # Find closest character position
                    best_pos = 0
                    min_diff = float('inf')
                    
                    for i in range(len(self.text) + 1):
                        # Get position of character i
                        text_width = self.font.size(self.text[:i])[0]
                        diff = abs(text_width - click_x)
                        
                        if diff < min_diff:
                            min_diff = diff
                            best_pos = i
                    
                    self.cursor_position = best_pos
                else:
                    self.cursor_position = len(self.text)
                
                return True
            else:
                self.focus = False
                
            # Call callback if focus changed
            if prev_focus != self.focus and self.callback:
                try:
                    self.callback(self)
                except Exception as e:
                    logger.error(f"Error in input field callback: {e}")
        
        # Handle keyboard events when focused
        elif event.type == pygame.KEYDOWN and self.focus:
            if event.key == pygame.K_BACKSPACE:
                # Delete character before cursor
                if self.cursor_position > 0:
                    self.text = self.text[:self.cursor_position-1] + self.text[self.cursor_position:]
                    self.cursor_position -= 1
                    self._update_text_offset()
                    
                    # Call callback
                    if self.callback:
                        try:
                            self.callback(self)
                        except Exception as e:
                            logger.error(f"Error in input field callback: {e}")
                
            elif event.key == pygame.K_DELETE:
                # Delete character after cursor
                if self.cursor_position < len(self.text):
                    self.text = self.text[:self.cursor_position] + self.text[self.cursor_position+1:]
                    self._update_text_offset()
                    
                    # Call callback
                    if self.callback:
                        try:
                            self.callback(self)
                        except Exception as e:
                            logger.error(f"Error in input field callback: {e}")
            
            elif event.key == pygame.K_LEFT:
                # Move cursor left
                self.cursor_position = max(0, self.cursor_position - 1)
                self._update_text_offset()
            
            elif event.key == pygame.K_RIGHT:
                # Move cursor right
                self.cursor_position = min(len(self.text), self.cursor_position + 1)
                self._update_text_offset()
            
            elif event.key == pygame.K_HOME:
                # Move cursor to start
                self.cursor_position = 0
                self._update_text_offset()
            
            elif event.key == pygame.K_END:
                # Move cursor to end
                self.cursor_position = len(self.text)
                self._update_text_offset()
            
            elif event.key == pygame.K_RETURN:
                # Lose focus on Enter
                self.focus = False
                
                # Call callback
                if self.callback:
                    try:
                        self.callback(self)
                    except Exception as e:
                        logger.error(f"Error in input field callback: {e}")
            
            else:
                # Add character if not control key
                if len(self.text) < self.max_length and event.unicode:
                    self.text = self.text[:self.cursor_position] + event.unicode + self.text[self.cursor_position:]
                    self.cursor_position += len(event.unicode)
                    self._update_text_offset()
                    
                    # Call callback
                    if self.callback:
                        try:
                            self.callback(self)
                        except Exception as e:
                            logger.error(f"Error in input field callback: {e}")
            
            return True
        
        # Mouse movement for hover state
        elif event.type == pygame.MOUSEMOTION:
            self.hover = abs_rect.collidepoint(event.pos)
        
        return False
    
    def update(self, dt):
        """
        Update element state.
        
        Args:
            dt: Time delta in seconds
        """
        super().update(dt)
        
        # Update cursor blink timer
        if self.focus:
            self.cursor_blink_timer += dt
            if self.cursor_blink_timer >= self.cursor_blink_rate:
                self.cursor_visible = not self.cursor_visible
                self.cursor_blink_timer = 0
    
    def _update_text_offset(self):
        """Update text offset to keep cursor visible."""
        if not self.font:
            return
        
        # Calculate text width and field width
        field_width = self.rect.width - (self.padding * 2)
        
        # Get cursor position in pixels
        cursor_x = self.font.size(self.text[:self.cursor_position])[0]
        
        # Adjust offset if cursor would be outside visible area
        if cursor_x < self.text_offset:
            # Cursor is to the left of visible area
            self.text_offset = max(0, cursor_x - 10)
        elif cursor_x > self.text_offset + field_width:
            # Cursor is to the right of visible area
            self.text_offset = cursor_x - field_width + 10
    
    def _draw_element(self, surface, rect):
        """
        Draw the input field.
        
        Args:
            surface: Pygame surface to render to
            rect: Absolute position rectangle
        """
        # Draw background
        if len(self.colors['background']) == 4:
            # RGBA color
            bg_surface = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            bg_surface.fill(self.colors['background'])
            surface.blit(bg_surface, rect)
        else:
            # RGB color
            pygame.draw.rect(surface, self.colors['background'], rect)
        
        # Draw border (highlighted when focused)
        border_color = self.colors['highlight'] if self.focus else self.colors['border']
        pygame.draw.rect(surface, border_color, rect, self.border_width)
        
        # Create text area for clipping
        text_area = pygame.Rect(
            rect.x + self.padding,
            rect.y + self.padding,
            rect.width - (self.padding * 2),
            rect.height - (self.padding * 2)
        )
        
        # Draw text if font is available
        if self.font:
            if self.text:
                # Display text or password placeholder
                display_text = '*' * len(self.text) if self.password_mode else self.text
                
                text_color = self.colors['text'] if self.enabled else self.colors['disabled']
                text_surface = self.font.render(display_text, True, text_color)
                
                # Create a subsurface for clipping
                text_rect = text_surface.get_rect()
                text_rect.x = text_area.x - self.text_offset
                text_rect.centery = text_area.centery
                
                # Create a clip rect
                old_clip = surface.get_clip()
                surface.set_clip(text_area)
                
                # Draw text
                surface.blit(text_surface, text_rect)
                
                # Draw cursor when focused
                if self.focus and self.cursor_visible:
                    cursor_x = text_rect.x + self.font.size(display_text[:self.cursor_position])[0]
                    pygame.draw.line(
                        surface,
                        self.colors['text'],
                        (cursor_x, text_area.y + 2),
                        (cursor_x, text_area.bottom - 2),
                        1
                    )
                
                # Restore clip
                surface.set_clip(old_clip)
            else:
                # Draw placeholder text
                text_color = self.colors['disabled']
                text_surface = self.font.render(self.placeholder, True, text_color)
                
                text_rect = text_surface.get_rect()
                text_rect.x = text_area.x
                text_rect.centery = text_area.centery
                
                # Create a clip rect
                old_clip = surface.get_clip()
                surface.set_clip(text_area)
                
                # Draw placeholder
                surface.blit(text_surface, text_rect)
                
                # Draw cursor when focused
                if self.focus and self.cursor_visible:
                    cursor_x = text_rect.x
                    pygame.draw.line(
                        surface,
                        self.colors['text'],
                        (cursor_x, text_area.y + 2),
                        (cursor_x, text_area.bottom - 2),
                        1
                    )
                
                # Restore clip
                surface.set_clip(old_clip)

class UISlider(UIElement):
    """Slider UI element for numeric input."""
    
    def __init__(self, rect, min_value=0, max_value=100, value=50, parent=None):
        """
        Initialize slider.
        
        Args:
            rect: Rectangle defining position and size
            min_value: Minimum value
            max_value: Maximum value
            value: Initial value
            parent: Optional parent element
        """
        super().__init__(rect, UIElementType.SLIDER, parent)
        self.min_value = min_value
        self.max_value = max_value
        self.value = value
        self.orientation = "horizontal"  # or "vertical"
        self.dragging = False
        self.thumb_size = 16
        self.thumb_rect = pygame.Rect(0, 0, self.thumb_size, self.thumb_size)
        self._update_thumb_position()
    
    def handle_event(self, event):
        """
        Handle a pygame event.
        
        Args:
            event: Pygame event
            
        Returns:
            Boolean indicating if event was handled
        """
        if not self.visible or not self.enabled:
            return False
        
        abs_rect = self.get_absolute_rect()
        
        # Update thumb rectangle with absolute coordinates
        thumb_abs_rect = pygame.Rect(
            abs_rect.x + self.thumb_rect.x,
            abs_rect.y + self.thumb_rect.y,
            self.thumb_rect.width,
            self.thumb_rect.height
        )
        
        # Handle mouse button events
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:  # Left click
            if thumb_abs_rect.collidepoint(event.pos):
                self.dragging = True
                self.focus = True
                return True
            elif abs_rect.collidepoint(event.pos):
                # Click on track sets value directly
                self.focus = True
                self._set_value_from_pos(event.pos, abs_rect)
                self.dragging = True
                
                # Call callback
                if self.callback:
                    try:
                        self.callback(self)
                    except Exception as e:
                        logger.error(f"Error in slider callback: {e}")
                
                return True
            else:
                self.focus = False
        
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:  # Left release
            if self.dragging:
                self.dragging = False
                return True
        
        elif event.type == pygame.MOUSEMOTION:
            # Update hover state
            self.hover = abs_rect.collidepoint(event.pos)
            
            # Update thumb position when dragging
            if self.dragging:
                self._set_value_from_pos(event.pos, abs_rect)
                
                # Call callback
                if self.callback:
                    try:
                        self.callback(self)
                    except Exception as e:
                        logger.error(f"Error in slider callback: {e}")
                
                return True
        
        return False
    
    def _set_value_from_pos(self, pos, abs_rect):
        """
        Set slider value based on mouse position.
        
        Args:
            pos: Mouse position tuple (x, y)
            abs_rect: Absolute slider rectangle
        """
        if self.orientation == "horizontal":
            # Calculate value based on x position
            track_length = abs_rect.width - self.thumb_size
            track_pos = pos[0] - abs_rect.x - self.thumb_size // 2
            track_pos = max(0, min(track_pos, track_length))
            
            # Convert position to value
            value_range = self.max_value - self.min_value
            self.value = self.min_value + (track_pos / track_length) * value_range
        else:
            # Calculate value based on y position (inverted)
            track_length = abs_rect.height - self.thumb_size
            track_pos = pos[1] - abs_rect.y - self.thumb_size // 2
            track_pos = max(0, min(track_pos, track_length))
            
            # Convert position to value (inverted)
            value_range = self.max_value - self.min_value
            self.value = self.max_value - (track_pos / track_length) * value_range
        
        # Clamp value to range
        self.value = max(self.min_value, min(self.max_value, self.value))
        
        # Update thumb position
        self._update_thumb_position()
    
    def _update_thumb_position(self):
        """Update thumb position based on value."""
        # Calculate position based on value
        value_range = self.max_value - self.min_value
        value_pos = (self.value - self.min_value) / value_range
        
        if self.orientation == "horizontal":
            track_length = self.rect.width - self.thumb_size
            thumb_x = value_pos * track_length
            
            self.thumb_rect.x = thumb_x
            self.thumb_rect.y = (self.rect.height - self.thumb_size) // 2
        else:
            track_length = self.rect.height - self.thumb_size
            thumb_y = (1.0 - value_pos) * track_length  # Inverted
            
            self.thumb_rect.x = (self.rect.width - self.thumb_size) // 2
            self.thumb_rect.y = thumb_y
    
    def set_value(self, value):
        """
        Set slider value.
        
        Args:
            value: New value
        """
        self.value = max(self.min_value, min(self.max_value, value))
        self._update_thumb_position()
    
    def _draw_element(self, surface, rect):
        """
        Draw the slider.
        
        Args:
            surface: Pygame surface to render to
            rect: Absolute position rectangle
        """
        # Draw background
        if len(self.colors['background']) == 4:
            # RGBA color
            bg_surface = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            bg_surface.fill(self.colors['background'])
            surface.blit(bg_surface, rect)
        else:
            # RGB color
            pygame.draw.rect(surface, self.colors['background'], rect)
        
        # Draw track
        track_color = self.colors['border']
        
        if self.orientation == "horizontal":
            track_rect = pygame.Rect(
                rect.x + self.thumb_size // 2,
                rect.centery - 2,
                rect.width - self.thumb_size,
                4
            )
        else:
            track_rect = pygame.Rect(
                rect.centerx - 2,
                rect.y + self.thumb_size // 2,
                4,
                rect.height - self.thumb_size
            )
        
        pygame.draw.rect(surface, track_color, track_rect)
        
        # Draw filled track
        if self.orientation == "horizontal":
            filled_width = int((self.thumb_rect.centerx / self.rect.width) * track_rect.width)
            filled_rect = pygame.Rect(
                track_rect.x,
                track_rect.y,
                filled_width,
                track_rect.height
            )
        else:
            filled_height = int(((self.rect.height - self.thumb_rect.centery) / self.rect.height) * track_rect.height)
            filled_rect = pygame.Rect(
                track_rect.x,
                track_rect.bottom - filled_height,
                track_rect.width,
                filled_height
            )
        
        pygame.draw.rect(surface, self.colors['highlight'], filled_rect)
        
        # Draw thumb
        thumb_rect = pygame.Rect(
            rect.x + self.thumb_rect.x,
            rect.y + self.thumb_rect.y,
            self.thumb_rect.width,
            self.thumb_rect.height
        )
        
        thumb_color = self.colors['highlight'] if self.hover or self.focus or self.dragging else self.colors['border']
        pygame.draw.rect(surface, thumb_color, thumb_rect, 0, 5)  # Rounded corners
        
        # Draw value text if enabled
        if self.font:
            text_color = self.colors['text'] if self.enabled else self.colors['disabled']
            value_text = self.font.render(f"{int(self.value)}", True, text_color)
            
            # Position below or beside the slider
            if self.orientation == "horizontal":
                text_rect = value_text.get_rect(centerx=thumb_rect.centerx, top=rect.bottom + 5)
            else:
                text_rect = value_text.get_rect(centery=thumb_rect.centery, left=rect.right + 5)
            
            surface.blit(value_text, text_rect)

class UICheckbox(UIElement):
    """Checkbox UI element for boolean input."""
    
    def __init__(self, rect, text="", checked=False, parent=None):
        """
        Initialize checkbox.
        
        Args:
            rect: Rectangle defining position and size
            text: Checkbox label text
            checked: Initial checked state
            parent: Optional parent element
        """
        super().__init__(rect, UIElementType.CHECKBOX, parent)
        self.text = text
        self.checked = checked
        self.box_size = min(rect.height - 4, 20)
    
    def handle_event(self, event):
        """
        Handle a pygame event.
        
        Args:
            event: Pygame event
            
        Returns:
            Boolean indicating if event was handled
        """
        if not self.visible or not self.enabled:
            return False
        
        abs_rect = self.get_absolute_rect()
        
        # Handle mouse button events
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:  # Left click
            if abs_rect.collidepoint(event.pos):
                self.focus = True
                self.checked = not self.checked
                
                # Execute callback if available
                if self.callback:
                    try:
                        self.callback(self)
                    except Exception as e:
                        logger.error(f"Error in checkbox callback: {e}")
                
                return True
            else:
                self.focus = False
        
        # Mouse movement for hover state
        elif event.type == pygame.MOUSEMOTION:
            self.hover = abs_rect.collidepoint(event.pos)
        
        return False
    
    def _draw_element(self, surface, rect):
        """
        Draw the checkbox.
        
        Args:
            surface: Pygame surface to render to
            rect: Absolute position rectangle
        """
        # Draw background if larger than box (for highlighting)
        if rect.width > self.box_size or rect.height > self.box_size:
            if self.hover:
                hover_color = (*self.colors['background'][:3], 100)  # Semi-transparent
                
                hover_surface = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
                hover_surface.fill(hover_color)
                surface.blit(hover_surface, rect)
        
        # Draw checkbox box
        box_rect = pygame.Rect(
            rect.x,
            rect.centery - self.box_size // 2,
            self.box_size,
            self.box_size
        )
        
        # Draw box background
        pygame.draw.rect(surface, self.colors['background'], box_rect)
        
        # Draw box border
        border_color = self.colors['highlight'] if self.focus else self.colors['border']
        pygame.draw.rect(surface, border_color, box_rect, self.border_width)
        
        # Draw check mark if checked
        if self.checked:
            check_color = self.colors['highlight']
            
            # Draw a check mark (X)
            padding = self.box_size // 4
            pygame.draw.line(
                surface,
                check_color,
                (box_rect.left + padding, box_rect.top + padding),
                (box_rect.right - padding, box_rect.bottom - padding),
                2
            )
            pygame.draw.line(
                surface,
                check_color,
                (box_rect.left + padding, box_rect.bottom - padding),
                (box_rect.right - padding, box_rect.top + padding),
                2
            )
        
        # Draw label text
        if self.font and self.text:
            text_color = self.colors['text'] if self.enabled else self.colors['disabled']
            text_surface = self.font.render(self.text, True, text_color)
            
            # Position text to the right of the box
            text_pos = (box_rect.right + 10, rect.centery - text_surface.get_height() // 2)
            surface.blit(text_surface, text_pos)

class UIProgressBar(UIElement):
    """Progress bar UI element."""
    
    def __init__(self, rect, value=0, max_value=100, parent=None):
        """
        Initialize progress bar.
        
        Args:
            rect: Rectangle defining position and size
            value: Initial value
            max_value: Maximum value
            parent: Optional parent element
        """
        super().__init__(rect, UIElementType.PROGRESSBAR, parent)
        self.value = value
        self.max_value = max_value
        self.show_text = True
        self.bar_color = (0, 200, 0)  # Default green
    
    def set_value(self, value):
        """
        Set progress bar value.
        
        Args:
            value: New value
        """
        self.value = max(0, min(self.max_value, value))
    
    def _draw_element(self, surface, rect):
        """
        Draw the progress bar.
        
        Args:
            surface: Pygame surface to render to
            rect: Absolute position rectangle
        """
        # Draw background
        if len(self.colors['background']) == 4:
            # RGBA color
            bg_surface = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            bg_surface.fill(self.colors['background'])
            surface.blit(bg_surface, rect)
        else:
            # RGB color
            pygame.draw.rect(surface, self.colors['background'], rect)
        
        # Draw border
        pygame.draw.rect(surface, self.colors['border'], rect, self.border_width)
        
        # Calculate progress width
        progress_width = int((self.value / self.max_value) * (rect.width - 2 * self.border_width))
        
        # Draw progress bar
        if progress_width > 0:
            progress_rect = pygame.Rect(
                rect.x + self.border_width,
                rect.y + self.border_width,
                progress_width,
                rect.height - 2 * self.border_width
            )
            pygame.draw.rect(surface, self.bar_color, progress_rect)
        
        # Draw text if enabled
        if self.show_text and self.font:
            percent = int((self.value / self.max_value) * 100)
            text = f"{percent}%"
            
            text_surface = self.font.render(text, True, self.colors['text'])
            text_rect = text_surface.get_rect(center=rect.center)
            
            surface.blit(text_surface, text_rect)

class UIDropdown(UIElement):
    """Dropdown menu UI element."""
    
    def __init__(self, rect, options=None, selected_index=0, parent=None):
        """
        Initialize dropdown.
        
        Args:
            rect: Rectangle defining position and size
            options: List of option strings
            selected_index: Initially selected option index
            parent: Optional parent element
        """
        super().__init__(rect, UIElementType.DROPDOWN, parent)
        self.options = options or []
        self.selected_index = selected_index if 0 <= selected_index < len(self.options) else 0
        self.expanded = False
        self.hover_index = -1
        self.max_visible_items = 5
        self.item_height = 30
    
    def handle_event(self, event):
        """
        Handle a pygame event.
        
        Args:
            event: Pygame event
            
        Returns:
            Boolean indicating if event was handled
        """
        if not self.visible or not self.enabled:
            return False
        
        abs_rect = self.get_absolute_rect()
        
        # Handle mouse button events
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:  # Left click
            # Check if clicked on main dropdown
            if abs_rect.collidepoint(event.pos):
                self.focus = True
                self.expanded = not self.expanded
                return True
            
            # Check if clicked on dropdown list
            if self.expanded:
                list_rect = self._get_list_rect(abs_rect)
                
                if list_rect.collidepoint(event.pos):
                    # Calculate which item was clicked
                    rel_y = event.pos[1] - list_rect.y
                    item_index = rel_y // self.item_height
                    
                    # Check if valid index
                    if 0 <= item_index < min(len(self.options), self.max_visible_items):
                        # Set selected index
                        self.selected_index = item_index
                        self.expanded = False
                        
                        # Execute callback if available
                        if self.callback:
                            try:
                                self.callback(self)
                            except Exception as e:
                                logger.error(f"Error in dropdown callback: {e}")
                    
                    return True
                else:
                    # Close if clicked outside
                    self.expanded = False
            
            self.focus = False
        
        # Mouse movement for hover state
        elif event.type == pygame.MOUSEMOTION:
            self.hover = abs_rect.collidepoint(event.pos)
            
            # Update hover index for expanded list
            if self.expanded:
                list_rect = self._get_list_rect(abs_rect)
                
                if list_rect.collidepoint(event.pos):
                    rel_y = event.pos[1] - list_rect.y
                    self.hover_index = rel_y // self.item_height
                    
                    # Clamp to valid indices
                    if not (0 <= self.hover_index < min(len(self.options), self.max_visible_items)):
                        self.hover_index = -1
                else:
                    self.hover_index = -1
        
        return False
    
    def _get_list_rect(self, abs_rect):
        """
        Get the rectangle for the expanded dropdown list.
        
        Args:
            abs_rect: Absolute dropdown rectangle
            
        Returns:
            Pygame Rect for dropdown list
        """
        list_height = min(len(self.options), self.max_visible_items) * self.item_height
        
        return pygame.Rect(
            abs_rect.x,
            abs_rect.bottom,
            abs_rect.width,
            list_height
        )
    
    def _draw_element(self, surface, rect):
        """
        Draw the dropdown.
        
        Args:
            surface: Pygame surface to render to
            rect: Absolute position rectangle
        """
        # Draw background
        if len(self.colors['background']) == 4:
            # RGBA color
            bg_surface = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            bg_surface.fill(self.colors['background'])
            surface.blit(bg_surface, rect)
        else:
            # RGB color
            pygame.draw.rect(surface, self.colors['background'], rect)
        
        # Draw border (highlighted when focused)
        border_color = self.colors['highlight'] if self.focus else self.colors['border']
        pygame.draw.rect(surface, border_color, rect, self.border_width)
        
        # Draw selected text
        if self.font and self.options and 0 <= self.selected_index < len(self.options):
            text_color = self.colors['text'] if self.enabled else self.colors['disabled']
            text_surface = self.font.render(self.options[self.selected_index], True, text_color)
            
            # Position text with padding
            text_pos = (rect.x + self.padding, rect.centery - text_surface.get_height() // 2)
            surface.blit(text_surface, text_pos)
        
        # Draw dropdown arrow
        arrow_size = min(10, rect.height // 3)
        arrow_x = rect.right - arrow_size * 2
        arrow_y = rect.centery
        
        arrow_color = self.colors['text'] if self.enabled else self.colors['disabled']
        
        if self.expanded:
            # Up arrow
            pygame.draw.polygon(
                surface,
                arrow_color,
                [
                    (arrow_x, arrow_y + arrow_size),
                    (arrow_x + arrow_size, arrow_y - arrow_size),
                    (arrow_x + arrow_size * 2, arrow_y + arrow_size)
                ]
            )
        else:
            # Down arrow
            pygame.draw.polygon(
                surface,
                arrow_color,
                [
                    (arrow_x, arrow_y - arrow_size),
                    (arrow_x + arrow_size * 2, arrow_y - arrow_size),
                    (arrow_x + arrow_size, arrow_y + arrow_size)
                ]
            )
        
        # Draw expanded dropdown list
        if self.expanded:
            list_rect = self._get_list_rect(rect)
            
            # Draw list background
            if len(self.colors['background']) == 4:
                list_bg = pygame.Surface((list_rect.width, list_rect.height), pygame.SRCALPHA)
                list_bg.fill(self.colors['background'])
                surface.blit(list_bg, list_rect)
            else:
                pygame.draw.rect(surface, self.colors['background'], list_rect)
            
            # Draw list border
            pygame.draw.rect(surface, self.colors['border'], list_rect, self.border_width)
            
            # Draw options
            if self.font:
                for i, option in enumerate(self.options[:self.max_visible_items]):
                    item_rect = pygame.Rect(
                        list_rect.x,
                        list_rect.y + i * self.item_height,
                        list_rect.width,
                        self.item_height
                    )
                    
                    # Highlight on hover or selected
                    if i == self.hover_index:
                        pygame.draw.rect(surface, self.colors['highlight'], item_rect)
                    elif i == self.selected_index:
                        highlight_color = (*self.colors['highlight'][:3], 128)
                        highlight_surf = pygame.Surface((item_rect.width, item_rect.height), pygame.SRCALPHA)
                        highlight_surf.fill(highlight_color)
                        surface.blit(highlight_surf, item_rect)
                    
                    # Draw option text
                    text_color = self.colors['text']
                    text_surface = self.font.render(option, True, text_color)
                    
                    text_pos = (item_rect.x + self.padding, item_rect.centery - text_surface.get_height() // 2)
                    surface.blit(text_surface, text_pos)

class UITooltip(UIElement):
    """Tooltip UI element for displaying help text."""
    
    def __init__(self, text="", parent=None):
        """
        Initialize tooltip.
        
        Args:
            text: Tooltip text
            parent: Optional parent element (usually None)
        """
        # Dummy rect, will be positioned when shown
        super().__init__(pygame.Rect(0, 0, 100, 30), UIElementType.TOOLTIP, parent)
        self.text = text
        self.visible = False
        self.max_width = 300
        self.transparent = False
        self.border_width = 1
        self.colors['background'] = (30, 30, 30, 230)  # Semi-transparent dark background
    
    def show(self, position, screen_size=None):
        """
        Show tooltip at position.
        
        Args:
            position: (x, y) position tuple
            screen_size: Optional (width, height) tuple for screen bounds
        """
        self.visible = True
        
        # Size tooltip based on text
        if self.font:
            # Split text into lines based on max width
            words = self.text.split()
            lines = []
            current_line = ""
            
            for word in words:
                test_line = current_line + " " + word if current_line else word
                if self.font.size(test_line)[0] <= self.max_width:
                    current_line = test_line
                else:
                    lines.append(current_line)
                    current_line = word
            
            if current_line:
                lines.append(current_line)
            
            # Calculate size based on text
            line_height = self.font.get_linesize()
            if lines:
                width = min(self.max_width, max(self.font.size(line)[0] for line in lines) + self.padding * 2)
            else:
                width = 100  # Default width if no lines
            height = line_height * len(lines) + self.padding * 2
            
            self.rect.width = width
            self.rect.height = height
        
        # Position tooltip
        self.rect.x = position[0]
        self.rect.y = position[1] + 20  # Offset to not cover cursor
        
        # Adjust to keep on screen
        if screen_size:
            if self.rect.right > screen_size[0]:
                self.rect.right = screen_size[0] - 5
            
            if self.rect.bottom > screen_size[1]:
                self.rect.bottom = screen_size[1] - 5
    
    def hide(self):
        """Hide tooltip."""
        self.visible = False
    
    def _draw_element(self, surface, rect):
        """
        Draw the tooltip.
        
        Args:
            surface: Pygame surface to render to
            rect: Absolute position rectangle
        """
        # Draw background with alpha
        if len(self.colors['background']) == 4:
            # RGBA color
            bg_surface = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            bg_surface.fill(self.colors['background'])
            surface.blit(bg_surface, rect)
        else:
            # RGB color
            pygame.draw.rect(surface, self.colors['background'], rect)
        
        # Draw border
        pygame.draw.rect(surface, self.colors['border'], rect, self.border_width)
        
        # Draw text
        if self.font and self.text:
            # Split text into lines based on max width
            words = self.text.split()
            lines = []
            current_line = ""
            
            for word in words:
                test_line = current_line + " " + word if current_line else word
                if self.font.size(test_line)[0] <= self.max_width:
                    current_line = test_line
                else:
                    lines.append(current_line)
                    current_line = word
            
            if current_line:
                lines.append(current_line)
            
            # Draw each line
            line_height = self.font.get_linesize()
            y_offset = self.padding
            
            for line in lines:
                if line:
                    text_surface = self.font.render(line, True, self.colors['text'])
                    surface.blit(text_surface, (rect.x + self.padding, rect.y + y_offset))
                y_offset += line_height

class UIManager:
    """
    Manager for UI elements.
    
    This handles event processing, updates, and rendering for all UI elements.
    """
    
    def __init__(self, surface):
        """
        Initialize UI manager.
        
        Args:
            surface: Pygame surface to render to
        """
        self.surface = surface
        self.elements = []
        self.tooltips = []
        self.default_font = None
        self.default_tooltip = None
        self.hover_element = None
        self.hover_time = 0.0
        self.tooltip_delay = 0.5  # Seconds
        
        # Initialize fonts
        pygame.font.init()
        try:
            self.default_font = pygame.font.SysFont(None, 24)
        except:
            logger.warning("Failed to load default font")
        
        # Create default tooltip
        self.default_tooltip = UITooltip()
        self.default_tooltip.set_font(self.default_font)
        
        logger.info("UIManager initialized")
    
    def add_element(self, element):
        """
        Add a UI element.
        
        Args:
            element: UIElement to add
            
        Returns:
            Added element
        """
        self.elements.append(element)
        
        # Set default font if not already set
        if element.font is None:
            element.set_font(self.default_font)
        
        # Add to parent's children list if parent is specified
        if element.parent and element.parent in self.elements:
            element.parent.add_child(element)
        
        return element
    
    def remove_element(self, element):
        """
        Remove a UI element.
        
        Args:
            element: UIElement to remove
            
        Returns:
            Boolean indicating if element was removed
        """
        if element in self.elements:
            # Remove from parent's children list if parent is specified
            if element.parent:
                element.parent.remove_child(element)
            
            # Remove element and all its children
            self._remove_element_and_children(element)
            return True
        
        return False
    
    def _remove_element_and_children(self, element):
        """
        Remove an element and all its children recursively.
        
        Args:
            element: UIElement to remove
        """
        # Remove all children first
        for child in element.children.copy():
            self._remove_element_and_children(child)
        
        # Remove element
        if element in self.elements:
            self.elements.remove(element)
    
    def clear(self):
        """Remove all UI elements."""
        self.elements = []
    
    def handle_event(self, event):
        """
        Handle a pygame event.
        
        Args:
            event: Pygame event
            
        Returns:
            Boolean indicating if event was handled
        """
        # Process event for all root-level elements (in reverse order for proper z-index)
        for element in reversed([e for e in self.elements if e.parent is None]):
            if element.handle_event(event):
                return True
        
        # Hide tooltip if mouse moves
        if event.type == pygame.MOUSEMOTION:
            self.default_tooltip.hide()
            
            # Update hover element and timer
            old_hover = self.hover_element
            self.hover_element = self._get_element_at(event.pos)
            
            if self.hover_element != old_hover:
                self.hover_time = 0.0
        
        return False
    
    def update(self, dt):
        """
        Update all UI elements.
        
        Args:
            dt: Time delta in seconds
        """
        # Update all elements
        for element in self.elements:
            element.update(dt)
        
        # Update default tooltip
        self.default_tooltip.update(dt)
        
        # Update hover timer for tooltip
        if self.hover_element and hasattr(self.hover_element, 'text'):
            self.hover_time += dt
            
            if self.hover_time >= self.tooltip_delay and not self.default_tooltip.visible:
                # Show tooltip
                mouse_pos = pygame.mouse.get_pos()
                screen_size = self.surface.get_size()
                
                self.default_tooltip.set_text(self.hover_element.text)
                self.default_tooltip.show(mouse_pos, screen_size)
        else:
            self.hover_time = 0.0
    
    def render(self):
        """Render all UI elements."""
        # Render root-level elements (which will render their children)
        for element in [e for e in self.elements if e.parent is None]:
            element.render(self.surface)
        
        # Render default tooltip (always on top)
        if self.default_tooltip.visible:
            self.default_tooltip.render(self.surface)
    
    def _get_element_at(self, position):
        """
        Get the topmost element at a position.
        
        Args:
            position: (x, y) position tuple
            
        Returns:
            UIElement at position or None
        """
        # Check all elements in reverse order (for proper z-index)
        for element in reversed(self.elements):
            if element.visible and element.get_absolute_rect().collidepoint(position):
                return element
        
        return None
    
    def create_panel(self, rect, parent=None):
        """
        Create and add a panel.
        
        Args:
            rect: Rectangle defining position and size
            parent: Optional parent element
            
        Returns:
            New UIPanel instance
        """
        panel = UIPanel(rect, parent)
        return self.add_element(panel)
    
    def create_button(self, rect, text="", callback=None, parent=None):
        """
        Create and add a button.
        
        Args:
            rect: Rectangle defining position and size
            text: Button text
            callback: Function to call when button is clicked
            parent: Optional parent element
            
        Returns:
            New UIButton instance
        """
        button = UIButton(rect, text, parent)
        if callback:
            button.set_callback(callback)
        return self.add_element(button)
    
    def create_label(self, rect, text="", parent=None):
        """
        Create and add a label.
        
        Args:
            rect: Rectangle defining position and size
            text: Label text
            parent: Optional parent element
            
        Returns:
            New UILabel instance
        """
        label = UILabel(rect, text, parent)
        return self.add_element(label)
    
    def create_image(self, rect, image=None, parent=None):
        """
        Create and add an image.
        
        Args:
            rect: Rectangle defining position and size
            image: Pygame surface
            parent: Optional parent element
            
        Returns:
            New UIImage instance
        """
        image_element = UIImage(rect, image, parent)
        return self.add_element(image_element)
    
    def create_input_field(self, rect, text="", placeholder="", callback=None, parent=None):
        """
        Create and add an input field.
        
        Args:
            rect: Rectangle defining position and size
            text: Initial text
            placeholder: Placeholder text when empty
            callback: Function to call when input changes
            parent: Optional parent element
            
        Returns:
            New UIInputField instance
        """
        input_field = UIInputField(rect, text, placeholder, parent)
        if callback:
            input_field.set_callback(callback)
        return self.add_element(input_field)
    
    def create_slider(self, rect, min_value=0, max_value=100, value=50, callback=None, parent=None):
        """
        Create and add a slider.
        
        Args:
            rect: Rectangle defining position and size
            min_value: Minimum value
            max_value: Maximum value
            value: Initial value
            callback: Function to call when value changes
            parent: Optional parent element
            
        Returns:
            New UISlider instance
        """
        slider = UISlider(rect, min_value, max_value, value, parent)
        if callback:
            slider.set_callback(callback)
        return self.add_element(slider)
    
    def create_checkbox(self, rect, text="", checked=False, callback=None, parent=None):
        """
        Create and add a checkbox.
        
        Args:
            rect: Rectangle defining position and size
            text: Checkbox label text
            checked: Initial checked state
            callback: Function to call when checked state changes
            parent: Optional parent element
            
        Returns:
            New UICheckbox instance
        """
        checkbox = UICheckbox(rect, text, checked, parent)
        if callback:
            checkbox.set_callback(callback)
        return self.add_element(checkbox)
    
    def create_dropdown(self, rect, options=None, selected_index=0, callback=None, parent=None):
        """
        Create and add a dropdown.
        
        Args:
            rect: Rectangle defining position and size
            options: List of option strings
            selected_index: Initially selected option index
            callback: Function to call when selection changes
            parent: Optional parent element
            
        Returns:
            New UIDropdown instance
        """
        dropdown = UIDropdown(rect, options, selected_index, parent)
        if callback:
            dropdown.set_callback(callback)
        return self.add_element(dropdown)
    
    def create_progress_bar(self, rect, value=0, max_value=100, parent=None):
        """
        Create and add a progress bar.
        
        Args:
            rect: Rectangle defining position and size
            value: Initial value
            max_value: Maximum value
            parent: Optional parent element
            
        Returns:
            New UIProgressBar instance
        """
        progress_bar = UIProgressBar(rect, value, max_value, parent)
        return self.add_element(progress_bar)
