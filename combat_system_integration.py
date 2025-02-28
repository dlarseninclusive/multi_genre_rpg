import logging
import random
from enum import Enum, auto
from combat_system import Combat, CombatEntity, DamageType, StatusEffect
from combat_system import DamageSkill, HealingSkill, BuffSkill, DebuffSkill
from combat_system import MonsterGenerator, PlayerCharacter
from combat_ai import CombatAI, BossAI
from event_bus import EventBus
from character import Character

logger = logging.getLogger("combat_integration")

class CombatType(Enum):
    """Types of combat encounters"""
    RANDOM = auto()      # Random wilderness encounter
    DUNGEON = auto()     # Dungeon combat
    STORY = auto()       # Story-based combat
    BOSS = auto()        # Boss fight
    ARENA = auto()       # Arena/tournament combat

class CombatResult(Enum):
    """Possible results of combat"""
    VICTORY = auto()     # Players won
    DEFEAT = auto()      # Players lost
    FLEE = auto()        # Players fled
    DRAW = auto()        # Combat ended in draw (rare)

class CombatManager:
    """
    Integrates the combat system with the game state.
    Handles combat initialization, updates, and results.
    """
    
    def __init__(self, event_bus, settings):
        """Initialize the combat manager."""
        self.event_bus = event_bus
        self.settings = settings
        self.active_combat = None
        self.combat_log = None
        self.monster_generator = MonsterGenerator()
        self.combat_ai = CombatAI()
        
        # Subscribe to events
        self.event_bus.subscribe("combat_action", self._handle_combat_action)
        logger.info("CombatManager initialized")
    
    def start_combat(self, player_character, enemies=None, location=None):
        """
        Start a new combat encounter.
        
        Args:
            player_character: Player character
            enemies: List of enemy entities (optional)
            location: Optional location data
            
        Returns:
            Combat instance
        """
        # Create combat instance
        combat = Combat()
        
        # Convert player character to combat entity if needed
        if not isinstance(player_character, CombatEntity):
            player_entity = self._convert_to_combat_entity(player_character)
        else:
            player_entity = player_character
        
        # Generate enemies if not provided
        if not enemies:
            player_level = player_entity.level
            enemies = self.monster_generator.generate_encounter(
                player_level, "normal", "neutral"
            )
        
        # Initialize combat
        combat.initialize_from_entity_lists([player_entity], enemies)
        
        # Store active combat
        self.active_combat = combat
        
        # Start combat
        combat.start()
        
        # Log combat start
        logger.info(f"Started combat with {len(enemies)} enemies")
        
        return combat
    
    def end_combat(self, result="defeat"):
        """
        End the current combat encounter.
        
        Args:
            result: Result of combat ("victory", "defeat", "flee")
        """
        if not self.active_combat:
            return
        
        # Get rewards
        rewards = {}
        if result == "victory":
            rewards = self.active_combat.get_rewards()
        
        # Publish combat ended event
        self.event_bus.publish("combat_ended", {
            "result": result,
            "rewards": rewards
        })
        
        # Clear active combat
        self.active_combat = None
        
        logger.info(f"Combat ended with result: {result}")
    
    def update(self, dt):
        """
        Update combat state.
        
        Args:
            dt: Time delta in seconds
        """
        if not self.active_combat:
            return
        
        # Check if combat is over
        if self.active_combat.is_over():
            winners = self.active_combat.get_winners()
            result = "victory" if winners == 0 else "defeat"
            self.end_combat(result)
            return
        
        # Get current entity
        current_entity = self.active_combat.turn_manager.get_current_entity()
        
        # Skip if no current entity
        if not current_entity:
            return
        
        # Process AI turns for enemies
        if current_entity.team != 0:  # Not player team
            self._process_enemy_turn(current_entity)
    
    def _process_enemy_turn(self, enemy):
        """
        Process an enemy's turn using AI.
        
        Args:
            enemy: Enemy entity
        """
        # Skip if enemy can't take a turn
        if not enemy.can_take_turn():
            self.active_combat.end_turn()
            return
        
        # Use AI to choose action
        action = self.combat_ai.choose_action(enemy, self.active_combat)
        
        # Process action
        if action['action'] == CombatAction.ATTACK:
            # Attack
            if 'targets' in action and action['targets']:
                result = enemy.attack(action['targets'][0])
                
                # Publish attack result
                self.event_bus.publish("enemy_attack", {
                    "enemy": enemy,
                    "target": action['targets'][0],
                    "result": result
                })
        
        elif action['action'] == CombatAction.SKILL:
            # Use skill
            if 'skill' in action and 'targets' in action:
                result = enemy.use_skill(action['skill'], action['targets'])
                
                # Publish skill result
                self.event_bus.publish("enemy_skill", {
                    "enemy": enemy,
                    "skill": action['skill'],
                    "targets": action['targets'],
                    "result": result
                })
        
        elif action['action'] == CombatAction.DEFEND:
            # Defend
            enemy.defend()
            
            # Publish defend action
            self.event_bus.publish("enemy_defend", {
                "enemy": enemy
            })
        
        # End enemy turn
        self.active_combat.end_turn()
    
    def _handle_combat_action(self, data):
        """
        Handle combat_action event from UI.
        
        Args:
            data: Event data with action details
        """
        if not self.active_combat:
            return
        
        # Get current entity
        entity = self.active_combat.turn_manager.get_current_entity()
        
        # Skip if not player's turn
        if not entity or entity.team != 0:
            return
        
        action_type = data.get("type")
        
        if action_type == "attack":
            self._handle_attack_action(entity, data)
        elif action_type == "skill":
            self._handle_skill_action(entity, data)
        elif action_type == "item":
            self._handle_item_action(entity, data)
        elif action_type == "defend":
            self._handle_defend_action(entity)
        elif action_type == "flee":
            self._handle_flee_action(entity)
    
    def _handle_attack_action(self, entity, data):
        """Handle attack action."""
        # Get target
        target_index = data.get("target", 0)
        targets = self.active_combat.turn_manager.get_targets(entity, "enemy")
        
        if 0 <= target_index < len(targets):
            # Execute attack
            result = entity.attack(targets[target_index])
            
            # Publish attack result
            self.event_bus.publish("attack_result", {
                "attacker": entity,
                "target": targets[target_index],
                "result": result
            })
            
            # End turn
            self.active_combat.end_turn()
    
    def _handle_skill_action(self, entity, data):
        """Handle skill action."""
        # Get skill and targets
        skill_index = data.get("skill_index", 0)
        target_indices = data.get("targets", [0])
        
        if skill_index < len(entity.skills):
            skill = entity.skills[skill_index]
            
            # Get appropriate targets based on skill type
            if skill.target_type == "enemy":
                all_targets = self.active_combat.turn_manager.get_targets(entity, "enemy")
            elif skill.target_type == "ally":
                all_targets = self.active_combat.turn_manager.get_targets(entity, "ally")
            elif skill.target_type == "self":
                all_targets = [entity]
            else:
                all_targets = []
            
            # Filter valid targets
            targets = []
            for idx in target_indices:
                if 0 <= idx < len(all_targets):
                    targets.append(all_targets[idx])
            
            if targets:
                # Use skill
                result = entity.use_skill(skill, targets)
                
                # Publish skill result
                self.event_bus.publish("skill_result", {
                    "user": entity,
                    "skill": skill,
                    "targets": targets,
                    "result": result
                })
                
                # End turn
                self.active_combat.end_turn()
    
    def _handle_item_action(self, entity, data):
        """Handle item action."""
        # This would require inventory integration
        # For now, just end the turn
        self.active_combat.end_turn()
    
    def _handle_defend_action(self, entity):
        """Handle defend action."""
        # Execute defend
        entity.defend()
        
        # Publish defend result
        self.event_bus.publish("defend_result", {
            "entity": entity
        })
        
        # End turn
        self.active_combat.end_turn()
    
    def _handle_flee_action(self, entity):
        """Handle flee action."""
        # Attempt to flee
        result = entity.flee(self.active_combat)
        
        if result['success']:
            # Successfully fled
            self.end_combat("flee")
        else:
            # Failed to flee
            self.event_bus.publish("flee_result", {
                "success": False,
                "message": result['message']
            })
            
            # End turn
            self.active_combat.end_turn()
    
    def _convert_to_combat_entity(self, character):
        """
        Convert a character to a combat entity.
        
        Args:
            character: Character to convert
            
        Returns:
            CombatEntity instance
        """
        # If already a combat entity, return as is
        if isinstance(character, CombatEntity):
            return character
        
        # Create a basic player character
        player = PlayerCharacter(
            name=getattr(character, "name", "Player"),
            character_class=getattr(character, "character_class", "warrior"),
            level=getattr(character, "level", 1)
        )
        
        return player

