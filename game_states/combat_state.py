import pygame
import logging
import random  # Add this import
from dataclasses import dataclass
@dataclass
class SimpleCombatEntity:
    name: str
    max_health: int
    health: int
    level: int
    attack: int = 5
    defense: int = 2

    def take_damage(self, amount):
        actual_damage = max(1, amount - self.defense)
        self.health = max(0, self.health - actual_damage)
        return actual_damage

    def is_alive(self):
        return self.health > 0

    def attack_target(self, target):
        damage = self.attack + random.randint(0, 3) - 1  # Add some randomness
        return target.take_damage(damage)

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
        from combat_system_integration import CombatManager
        self.combat_manager = CombatManager(event_bus, settings)
        self.active_combat = False
        self.selected_action = 0
        self.selected_target = 0
        self.current_turn = 0
        self.player_entity = None
        self.enemy_entities = []
        logger.info("CombatGameState initialized")
    
    def enter(self, data=None):
        """Enter the combat state."""
        super().enter(data)
        
        try:
            # Get player character from game data
            player_character = self.state_manager.get_persistent_data("player_character")
            
            # Check if this is a random encounter
            encounter_type = data.get("encounter_type") if data else None
            terrain = data.get("terrain") if data else "plains"
            
            # Generate appropriate enemies based on encounter type
            if encounter_type == "random":
                # Generate random enemies based on terrain and player level
                self._generate_random_enemies(player_character, terrain)
            else:
                # Use enemies provided in data if available
                enemies = data.get("enemies", []) if data else []
                if not enemies:
                    # Create default enemy for testing
                    self._generate_random_enemies(player_character, terrain)
            
            # Subscribe to combat events
            self.event_bus.subscribe("combat_ended", self._handle_combat_end)
            self.event_bus.subscribe("attack_result", self._handle_attack_result)
            self.event_bus.subscribe("skill_result", self._handle_skill_result)
            
            # Show notification
            self.event_bus.publish("show_notification", {
                "title": "Combat Started",
                "message": "Prepare for battle!",
                "duration": 3.0
            })
            
            logger.info("Entered combat state")
            
        except Exception as e:
            logger.error(f"Error entering combat state: {e}", exc_info=True)
    
    def _generate_random_enemies(self, player_character, terrain):
        """Generate random enemies based on terrain and player level."""
        logger.info(f"Generating random enemies for {terrain} terrain")
        
        # Default to level 1 if player_character is None
        player_level = getattr(player_character, 'level', 1)
        
        # Create simple enemy entities based on the terrain
        enemy_count = random.randint(1, 2)  # Start with fewer enemies
        enemies = []
        
        for i in range(enemy_count):
            # Create a simple enemy based on terrain
            if terrain == "forest":
                enemy_name = "Wolf"
                enemy_health = 20
                enemy_attack = 4 + player_level
            elif terrain == "mountains":
                enemy_name = "Troll"
                enemy_health = 30
                enemy_attack = 6 + player_level
            else:
                enemy_name = "Bandit"
                enemy_health = 25
                enemy_attack = 5 + player_level
                
            # Create a simple enemy entity
            enemy = SimpleCombatEntity(
                name=f"{enemy_name} #{i+1}", 
                max_health=enemy_health,
                health=enemy_health,
                level=player_level,
                attack=enemy_attack,
                defense=player_level
            )
            enemies.append(enemy)
        
        # Notify about enemy encounter
        self.event_bus.publish("show_notification", {
            "title": "Combat",
            "message": f"Encountered {enemy_count} {enemies[0].name.split()[0]}!",
            "duration": 2.0
        })
        
        logger.info(f"Generated {enemy_count} random enemies")
        
        # Create player proxy if we don't have a real character
        if not player_character:
            player_character = SimpleCombatEntity(
                name="Player",
                max_health=50,
                health=50,
                level=1,
                attack=8,
                defense=3
            )
        
        # Store combat entities
        self.player_entity = player_character
        self.enemy_entities = enemies
        self.active_combat = True
        self.current_turn = 0  # 0 for player, 1+ for enemies
        
        # Show combat start message
        self.event_bus.publish("show_notification", {
            "title": "Combat Started",
            "message": f"Your turn! Press SPACE to attack or ESC to flee.",
            "duration": 3.0
        })
        
    def exit(self):
        """Exit the combat state."""
        super().exit()
        
        # Unsubscribe from events
        self.event_bus.unsubscribe("combat_ended", self._handle_combat_end)
        self.event_bus.unsubscribe("attack_result", self._handle_attack_result)
        self.event_bus.unsubscribe("skill_result", self._handle_skill_result)
        
        logger.info("Exited combat state")
    
    def handle_event(self, event):
        """
        Handle pygame events.
        
        Args:
            event: Pygame event
            
        Returns:
            Boolean indicating if event was handled
        """
        if not self.active_combat:
            # If no active combat, just handle escape key
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.change_state("world_exploration")
                return True
            return super().handle_event(event)
        
        # Check if it's player's turn
        is_player_turn = self.active_combat.is_player_turn()
        
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                # Set action to flee and execute
                self.selected_action = 4  # Index for "flee" in actions list
                self._execute_selected_action()
                return True
                
            if is_player_turn:
                # Action selection
                if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    self._execute_selected_action()
                    return True
                
                # Target selection
                elif event.key == pygame.K_UP or event.key == pygame.K_DOWN:
                    enemy_count = len(self.active_combat.get_enemy_entities())
                    if enemy_count > 0:
                        if event.key == pygame.K_UP:
                            self.selected_target = (self.selected_target - 1) % enemy_count
                        else:
                            self.selected_target = (self.selected_target + 1) % enemy_count
                        target = self.active_combat.get_enemy_entities()[self.selected_target]
                        self.event_bus.publish("show_notification", {
                            "title": "Target Selected",
                            "message": f"Targeting {target.name} ({target.health}/{target.max_health} HP)",
                            "duration": 1.0
                        })
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
        self.combat_manager.update(dt)
    
    def render(self, screen):
        """
        Render state.
        
        Args:
            screen: Pygame surface to render on
        """
        # Clear screen with dark background
        screen.fill((20, 20, 40))
        
        if not self.active_combat:
            # Draw placeholder if no active combat
            self._render_placeholder(screen)
            return
        
        if isinstance(self.active_combat, bool):
            self._render_placeholder(screen)
            return
        
        # Get entities
        player_entities = [self.player_entity] if self.player_entity else []
        enemy_entities = self.enemy_entities
        
        # Draw combat UI
        self._render_combat_ui(screen, player_entities, enemy_entities)
        
        # Draw turn indicator
        current_entity = self.player_entity if self.current_turn == 0 else (self.enemy_entities[self.current_turn-1] if len(self.enemy_entities) > 0 else None)
        if current_entity:
            is_player_turn = (self.current_turn == 0)
            self._render_turn_indicator(screen, current_entity, is_player_turn)
        
        # Draw action menu if it's player's turn
        if self.current_turn == 0:
            self._render_action_menu(screen)
    
    def _render_placeholder(self, screen):
        """Render placeholder combat screen."""
        font = pygame.font.SysFont(None, 36)
        
        # Title
        title_text = font.render("COMBAT MODE", True, (255, 255, 255))
        screen.blit(title_text, (screen.get_width() // 2 - title_text.get_width() // 2, 50))
        
        # Instructions
        font_small = pygame.font.SysFont(None, 24)
        instr1 = font_small.render("Loading combat...", True, (200, 200, 200))
        
        screen.blit(instr1, (screen.get_width() // 2 - instr1.get_width() // 2, 120))
        
        # Player area
        pygame.draw.rect(screen, (50, 50, 80), (50, 200, screen.get_width() - 100, 100))
        player_text = font.render("Player", True, (255, 255, 255))
        screen.blit(player_text, (100, 230))
        
        # Enemy area
        pygame.draw.rect(screen, (80, 50, 50), (50, 350, screen.get_width() - 100, 100))
        enemy_text = font.render("Enemy", True, (255, 255, 255))
        screen.blit(enemy_text, (100, 380))
    
    def _render_combat_ui(self, screen, player_entities, enemy_entities):
        """Render the main combat UI with entities."""
        # Header
        font_large = pygame.font.SysFont(None, 36)
        title_text = font_large.render("COMBAT", True, (255, 255, 255))
        screen.blit(title_text, (screen.get_width() // 2 - title_text.get_width() // 2, 20))
        
        # Player area
        player_area_height = 150
        player_area_y = screen.get_height() - player_area_height - 20
        pygame.draw.rect(screen, (50, 50, 80), (20, player_area_y, screen.get_width() - 40, player_area_height))
        
        # Enemy area
        enemy_area_height = 150
        enemy_area_y = 70
        pygame.draw.rect(screen, (80, 50, 50), (20, enemy_area_y, screen.get_width() - 40, enemy_area_height))
        
        # Render player entities
        self._render_entities(screen, player_entities, player_area_y, is_player=True)
        
        # Render enemy entities
        self._render_entities(screen, enemy_entities, enemy_area_y, is_player=False)
    
    def _render_entities(self, screen, entities, base_y, is_player=True):
        """Render a group of entities."""
        if not entities:
            return
        
        entity_width = 120
        entity_height = 120
        
        # Calculate total width needed
        total_width = len(entities) * entity_width
        
        # Center entities
        start_x = (screen.get_width() - total_width) // 2
        
        font = pygame.font.SysFont(None, 24)
        font_small = pygame.font.SysFont(None, 18)
        
        for i, entity in enumerate(entities):
            x = start_x + i * entity_width
            y = base_y + 15
            
            # Entity background
            bg_color = (30, 30, 40) if is_player else (40, 30, 30)
            
            # Highlight selected target
            if not is_player and i == self.selected_target and self.active_combat.is_player_turn():
                bg_color = (60, 40, 40)
                pygame.draw.rect(screen, (255, 200, 0), 
                               (x + 8, y - 2, entity_width - 16, entity_height - 26), 2)
            
            pygame.draw.rect(screen, bg_color, (x + 10, y, entity_width - 20, entity_height - 30))
            
            # Entity name
            name_text = font.render(entity.name, True, (255, 255, 255))
            screen.blit(name_text, (x + entity_width//2 - name_text.get_width()//2, y + 5))
            
            # HP bar
            hp_percent = entity.health / entity.max_health
            hp_bar_width = entity_width - 40
            hp_bar_height = 10
            hp_bar_x = x + 20
            hp_bar_y = y + 30
            
            # HP bar background
            pygame.draw.rect(screen, (100, 100, 100), 
                           (hp_bar_x, hp_bar_y, hp_bar_width, hp_bar_height))
            
            # HP bar fill
            hp_fill_width = int(hp_bar_width * hp_percent)
            hp_color = (0, 255, 0) if hp_percent > 0.5 else (255, 255, 0) if hp_percent > 0.25 else (255, 0, 0)
            pygame.draw.rect(screen, hp_color, 
                           (hp_bar_x, hp_bar_y, hp_fill_width, hp_bar_height))
            
            # HP text
            hp_text = font_small.render(f"{entity.health}/{entity.max_health}", True, (255, 255, 255))
            screen.blit(hp_text, (hp_bar_x + hp_bar_width//2 - hp_text.get_width()//2, hp_bar_y + 12))
            
            # Status effects
            if hasattr(entity, 'status_effects') and entity.status_effects:
                status_y = hp_bar_y + 30
                for j, status in enumerate(entity.status_effects):
                    if j >= 3:  # Show max 3 status effects
                        break
                    status_text = font_small.render(status.name, True, (200, 200, 255))
                    screen.blit(status_text, (hp_bar_x, status_y + j * 15))
    
    def _render_turn_indicator(self, screen, entity, is_player_turn):
        """Render indicator for whose turn it is."""
        font = pygame.font.SysFont(None, 28)
        turn_text = font.render(f"{'Your' if is_player_turn else entity.name + '\'s'} Turn", True, (255, 255, 0))
        
        screen.blit(turn_text, (screen.get_width() // 2 - turn_text.get_width() // 2, 225))
    
    def _render_action_menu(self, screen):
        """Render action menu for player turn."""
        menu_width = 400
        menu_height = 60
        menu_x = (screen.get_width() - menu_width) // 2
        menu_y = 250
        
        # Menu background
        pygame.draw.rect(screen, (40, 40, 60), (menu_x, menu_y, menu_width, menu_height))
        pygame.draw.rect(screen, (100, 100, 150), (menu_x, menu_y, menu_width, menu_height), 2)
        
        # Actions
        actions = ["Attack", "Skill", "Item", "Defend", "Flee"]
        font = pygame.font.SysFont(None, 24)
        
        for i, action in enumerate(actions):
            action_width = menu_width // len(actions)
            action_x = menu_x + i * action_width
            
            # Highlight if selected
            if i == self.selected_action:
                pygame.draw.rect(screen, (60, 60, 100), (action_x, menu_y, action_width, menu_height))
            
            # Action text
            text = font.render(action, True, (255, 255, 255))
            screen.blit(text, (action_x + action_width//2 - text.get_width()//2, menu_y + menu_height//2 - text.get_height()//2))
    
    def _execute_selected_action(self):
        """Execute the currently selected action."""
        if not self.active_combat:
            return
        
        actions = ["attack", "skill", "item", "defend", "flee"]
        action = actions[self.selected_action]
        
        if action == "attack":
            # Player attacks the selected enemy
            if self.current_turn == 0 and 0 <= self.selected_target < len(self.enemy_entities):
                target = self.enemy_entities[self.selected_target]
                damage = self.player_entity.attack_target(target)
                
                # Show attack message
                self.event_bus.publish("show_notification", {
                    "title": "Player Attack",
                    "message": f"You hit {target.name} for {damage} damage! ({target.health}/{target.max_health} HP)",
                    "duration": 2.0
                })
                
                # Check if enemy is defeated
                if not target.is_alive():
                    self.event_bus.publish("show_notification", {
                        "title": "Enemy Defeated",
                        "message": f"You defeated {target.name}!",
                        "duration": 2.0
                    })
                    self.enemy_entities.remove(target)
                
                # Check if all enemies are defeated
                if not self.enemy_entities:
                    self._handle_combat_victory()
                    return
                
                # Change to enemy turn
                self.current_turn = 1
                self._execute_enemy_turn()
    
        elif action == "flee":
            # 50% chance to flee successfully
            if random.random() < 0.5:
                self.event_bus.publish("show_notification", {
                    "title": "Escaped",
                    "message": "You fled from battle.",
                    "duration": 2.0
                })
                self.change_state("world_exploration")
            else:
                self.event_bus.publish("show_notification", {
                    "title": "Failed to Escape",
                    "message": "You couldn't escape! Enemy's turn.",
                    "duration": 2.0
                })
                # Change to enemy turn
                self.current_turn = 1
                self._execute_enemy_turn()
    
    def _handle_combat_victory(self):
        """Handle combat victory."""
        # End combat with victory
        self.combat_manager.end_combat("victory")
    def _handle_combat_end(self, data):
        """Handle combat_ended event."""
        result = data.get("result", "defeat")
        rewards = data.get("rewards", {})
        
        if result == "victory":
            # Show victory notification
            self.event_bus.publish("show_notification", {
                "title": "Victory!",
                "message": "You won the battle!",
                "duration": 3.0
            })
            
            # Show rewards if any
            if rewards:
                xp = rewards.get("experience", 0)
                gold = rewards.get("gold", 0)
                
                self.event_bus.publish("show_notification", {
                    "title": "Rewards",
                    "message": f"Gained {xp} XP and {gold} gold",
                    "duration": 3.0
                })
        
        elif result == "defeat":
            # Show defeat notification
            self.event_bus.publish("show_notification", {
                "title": "Defeat",
                "message": "You were defeated in battle.",
                "duration": 3.0
            })
        
        elif result == "flee":
            # Show flee notification
            self.event_bus.publish("show_notification", {
                "title": "Escaped",
                "message": "You fled from battle.",
                "duration": 3.0
            })
        
        # Return to world exploration
        self.change_state("world_exploration")
    
    def _handle_attack_result(self, data):
        """Handle attack_result event."""
        # Could be used for animations or sound effects
        pass
    
    def _handle_skill_result(self, data):
        """Handle skill_result event."""
        # Could be used for animations or sound effects
        pass
