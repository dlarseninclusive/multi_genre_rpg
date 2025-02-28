import random
import math
import logging
from combat_system import Combat, CombatEntity, PlayerCharacter, StatusEffect, DamageType

logger = logging.getLogger("combat_integration")

class CombatManager:
    """
    Integrates the combat system with the game state.
    Handles combat initialization, updates, and results.
    """
    
    def __init__(self, event_bus, settings):
        self.event_bus = event_bus
        self.settings = settings
        self.active_combat = None
        self.turn_in_progress = False
        
        # Subscribe to events
        self.event_bus.subscribe("combat_action", self._handle_combat_action)
        logger.info("CombatManager initialized")
    
    def start_combat(self, player_character, enemies, location=None):
        """
        Start a new combat encounter.
        
        Args:
            player_character: Player character (from character system)
            enemies: List of enemy entities
            location: Optional location data
        
        Returns:
            New Combat instance
        """
        try:
            # Convert player character to combat entity
            player_combat_entity = self._convert_character_to_combat_entity(player_character)
            
            # Create combat instance
            self.active_combat = Combat()
            self.active_combat.initialize_combat(
                player_entities=[player_combat_entity],
                enemy_entities=enemies
            )
            
            logger.info(f"Started combat with {len(enemies)} enemies")
            
            # Publish combat started event
            self.event_bus.publish("combat_started", {
                "combat": self.active_combat,
                "player": player_combat_entity,
                "enemies": enemies
            })
            
            return self.active_combat
            
        except Exception as e:
            logger.error(f"Error starting combat: {e}", exc_info=True)
            return None
    
    def end_combat(self, result="defeat"):
        """
        End the current combat encounter.
        
        Args:
            result: Result of combat ("victory", "defeat", "flee")
        """
        if not self.active_combat:
            return
            
        try:
            # Calculate rewards if victorious
            rewards = {}
            if result == "victory":
                rewards = self._calculate_rewards()
            
            # Publish combat ended event
            self.event_bus.publish("combat_ended", {
                "result": result,
                "rewards": rewards
            })
            
            # Clear active combat
            self.active_combat = None
            self.turn_in_progress = False
            
            logger.info(f"Combat ended with result: {result}")
            
        except Exception as e:
            logger.error(f"Error ending combat: {e}", exc_info=True)
    
    def update(self, dt):
        """
        Update combat state.
        
        Args:
            dt: Time delta in seconds
        """
        if not self.active_combat:
            return
            
        try:
            # Check for combat completion
            if self.active_combat.is_combat_over():
                result = "victory" if self.active_combat.is_player_victorious() else "defeat"
                self.end_combat(result)
                return
                
            # Process AI turns if it's enemy turn
            if (not self.turn_in_progress and 
                self.active_combat.current_turn and 
                not self.active_combat.is_player_turn()):
                
                self._process_enemy_turn()
                
        except Exception as e:
            logger.error(f"Error updating combat: {e}", exc_info=True)
    
    def _handle_combat_action(self, data):
        """
        Handle combat_action event.
        
        Args:
            data: Event data with action type and parameters
        """
        if not self.active_combat or not self.active_combat.is_player_turn():
            return
            
        try:
            action_type = data.get("type")
            
            if action_type == "attack":
                self._handle_attack_action(data)
            elif action_type == "skill":
                self._handle_skill_action(data)
            elif action_type == "item":
                self._handle_item_action(data)
            elif action_type == "defend":
                self._handle_defend_action()
            elif action_type == "flee":
                self._handle_flee_action()
                
        except Exception as e:
            logger.error(f"Error handling combat action: {e}", exc_info=True)
    
    def _convert_character_to_combat_entity(self, character):
        """
        Convert a Character to a combat entity.
        
        Args:
            character: Character instance from character system
            
        Returns:
            PlayerCharacter instance for combat
        """
        if not character:
            # Create a default character if none provided
            logger.warning("No character provided, creating default")
            return PlayerCharacter(
                name="Hero",
                character_class="warrior",
                level=1
            )
            
        # Check if character is already a dict (from save data)
        if isinstance(character, dict):
            name = character.get("name", "Hero")
            character_class = character.get("class", "warrior")
            level = character.get("level", 1)
            
            # Create player combat entity
            player_entity = PlayerCharacter(
                name=name,
                character_class=character_class,
                level=level
            )
            
            return player_entity
        
        # If it's a Character object
        try:
            # Create player combat entity
            player_entity = PlayerCharacter(
                name=character.name,
                character_class=getattr(character, "character_class", "warrior"),
                level=getattr(character, "level", 1)
            )
            
            return player_entity
        except Exception as e:
            logger.error(f"Error converting character to combat entity: {e}", exc_info=True)
            return PlayerCharacter(
                name="Hero",
                character_class="warrior",
                level=1
            )
    
    def _process_enemy_turn(self):
        """Process enemy turn using AI."""
        if not self.active_combat:
            return
            
        # Mark turn in progress to prevent multiple calls
        self.turn_in_progress = True
        
        try:
            enemy = self.active_combat.get_current_entity()
            if not enemy:
                self.active_combat.next_turn()
                self.turn_in_progress = False
                return
                
            # Simple AI for enemy actions
            import random
            
            # Get player entities as targets
            player_entities = self.active_combat.get_player_entities()
            if not player_entities:
                self.active_combat.next_turn()
                self.turn_in_progress = False
                return
                
            # Choose a random player target
            target = random.choice(player_entities)
            
            # 70% chance to attack, 30% chance to defend
            if random.random() < 0.7:
                # Attack
                damage = enemy.attack(target)
                
                # Publish enemy action event
                self.event_bus.publish("enemy_action", {
                    "type": "attack",
                    "enemy": enemy,
                    "target": target,
                    "damage": damage
                })
            else:
                # Defend
                enemy.defend()
                
                # Publish enemy action event
                self.event_bus.publish("enemy_action", {
                    "type": "defend",
                    "enemy": enemy
                })
            
            # End turn after small delay
            # In a real implementation, you might use a timer here
            self.active_combat.next_turn()
            
        except Exception as e:
            logger.error(f"Error processing enemy turn: {e}", exc_info=True)
            
        finally:
            # End turn in progress
            self.turn_in_progress = False
    
    def _handle_attack_action(self, data):
        """Handle basic attack action."""
        if not self.active_combat:
            return
            
        target_index = data.get("target", 0)
        targets = self.active_combat.get_enemy_entities()
        
        if 0 <= target_index < len(targets):
            player = self.active_combat.get_current_entity()
            target = targets[target_index]
            
            # Process attack
            damage = player.attack(target)
            
            # Publish attack result
            self.event_bus.publish("attack_result", {
                "attacker": player,
                "target": target,
                "damage": damage
            })
            
            # End turn
            self.active_combat.next_turn()
    
    def _handle_skill_action(self, data):
        """Handle skill usage action."""
        if not self.active_combat:
            return
            
        skill_index = data.get("skill", 0)
        target_indices = data.get("targets", [0])
        
        player = self.active_combat.get_current_entity()
        
        # Get skill and targets
        if hasattr(player, "skills") and player.skills and 0 <= skill_index < len(player.skills):
            skill = player.skills[skill_index]
            
            all_targets = self.active_combat.get_enemy_entities()
            targets = [all_targets[i] for i in target_indices if 0 <= i < len(all_targets)]
            
            if targets:
                # Use skill
                result = player.use_skill(skill, targets)
                
                # Publish skill result
                self.event_bus.publish("skill_result", {
                    "user": player,
                    "skill": skill,
                    "targets": targets,
                    "result": result
                })
                
                # End turn
                self.active_combat.next_turn()
    
    def _handle_item_action(self, data):
        """Handle item usage action."""
        # Placeholder for item handling
        self.active_combat.next_turn()
    
    def _handle_defend_action(self):
        """Handle defend action."""
        if not self.active_combat:
            return
            
        player = self.active_combat.get_current_entity()
        
        # Apply defend effect
        player.defend()
        
        # Publish defend action
        self.event_bus.publish("defend_action", {
            "entity": player
        })
        
        # End turn
        self.active_combat.next_turn()
    
    def _handle_flee_action(self):
        """Handle flee action."""
        if not self.active_combat:
            return
            
        # Calculate flee success chance
        import random
        success = random.random() < 0.5  # 50% chance to flee
        
        if success:
            # Successfully fled
            self.event_bus.publish("flee_result", {
                "success": True
            })
            
            # End combat with flee result
            self.end_combat("flee")
        else:
            # Failed to flee
            self.event_bus.publish("flee_result", {
                "success": False
            })
            
            # End turn
            self.active_combat.next_turn()
    
    def _calculate_rewards(self):
        """Calculate rewards for winning combat."""
        if not self.active_combat:
            return {}
            
        # Simple reward calculation
        enemy_count = len(self.active_combat.get_enemy_entities())
        
        # Experience
        total_xp = enemy_count * 50
        
        # Gold
        total_gold = enemy_count * 25
        
        # Items (placeholder)
        items = []
        
        return {
            "experience": total_xp,
            "gold": total_gold,
            "items": items
        }