class CombatIntegration:
    """
    Integrates the combat system with the rest of the game.
    Handles conversion between game characters and combat entities,
    manages encounters, and processes combat results.
    """
    
    def __init__(self, character_manager, world_manager):
        """
        Initialize combat integration.
        
        Args:
            character_manager: Character management system
            world_manager: World management system
        """
        self.character_manager = character_manager
        self.world_manager = world_manager
        self.event_bus = EventBus()
        self.monster_generator = MonsterGenerator()
        
        # Register event handlers
        self.event_bus.subscribe("combat_end", self.handle_combat_end)
    
    def convert_character_to_combat_entity(self, character):
        """
        Convert a game character to a combat entity.
        
        Args:
            character: Character instance
            
        Returns:
            CombatEntity instance
        """
        # Create base entity
        entity = CombatEntity(character.name, character.level, team=0)
        
        # Copy stats
        entity.strength = character.attributes.strength
        entity.intelligence = character.attributes.intelligence
        entity.dexterity = character.attributes.dexterity
        entity.constitution = character.attributes.constitution
        entity.speed = character.attributes.agility
        
        # Set health and mana
        entity.max_health = character.max_health
        entity.health = character.current_health
        entity.max_mana = character.max_mana
        entity.mana = character.current_mana
        
        # Update derived stats
        entity._update_derived_stats()
        
        # Add resistances based on character equipment and traits
        for damage_type in DamageType:
            if damage_type != DamageType.TRUE:
                resistance = character.get_resistance(damage_type.name.lower())
                entity.set_resistance(damage_type, resistance)
        
        # Add skills
        for character_skill in character.skills:
            entity_skill = self.convert_skill(character_skill)
            if entity_skill:
                entity.skills.append(entity_skill)
        
        return entity
    
    def convert_skill(self, character_skill):
        """
        Convert a character skill to a combat skill.
        
        Args:
            character_skill: Character skill
            
        Returns:
            Combat skill instance
        """
        skill_type = character_skill.skill_type
        
        if skill_type == "DAMAGE":
            # Create damage skill
            damage_type = DamageType[character_skill.damage_type.upper()]
            
            skill = DamageSkill(
                character_skill.name,
                character_skill.description,
                damage_type,
                character_skill.power,
                character_skill.mana_cost,
                character_skill.cooldown
            )
            
        elif skill_type == "HEALING":
            # Create healing skill
            skill = HealingSkill(
                character_skill.name,
                character_skill.description,
                character_skill.power,
                character_skill.mana_cost,
                character_skill.cooldown
            )
            
        elif skill_type == "BUFF":
            # Create buff skill
            effect_type = StatusEffect[character_skill.effect_type.upper()]
            
            skill = BuffSkill(
                character_skill.name,
                character_skill.description,
                effect_type,
                character_skill.duration,
                character_skill.potency,
                character_skill.mana_cost,
                character_skill.cooldown
            )
            
        elif skill_type == "DEBUFF":
            # Create debuff skill
            effect_type = StatusEffect[character_skill.effect_type.upper()]
            
            skill = DebuffSkill(
                character_skill.name,
                character_skill.description,
                effect_type,
                character_skill.duration,
                character_skill.potency,
                character_skill.mana_cost,
                character_skill.cooldown
            )
            
        else:
            # Unknown skill type
            return None
        
        # Set current cooldown
        skill.current_cooldown = character_skill.current_cooldown
        
        # Set skill level
        skill.level = character_skill.level
        
        # Set targeting type
        skill.target_type = character_skill.target_type
        
        return skill
    
    def update_character_from_combat_entity(self, character, entity):
        """
        Update a game character from a combat entity after combat.
        
        Args:
            character: Character instance to update
            entity: CombatEntity instance with post-combat state
        """
        # Update health and mana
        character.current_health = entity.health
        character.current_mana = entity.mana
        
        # Update skill cooldowns
        for entity_skill in entity.skills:
            for character_skill in character.skills:
                if character_skill.name == entity_skill.name:
                    character_skill.current_cooldown = entity_skill.current_cooldown
        
        # Update status effects (convert combat status effects to character effects)
        character.status_effects = []
        for effect in entity.status_effects:
            character_effect = {
                'type': effect.effect_type.name.lower(),
                'duration': effect.duration,
                'potency': effect.potency,
                'source': effect.source
            }
            character.status_effects.append(character_effect)
    
    def create_combat_encounter(self, encounter_type=CombatType.RANDOM, location=None, 
                               difficulty="normal", enemy_level=None, enemies=None):
        """
        Create a combat encounter.
        
        Args:
            encounter_type: Type of encounter from CombatType enum
            location: Location where combat takes place
            difficulty: Difficulty setting (easy, normal, hard)
            enemy_level: Level of enemies, or None to use player level
            enemies: Specific enemies to use, or None to generate
            
        Returns:
            Combat instance ready to start
        """
        # Create new combat instance
        combat = Combat()
        
        # Set environment based on location
        if location:
            environment = self.world_manager.get_location_environment(location)
            combat.environment = environment
        else:
            combat.environment = "neutral"
        
        # Convert player characters to combat entities
        player_characters = self.character_manager.get_party_members()
        player_entities = [self.convert_character_to_combat_entity(char) for char in player_characters]
        
        # Get player level for scaling
        if enemy_level is None:
            enemy_level = self.character_manager.get_party_average_level()
        
        # Generate or use provided enemies
        if enemies:
            # Use provided enemies
            enemy_entities = enemies
        else:
            # Generate enemies based on encounter type
            if encounter_type == CombatType.BOSS:
                # Boss encounter
                enemy_entities = self.monster_generator.generate_encounter(
                    enemy_level, "boss", combat.environment)
                combat.is_boss_fight = True
                
            elif encounter_type == CombatType.DUNGEON:
                # Dungeon encounter - slightly harder than random
                enemy_type = "elite" if random.random() < 0.3 else "normal"
                enemy_entities = self.monster_generator.generate_encounter(
                    enemy_level, enemy_type, combat.environment)
                
            elif encounter_type == CombatType.STORY:
                # Story encounter - tailored for narrative
                # This would normally come from quest/story data
                enemy_entities = self.monster_generator.generate_encounter(
                    enemy_level, "normal", combat.environment)
                
            elif encounter_type == CombatType.ARENA:
                # Arena encounter - balanced for competition
                enemy_entities = self.monster_generator.generate_encounter(
                    enemy_level, "normal", "arena")
                
            else:  # RANDOM
                # Random wilderness encounter
                enemy_entities = self.monster_generator.generate_encounter(
                    enemy_level, "random", combat.environment)
                combat.is_random_encounter = True
        
        # Initialize combat with entities
        combat.initialize_from_entity_lists(player_entities, enemy_entities)
        
        # Set encounter level
        combat.encounter_level = enemy_level
        
        # Modify combat based on difficulty
        if difficulty == "easy":
            # Reduce enemy stats
            for entity in enemy_entities:
                entity.strength = int(entity.strength * 0.8)
                entity.intelligence = int(entity.intelligence * 0.8)
                entity.dexterity = int(entity.dexterity * 0.8)
                entity.constitution = int(entity.constitution * 0.8)
                entity._update_derived_stats()
                
        elif difficulty == "hard":
            # Increase enemy stats
            for entity in enemy_entities:
                entity.strength = int(entity.strength * 1.2)
                entity.intelligence = int(entity.intelligence * 1.2)
                entity.dexterity = int(entity.dexterity * 1.2)
                entity.constitution = int(entity.constitution * 1.2)
                entity._update_derived_stats()
        
        return combat
    
    def handle_combat_end(self, event_data):
        """
        Handle end of combat event.
        
        Args:
            event_data: Event data including combat result and rewards
        """
        result = event_data['result']
        
        if result == 'victory':
            # Handle victory
            rewards = event_data.get('rewards', {})
            
            # Award XP and gold to party
            xp = rewards.get('experience', 0)
            gold = rewards.get('gold', 0)
            
            self.character_manager.award_party_xp(xp)
            self.character_manager.award_party_gold(gold)
            
            # Add any items to inventory
            items = rewards.get('items', [])
            for item in items:
                self.character_manager.add_item_to_inventory(item)
            
            # Log rewards
            logger.info(f"Combat victory: {xp} XP, {gold} gold, {len(items)} items")
            
            # Publish reward event for UI to display
            self.event_bus.publish("combat_rewards", {
                'xp': xp,
                'gold': gold,
                'items': items
            })
        
        elif result == 'defeat':
            # Handle defeat
            logger.info("Combat defeat")
            
            # Trigger game over or respawn based on game rules
            self.event_bus.publish("player_defeated", {})
        
        elif result == 'flee':
            # Handle successful flee
            logger.info("Combat fled")
            
            # No rewards for fleeing
            pass
        
        # Update characters from combat entities
        # This would happen when returning to the game state
        # self.update_characters_from_combat()
    
    def update_characters_from_combat(self, combat):
        """
        Update all characters from combat entities after combat.
        
        Args:
            combat: Combat instance that just ended
        """
        # Get player entities
        player_entities = [e for e in combat.turn_manager.entities if e.team == 0]
        
        # Get party members
        party_members = self.character_manager.get_party_members()
        
        # Update each character
        for character in party_members:
            # Find matching entity
            entity = next((e for e in player_entities if e.name == character.name), None)
            
            if entity:
                self.update_character_from_combat_entity(character, entity)
    
    def get_combat_state_data(self, combat):
        """
        Get data needed for creating a combat state.
        
        Args:
            combat: Combat instance
            
        Returns:
            Dictionary with data for combat state
        """
        # Get environment
        environment = combat.environment
        
        # Get enemy entities
        enemy_entities = [e for e in combat.turn_manager.entities if e.team == 1]
        
        # Get is_boss flag
        is_boss = combat.is_boss_fight
        
        # Get encounter level
        encounter_level = combat.encounter_level
        
        return {
            'environment': environment,
            'enemy_entities': enemy_entities,
            'is_boss': is_boss,
            'enemy_level': encounter_level,
            'encounter_type': 'boss' if is_boss else 'normal'
        }
