import logging
import pygame
from game_state import GameState

logger = logging.getLogger("state_manager")

class StateManager:
    """
    Manages different game states and transitions between them.
    Implements a state stack allowing for state layering (e.g., pause menu over gameplay).
    """
    
    def __init__(self, screen, event_bus):
        """
        Initialize the state manager.
        
        Args:
            screen: The Pygame display surface
            event_bus: EventBus instance for communication between systems
        """
        self.screen = screen
        self.event_bus = event_bus
        self.states = {}  # Registered states
        self.state_stack = []  # Active state stack (allows for layered states)
        self.transitioning = False
        self.persistent_data = {}  # Data that persists between state transitions
        self.current_state = None  # Current active state (top of the stack)
        
        # Subscribe to relevant events
        self.event_bus.subscribe("request_state_change", self._handle_state_change_request)
        self.event_bus.subscribe("push_state", self._handle_push_state)
        self.event_bus.subscribe("pop_state", self._handle_pop_state)
        
        logger.info("StateManager initialized")
    
    def register_state(self, state_id, state_instance):
        """
        Register a game state.
        
        Args:
            state_id: Unique identifier for the state
            state_instance: Instance of a GameState subclass
        """
        if not isinstance(state_instance, GameState):
            raise TypeError("State must be an instance of GameState")
        
        self.states[state_id] = state_instance
        logger.info(f"Registered state: {state_id}")
    
    def change_state(self, state_id, data=None):
        """
        Change to a different game state.
        
        Args:
            state_id: ID of the state to change to
            data: Optional data to pass to the new state
        """
        if state_id not in self.states:
            logger.error(f"Attempted to change to unknown state: {state_id}")
            return
        
        logger.info(f"Changing state to: {state_id}")
        
        # Clear the entire state stack
        while self.state_stack:
            leaving_state = self.state_stack.pop()
            leaving_state.exit()
        
        # Initialize the new state with persistent data
        new_state = self.states[state_id]
        merged_data = {**self.persistent_data}
        if data:
            merged_data.update(data)
        
        new_state.enter(merged_data)
        self.state_stack.append(new_state)
        self.current_state = new_state
    
    def push_state(self, state_id, data=None):
        """
        Push a new state onto the stack (e.g., for menus overlaid on gameplay).
        
        Args:
            state_id: ID of the state to push
            data: Optional data to pass to the new state
        """
        if state_id not in self.states:
            logger.error(f"Attempted to push unknown state: {state_id}")
            return
        
        logger.info(f"Pushing state: {state_id}")
        
        # Pause the current state if one exists
        if self.state_stack:
            self.state_stack[-1].pause()
        
        # Initialize and push the new state
        new_state = self.states[state_id]
        merged_data = {**self.persistent_data}
        if data:
            merged_data.update(data)
        
        new_state.enter(merged_data)
        self.state_stack.append(new_state)
        self.current_state = new_state
    
    def pop_state(self):
        """Remove the top state from the stack."""
        if not self.state_stack:
            logger.warning("Attempted to pop state with empty stack")
            return
        
        # Exit the current state
        leaving_state = self.state_stack.pop()
        leaving_state.exit()
        logger.info(f"Popped state: {leaving_state.__class__.__name__}")
        
        # Resume the previous state if one exists
        if self.state_stack:
            self.state_stack[-1].resume()
            self.current_state = self.state_stack[-1]
        else:
            self.current_state = None
    
    def set_persistent_data(self, key, value):
        """
        Store data that should persist between state transitions.
        
        Args:
            key: The key to store the data under
            value: The data to store
        """
        self.persistent_data[key] = value
    
    def get_persistent_data(self, key, default=None):
        """
        Retrieve persistent data.
        
        Args:
            key: The key to retrieve
            default: Default value if key doesn't exist
            
        Returns:
            The stored data or the default value
        """
        return self.persistent_data.get(key, default)
    
    def handle_event(self, event):
        """
        Forward events to the current active state.
        
        Args:
            event: Pygame event to handle
        """
        if self.state_stack:
            self.state_stack[-1].handle_event(event)
    
    def update(self, dt):
        """
        Update the current active state.
        
        Args:
            dt: Delta time since last update
        """
        if self.state_stack:
            self.state_stack[-1].update(dt)
    
    def render(self):
        """Render all visible states in the stack from bottom to top."""
        # Render all states that are visible
        for state in self.state_stack:
            if state.visible:
                state.render(self.screen)
    
    def _handle_state_change_request(self, data):
        """Handle state change request from event bus."""
        state_id = data.get("state_id")
        state_data = data.get("data")
        self.change_state(state_id, state_data)
    
    def _handle_push_state(self, data):
        """Handle push state request from event bus."""
        state_id = data.get("state_id")
        state_data = data.get("data")
        self.push_state(state_id, state_data)
    
    def _handle_pop_state(self, _):
        """Handle pop state request from event bus."""
        self.pop_state()