class CombatAI:
    """AI controller for combat entities"""
    
    def __init__(self, difficulty="normal"):
        """
        Initialize combat AI.
        
        Args:
            difficulty: AI difficulty setting (easy, normal, hard)
        """
        self.difficulty = difficulty
        
        # Thresholds for decision making
        if difficulty == "easy":
            self.low_health_threshold = 0.2  # 20% of max health
            self.medium_health_threshold = 0.5  # 50% of max health
            self.skill_use_chance = 0.5  # 50% chance to use skills
            self.target_weakest_chance = 0.3  # 30% chance to target weakest
            self.buff_ally_chance = 0.3  # 30% chance to buff allies
            self.flee_threshold = 0.1  # Flee at 10% health
        elif difficulty == "hard":
            self.low_health_threshold = 0.3  # 30% of max health
            self.medium_health_threshold = 0.6  # 60% of max health
            self.skill_use_chance = 0.8  # 80% chance to use skills
            self.target_weakest_chance = 0.8  # 80% chance to target weakest
            self.buff_ally_chance = 0.7  # 70% chance to buff allies
            self.flee_threshold = 0.0  # Never flee
        else:  # normal
            self.low_health_threshold = 0.25  # 25% of max health
            self.medium_health_threshold = 0.5  # 50% of max health
            self.skill_use_chance = 0.7  # 70% chance to use skills
            self.target_weakest_chance = 0.5  # 50% chance to target weakest
            self.buff_ally_chance = 0.5  # 50% chance to buff allies
            self.flee_threshold = 0.05  # Flee at 5% health
    
    def choose_action(self, entity, combat):
        """
        Choose an action for the entity.
        
        Args:
            entity: Entity taking the action
            combat: Combat instance
            
        Returns:
            Dict with action information
        """
        # Get available targets
        enemy_targets = combat.turn_manager.get_targets(entity, "enemy")
        ally_targets = combat.turn_manager.get_targets(entity, "ally")
        
        # Check health status
        health_ratio = entity.health / entity.max_health
        
        # Attempt to flee if health is critically low (non-boss enemies only)
        if (health_ratio <= self.flee_threshold and 
            not combat.is_boss_fight and 
            random.random() < 0.7):  # 70% chance to attempt flee when low
            return {
                'action': 'flee',
                'target': None
            }
        
        # Decide whether to heal
        if health_ratio <= self.low_health_threshold:
            # Try to use a healing item or skill
            healing_action = self._choose_healing_action(entity, [entity])
            if healing_action:
                return healing_action
        
        # Check if any allies need healing (only if we have healing capabilities)
        has_healing = any(isinstance(s, HealingSkill) for s in entity.skills)
        if has_healing and ally_targets:
            # Find critically wounded allies
            wounded_allies = [a for a in ally_targets 
                             if a.health / a.max_health <= self.low_health_threshold]
            
            if wounded_allies:
                healing_action = self._choose_healing_action(entity, wounded_allies)
                if healing_action:
                    return healing_action
        
        # Consider using buff skills on self or allies
        if random.random() < self.buff_ally_chance:
            buff_action = self._choose_buff_action(entity, [entity] + ally_targets)
            if buff_action:
                return buff_action
        
        # Consider using debuff skills on enemies
        debuff_action = self._choose_debuff_action(entity, enemy_targets)
        if debuff_action:
            return debuff_action
        
        # Consider using damage skills on enemies
        if enemy_targets and random.random() < self.skill_use_chance:
            damage_action = self._choose_damage_action(entity, enemy_targets)
            if damage_action:
                return damage_action
        
        # Default to basic attack if enemies exist
        if enemy_targets:
            # Choose target - either random or strategic based on difficulty
            target = self._choose_attack_target(entity, enemy_targets)
            
            return {
                'action': 'attack',
                'target': target
            }
        
        # If no enemies, defend
        return {
            'action': 'defend',
            'target': None
        }
    
    def _choose_healing_action(self, entity, potential_targets):
        """Choose a healing action if available"""
        # Check for healing skills
        healing_skills = [s for s in entity.skills 
                         if isinstance(s, HealingSkill) 
                         and s.current_cooldown == 0
                         and s.mana_cost <= entity.mana]
        
        if healing_skills:
            # Sort targets by health percentage (lowest first)
            sorted_targets = sorted(potential_targets, 
                                   key=lambda t: t.health / t.max_health)
            
            # Choose most wounded target
            target = sorted_targets[0]
            
            # Only heal if target is below medium health threshold
            if target.health / target.max_health <= self.medium_health_threshold:
                # Choose most powerful healing skill that won't overheal too much
                chosen_skill = max(healing_skills, key=lambda s: s.power)
                
                return {
                    'action': 'skill',
                    'skill': chosen_skill,
                    'target': target
                }
        
        # No suitable healing action
        return None
    
    def _choose_buff_action(self, entity, potential_targets):
        """Choose a buff action if available"""
        # Check for buff skills
        buff_skills = [s for s in entity.skills 
                      if isinstance(s, BuffSkill) 
                      and s.current_cooldown == 0
                      and s.mana_cost <= entity.mana]
        
        if buff_skills and random.random() < self.buff_ally_chance:
            # Choose a random buff skill
            skill = random.choice(buff_skills)
            
            # Choose appropriate target based on buff type
            if skill.effect_type in [StatusEffect.STRENGTHENED, StatusEffect.HASTED]:
                # Offensive buffs go to highest damage dealers
                sorted_targets = sorted(potential_targets, 
                                       key=lambda t: t.physical_attack + t.magical_attack,
                                       reverse=True)
            elif skill.effect_type == StatusEffect.PROTECTED:
                # Defensive buffs go to lowest health or tanks
                sorted_targets = sorted(potential_targets, 
                                       key=lambda t: t.health / t.max_health)
            else:
                # Other buffs - random target
                sorted_targets = list(potential_targets)
                random.shuffle(sorted_targets)
            
            if sorted_targets:
                target = sorted_targets[0]
                
                # Check if target already has this buff
                already_has_buff = any(effect.effect_type == skill.effect_type 
                                      for effect in target.status_effects)
                
                if not already_has_buff:
                    return {
                        'action': 'skill',
                        'skill': skill,
                        'target': target
                    }
        
        # No suitable buff action
        return None
    
    def _choose_debuff_action(self, entity, potential_targets):
        """Choose a debuff action if available"""
        # Check for debuff skills
        debuff_skills = [s for s in entity.skills 
                        if isinstance(s, DebuffSkill) 
                        and s.current_cooldown == 0
                        and s.mana_cost <= entity.mana]
        
        if debuff_skills and potential_targets and random.random() < self.skill_use_chance:
            # Choose a random debuff skill
            skill = random.choice(debuff_skills)
            
            # Choose appropriate target based on debuff type
            if skill.effect_type in [StatusEffect.WEAKENED, StatusEffect.SLOWED]:
                # Weakening debuffs go to highest damage dealers
                sorted_targets = sorted(potential_targets, 
                                       key=lambda t: t.physical_attack + t.magical_attack,
                                       reverse=True)
            elif skill.effect_type in [StatusEffect.STUNNED, StatusEffect.CONFUSED]:
                # Control debuffs prioritize dangerous targets
                sorted_targets = sorted(potential_targets,
                                       key=lambda t: t.speed * (t.physical_attack + t.magical_attack),
                                       reverse=True)
            else:
                # Other debuffs (like DOTs) - prioritize low health
                sorted_targets = sorted(potential_targets, 
                                       key=lambda t: t.health)
            
            if sorted_targets:
                target = sorted_targets[0]
                
                # Check if target already has this debuff
                already_has_debuff = any(effect.effect_type == skill.effect_type 
                                        for effect in target.status_effects)
                
                if not already_has_debuff:
                    return {
                        'action': 'skill',
                        'skill': skill,
                        'target': target
                    }
        
        # No suitable debuff action
        return None
    
    def _choose_damage_action(self, entity, potential_targets):
        """Choose a damage action if available"""
        # Check for damage skills
        damage_skills = [s for s in entity.skills 
                        if isinstance(s, DamageSkill) 
                        and s.current_cooldown == 0
                        and s.mana_cost <= entity.mana]
        
        if damage_skills and random.random() < self.skill_use_chance:
            # Choose skill based on target vulnerabilities or just highest power
            target = self._choose_attack_target(entity, potential_targets)
            
            # Find skill that targets a vulnerability if possible
            best_skill = None
            best_score = 0
            
            for skill in damage_skills:
                score = skill.power  # Base score is power
                
                # Bonus if target has weakness to this damage type
                resistance = target.get_resistance(skill.damage_type)
                if resistance < 0:  # Negative resistance means vulnerability
                    score += 50 * abs(resistance) / 100  # Boost score based on vulnerability
                elif resistance > 50:  # High resistance
                    score -= 50 * resistance / 100  # Lower score for resistant targets
                
                if score > best_score:
                    best_score = score
                    best_skill = skill
            
            if best_skill:
                return {
                    'action': 'skill',
                    'skill': best_skill,
                    'target': target
                }
        
        # No suitable damage skill action
        return None
    
    def _choose_attack_target(self, entity, potential_targets):
        """Choose a target for attack"""
        if not potential_targets:
            return None
        
        # Possibly target the weakest enemy
        if random.random() < self.target_weakest_chance:
            # Sort by health (lowest first)
            sorted_targets = sorted(potential_targets, 
                                   key=lambda t: t.health)
            return sorted_targets[0]
        else:
            # Random target
            return random.choice(potential_targets)
    
    def execute_action(self, action_data, entity, combat):
        """
        Execute the chosen action.
        
        Args:
            action_data: Action information dict
            entity: Entity taking the action
            combat: Combat instance
            
        Returns:
            Action result data
        """
        action_type = action_data['action']
        
        if action_type == 'attack':
            # Basic attack
            return entity.attack(action_data['target'])
        
        elif action_type == 'skill':
            # Use skill
            skill = action_data['skill']
            if isinstance(action_data['target'], list):
                targets = action_data['target']
            else:
                targets = [action_data['target']]
            
            return entity.use_skill(skill, targets)
        
        elif action_type == 'item':
            # Use item
            item = action_data['item']
            if isinstance(action_data['target'], list):
                targets = action_data['target']
            else:
                targets = [action_data['target']]
            
            return entity.use_item(item, targets)
        
        elif action_type == 'defend':
            # Defend
            return entity.defend()
        
        elif action_type == 'flee':
            # Attempt to flee
            return entity.flee(combat)
        
        # Unknown action type
        return {'success': False, 'message': f"Unknown action type: {action_type}"}


