import pygame
import logging

logger = logging.getLogger("notification")

class Notification:
    """Display on-screen notifications."""
    
    def __init__(self, title, message, duration=3.0):
        """
        Initialize notification.
        
        Args:
            title: Notification title
            message: Notification message
            duration: Duration in seconds to display
        """
        self.title = title
        self.message = message
        self.duration = duration
        self.time_remaining = duration
        self.alpha = 255  # For fade effect
    
    def update(self, dt):
        """
        Update notification.
        
        Args:
            dt: Time delta in seconds
            
        Returns:
            True if notification should continue displaying, False if expired
        """
        self.time_remaining -= dt
        
        # Fade out in the last second
        if self.time_remaining < 1.0:
            self.alpha = int(255 * self.time_remaining)
        
        return self.time_remaining > 0
    
    def render(self, surface, position=(50, 50)):
        """
        Render notification on screen.
        
        Args:
            surface: Pygame surface to render on
            position: (x, y) position tuple for top-left corner
        """
        try:
            # Initialize font if not already available
            font_title = pygame.font.SysFont(None, 28)
            font_message = pygame.font.SysFont(None, 24)
            
            # Calculate size based on text
            title_surface = font_title.render(self.title, True, (255, 255, 255))
            message_surface = font_message.render(self.message, True, (220, 220, 220))
            
            width = max(title_surface.get_width(), message_surface.get_width()) + 20
            height = title_surface.get_height() + message_surface.get_height() + 30
            
            # Create notification surface with alpha
            notification_surface = pygame.Surface((width, height), pygame.SRCALPHA)
            
            # Fill with semi-transparent background
            notification_surface.fill((0, 0, 0, min(200, self.alpha)))
            
            # Draw text with proper alpha
            title_surface.set_alpha(self.alpha)
            message_surface.set_alpha(self.alpha)
            
            # Position text
            notification_surface.blit(title_surface, (10, 10))
            notification_surface.blit(message_surface, (10, title_surface.get_height() + 15))
            
            # Draw border
            pygame.draw.rect(notification_surface, (150, 150, 200, self.alpha), 
                           (0, 0, width, height), 2)
            
            # Draw on main surface
            surface.blit(notification_surface, position)
        except Exception as e:
            logger.error(f"Error rendering notification: {e}")

class NotificationManager:
    """Manages and displays notifications."""
    
    def __init__(self, event_bus):
        """
        Initialize notification manager.
        
        Args:
            event_bus: Event bus for communication
        """
        self.event_bus = event_bus
        self.notifications = []
        self.max_notifications = 3
        
        # Register for events
        self.event_bus.subscribe("show_notification", self._handle_show_notification)
    
    def _handle_show_notification(self, data):
        """Handle show_notification event."""
        if not data:
            return
            
        title = data.get("title", "Notification")
        message = data.get("message", "")
        duration = data.get("duration", 3.0)
        
        self.add_notification(title, message, duration)
    
    def add_notification(self, title, message, duration=3.0):
        """
        Add a new notification.
        
        Args:
            title: Notification title
            message: Notification message
            duration: Duration in seconds
        """
        notification = Notification(title, message, duration)
        
        # Keep maximum number of notifications
        if len(self.notifications) >= self.max_notifications:
            self.notifications.pop(0)
        
        self.notifications.append(notification)
        logger.debug(f"Added notification: {title} - {message}")
    
    def update(self, dt):
        """
        Update all notifications.
        
        Args:
            dt: Time delta in seconds
        """
        # Update and remove expired notifications
        self.notifications = [n for n in self.notifications if n.update(dt)]
    
    def render(self, surface):
        """
        Render all notifications.
        
        Args:
            surface: Pygame surface to render on
        """
        y_offset = 50
        
        for notification in self.notifications:
            notification.render(surface, (50, y_offset))
            y_offset += 80  # Fixed spacing between notifications
