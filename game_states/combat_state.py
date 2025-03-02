import pygame
import logging
import random
from dataclasses import dataclass
from game_state import GameState
logger = logging.getLogger("combat")

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


class SimpleCombat:
    """A simplified combat class for handling turn-based combat."""
    
    def __init__(self, player, enemies, event_bus=None):
        self.player = player
        self.enemies = enemies
        self.event_bus = event_bus
        self.current_turn = 0  # 0 for player, 1+ for enemies
        self.round = 1
        
    def is_player_turn(self):
        """Check if it's the player's turn."""
        return self.current_turn == 0
    
    def get_current_entity(self):
        """Get the entity whose turn it is."""
        if self.is_player_turn():
            return self.player
        else:
            enemy_index = self.current_turn - 1
            if enemy_index < len(self.enemies):
                return self.enemies[enemy_index]
        return None
    
    def get_enemy_entities(self):
        """Get all enemy entities."""
        return self.enemies
    
    def next_turn(self):
        """Advance to the next turn."""
        self.current_turn += 1
        if self.current_turn > len(self.enemies):
            self.current_turn = 0
            self.round += 1
            return True  # New round
        return False  # Same round, different entity


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
        self.active_combat = None
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
        self.active_combat = SimpleCombat(player_character, enemies, self.event_bus)
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
                    return True
                
                # Action selection
                elif event.key == pygame.K_LEFT or event.key == pygame.K_RIGHT:
                    action_count = 5  # attack, skill, item, defend, flee
                    if event.key == pygame.K_LEFT:
                        self.selected_action = (self.selected_action - 1) % action_count
                    else:
                        self.selected_action = (self.selected_action + 1) % action_count
                    return True
        
        return super().handle_event(event)
    
    def update(self, dt):
        """
        Update combat state.
        
        Args:
            dt: Time delta in seconds
        """
        super().update(dt)
        
        # If no active combat, return
        if not self.active_combat:
            return
        
        # Handle AI turns if not player's turn
        if not self.active_combat.is_player_turn():
            # Simple AI: just attack the player
            enemy = self.active_combat.get_current_entity()
            if enemy and self.player_entity:
                # AI performs an attack
                damage = enemy.attack
                taken = self.player_entity.take_damage(damage)
                
                # Notify about the attack
                self.event_bus.publish("attack_result", {
                    "attacker": enemy.name,
                    "target": self.player_entity.name,
                    "damage": taken
                })
                
                # Check if player is defeated
                if not self.player_entity.is_alive():
                    self._handle_combat_defeat()
                    return
                
                # Advance turn
                self.active_combat.next_turn()
    
    def render(self, screen):
        """
        Render the combat state.
        
        Args:
            screen: Pygame surface to render on
        """
        if not self.visible:
            return
        
        # Fill background with a dark color
        screen.fill((20, 20, 40))
        
        # If no active combat, just show a message
        if not self.active_combat:
            font = pygame.font.Font(None, 36)
            text = font.render("No active combat. Press ESC to exit.", True, (255, 255, 255))
            screen.blit(text, (screen.get_width() // 2 - text.get_width() // 2, 
                              screen.get_height() // 2 - text.get_height() // 2))
            return
        
        # Draw player entity
        if self.player_entity:
            player_rect = pygame.Rect(100, 300, 50, 50)
            pygame.draw.rect(screen, (0, 128, 255), player_rect)
            
            # Draw player health bar
            health_percent = self.player_entity.health / self.player_entity.max_health
            health_bar_rect = pygame.Rect(100, 360, 100, 10)
            pygame.draw.rect(screen, (200, 0, 0), health_bar_rect)
            pygame.draw.rect(screen, (0, 200, 0), 
                            pygame.Rect(health_bar_rect.x, health_bar_rect.y, 
                                        health_bar_rect.width * health_percent, health_bar_rect.height))
            
            # Draw player name
            font = pygame.font.Font(None, 24)
            name_text = font.render(self.player_entity.name, True, (255, 255, 255))
            screen.blit(name_text, (100, 375))
            
            # Draw player health
            health_text = font.render(f"HP: {self.player_entity.health}/{self.player_entity.max_health}", 
                                     True, (255, 255, 255))
            screen.blit(health_text, (100, 400))
        
        # Draw enemies
        enemy_spacing = 150
        for i, enemy in enumerate(self.enemy_entities):
            # Highlight selected enemy
            color = (255, 0, 0) if i == self.selected_target else (200, 0, 0)
            
            # Draw enemy
            enemy_rect = pygame.Rect(400 + i * enemy_spacing, 200, 40, 40)
            pygame.draw.rect(screen, color, enemy_rect)
            
            # Draw enemy health bar
            health_percent = enemy.health / enemy.max_health
            health_bar_rect = pygame.Rect(400 + i * enemy_spacing, 250, 80, 10)
            pygame.draw.rect(screen, (200, 0, 0), health_bar_rect)
            pygame.draw.rect(screen, (0, 200, 0), 
                            pygame.Rect(health_bar_rect.x, health_bar_rect.y, 
                                        health_bar_rect.width * health_percent, health_bar_rect.height))
            
            # Draw enemy name
            font = pygame.font.Font(None, 24)
            name_text = font.render(enemy.name, True, (255, 255, 255))
            screen.blit(name_text, (400 + i * enemy_spacing, 265))
            
            # Draw enemy health
            health_text = font.render(f"HP: {enemy.health}/{enemy.max_health}", 
                                     True, (255, 255, 255))
            screen.blit(health_text, (400 + i * enemy_spacing, 290))
        
        # Draw action menu if it's player's turn
        if self.active_combat and self.active_combat.is_player_turn():
            self._draw_action_menu(screen)
    
    def _draw_action_menu(self, screen):
        """Draw the action menu for player turns."""
        actions = ["Attack", "Skill", "Item", "Defend", "Flee"]
        
        menu_rect = pygame.Rect(50, 500, screen.get_width() - 100, 60)
        pygame.draw.rect(screen, (50, 50, 80), menu_rect)
        pygame.draw.rect(screen, (100, 100, 150), menu_rect, 2)
        
        # Draw actions
        font = pygame.font.Font(None, 28)
        action_width = menu_rect.width / len(actions)
        
        for i, action in enumerate(actions):
            # Highlight selected action
            if i == self.selected_action:
                action_rect = pygame.Rect(
                    menu_rect.x + i * action_width, menu_rect.y, 
                    action_width, menu_rect.height
                )
                pygame.draw.rect(screen, (80, 80, 120), action_rect)
            
            text = font.render(action, True, (255, 255, 255))
            screen.blit(text, (
                menu_rect.x + i * action_width + (action_width / 2 - text.get_width() / 2),
                menu_rect.y + 20
            ))
        
        # Draw turn indicator
        turn_text = font.render("Your Turn", True, (255, 255, 100))
        screen.blit(turn_text, (menu_rect.x + 10, menu_rect.y - 30))
    
    def _execute_selected_action(self):
        """Execute the currently selected action."""
        if not self.active_combat or not self.active_combat.is_player_turn():
            return
        
        # Get action type and target
        action_type = ["attack", "skill", "item", "defend", "flee"][self.selected_action]
        
        # Get target enemy if needed
        target = None
        if action_type in ["attack", "skill"] and self.enemy_entities:
            target = self.enemy_entities[self.selected_target]
        
        # Execute the action
        if action_type == "attack":
            self._execute_attack(target)
        elif action_type == "skill":
            self._execute_skill(target)
        elif action_type == "item":
            self._execute_item_use()
        elif action_type == "defend":
            self._execute_defend()
        elif action_type == "flee":
            self._execute_flee()
    
    def _execute_attack(self, target):
        """Execute an attack action."""
        if not target or not self.player_entity:
            return
        
        # Calculate damage (simple version)
        damage = self.player_entity.attack
        taken = target.take_damage(damage)
        
        # Notify about the attack
        self.event_bus.publish("attack_result", {
            "attacker": self.player_entity.name,
            "target": target.name,
            "damage": taken
        })
        
        # Check if target is defeated
        if not target.is_alive():
            # Remove dead enemy
            self.enemy_entities.remove(target)
            
            # Check if all enemies are defeated
            if not self.enemy_entities:
                self._handle_combat_victory()
                return
        
        # Advance turn
        self.active_combat.next_turn()
    
    def _execute_skill(self, target):
        """Execute a skill action."""
        # For now, just do a stronger attack
        if not target or not self.player_entity:
            return
        
        # Calculate damage (simple version)
        damage = int(self.player_entity.attack * 1.5)
        taken = target.take_damage(damage)
        
        # Notify about the skill use
        self.event_bus.publish("skill_result", {
            "user": self.player_entity.name,
            "skill": "Power Strike",
            "target": target.name,
            "damage": taken
        })
        
        # Check if target is defeated
        if not target.is_alive():
            # Remove dead enemy
            self.enemy_entities.remove(target)
            
            # Check if all enemies are defeated
            if not self.enemy_entities:
                self._handle_combat_victory()
                return
        
        # Advance turn
        self.active_combat.next_turn()
    
    def _execute_item_use(self):
        """Execute an item use action."""
        # For now, just a simple heal
        if not self.player_entity:
            return
        
        # Heal player
        heal_amount = int(self.player_entity.max_health * 0.3)
        self.player_entity.health = min(self.player_entity.max_health, 
                                      self.player_entity.health + heal_amount)
        
        # Notify about the item use
        self.event_bus.publish("item_used", {
            "user": self.player_entity.name,
            "item": "Health Potion",
            "heal": heal_amount
        })
        
        # Advance turn
        self.active_combat.next_turn()
    
    def _execute_defend(self):
        """Execute a defend action."""
        # For now, just skip the turn (would normally boost defense)
        if not self.player_entity:
            return
        
        # Notify about the defend action
        self.event_bus.publish("defend", {
            "entity": self.player_entity.name
        })
        
        # Advance turn
        self.active_combat.next_turn()
    
    def _execute_flee(self):
        """Execute a flee action."""
        # Random chance to flee
        if random.random() < 0.7:
            # Success - end combat
            self.event_bus.publish("combat_ended", {
                "result": "flee",
                "message": "You successfully fled from combat!"
            })
        else:
            # Failed - lose turn
            self.event_bus.publish("flee_failed", {
                "entity": self.player_entity.name,
                "message": "Failed to escape!"
            })
            
            # Advance turn
            self.active_combat.next_turn()
    
    def _handle_combat_victory(self):
        """Handle victory in combat."""
        # Calculate rewards
        xp_reward = sum(enemy.level * 10 for enemy in self.enemy_entities)
        gold_reward = sum(enemy.level * 5 for enemy in self.enemy_entities)
        
        # Notify about victory
        self.event_bus.publish("combat_ended", {
            "result": "victory",
            "message": f"Victory! Gained {xp_reward} XP and {gold_reward} gold.",
            "rewards": {
                "xp": xp_reward,
                "gold": gold_reward
            }
        })
    
    def _handle_combat_defeat(self):
        """Handle defeat in combat."""
        # Notify about defeat
        self.event_bus.publish("combat_ended", {
            "result": "defeat",
            "message": "Defeat! You have been defeated in combat."
        })
    
    def _handle_combat_end(self, data):
        """Handle the end of combat."""
        # Log combat result
        result = data.get("result", "unknown")
        message = data.get("message", "Combat ended.")
        logger.info(f"Combat ended with result: {result}. {message}")
        
        # Handle rewards if victory
        if result == "victory":
            rewards = data.get("rewards", {})
            self._award_combat_rewards(rewards)
        
        # Change back to previous state after a delay
        self.active_combat = None
        self.event_bus.publish("show_notification", {
            "title": "Combat Ended",
            "message": message,
            "duration": 3.0
        })
        
        # Add a slight delay before returning
        pygame.time.set_timer(pygame.USEREVENT + 1, 2000)  # 2 second delay
    
    def _award_combat_rewards(self, rewards):
        """Award combat rewards to the player."""
        # Get player character from persistent data
        player_character = self.state_manager.get_persistent_data("player_character")
        if not player_character:
            logger.warning("No player character found to award rewards to")
            return
        
        # Award XP
        xp_reward = rewards.get("xp", 0)
        if hasattr(player_character, "gain_xp") and callable(getattr(player_character, "gain_xp")):
            player_character.gain_xp(xp_reward)
        
        # Award gold
        gold_reward = rewards.get("gold", 0)
        if hasattr(player_character, "gold"):
            player_character.gold += gold_reward
    
    def _handle_attack_result(self, data):
        """Handle attack result event."""
        # Update UI or play animations based on attack result
        target = data.get("target")
        if target and hasattr(target, "health") and target.health <= 0:
            # Enemy defeated - update quest objectives
            if hasattr(target, "enemy_type"):
                enemy_type = target.enemy_type
                # Publish an event for quest system to pick up
                self.event_bus.publish("enemy_killed", {
                    "enemy_type": enemy_type,
                    "enemy_id": getattr(target, "id", "unknown")
                })
                logger.info(f"Enemy of type {enemy_type} defeated, notifying quest system")
    
    def _handle_skill_result(self, data):
        """Handle skill result event."""
        # Update UI or play animations based on skill result
        pass
    