class BossAI(CombatAI):
    """Specialized AI for boss entities"""
    
    def __init__(self, boss_type="generic"):
        """
        Initialize boss AI.
        
        Args:
            boss_type: Type of boss (affects behavior patterns)
        """
        super().__init__("hard")  # Boss AI is always hard difficulty
        self.boss_type = boss_type
        self.phase = 1  # Boss fight phase
        self.turns_in_phase = 0
        self.max_phase = 3  # Most bosses have 3 phases
        
        # Override thresholds
        self.low_health_threshold = 0.3  # Higher threshold for healing
        self.medium_health_threshold = 0.6
        self.skill_use_chance = 0.9  # More likely to use skills
        self.target_weakest_chance = 0.7  # More likely to target weak players
        self.buff_ally_chance = 0.8  # More likely to buff allies/minions
        self.flee_threshold = 0.0  # Bosses never flee
        
        # Phase transition thresholds (percentage of max health)
        self.phase_transitions = [0.7, 0.3]  # Phase 1 -> 2 at 70%, Phase 2 -> 3 at 30%
        
        # Special attack counter
        self.turns_since_special = 0
        self.special_attack_frequency = 3  # Use special attack every 3 turns
    
    def choose_action(self, entity, combat):
        """
        Choose an action for the boss entity.
        
        Args:
            entity: Boss entity taking the action
            combat: Combat instance
            
        Returns:
            Dict with action information
        """
        # Update phase based on health percentage
        health_ratio = entity.health / entity.max_health
        
        # Check for phase transition
        current_phase = self.phase
        for i, threshold in enumerate(self.phase_transitions, 1):
            if health_ratio <= threshold and current_phase <= i:
                self.phase = i + 1
                self.turns_in_phase = 0
                
                # Phase transition action (like a special attack or buff)
                phase_action = self._phase_transition_action(entity, combat)
                if phase_action:
                    return phase_action
        
        # Increment phase counters
        self.turns_in_phase += 1
        self.turns_since_special += 1
        
        # Check if it's time for a special attack
        if self.turns_since_special >= self.special_attack_frequency:
            special_action = self._special_attack(entity, combat)
            if special_action:
                self.turns_since_special = 0
                return special_action
        
        # Get available targets
        enemy_targets = combat.turn_manager.get_targets(entity, "enemy")
        ally_targets = combat.turn_manager.get_targets(entity, "ally")
        
        # Boss behavior based on type
        if self.boss_type == "berserker":
            return self._berserker_behavior(entity, combat, enemy_targets, ally_targets)
        elif self.boss_type == "mage":
            return self._mage_behavior(entity, combat, enemy_targets, ally_targets)
        elif self.boss_type == "summoner":
            return self._summoner_behavior(entity, combat, enemy_targets, ally_targets)
        else:
            # Generic boss behavior - prioritize high-damage attacks
            
            # First, check if we need to heal
            if health_ratio <= self.low_health_threshold:
                healing_action = self._choose_healing_action(entity, [entity])
                if healing_action:
                    return healing_action
            
            # Then, consider buffs on self
            buff_action = self._choose_buff_action(entity, [entity])
            if buff_action:
                return buff_action
            
            # Then, consider debuffs on strongest enemy
            debuff_action = self._choose_debuff_action(entity, enemy_targets)
            if debuff_action:
                return debuff_action
            
            # Use damage skills frequently
            damage_action = self._choose_damage_action(entity, enemy_targets)
            if damage_action:
                return damage_action
            
            # Default to basic attack
            target = self._choose_attack_target(entity, enemy_targets)
            return {
                'action': 'attack',
                'target': target
            }
    
    def _phase_transition_action(self, entity, combat):
        """Generate a special action for phase transition"""
        # Get available targets
        enemy_targets = combat.turn_manager.get_targets(entity, "enemy")
        ally_targets = combat.turn_manager.get_targets(entity, "ally")
        
        if self.phase == 2:
            # Phase 1 -> 2 transition
            # Buff self with increased damage or protection
            buff_skills = [s for s in entity.skills 
                          if isinstance(s, BuffSkill) 
                          and s.current_cooldown == 0
                          and s.effect_type in [StatusEffect.STRENGTHENED, StatusEffect.PROTECTED]]
            
            if buff_skills:
                skill = buff_skills[0]
                return {
                    'action': 'skill',
                    'skill': skill,
                    'target': entity
                }
            
            # If no buff skills, do an AOE attack if possible
            aoe_skills = [s for s in entity.skills 
                         if isinstance(s, DamageSkill) 
                         and s.current_cooldown == 0
                         and s.target_type == "all_enemies"]
            
            if aoe_skills and enemy_targets:
                skill = aoe_skills[0]
                return {
                    'action': 'skill',
                    'skill': skill,
                    'target': enemy_targets
                }
        
        elif self.phase == 3:
            # Phase 2 -> 3 transition (final phase)
            # Go all out with strongest attacks
            # Try to use the most powerful damage skill
            damage_skills = [s for s in entity.skills 
                            if isinstance(s, DamageSkill) 
                            and s.current_cooldown == 0]
            
            if damage_skills and enemy_targets:
                # Use the highest power skill
                skill = max(damage_skills, key=lambda s: s.power)
                
                # Target the weakest enemy for maximum effect
                target = min(enemy_targets, key=lambda t: t.health)
                
                return {
                    'action': 'skill',
                    'skill': skill,
                    'target': target
                }
        
        # No special transition action available
        return None
    
    def _special_attack(self, entity, combat):
        """Execute a special attack based on boss type and phase"""
        # Get available targets
        enemy_targets = combat.turn_manager.get_targets(entity, "enemy")
        
        if not enemy_targets:
            return None
        
        # Find skills that could be considered "special"
        # These are typically high damage skills or skills with status effects
        special_skills = [s for s in entity.skills 
                         if s.current_cooldown == 0 
                         and s.mana_cost <= entity.mana
                         and ((isinstance(s, DamageSkill) and s.power >= 150) or
                              isinstance(s, DebuffSkill))]
        
        if not special_skills:
            return None
        
        # Choose skill based on boss type and phase
        if self.boss_type == "berserker":
            # Berserker prefers high damage single target skills
            damage_skills = [s for s in special_skills if isinstance(s, DamageSkill)]
            if damage_skills:
                skill = max(damage_skills, key=lambda s: s.power)
                target = self._choose_attack_target(entity, enemy_targets)
                return {
                    'action': 'skill',
                    'skill': skill,
                    'target': target
                }
        
        elif self.boss_type == "mage":
            # Mage prefers debuffs or elemental damage
            elemental_skills = [s for s in special_skills 
                              if isinstance(s, DamageSkill) and 
                              s.damage_type in [DamageType.FIRE, DamageType.ICE, DamageType.LIGHTNING]]
            
            if elemental_skills:
                skill = random.choice(elemental_skills)
                target = self._choose_attack_target(entity, enemy_targets)
                return {
                    'action': 'skill',
                    'skill': skill,
                    'target': target
                }
            
            # If no elemental skills, try debuffs
            debuff_skills = [s for s in special_skills if isinstance(s, DebuffSkill)]
            if debuff_skills:
                skill = random.choice(debuff_skills)
                # Target the strongest enemy for debuffs
                target = max(enemy_targets, 
                           key=lambda t: t.physical_attack + t.magical_attack)
                return {
                    'action': 'skill',
                    'skill': skill,
                    'target': target
                }
        
        # Default: choose a random special skill
        skill = random.choice(special_skills)
        target = self._choose_attack_target(entity, enemy_targets)
        
        return {
            'action': 'skill',
            'skill': skill,
            'target': target
        }
    
    def _berserker_behavior(self, entity, combat, enemy_targets, ally_targets):
        """Berserker boss behavior"""
        # Berserkers focus on high damage and get stronger as health decreases
        health_ratio = entity.health / entity.max_health
        
        # Chance to buff self increases as health decreases
        buff_chance = self.buff_ally_chance + (1 - health_ratio) * 0.5
        
        if random.random() < buff_chance:
            # Try to use strength buff
            buff_skills = [s for s in entity.skills 
                          if isinstance(s, BuffSkill) 
                          and s.current_cooldown == 0
                          and s.effect_type == StatusEffect.STRENGTHENED]
            
            if buff_skills:
                skill = buff_skills[0]
                return {
                    'action': 'skill',
                    'skill': skill,
                    'target': entity
                }
        
        # Always prefer high damage skills
        damage_skills = [s for s in entity.skills 
                        if isinstance(s, DamageSkill) 
                        and s.current_cooldown == 0
                        and s.mana_cost <= entity.mana]
        
        if damage_skills and enemy_targets:
            # Sort by power
            damage_skills.sort(key=lambda s: s.power, reverse=True)
            
            # Use highest power skill
            skill = damage_skills[0]
            target = self._choose_attack_target(entity, enemy_targets)
            
            return {
                'action': 'skill',
                'skill': skill,
                'target': target
            }
        
        # Default to basic attack
        if enemy_targets:
            target = self._choose_attack_target(entity, enemy_targets)
            return {
                'action': 'attack',
                'target': target
            }
        
        # Defend if no targets
        return {
            'action': 'defend',
            'target': None
        }
    
    def _mage_behavior(self, entity, combat, enemy_targets, ally_targets):
        """Mage boss behavior"""
        # Mages focus on magical attacks and status effects
        health_ratio = entity.health / entity.max_health
        
        # First, check if we need to heal
        if health_ratio <= self.low_health_threshold:
            healing_action = self._choose_healing_action(entity, [entity])
            if healing_action:
                return healing_action
        
        # Consider using debuffs
        if random.random() < 0.6:  # 60% chance to try debuff
            debuff_action = self._choose_debuff_action(entity, enemy_targets)
            if debuff_action:
                return debuff_action
        
        # Prefer elemental damage skills
        elemental_skills = [s for s in entity.skills 
                          if isinstance(s, DamageSkill) 
                          and s.current_cooldown == 0
                          and s.mana_cost <= entity.mana
                          and s.damage_type in [DamageType.FIRE, DamageType.ICE, DamageType.LIGHTNING]]
        
        if elemental_skills and enemy_targets:
            # Try to choose a skill that targets an enemy weakness
            best_skill = None
            best_target = None
            best_score = 0
            
            for target in enemy_targets:
                for skill in elemental_skills:
                    # Calculate effectiveness score
                    resistance = target.get_resistance(skill.damage_type)
                    score = skill.power * (2.0 - resistance / 100.0)
                    
                    if score > best_score:
                        best_score = score
                        best_skill = skill
                        best_target = target
            
            if best_skill and best_target:
                return {
                    'action': 'skill',
                    'skill': best_skill,
                    'target': best_target
                }
        
        # Default to any damage skill
        damage_action = self._choose_damage_action(entity, enemy_targets)
        if damage_action:
            return damage_action
        
        # Default to basic attack
        if enemy_targets:
            target = self._choose_attack_target(entity, enemy_targets)
            return {
                'action': 'attack',
                'target': target
            }
        
        # Defend if no targets
        return {
            'action': 'defend',
            'target': None
        }
    
    def _summoner_behavior(self, entity, combat, enemy_targets, ally_targets):
        """Summoner boss behavior"""
        # Summoners focus on buffing allies and debuffing enemies
        health_ratio = entity.health / entity.max_health
        
        # Check if we have minions
        has_minions = len(ally_targets) > 0
        
        # TODO: Implement minion summoning when we add that capability
        # For now, focus on buffing existing allies or debuffing enemies
        
        # Buff allies if we have them
        if has_minions and random.random() < 0.7:  # 70% chance to buff allies
            buff_skills = [s for s in entity.skills 
                          if isinstance(s, BuffSkill) 
                          and s.current_cooldown == 0
                          and s.mana_cost <= entity.mana]
            
            if buff_skills:
                skill = random.choice(buff_skills)
                # Choose ally with highest damage potential
                target = max(ally_targets, 
                           key=lambda a: a.physical_attack + a.magical_attack)
                
                return {
                    'action': 'skill',
                    'skill': skill,
                    'target': target
                }
        
        # Debuff enemies
        if enemy_targets and random.random() < 0.6:  # 60% chance to debuff
            debuff_action = self._choose_debuff_action(entity, enemy_targets)
            if debuff_action:
                return debuff_action
        
        # Use damage skills as fallback
        damage_action = self._choose_damage_action(entity, enemy_targets)
        if damage_action:
            return damage_action
        
        # Default to basic attack
        if enemy_targets:
            target = self._choose_attack_target(entity, enemy_targets)
            return {
                'action': 'attack',
                'target': target
            }
        
        # Defend if no targets
        return {
            'action': 'defend',
            'target': None
        }
