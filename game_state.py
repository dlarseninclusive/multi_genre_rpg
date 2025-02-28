import pygame
import logging

class GameState:
    """
    Base class for all game states.
    
    Game states represent different modes of gameplay or UI screens
    such as main menu, world exploration, dungeon, etc.
    """
    
    def __init__(self, state_manager, event_bus, settings):
        """
        Initialize the game state.
        
        Args:
            state_manager: StateManager instance
            event_bus: EventBus instance
            settings: Game settings
        """
        self.state_manager = state_manager
        self.event_bus = event_bus
        self.settings = settings
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Default properties
        self.visible = True  # Whether the state should be rendered
        self.active = True   # Whether the state should be updated
        
        # State-specific data
        self.state_data = {}
    
    def enter(self, data=None):
        """
        Called when entering this state.
        
        Args:
            data: Optional data passed from the previous state
        """
        self.active = True
        self.visible = True
        if data:
            self.state_data.update(data)
        self.logger.info(f"Entered state: {self.__class__.__name__}")
    
    def exit(self):
        """Called when exiting this state."""
        self.active = False
        self.visible = False
        self.logger.info(f"Exited state: {self.__class__.__name__}")
    
    def pause(self):
        """Called when this state is paused (another state is pushed on top)."""
        self.active = False
        self.logger.info(f"Paused state: {self.__class__.__name__}")
    
    def resume(self):
        """Called when this state is resumed (a state on top was popped)."""
        self.active = True
        self.logger.info(f"Resumed state: {self.__class__.__name__}")
    
    def handle_event(self, event):
        """
        Process a pygame event.
        
        Args:
            event: Pygame event to handle
        """
        pass
    
    def update(self, dt):
        """
        Update the state logic.
        
        Args:
            dt: Delta time since last update (in seconds)
        """
        pass
    
    def render(self, screen):
        """
        Render the state to the screen.
        
        Args:
            screen: Pygame surface to render to
        """
        pass
    
    def change_state(self, state_id, data=None):
        """
        Request a state change via the event bus.
        
        Args:
            state_id: ID of the state to change to
            data: Optional data to pass to the new state
        """
        self.event_bus.publish("request_state_change", {
            "state_id": state_id,
            "data": data
        })
    
    def push_state(self, state_id, data=None):
        """
        Request to push a state onto the stack via the event bus.
        
        Args:
            state_id: ID of the state to push
            data: Optional data to pass to the new state
        """
        self.event_bus.publish("push_state", {
            "state_id": state_id,
            "data": data
        })
    
    def pop_state(self):
        """Request to pop the current state from the stack via the event bus."""
        self.event_bus.publish("pop_state", None)
