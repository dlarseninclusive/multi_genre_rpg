import logging
from collections import defaultdict

logger = logging.getLogger("event_bus")

class EventBus:
    """
    Event bus system for communication between game components.
    
    This implementation follows the Publisher-Subscriber pattern
    allowing loose coupling between different game systems.
    """
    
    def __init__(self):
        """Initialize the event bus."""
        # Dictionary mapping event types to list of subscribers
        self._subscribers = defaultdict(list)
        logger.info("EventBus initialized")
    
    def subscribe(self, event_type, callback):
        """
        Subscribe to an event type.
        
        Args:
            event_type: String identifier for the event type
            callback: Function to call when event is published
        """
        self._subscribers[event_type].append(callback)
        logger.debug(f"Subscribed to '{event_type}' event")
    
    def unsubscribe(self, event_type, callback):
        """
        Unsubscribe from an event type.
        
        Args:
            event_type: String identifier for the event type
            callback: Function to remove from subscribers
        """
        if event_type in self._subscribers:
            try:
                self._subscribers[event_type].remove(callback)
                logger.debug(f"Unsubscribed from '{event_type}' event")
            except ValueError:
                logger.warning(f"Attempted to unsubscribe callback not registered for '{event_type}'")
    
    def publish(self, event_type, data=None):
        """
        Publish an event to all subscribers.
        
        Args:
            event_type: String identifier for the event type
            data: Optional data to pass to subscribers
        """
        if event_type in self._subscribers:
            # Make a copy of subscribers list to allow for unsubscribing during event handling
            subscribers = self._subscribers[event_type].copy()
            
            logger.debug(f"Publishing '{event_type}' event with {len(subscribers)} subscribers")
            
            for callback in subscribers:
                try:
                    callback(data)
                except Exception as e:
                    logger.error(f"Error in event handler for '{event_type}': {e}", exc_info=True)
        else:
            logger.debug(f"Published '{event_type}' event with no subscribers")
    
    def clear_subscribers(self):
        """Remove all subscribers."""
        self._subscribers.clear()
        logger.debug("Cleared all event subscribers")
    
    def clear_event_subscribers(self, event_type):
        """
        Remove all subscribers for a specific event type.
        
        Args:
            event_type: String identifier for the event type
        """
        if event_type in self._subscribers:
            self._subscribers[event_type] = []
            logger.debug(f"Cleared subscribers for '{event_type}' event")
