import random
import logging
import math
from enum import Enum

logger = logging.getLogger("combat_system")

class CombatAction(Enum):
    """Types of actions that can be taken in combat."""
    ATTACK = 0
    SKILL = 1
    ITEM = 2
    DEFEND = 3
    FLEE = 4

class DamageType(Enum):
    """Types of damage that can be dealt in combat."""
    PHYSICAL = 0
    MAGICAL = 1
    FIRE = 2
    ICE = 3
    LIGHTNING = 4
    POISON = 5
    TRUE = 6  # Ignores resistances

class StatusEffect(Enum):
    """Status effects that can be applied in combat."""
    POISONED = 0      # Damage over time
    BURNED = 1        # Damage over time
    FROZEN = 2        # Reduced speed
    STUNNED = 3       # Skip turn
    BLEEDING = 4      # Damage over time
    WEAKENED = 5      # Reduced damage
    STRENGTHENED = 6  # Increased damage
    PROTECTED = 7     # Reduced damage taken
    HASTED = 8        # Increased speed
    SLOWED = 9        # Reduced speed
    CONFUSED = 10     # Random target
    CHARMED = 11      # Attack allies

class StatusEffectInstance:
    """Instance of a status effect with duration and potency."""
    
    def __init__(self, effect_type, duration, potency=1.0, source=None):
        """
        Initialize a status effect instance.
        
        Args:
            effect_type: Type from StatusEffect enum
            duration: Effect duration in turns
            potency: Effect strength multiplier
            source: Source of the effect (entity or skill)
        """
        self.effect_type = effect_type
        self.duration = duration
        self.potency = potency
        self.source = source
    
    def update(self):
        """
        Update effect for a new turn.
        
        Returns:
            Boolean indicating if effect is still active
        """
        self.duration -= 1
        return self.duration > 0
    
    def to_dict(self):
        """Convert to dictionary for serialization."""
        return {
            'effect_type': self.effect_type.value,
            'duration': self.duration,
            'potency': self.potency,
            'source': str(self.source) if self.source else None
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create from dictionary."""
        return cls(
            StatusEffect(data['effect_type']),
            data['duration'],
            data['potency'],
            data['source']
        )

class CombatEntity:
    """Base class for entities in combat (characters, monsters, etc.)."""
    
    def __init__(self, name, level=1, team=0):
        """
        Initialize a combat entity.
        
        Args:
            name: Entity name
            level: Entity level
            team: Team identifier (0=player, 1=enemy, 2=neutral)
        """
        self.name = name
        self.level = level
        self.team = team
        
        # Base stats
        self.max_health = 100
        self.health = 100
        self.max_mana = 50
        self.mana = 50
        self.strength = 10
        self.intelligence = 10
        self.dexterity = 10
        self.constitution = 10
        self.speed = 10
        
        # Derived stats
        self.physical_attack = 10
        self.magical_attack = 10
        self.physical_defense = 10
        self.magical_defense = 10
        self.hit_chance = 90
        self.evasion = 10
        self.critical_chance = 5
        self.critical_damage = 150  # Percentage
        
        # Resistances (percentage reduction)
        self.resistances = {
            DamageType.PHYSICAL: 0,
            DamageType.MAGICAL: 0,
            DamageType.FIRE: 0,
            DamageType.ICE: 0,
            DamageType.LIGHTNING: 0,
            DamageType.POISON: 0
        }
        
        # Combat state
        self.status_effects = []
        self.defending = False
        self.turn_meter = 0
        self.is_dead = False
        
        # Skills and abilities
        self.skills = []
        self.innate_abilities = []
        
        self._update_derived_stats()
    
    def _update_derived_stats(self):
        """Update derived stats based on base stats."""
        # Physical attack based on strength
        self.physical_attack = self.strength * 1.5
        
        # Magical attack based on intelligence
        self.magical_attack = self.intelligence * 1.5
        
        # Physical defense based on constitution
        self.physical_defense = self.constitution * 1.0
        
        # Magical defense based on intelligence
        self.magical_defense = self.intelligence * 0.5
        
        # Hit chance based on dexterity
        self.hit_chance = 80 + (self.dexterity * 0.5)
        
        # Evasion based on dexterity
        self.evasion = self.dexterity * 0.5
        
        # Critical chance based on dexterity
        self.critical_chance = 5 + (self.dexterity * 0.2)
        
        # Maximum health based on constitution
        self.max_health = 50 + (self.constitution * 10) + (self.level * 10)
        
        # Maximum mana based on intelligence
        self.max_mana = 20 + (self.intelligence * 5) + (self.level * 5)
    
    def take_damage(self, amount, damage_type=DamageType.PHYSICAL, critical=False, attacker=None):
        """
        Apply damage to this entity.
        
        Args:
            amount: Base damage amount
            damage_type: Type of damage from DamageType enum
            critical: Whether this is a critical hit
            attacker: Entity dealing the damage
            
        Returns:
            Dict with damage info (amount, critical, etc.)
        """
        # Check if dead
        if self.is_dead:
            return {'damage': 0, 'critical': False, 'blocked': False, 'status_effects': []}
        
        # Apply damage modifiers
        damage = amount
        
        # Apply resistance (except for true damage)
        if damage_type != DamageType.TRUE:
            resistance = self.get_resistance(damage_type)
            damage *= (1 - resistance / 100)
        
        # Apply defense
        if damage_type == DamageType.PHYSICAL:
            damage = max(1, damage - self.physical_defense * 0.5)
        elif damage_type in [DamageType.MAGICAL, DamageType.FIRE, DamageType.ICE, DamageType.LIGHTNING]:
            damage = max(1, damage - self.magical_defense * 0.5)
        
        # Apply status effects
        for effect in self.status_effects:
            if effect.effect_type == StatusEffect.PROTECTED:
                damage *= max(0.5, 1.0 - (effect.potency * 0.2))  # 20% reduction per potency
        
        # Apply critical multiplier
        if critical:
            damage *= self.critical_damage / 100
        
        # Apply defending
        blocked = False
        if self.defending:
            damage *= 0.5
            blocked = True
            self.defending = False  # Reset defending status
        
        # Round to integer
        final_damage = max(1, int(damage))
        
        # Apply damage
        self.health = max(0, self.health - final_damage)
        
        # Check if dead
        if self.health <= 0:
            self.is_dead = True
            self.health = 0
        
        # Apply potential status effects
        applied_effects = []
        if attacker:
            # For example, weapons that cause bleeding or poison
            pass
        
        # Log damage
        logger.debug(f"{self.name} took {final_damage} {damage_type.name} damage" + 
                    f"{' (CRITICAL)' if critical else ''}" +
                    f"{' (BLOCKED)' if blocked else ''}")
        
        return {
            'damage': final_damage,
            'critical': critical,
            'blocked': blocked,
            'status_effects': applied_effects
        }
    
    def heal(self, amount, healer=None):
        """
        Heal this entity.
        
        Args:
            amount: Healing amount
            healer: Entity providing the healing
            
        Returns:
            Actual amount healed
        """
        # Check if dead
        if self.is_dead:
            return 0
        
        # Calculate healing
        old_health = self.health
        self.health = min(self.max_health, self.health + amount)
        actual_heal = self.health - old_health
        
        # Log healing
        if actual_heal > 0:
            healer_name = healer.name if healer else "Unknown"
            logger.debug(f"{self.name} healed for {actual_heal} by {healer_name}")
        
        return actual_heal
    
    def add_status_effect(self, effect):
        """
        Add a status effect to this entity.
        
        Args:
            effect: StatusEffectInstance to add
            
        Returns:
            Boolean indicating if effect was added
        """
        # Check if dead
        if self.is_dead:
            return False
        
        # Check if already has this effect, refresh duration if so
        for existing in self.status_effects:
            if existing.effect_type == effect.effect_type:
                # Take the longer duration
                existing.duration = max(existing.duration, effect.duration)
                # Take the higher potency
                existing.potency = max(existing.potency, effect.potency)
                return False
        
        # Add new effect
        self.status_effects.append(effect)
        
        # Log effect
        logger.debug(f"{self.name} gained status effect: {effect.effect_type.name} " +
                    f"for {effect.duration} turns at {effect.potency} potency")
        
        return True
    
    def remove_status_effect(self, effect_type):
        """
        Remove a status effect from this entity.
        
        Args:
            effect_type: StatusEffect enum value to remove
            
        Returns:
            Boolean indicating if effect was removed
        """
        for i, effect in enumerate(self.status_effects):
            if effect.effect_type == effect_type:
                self.status_effects.pop(i)
                logger.debug(f"Removed {effect_type.name} from {self.name}")
                return True
        
        return False
    
    def update_status_effects(self):
        """
        Update status effects for a new turn.
        
        Returns:
            List of effects that were applied/triggered
        """
        # Skip if dead
        if self.is_dead:
            return []
        
        triggered_effects = []
        remaining_effects = []
        
        for effect in self.status_effects:
            # Apply effect
            if effect.effect_type == StatusEffect.POISONED:
                damage = int(self.max_health * 0.05 * effect.potency)
                self.health = max(0, self.health - damage)
                triggered_effects.append((effect.effect_type, damage))
            
            elif effect.effect_type == StatusEffect.BURNED:
                damage = int(self.max_health * 0.08 * effect.potency)
                self.health = max(0, self.health - damage)
                triggered_effects.append((effect.effect_type, damage))
            
            elif effect.effect_type == StatusEffect.BLEEDING:
                damage = int(self.max_health * 0.07 * effect.potency)
                self.health = max(0, self.health - damage)
                triggered_effects.append((effect.effect_type, damage))
            
            # Update duration
            if effect.update():
                remaining_effects.append(effect)
            else:
                logger.debug(f"{effect.effect_type.name} expired on {self.name}")
        
        # Replace status effects list with remaining effects
        self.status_effects = remaining_effects
        
        # Check if dead from damage over time
        if self.health <= 0:
            self.is_dead = True
            self.health = 0
            logger.debug(f"{self.name} died from status effects")
        
        return triggered_effects
    
    def get_resistance(self, damage_type):
        """
        Get resistance to a damage type.
        
        Args:
            damage_type: DamageType enum value
            
        Returns:
            Resistance percentage (0-100)
        """
        return self.resistances.get(damage_type, 0)
    
    def set_resistance(self, damage_type, value):
        """
        Set resistance to a damage type.
        
        Args:
            damage_type: DamageType enum value
            value: Resistance percentage (0-100)
        """
        self.resistances[damage_type] = max(0, min(100, value))
    
    def can_take_turn(self):
        """
        Check if entity can take a turn.
        
        Returns:
            Boolean indicating if entity can take a turn
        """
        # Check if dead
        if self.is_dead:
            return False
        
        # Check for status effects that prevent turns
        for effect in self.status_effects:
            if effect.effect_type == StatusEffect.STUNNED:
                return False
        
        return True
    
    def get_turn_speed(self):
        """
        Get entity's speed for turn order calculation.
        
        Returns:
            Modified speed value
        """
        base_speed = self.speed
        
        # Apply status effects
        for effect in self.status_effects:
            if effect.effect_type == StatusEffect.HASTED:
                base_speed *= (1 + effect.potency * 0.2)  # 20% increase per potency
            elif effect.effect_type == StatusEffect.SLOWED:
                base_speed *= (1 - effect.potency * 0.2)  # 20% decrease per potency
            elif effect.effect_type == StatusEffect.FROZEN:
                base_speed *= 0.5  # 50% decrease
        
        return max(1, base_speed)
    
    def defend(self):
        """
        Take defend action.
        
        Returns:
            Action result data
        """
        self.defending = True
        logger.debug(f"{self.name} is defending")
        return {'action': CombatAction.DEFEND, 'success': True}
    
    def use_skill(self, skill, targets):
        """
        Use a skill on targets.
        
        Args:
            skill: Skill to use
            targets: List of target entities
            
        Returns:
            Action result data
        """
        # Check if entity can use skill
        if not self.can_take_turn():
            return {'action': CombatAction.SKILL, 'success': False, 'message': "Unable to act"}
        
        # Check if skill is available
        if skill not in self.skills:
            return {'action': CombatAction.SKILL, 'success': False, 'message': "Skill not available"}
        
        # Check mana cost
        if skill.mana_cost > self.mana:
            return {'action': CombatAction.SKILL, 'success': False, 'message': "Not enough mana"}
        
        # Check cooldown
        if skill.current_cooldown > 0:
            return {'action': CombatAction.SKILL, 'success': False, 'message': "Skill on cooldown"}
        
        # Use skill
        result = skill.use(self, targets)
        
        # Apply mana cost
        self.mana -= skill.mana_cost
        
        # Set cooldown
        skill.current_cooldown = skill.cooldown
        
        return {
            'action': CombatAction.SKILL,
            'success': True,
            'skill': skill.name,
            'targets': [target.name for target in targets],
            'results': result
        }
    
    def use_item(self, item, targets):
        """
        Use an item on targets.
        
        Args:
            item: Item to use
            targets: List of target entities
            
        Returns:
            Action result data
        """
        # Check if entity can use item
        if not self.can_take_turn():
            return {'action': CombatAction.ITEM, 'success': False, 'message': "Unable to act"}
        
        # Use item
        result = item.use(self, targets)
        
        return {
            'action': CombatAction.ITEM,
            'success': True,
            'item': item.name,
            'targets': [target.name for target in targets],
            'results': result
        }
    
    def attack(self, target):
        """
        Perform a basic attack on a target.
        
        Args:
            target: Target entity
            
        Returns:
            Action result data
        """
        # Check if entity can attack
        if not self.can_take_turn():
            return {'action': CombatAction.ATTACK, 'success': False, 'message': "Unable to act"}
        
        # Check if target is valid
        if target.is_dead:
            return {'action': CombatAction.ATTACK, 'success': False, 'message': "Target is already dead"}
        
        # Calculate hit chance
        hit_chance = self.hit_chance - target.evasion
        hit_roll = random.randint(1, 100)
        
        if hit_roll > hit_chance:
            # Attack missed
            logger.debug(f"{self.name}'s attack missed {target.name}")
            return {
                'action': CombatAction.ATTACK,
                'success': False,
                'message': "Attack missed",
                'target': target.name
            }
        
        # Calculate critical hit
        critical_roll = random.randint(1, 100)
        critical = critical_roll <= self.critical_chance
        
        # Calculate damage
        base_damage = self.physical_attack
        
        # Apply status effects
        for effect in self.status_effects:
            if effect.effect_type == StatusEffect.STRENGTHENED:
                base_damage *= (1 + effect.potency * 0.2)  # 20% increase per potency
            elif effect.effect_type == StatusEffect.WEAKENED:
                base_damage *= (1 - effect.potency * 0.2)  # 20% decrease per potency
        
        # Apply damage
        damage_result = target.take_damage(
            base_damage, 
            DamageType.PHYSICAL, 
            critical, 
            self
        )
        
        # Log attack
        logger.debug(f"{self.name} attacked {target.name} for {damage_result['damage']} damage")
        
        return {
            'action': CombatAction.ATTACK,
            'success': True,
            'target': target.name,
            'damage': damage_result['damage'],
            'critical': damage_result['critical'],
            'blocked': damage_result['blocked'],
            'status_effects': [e.effect_type.name for e in damage_result['status_effects']]
        }
    
    def flee(self, combat):
        """
        Attempt to flee from combat.
        
        Args:
            combat: Combat instance
            
        Returns:
            Action result data
        """
        # Check if entity can flee
        if not self.can_take_turn():
            return {'action': CombatAction.FLEE, 'success': False, 'message': "Unable to act"}
        
        # Calculate flee chance
        flee_chance = 30 + (self.speed * 2)
        
        # Reduce chance based on enemy count
        enemies = [e for e in combat.entities if e.team != self.team and not e.is_dead]
        flee_chance -= len(enemies) * 5
        
        # Apply status effects
        for effect in self.status_effects:
            if effect.effect_type == StatusEffect.SLOWED:
                flee_chance -= 20 * effect.potency
            elif effect.effect_type == StatusEffect.FROZEN:
                flee_chance -= 30
        
        # Clamp chance
        flee_chance = max(5, min(95, flee_chance))
        
        # Roll for success
        roll = random.randint(1, 100)
        success = roll <= flee_chance
        
        if success:
            logger.debug(f"{self.name} successfully fled from combat")
            return {
                'action': CombatAction.FLEE,
                'success': True,
                'message': "Successfully fled from combat"
            }
        else:
            logger.debug(f"{self.name} failed to flee from combat")
            return {
                'action': CombatAction.FLEE,
                'success': False,
                'message': "Failed to flee from combat"
            }
    
    def to_dict(self):
        """Convert to dictionary for serialization."""
        return {
            'name': self.name,
            'level': self.level,
            'team': self.team,
            'max_health': self.max_health,
            'health': self.health,
            'max_mana': self.max_mana,
            'mana': self.mana,
            'strength': self.strength,
            'intelligence': self.intelligence,
            'dexterity': self.dexterity,
            'constitution': self.constitution,
            'speed': self.speed,
            'physical_attack': self.physical_attack,
            'magical_attack': self.magical_attack,
            'physical_defense': self.physical_defense,
            'magical_defense': self.magical_defense,
            'hit_chance': self.hit_chance,
            'evasion': self.evasion,
            'critical_chance': self.critical_chance,
            'critical_damage': self.critical_damage,
            'resistances': {k.value: v for k, v in self.resistances.items()},
            'status_effects': [e.to_dict() for e in self.status_effects],
            'defending': self.defending,
            'turn_meter': self.turn_meter,
            'is_dead': self.is_dead,
            'skills': [s.name for s in self.skills],
            'innate_abilities': [a.name for a in self.innate_abilities]
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create from dictionary."""
        entity = cls(data['name'], data['level'], data['team'])
        entity.max_health = data['max_health']
        entity.health = data['health']
        entity.max_mana = data['max_mana']
        entity.mana = data['mana']
        entity.strength = data['strength']
        entity.intelligence = data['intelligence']
        entity.dexterity = data['dexterity']
        entity.constitution = data['constitution']
        entity.speed = data['speed']
        entity.physical_attack = data['physical_attack']
        entity.magical_attack = data['magical_attack']
        entity.physical_defense = data['physical_defense']
        entity.magical_defense = data['magical_defense']
        entity.hit_chance = data['hit_chance']
        entity.evasion = data['evasion']
        entity.critical_chance = data['critical_chance']
        entity.critical_damage = data['critical_damage']
        entity.resistances = {DamageType(int(k)): v for k, v in data['resistances'].items()}
        entity.status_effects = [StatusEffectInstance.from_dict(e) for e in data['status_effects']]
        entity.defending = data['defending']
        entity.turn_meter = data['turn_meter']
        entity.is_dead = data['is_dead']
        
        # Skills and abilities would need to be loaded separately
        
        return entity

class Skill:
    """A skill that can be used in combat."""
    
    def __init__(self, name, description, mana_cost=0, cooldown=0):
        """
        Initialize a skill.
        
        Args:
            name: Skill name
            description: Skill description
            mana_cost: Mana cost to use skill
            cooldown: Cooldown in turns
        """
        self.name = name
        self.description = description
        self.mana_cost = mana_cost
        self.cooldown = cooldown
        self.current_cooldown = 0
        self.level = 1
        self.max_level = 5
        self.target_type = "enemy"  # enemy, ally, self, all_enemies, all_allies, all
    
    def use(self, user, targets):
        """
        Use the skill.
        
        Args:
            user: Entity using the skill
            targets: List of target entities
            
        Returns:
            Skill result data
        """
        # Base implementation does nothing
        return {'success': False, 'message': "Skill not implemented"}
    
    def update_cooldown(self):
        """
        Update cooldown for a new turn.
        
        Returns:
            Boolean indicating if skill is ready
        """
        if self.current_cooldown > 0:
            self.current_cooldown -= 1
        
        return self.current_cooldown == 0
    
    def to_dict(self):
        """Convert to dictionary for serialization."""
        return {
            'name': self.name,
            'description': self.description,
            'mana_cost': self.mana_cost,
            'cooldown': self.cooldown,
            'current_cooldown': self.current_cooldown,
            'level': self.level,
            'max_level': self.max_level,
            'target_type': self.target_type
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create from dictionary."""
        skill = cls(
            data['name'],
            data['description'],
            data['mana_cost'],
            data['cooldown']
        )
        skill.current_cooldown = data['current_cooldown']
        skill.level = data['level']
        skill.max_level = data['max_level']
        skill.target_type = data['target_type']
        return skill

class DamageSkill(Skill):
    """A skill that deals damage to targets."""
    
    def __init__(self, name, description, damage_type=DamageType.PHYSICAL, 
                power=100, mana_cost=10, cooldown=0):
        """
        Initialize a damage skill.
        
        Args:
            name: Skill name
            description: Skill description
            damage_type: Type of damage from DamageType enum
            power: Base damage percentage (100 = 100% of attack)
            mana_cost: Mana cost to use skill
            cooldown: Cooldown in turns
        """
        super().__init__(name, description, mana_cost, cooldown)
        self.damage_type = damage_type
        self.power = power
        self.target_type = "enemy"
    
    def use(self, user, targets):
        """
        Use the skill.
        
        Args:
            user: Entity using the skill
            targets: List of target entities
            
        Returns:
            Skill result data
        """
        results = []
        
        for target in targets:
            # Calculate damage
            if self.damage_type == DamageType.PHYSICAL:
                base_damage = user.physical_attack
            else:
                base_damage = user.magical_attack
            
            damage = base_damage * (self.power / 100) * (1 + (self.level - 1) * 0.1)
            
            # Apply damage
            damage_result = target.take_damage(
                damage, 
                self.damage_type, 
                False,  # Critical handled separately for skills
                user
            )
            
            results.append({
                'target': target.name,
                'damage': damage_result['damage'],
                'critical': damage_result['critical'],
                'blocked': damage_result['blocked'],
                'status_effects': [e.effect_type.name for e in damage_result['status_effects']]
            })
        
        return {
            'success': True,
            'targets': results
        }
    
    def to_dict(self):
        """Convert to dictionary for serialization."""
        data = super().to_dict()
        data.update({
            'damage_type': self.damage_type.value,
            'power': self.power,
            'skill_type': 'damage'
        })
        return data
    
    @classmethod
    def from_dict(cls, data):
        """Create from dictionary."""
        skill = cls(
            data['name'],
            data['description'],
            DamageType(data['damage_type']),
            data['power'],
            data['mana_cost'],
            data['cooldown']
        )
        skill.current_cooldown = data['current_cooldown']
        skill.level = data['level']
        skill.max_level = data['max_level']
        skill.target_type = data['target_type']
        return skill

class HealingSkill(Skill):
    """A skill that heals targets."""
    
    def __init__(self, name, description, power=100, mana_cost=10, cooldown=0):
        """
        Initialize a healing skill.
        
        Args:
            name: Skill name
            description: Skill description
            power: Base healing percentage (100 = 10% of max health)
            mana_cost: Mana cost to use skill
            cooldown: Cooldown in turns
        """
        super().__init__(name, description, mana_cost, cooldown)
        self.power = power
        self.target_type = "ally"
    
    def use(self, user, targets):
        """
        Use the skill.
        
        Args:
            user: Entity using the skill
            targets: List of target entities
            
        Returns:
            Skill result data
        """
        results = []
        
        for target in targets:
            # Calculate healing
            base_healing = target.max_health * 0.1  # 10% of max health
            healing = base_healing * (self.power / 100) * (1 + (self.level - 1) * 0.1)
            
            # Apply healing based on user's magical attack
            healing_modifier = 1 + (user.magical_attack / 100)
            actual_healing = int(healing * healing_modifier)
            
            # Apply healing
            amount_healed = target.heal(actual_healing, user)
            
            results.append({
                'target': target.name,
                'healing': amount_healed
            })
        
        return {
            'success': True,
            'targets': results
        }
    
    def to_dict(self):
        """Convert to dictionary for serialization."""
        data = super().to_dict()
        data.update({
            'power': self.power,
            'skill_type': 'healing'
        })
        return data
    
    @classmethod
    def from_dict(cls, data):
        """Create from dictionary."""
        skill = cls(
            data['name'],
            data['description'],
            data['power'],
            data['mana_cost'],
            data['cooldown']
        )
        skill.current_cooldown = data['current_cooldown']
        skill.level = data['level']
        skill.max_level = data['max_level']
        skill.target_type = data['target_type']
        return skill

class BuffSkill(Skill):
    """A skill that applies beneficial status effects to targets."""
    
    def __init__(self, name, description, effect_type, duration=3, 
                potency=1.0, mana_cost=10, cooldown=1):
        """
        Initialize a buff skill.
        
        Args:
            name: Skill name
            description: Skill description
            effect_type: Type from StatusEffect enum
            duration: Effect duration in turns
            potency: Effect strength multiplier
            mana_cost: Mana cost to use skill
            cooldown: Cooldown in turns
        """
        super().__init__(name, description, mana_cost, cooldown)
        self.effect_type = effect_type
        self.duration = duration
        self.potency = potency
        self.target_type = "ally"
    
    def use(self, user, targets):
        """
        Use the skill.
        
        Args:
            user: Entity using the skill
            targets: List of target entities
            
        Returns:
            Skill result data
        """
        results = []
        
        for target in targets:
            # Calculate duration and potency based on level
            duration = self.duration + (self.level - 1)
            potency = self.potency * (1 + (self.level - 1) * 0.1)
            
            # Create status effect
            effect = StatusEffectInstance(
                self.effect_type,
                duration,
                potency,
                self.name
            )
            
            # Apply effect
            applied = target.add_status_effect(effect)
            
            results.append({
                'target': target.name,
                'effect': self.effect_type.name,
                'duration': duration,
                'potency': potency,
                'applied': applied
            })
        
        return {
            'success': True,
            'targets': results
        }
    
    def to_dict(self):
        """Convert to dictionary for serialization."""
        data = super().to_dict()
        data.update({
            'effect_type': self.effect_type.value,
            'duration': self.duration,
            'potency': self.potency,
            'skill_type': 'buff'
        })
        return data
    
    @classmethod
    def from_dict(cls, data):
        """Create from dictionary."""
        skill = cls(
            data['name'],
            data['description'],
            StatusEffect(data['effect_type']),
            data['duration'],
            data['potency'],
            data['mana_cost'],
            data['cooldown']
        )
        skill.current_cooldown = data['current_cooldown']
        skill.level = data['level']
        skill.max_level = data['max_level']
        skill.target_type = data['target_type']
        return skill

class DebuffSkill(Skill):
    """A skill that applies negative status effects to targets."""
    
    def __init__(self, name, description, effect_type, duration=3, 
                potency=1.0, mana_cost=10, cooldown=1):
        """
        Initialize a debuff skill.
        
        Args:
            name: Skill name
            description: Skill description
            effect_type: Type from StatusEffect enum
            duration: Effect duration in turns
            potency: Effect strength multiplier
            mana_cost: Mana cost to use skill
            cooldown: Cooldown in turns
        """
        super().__init__(name, description, mana_cost, cooldown)
        self.effect_type = effect_type
        self.duration = duration
        self.potency = potency
        self.target_type = "enemy"
        self.base_hit_chance = 80  # Base chance to apply effect
    
    def use(self, user, targets):
        """
        Use the skill.
        
        Args:
            user: Entity using the skill
            targets: List of target entities
            
        Returns:
            Skill result data
        """
        results = []
        
        for target in targets:
            # Calculate duration and potency based on level
            duration = self.duration + (self.level - 1)
            potency = self.potency * (1 + (self.level - 1) * 0.1)
            
            # Calculate hit chance (influenced by target's resistances)
            hit_chance = self.base_hit_chance + (user.magical_attack / 10)
            
            # Apply resistance based on effect type
            if self.effect_type in [StatusEffect.POISONED, StatusEffect.BURNED, StatusEffect.BLEEDING]:
                resistance = target.get_resistance(DamageType.POISON)
            elif self.effect_type in [StatusEffect.FROZEN]:
                resistance = target.get_resistance(DamageType.ICE)
            elif self.effect_type in [StatusEffect.BURNED]:
                resistance = target.get_resistance(DamageType.FIRE)
            else:
                resistance = target.get_resistance(DamageType.MAGICAL)
            
            hit_chance -= resistance / 2
            
            # Roll for hit
            roll = random.randint(1, 100)
            hit = roll <= hit_chance
            
            applied = False
            if hit:
                # Create status effect
                effect = StatusEffectInstance(
                    self.effect_type,
                    duration,
                    potency,
                    self.name
                )
                
                # Apply effect
                applied = target.add_status_effect(effect)
            
            results.append({
                'target': target.name,
                'effect': self.effect_type.name,
                'duration': duration,
                'potency': potency,
                'hit': hit,
                'applied': applied
            })
        
        return {
            'success': True,
            'targets': results
        }
    
    def to_dict(self):
        """Convert to dictionary for serialization."""
        data = super().to_dict()
        data.update({
            'effect_type': self.effect_type.value,
            'duration': self.duration,
            'potency': self.potency,
            'base_hit_chance': self.base_hit_chance,
            'skill_type': 'debuff'
        })
        return data
    
    @classmethod
    def from_dict(cls, data):
        """Create from dictionary."""
        skill = cls(
            data['name'],
            data['description'],
            StatusEffect(data['effect_type']),
            data['duration'],
            data['potency'],
            data['mana_cost'],
            data['cooldown']
        )
        skill.current_cooldown = data['current_cooldown']
        skill.level = data['level']
        skill.max_level = data['max_level']
        skill.target_type = data['target_type']
        skill.base_hit_chance = data['base_hit_chance']
        return skill

class CombatItem:
    """An item that can be used in combat."""
    
    def __init__(self, name, description):
        """
        Initialize a combat item.
        
        Args:
            name: Item name
            description: Item description
        """
        self.name = name
        self.description = description
        self.consumable = True
        self.target_type = "self"  # self, ally, enemy, all_allies, all_enemies, all
    
    def use(self, user, targets):
        """
        Use the item.
        
        Args:
            user: Entity using the item
            targets: List of target entities
            
        Returns:
            Item result data
        """
        # Base implementation does nothing
        return {'success': False, 'message': "Item not implemented"}
    
    def to_dict(self):
        """Convert to dictionary for serialization."""
        return {
            'name': self.name,
            'description': self.description,
            'consumable': self.consumable,
            'target_type': self.target_type,
            'item_type': 'base'
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create from dictionary."""
        item = cls(data['name'], data['description'])
        item.consumable = data['consumable']
        item.target_type = data['target_type']
        return item

class HealingItem(CombatItem):
    """An item that heals targets."""
    
    def __init__(self, name, description, heal_amount, heal_percentage=False):
        """
        Initialize a healing item.
        
        Args:
            name: Item name
            description: Item description
            heal_amount: Amount of health to restore
            heal_percentage: If True, heal_amount is a percentage of max health
        """
        super().__init__(name, description)
        self.heal_amount = heal_amount
        self.heal_percentage = heal_percentage
        self.target_type = "ally"
    
    def use(self, user, targets):
        """
        Use the item.
        
        Args:
            user: Entity using the item
            targets: List of target entities
            
        Returns:
            Item result data
        """
        results = []
        
        for target in targets:
            # Calculate healing
            if self.heal_percentage:
                amount = int(target.max_health * (self.heal_amount / 100))
            else:
                amount = self.heal_amount
            
            # Apply healing
            actual_heal = target.heal(amount, user)
            
            results.append({
                'target': target.name,
                'healing': actual_heal
            })
        
        return {
            'success': True,
            'targets': results
        }
    
    def to_dict(self):
        """Convert to dictionary for serialization."""
        data = super().to_dict()
        data.update({
            'heal_amount': self.heal_amount,
            'heal_percentage': self.heal_percentage,
            'item_type': 'healing'
        })
        return data
    
    @classmethod
    def from_dict(cls, data):
        """Create from dictionary."""
        item = cls(
            data['name'],
            data['description'],
            data['heal_amount'],
            data['heal_percentage']
        )
        item.consumable = data['consumable']
        item.target_type = data['target_type']
        return item

class CombatTurnManager:
    """Manages turn order and actions in combat."""
    
    def __init__(self):
        """Initialize the turn manager."""
        self.entities = []
        self.current_entity_index = 0
        self.turn_number = 0
        self.is_combat_over = False
        self.winners = None
        self.turn_time_limit = 30  # Seconds before auto-select action
    
    def add_entity(self, entity):
        """
        Add an entity to combat.
        
        Args:
            entity: CombatEntity to add
        """
        self.entities.append(entity)
    
    def start_combat(self):
        """
        Start combat.
        
        Returns:
            First entity to take a turn
        """
        # Sort entities by speed for initial turn order
        self.entities.sort(key=lambda e: e.speed, reverse=True)
        
        # Reset turn counters
        self.current_entity_index = 0
        self.turn_number = 1
        self.is_combat_over = False
        self.winners = None
        
        # Update initial turn meters
        for entity in self.entities:
            entity.turn_meter = 0
        
        # Find first active entity
        while (self.current_entity_index < len(self.entities) and 
              not self.entities[self.current_entity_index].can_take_turn()):
            self.current_entity_index += 1
            
            # If we've gone through all entities, advance to next turn
            if self.current_entity_index >= len(self.entities):
                self._advance_to_next_turn()
        
        # Check if combat is over before any turns
        self._check_combat_end()
        
        if self.is_combat_over:
            return None
        
        return self.entities[self.current_entity_index]
    
    def get_current_entity(self):
        """
        Get the entity whose turn it is.
        
        Returns:
            Current entity or None if combat is over
        """
        if self.is_combat_over:
            return None
        
        if self.current_entity_index < len(self.entities):
            return self.entities[self.current_entity_index]
        
        return None
    
    def end_turn(self):
        """
        End the current entity's turn.
        
        Returns:
            Next entity to take a turn or None if combat is over
        """
        # Move to next entity
        self.current_entity_index += 1
        
        # If we've gone through all entities, advance to next turn
        if self.current_entity_index >= len(self.entities):
            self._advance_to_next_turn()
        
        # Find next active entity
        while (self.current_entity_index < len(self.entities) and 
              not self.entities[self.current_entity_index].can_take_turn()):
            self.current_entity_index += 1
            
            # If we've gone through all entities, advance to next turn
            if self.current_entity_index >= len(self.entities):
                self._advance_to_next_turn()
        
        # Check if combat is over
        self._check_combat_end()
        
        if self.is_combat_over:
            return None
        
        return self.entities[self.current_entity_index]
    
    def _advance_to_next_turn(self):
        """Advance to the next turn."""
        self.current_entity_index = 0
        self.turn_number += 1
        
        logger.debug(f"Advancing to turn {self.turn_number}")
        
        # Update cooldowns and status effects
        for entity in self.entities:
            # Skip dead entities
            if entity.is_dead:
                continue
            
            # Update status effects
            entity.update_status_effects()
            
            # Update skill cooldowns
            for skill in entity.skills:
                skill.update_cooldown()
        
        # Sort entities by turn meter for next turn
        self.entities.sort(key=lambda e: e.turn_meter, reverse=True)
        
        # Reset turn meters
        for entity in self.entities:
            entity.turn_meter = 0
    
    def _check_combat_end(self):
        """Check if combat has ended."""
        # Get living entities by team
        teams = {}
        for entity in self.entities:
            if not entity.is_dead:
                if entity.team not in teams:
                    teams[entity.team] = []
                teams[entity.team].append(entity)
        
        # If only one team remains, they win
        if len(teams) <= 1:
            self.is_combat_over = True
            self.winners = list(teams.keys())[0] if teams else None
    
    def get_targets(self, entity, target_type):
        """
        Get valid targets for an action.
        
        Args:
            entity: Entity taking the action
            target_type: Target type string
            
        Returns:
            List of valid target entities
        """
        targets = []
        
        if target_type == "self":
            # Self-targeting
            targets = [entity]
        
        elif target_type == "ally":
            # Single ally targeting
            targets = [e for e in self.entities if e.team == entity.team and not e.is_dead and e != entity]
        
        elif target_type == "enemy":
            # Single enemy targeting
            targets = [e for e in self.entities if e.team != entity.team and not e.is_dead]
        
        elif target_type == "all_allies":
            # All allies including self
            targets = [e for e in self.entities if e.team == entity.team and not e.is_dead]
        
        elif target_type == "all_enemies":
            # All enemies
            targets = [e for e in self.entities if e.team != entity.team and not e.is_dead]
        
        elif target_type == "all":
            # All entities
            targets = [e for e in self.entities if not e.is_dead]
        
        return targets
    
    def get_team_entities(self, team):
        """
        Get all entities on a team.
        
        Args:
            team: Team identifier
            
        Returns:
            List of entities on the team
        """
        return [e for e in self.entities if e.team == team]
    
    def get_combat_summary(self):
        """
        Get a summary of the current combat state.
        
        Returns:
            Dictionary with combat summary
        """
        return {
            'turn_number': self.turn_number,
            'current_entity': self.entities[self.current_entity_index].name if not self.is_combat_over else None,
            'is_combat_over': self.is_combat_over,
            'winners': self.winners,
            'entities': [
                {
                    'name': e.name,
                    'team': e.team,
                    'health': e.health,
                    'max_health': e.max_health,
                    'mana': e.mana,
                    'max_mana': e.max_mana,
                    'is_dead': e.is_dead,
                    'status_effects': [eff.effect_type.name for eff in e.status_effects]
                }
                for e in self.entities
            ]
        }
    
    def to_dict(self):
        """Convert to dictionary for serialization."""
        return {
            'entities': [e.to_dict() for e in self.entities],
            'current_entity_index': self.current_entity_index,
            'turn_number': self.turn_number,
            'is_combat_over': self.is_combat_over,
            'winners': self.winners,
            'turn_time_limit': self.turn_time_limit
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create from dictionary."""
        manager = cls()
        manager.current_entity_index = data['current_entity_index']
        manager.turn_number = data['turn_number']
        manager.is_combat_over = data['is_combat_over']
        manager.winners = data['winners']
        manager.turn_time_limit = data['turn_time_limit']
        
        # Entities would need to be loaded separately
        
        return manager

class Combat:
    """Manages a complete combat encounter."""
    
    def __init__(self):
        """Initialize a combat encounter."""
        self.turn_manager = CombatTurnManager()
        self.encounter_level = 1
        self.environment = "neutral"  # neutral, forest, cave, desert, etc.
        self.rewards = {
            'experience': 0,
            'gold': 0,
            'items': []
        }
        self.is_boss_fight = False
        self.is_random_encounter = True
    
    def initialize_from_entity_lists(self, player_entities, enemy_entities):
        """
        Initialize combat from entity lists.
        
        Args:
            player_entities: List of player entities
            enemy_entities: List of enemy entities
        """
        # Add player entities
        for entity in player_entities:
            entity.team = 0  # Player team
            self.turn_manager.add_entity(entity)
        
        # Add enemy entities
        for entity in enemy_entities:
            entity.team = 1  # Enemy team
            self.turn_manager.add_entity(entity)
        
        # Calculate rewards
        self._calculate_rewards()
    
    def start(self):
        """
        Start the combat encounter.
        
        Returns:
            First entity to take a turn
        """
        return self.turn_manager.start_combat()
    
    def end_turn(self):
        """
        End the current entity's turn.
        
        Returns:
            Next entity to take a turn or None if combat is over
        """
        return self.turn_manager.end_turn()
    
    def is_over(self):
        """
        Check if combat is over.
        
        Returns:
            Boolean indicating if combat is over
        """
        return self.turn_manager.is_combat_over
    
    def get_winners(self):
        """
        Get the winning team.
        
        Returns:
            Team identifier of winners or None if no winners
        """
        return self.turn_manager.winners
    
    def get_rewards(self):
        """
        Get combat rewards.
        
        Returns:
            Dictionary with reward information
        """
        return self.rewards
    
    def _calculate_rewards(self):
        """Calculate rewards based on enemy entities."""
        total_exp = 0
        total_gold = 0
        
        # Get all enemy entities
        enemies = [e for e in self.turn_manager.entities if e.team == 1]
        
        # Calculate base rewards
        for enemy in enemies:
            # XP based on level
            exp = enemy.level * 10
            
            # Gold based on level
            gold = enemy.level * 5
            
            # Adjust for boss
            if self.is_boss_fight:
                exp *= 3
                gold *= 3
            
            total_exp += exp
            total_gold += gold
        
        # Set rewards
        self.rewards['experience'] = total_exp
        self.rewards['gold'] = total_gold
        
        # TODO: Generate item rewards
    
    def to_dict(self):
        """Convert to dictionary for serialization."""
        return {
            'turn_manager': self.turn_manager.to_dict(),
            'encounter_level': self.encounter_level,
            'environment': self.environment,
            'rewards': self.rewards,
            'is_boss_fight': self.is_boss_fight,
            'is_random_encounter': self.is_random_encounter
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create from dictionary."""
        combat = cls()
        combat.turn_manager = CombatTurnManager.from_dict(data['turn_manager'])
        combat.encounter_level = data['encounter_level']
        combat.environment = data['environment']
        combat.rewards = data['rewards']
        combat.is_boss_fight = data['is_boss_fight']
        combat.is_random_encounter = data['is_random_encounter']
        return combat

class MonsterGenerator:
    """Generates procedural monsters for combat."""
    
    def __init__(self):
        """Initialize the monster generator."""
        # Monster types
        self.monster_types = [
            "Goblin", "Skeleton", "Zombie", "Wolf", "Spider", "Slime",
            "Orc", "Troll", "Kobold", "Rat", "Bat", "Snake",
            "Bandit", "Ghoul", "Ghost", "Elemental", "Golem", "Dragon"
        ]
        
        # Monster prefixes (for variation)
        self.prefixes = [
            "Feral", "Savage", "Rabid", "Wild", "Dark", "Cursed",
            "Ancient", "Toxic", "Venomous", "Frost", "Fiery", "Electric",
            "Shadow", "Undead", "Corrupt", "Mighty", "Giant", "Small"
        ]
        
        # Monster attack skills
        self.attack_skills = [
            ("Slash", DamageType.PHYSICAL, 120),
            ("Bite", DamageType.PHYSICAL, 110),
            ("Fireball", DamageType.FIRE, 150),
            ("Ice Spike", DamageType.ICE, 140),
            ("Lightning Bolt", DamageType.LIGHTNING, 160),
            ("Poison Spit", DamageType.POISON, 130),
            ("Dark Blast", DamageType.MAGICAL, 170)
        ]
        
        # Monster debuff skills
        self.debuff_skills = [
            ("Poison Cloud", StatusEffect.POISONED, 3),
            ("Frost Breath", StatusEffect.FROZEN, 2),
            ("Paralyzing Touch", StatusEffect.STUNNED, 1),
            ("Weakening Strike", StatusEffect.WEAKENED, 3),
            ("Burning Aura", StatusEffect.BURNED, 3),
            ("Crippling Blow", StatusEffect.SLOWED, 2),
            ("Mind Fog", StatusEffect.CONFUSED, 2)
        ]
    
    def generate_monster(self, level, difficulty="normal", monster_type=None):
        """
        Generate a monster.
        
        Args:
            level: Monster level
            difficulty: Difficulty setting (easy, normal, hard, boss)
            monster_type: Specific monster type or None for random
            
        Returns:
            CombatEntity instance for the monster
        """
        # Choose monster type
        if monster_type is None:
            monster_type = random.choice(self.monster_types)
        
        # Choose a prefix for variety (50% chance)
        name = monster_type
        if random.random() < 0.5:
            prefix = random.choice(self.prefixes)
            name = f"{prefix} {monster_type}"
        
        # Create monster entity
        monster = CombatEntity(name, level, team=1)
        
        # Apply difficulty multiplier
        if difficulty == "easy":
            difficulty_multiplier = 0.8
        elif difficulty == "hard":
            difficulty_multiplier = 1.2
        elif difficulty == "boss":
            difficulty_multiplier = 2.0
            name = f"Boss {name}"
            monster.name = name
        else:  # normal
            difficulty_multiplier = 1.0
        
        # Set stats based on monster type and level
        self._set_monster_stats(monster, monster_type, level, difficulty_multiplier)
        
        # Add skills
        self._add_monster_skills(monster, monster_type, level, difficulty)
        
        # Set resistances
        self._set_monster_resistances(monster, monster_type)
        
        # Update derived stats
        monster._update_derived_stats()
        
        return monster
    
    def _set_monster_stats(self, monster, monster_type, level, difficulty_multiplier):
        """
        Set monster stats.
        
        Args:
            monster: Monster entity
            monster_type: Type of monster
            level: Monster level
            difficulty_multiplier: Stat multiplier for difficulty
        """
        # Base stats by type
        if monster_type in ["Goblin", "Kobold", "Rat", "Bat"]:
            # Fast, weak monsters
            monster.strength = 8 + level * 0.8
            monster.intelligence = 5 + level * 0.5
            monster.dexterity = 12 + level * 1.2
            monster.constitution = 6 + level * 0.6
            monster.speed = 15 + level * 0.5
        
        elif monster_type in ["Skeleton", "Zombie", "Ghoul", "Undead"]:
            # Undead monsters
            monster.strength = 10 + level * 1.0
            monster.intelligence = 3 + level * 0.3
            monster.dexterity = 7 + level * 0.7
            monster.constitution = 12 + level * 1.2
            monster.speed = 8 + level * 0.3
        
        elif monster_type in ["Wolf", "Spider", "Snake"]:
            # Animal monsters
            monster.strength = 9 + level * 0.9
            monster.intelligence = 4 + level * 0.4
            monster.dexterity = 14 + level * 1.4
            monster.constitution = 7 + level * 0.7
            monster.speed = 16 + level * 0.6
        
        elif monster_type in ["Orc", "Troll", "Bandit"]:
            # Humanoid monsters
            monster.strength = 14 + level * 1.4
            monster.intelligence = 6 + level * 0.6
            monster.dexterity = 8 + level * 0.8
            monster.constitution = 12 + level * 1.2
            monster.speed = 10 + level * 0.4
        
        elif monster_type in ["Slime", "Elemental", "Golem"]:
            # Elemental monsters
            monster.strength = 12 + level * 1.2
            monster.intelligence = 10 + level * 1.0
            monster.dexterity = 6 + level * 0.6
            monster.constitution = 15 + level * 1.5
            monster.speed = 7 + level * 0.3
        
        elif monster_type == "Dragon":
            # Dragon (powerful)
            monster.strength = 18 + level * 1.8
            monster.intelligence = 15 + level * 1.5
            monster.dexterity = 12 + level * 1.2
            monster.constitution = 20 + level * 2.0
            monster.speed = 14 + level * 0.7
        
        else:
            # Generic monster
            monster.strength = 10 + level * 1.0
            monster.intelligence = 8 + level * 0.8
            monster.dexterity = 10 + level * 1.0
            monster.constitution = 10 + level * 1.0
            monster.speed = 10 + level * 0.5
        
        # Apply difficulty multiplier
        monster.strength = int(monster.strength * difficulty_multiplier)
        monster.intelligence = int(monster.intelligence * difficulty_multiplier)
        monster.dexterity = int(monster.dexterity * difficulty_multiplier)
        monster.constitution = int(monster.constitution * difficulty_multiplier)
        monster.speed = int(monster.speed * difficulty_multiplier)
        
        # Make sure stats don't go below 1
        monster.strength = max(1, monster.strength)
        monster.intelligence = max(1, monster.intelligence)
        monster.dexterity = max(1, monster.dexterity)
        monster.constitution = max(1, monster.constitution)
        monster.speed = max(1, monster.speed)
    
    def _add_monster_skills(self, monster, monster_type, level, difficulty):
        """
        Add skills to monster.
        
        Args:
            monster: Monster entity
            monster_type: Type of monster
            level: Monster level
            difficulty: Difficulty setting
        """
        # Number of skills based on difficulty
        if difficulty == "easy":
            num_skills = 1
        elif difficulty == "normal":
            num_skills = 2
        elif difficulty == "hard":
            num_skills = 3
        else:  # boss
            num_skills = 4
        
        # Always add at least one attack skill
        attack_skill_name, damage_type, power = random.choice(self.attack_skills)
        
        # Customize skill name based on monster type
        if monster_type in ["Goblin", "Orc", "Troll", "Bandit"]:
            attack_skill_name = random.choice(["Smash", "Cleave", "Bash", "Chop"])
        elif monster_type in ["Wolf", "Spider", "Snake"]:
            attack_skill_name = random.choice(["Bite", "Claw", "Pounce", "Sting"])
        elif monster_type in ["Skeleton", "Zombie", "Ghoul"]:
            attack_skill_name = random.choice(["Bone Crush", "Death Touch", "Grave Smash"])
        elif monster_type in ["Elemental", "Slime"]:
            damage_type = random.choice([DamageType.FIRE, DamageType.ICE, DamageType.LIGHTNING])
            if damage_type == DamageType.FIRE:
                attack_skill_name = "Fire Blast"
            elif damage_type == DamageType.ICE:
                attack_skill_name = "Ice Spike"
            else:
                attack_skill_name = "Lightning Strike"
        elif monster_type == "Dragon":
            attack_skill_name = "Dragon Breath"
            damage_type = random.choice([DamageType.FIRE, DamageType.ICE, DamageType.POISON])
            power = 200  # Dragons hit hard
        
        # Create the attack skill
        attack_skill = DamageSkill(
            attack_skill_name,
            f"{attack_skill_name} deals {damage_type.name} damage to a target.",
            damage_type,
            power,
            level + 5,  # Mana cost
            2  # Cooldown
        )
        monster.skills.append(attack_skill)
        
        # Add additional skills if needed
        skills_added = 1
        
        # 50% chance for a debuff skill if num_skills > 1
        if num_skills > 1 and random.random() < 0.5:
            debuff_name, effect_type, duration = random.choice(self.debuff_skills)
            
            # Create the debuff skill
            debuff_skill = DebuffSkill(
                debuff_name,
                f"{debuff_name} applies {effect_type.name} to a target for {duration} turns.",
                effect_type,
                duration,
                1.0,  # Potency
                level + 8,  # Mana cost
                3  # Cooldown
            )
            monster.skills.append(debuff_skill)
            skills_added += 1
        
        # Add more attack skills to fill remaining slots
        while skills_added < num_skills:
            attack_skill_name, damage_type, power = random.choice(self.attack_skills)
            
            # Ensure it's different from the first skill
            if attack_skill_name == monster.skills[0].name:
                continue
                
            # Create another attack skill
            attack_skill = DamageSkill(
                attack_skill_name,
                f"{attack_skill_name} deals {damage_type.name} damage to a target.",
                damage_type,
                power,
                level + 5,  # Mana cost
                2  # Cooldown
            )
            monster.skills.append(attack_skill)
            skills_added += 1
    
    def _set_monster_resistances(self, monster, monster_type):
        """
        Set monster resistances.
        
        Args:
            monster: Monster entity
            monster_type: Type of monster
        """
        # Default resistances
        for damage_type in DamageType:
            if damage_type != DamageType.TRUE:
                monster.resistances[damage_type] = 0
        
        # Set resistances based on type
        if monster_type in ["Skeleton", "Zombie", "Ghoul", "Undead"]:
            # Undead monsters
            monster.resistances[DamageType.POISON] = 100  # Immune to poison
            monster.resistances[DamageType.PHYSICAL] = 20  # Resistant to physical
        
        elif monster_type in ["Slime"]:
            # Slimes
            monster.resistances[DamageType.PHYSICAL] = 50  # Very resistant to physical
            monster.resistances[DamageType.POISON] = 100  # Immune to poison
            monster.resistances[DamageType.LIGHTNING] = -50  # Vulnerable to lightning
        
        elif monster_type in ["Elemental"]:
            # Elementals (random resistance and weakness)
            element_type = random.choice([DamageType.FIRE, DamageType.ICE, DamageType.LIGHTNING])
            opposite_type = DamageType.ICE if element_type == DamageType.FIRE else DamageType.FIRE
            
            monster.resistances[element_type] = 80  # Strong resistance
            monster.resistances[opposite_type] = -50  # Weakness
        
        elif monster_type == "Dragon":
            # Dragons
            element_type = random.choice([DamageType.FIRE, DamageType.ICE, DamageType.LIGHTNING])
            monster.resistances[element_type] = 80  # Strong resistance
            monster.resistances[DamageType.PHYSICAL] = 30  # Resistant to physical
        
        elif monster_type in ["Wolf", "Spider", "Snake"]:
            # Animals
            monster.resistances[DamageType.POISON] = 20  # Slight poison resistance
        
        elif monster_type in ["Orc", "Troll"]:
            # Tough humanoids
            monster.resistances[DamageType.PHYSICAL] = 20  # Physical resistance
            monster.resistances[DamageType.MAGICAL] = -20  # Magical weakness
        
        elif monster_type == "Golem":
            # Golems
            monster.resistances[DamageType.PHYSICAL] = 70  # Very resistant to physical
            monster.resistances[DamageType.MAGICAL] = 30  # Resistant to magical
            monster.resistances[DamageType.LIGHTNING] = -40  # Weak to lightning
    
    def generate_encounter(self, player_level, encounter_type="normal", environment="neutral"):
        """
        Generate a complete monster encounter.
        
        Args:
            player_level: Player character level
            encounter_type: Type of encounter (normal, elite, boss)
            environment: Environment setting
            
        Returns:
            List of monster entities
        """
        monsters = []
        
        if encounter_type == "normal":
            # Normal encounter: 2-4 monsters
            count = random.randint(2, 4)
            difficulty = "normal"
            
            for i in range(count):
                # Vary levels slightly
                level_variation = random.randint(-1, 1)
                monster_level = max(1, player_level + level_variation)
                
                monster = self.generate_monster(monster_level, difficulty)
                monsters.append(monster)
        
        elif encounter_type == "elite":
            # Elite encounter: 1-2 tougher monsters
            count = random.randint(1, 2)
            difficulty = "hard"
            
            for i in range(count):
                # Elite monsters are higher level
                monster_level = player_level + random.randint(1, 2)
                
                monster = self.generate_monster(monster_level, difficulty)
                monsters.append(monster)
        
        elif encounter_type == "boss":
            # Boss encounter: 1 boss + possible minions
            # Generate boss
            boss_level = player_level + random.randint(2, 3)
            boss = self.generate_monster(boss_level, "boss")
            monsters.append(boss)
            
            # 50% chance to add minions
            if random.random() < 0.5:
                minion_count = random.randint(1, 2)
                
                for i in range(minion_count):
                    minion_level = player_level
                    minion = self.generate_monster(minion_level, "easy")
                    minion.name = f"{boss.name.split()[0]} Minion"
                    monsters.append(minion)
        
        else:  # random
            # Random encounter: varied composition
            total_threat = random.randint(2, 5)  # Threat level scales with number and strength
            current_threat = 0
            
            while current_threat < total_threat:
                # Determine monster difficulty
                roll = random.random()
                if roll < 0.6:  # 60% easy
                    difficulty = "easy"
                    threat_value = 0.5
                elif roll < 0.9:  # 30% normal
                    difficulty = "normal"
                    threat_value = 1.0
                else:  # 10% hard
                    difficulty = "hard"
                    threat_value = 2.0
                
                # If this would exceed our threat budget, adjust
                if current_threat + threat_value > total_threat + 0.5:
                    difficulty = "easy"
                    threat_value = 0.5
                
                # Generate monster
                level_variation = random.randint(-1, 1)
                monster_level = max(1, player_level + level_variation)
                
                monster = self.generate_monster(monster_level, difficulty)
                monsters.append(monster)
                
                current_threat += threat_value
        
        return monsters

# Example usage:
"""
# Create a combat encounter
combat = Combat()

# Generate player character
player = CombatEntity("Hero", level=5, team=0)
player.skills.append(DamageSkill("Fireball", "Launches a ball of fire at the target", DamageType.FIRE, 150, 10, 2))
player.skills.append(HealingSkill("Heal", "Heals target for 10% of max health", 100, 15, 3))

# Generate enemy monsters
monster_gen = MonsterGenerator()
enemies = monster_gen.generate_encounter(player_level=5, encounter_type="normal")

# Initialize combat
combat.initialize_from_entity_lists([player], enemies)

# Start combat
current_entity = combat.start()

# Main combat loop
while not combat.is_over():
    # Get current entity
    current_entity = combat.turn_manager.get_current_entity()
    
    if current_entity.team == 0:  # Player
        # Player turn: Choose action (attack in this example)
        targets = combat.turn_manager.get_targets(current_entity, "enemy")
        if targets:
            action_result = current_entity.attack(targets[0])
            print(f"{current_entity.name} attacks {targets[0].name} for {action_result['damage']} damage")
    else:  # Enemy
        # Enemy turn: Simple AI (attack player)
        targets = combat.turn_manager.get_targets(current_entity, "enemy")  # Player is enemy to monsters
        if targets:
            action_result = current_entity.attack(targets[0])
            print(f"{current_entity.name} attacks {targets[0].name} for {action_result['damage']} damage")
    
    # End turn
    current_entity = combat.end_turn()

# Combat over
if combat.get_winners() == 0:
    print("Players win!")
    rewards = combat.get_rewards()
    print(f"Gained {rewards['experience']} XP and {rewards['gold']} gold!")
else:
    print("Game over!")
"""
class CombatAI:
    """AI controller for entities in combat."""
    
    def __init__(self, difficulty="normal"):
        """
        Initialize combat AI.
        
        Args:
            difficulty: AI difficulty setting (easy, normal, hard)
        """
        self.difficulty = difficulty
        self.memory = {}  # For tracking battle information
    
    def choose_action(self, entity, combat):
        """
        Choose an action for an entity to take.
        
        Args:
            entity: Entity to choose action for
            combat: Combat instance
            
        Returns:
            Dictionary with action information
        """
        # Initialize entity memory if not present
        if entity.name not in self.memory:
            self.memory[entity.name] = {
                'target_preference': None,
                'heal_threshold': 0.3,  # Heal when below 30% health
                'last_used_skills': {}
            }
        
        # Skip turn if entity cannot act
        if not entity.can_take_turn():
            return {'action': None, 'reason': "Cannot take turn"}
        
        # Analyze combat state
        state = self._analyze_combat_state(entity, combat)
        
        # Choose action based on difficulty and state
        if self.difficulty == "easy":
            return self._choose_action_easy(entity, combat, state)
        elif self.difficulty == "hard":
            return self._choose_action_hard(entity, combat, state)
        else:  # normal
            return self._choose_action_normal(entity, combat, state)
    
    def _analyze_combat_state(self, entity, combat):
        """
        Analyze the current combat state.
        
        Args:
            entity: Entity to analyze for
            combat: Combat instance
            
        Returns:
            Dictionary with state information
        """
        # Get teams
        allies = [e for e in combat.turn_manager.entities 
                 if e.team == entity.team and not e.is_dead]
        enemies = [e for e in combat.turn_manager.entities 
                  if e.team != entity.team and not e.is_dead]
        
        # Check entity's health
        health_ratio = entity.health / entity.max_health
        low_health = health_ratio <= self.memory[entity.name]['heal_threshold']
        
        # Find low health allies
        low_health_allies = [a for a in allies 
                            if a.health / a.max_health <= self.memory[entity.name]['heal_threshold']]
        
        # Check for available skills
        available_skills = [s for s in entity.skills if s.current_cooldown == 0 and s.mana_cost <= entity.mana]
        
        # Categorize skills
        damage_skills = [s for s in available_skills if isinstance(s, DamageSkill)]
        healing_skills = [s for s in available_skills if isinstance(s, HealingSkill)]
        buff_skills = [s for s in available_skills if isinstance(s, BuffSkill)]
        debuff_skills = [s for s in available_skills if isinstance(s, DebuffSkill)]
        
        # Analyze threats
        threats = []
        for enemy in enemies:
            threat_level = self._calculate_threat_level(enemy)
            threats.append((enemy, threat_level))
        
        # Sort threats by threat level (descending)
        threats.sort(key=lambda x: x[1], reverse=True)
        
        return {
            'allies': allies,
            'enemies': enemies,
            'health_ratio': health_ratio,
            'low_health': low_health,
            'low_health_allies': low_health_allies,
            'available_skills': available_skills,
            'damage_skills': damage_skills,
            'healing_skills': healing_skills,
            'buff_skills': buff_skills,
            'debuff_skills': debuff_skills,
            'threats': threats,
            'turn_number': combat.turn_manager.turn_number
        }
    
    def _calculate_threat_level(self, entity):
        """
        Calculate the threat level of an entity.
        
        Args:
            entity: Entity to calculate threat for
            
        Returns:
            Threat level score
        """
        # Base threat from attack power
        threat = max(entity.physical_attack, entity.magical_attack)
        
        # Adjust for health ratio (lower health = lower threat)
        health_ratio = entity.health / entity.max_health
        threat *= health_ratio
        
        # Adjust for status effects
        for effect in entity.status_effects:
            if effect.effect_type == StatusEffect.STUNNED:
                threat *= 0.5  # Stunned enemies are less threatening
            elif effect.effect_type == StatusEffect.WEAKENED:
                threat *= (1 - 0.2 * effect.potency)  # Weakened reduces threat
            elif effect.effect_type == StatusEffect.STRENGTHENED:
                threat *= (1 + 0.2 * effect.potency)  # Strengthened increases threat
        
        return threat
    
    def _choose_action_easy(self, entity, combat, state):
        """
        Choose action for easy difficulty.
        
        Args:
            entity: Entity to choose action for
            combat: Combat instance
            state: Combat state information
            
        Returns:
            Dictionary with action information
        """
        # Easy AI doesn't use skills effectively and makes suboptimal choices
        
        # Simple healing check - 50% chance to heal if low health
        if state['low_health'] and state['healing_skills'] and random.random() < 0.5:
            heal_skill = random.choice(state['healing_skills'])
            targets = [entity]  # Self heal
            return {
                'action': CombatAction.SKILL,
                'skill': heal_skill,
                'targets': targets
            }
        
        # 70% chance to just attack
        if random.random() < 0.7 and state['enemies']:
            # Choose random enemy
            target = random.choice(state['enemies'])
            return {
                'action': CombatAction.ATTACK,
                'targets': [target]
            }
        
        # 30% chance to use a random skill if available
        if state['available_skills'] and random.random() < 0.3:
            skill = random.choice(state['available_skills'])
            
            # Get targets based on skill type
            if isinstance(skill, DamageSkill) or isinstance(skill, DebuffSkill):
                if state['enemies']:
                    targets = [random.choice(state['enemies'])]
                else:
                    targets = []
            elif isinstance(skill, HealingSkill) or isinstance(skill, BuffSkill):
                targets = [entity]  # Self targeting
            else:
                targets = []
            
            if targets:
                return {
                    'action': CombatAction.SKILL,
                    'skill': skill,
                    'targets': targets
                }
        
        # Default to attacking random enemy
        if state['enemies']:
            target = random.choice(state['enemies'])
            return {
                'action': CombatAction.ATTACK,
                'targets': [target]
            }
        
        # No valid action found
        return {
            'action': CombatAction.DEFEND,
            'targets': []
        }
    
    def _choose_action_normal(self, entity, combat, state):
        """
        Choose action for normal difficulty.
        
        Args:
            entity: Entity to choose action for
            combat: Combat instance
            state: Combat state information
            
        Returns:
            Dictionary with action information
        """
        # Normal AI makes reasonable choices but not optimal
        
        # Heal self if health is low and healing skill is available
        if state['low_health'] and state['healing_skills']:
            heal_skill = state['healing_skills'][0]  # Choose first healing skill
            targets = [entity]  # Self heal
            return {
                'action': CombatAction.SKILL,
                'skill': heal_skill,
                'targets': targets
            }
        
        # Heal ally if their health is very low and healing skill is available
        if state['low_health_allies'] and state['healing_skills']:
            # Find ally with lowest health
            lowest_health_ally = min(state['low_health_allies'], 
                                    key=lambda a: a.health / a.max_health)
            
            # Only heal if health ratio is below 25%
            if lowest_health_ally.health / lowest_health_ally.max_health < 0.25:
                heal_skill = state['healing_skills'][0]
                return {
                    'action': CombatAction.SKILL,
                    'skill': heal_skill,
                    'targets': [lowest_health_ally]
                }
        
        # Use damage skill on highest threat if available
        if state['damage_skills'] and state['threats']:
            # 70% chance to target highest threat, 30% random
            if random.random() < 0.7:
                target = state['threats'][0][0]  # Highest threat
            else:
                target = random.choice(state['enemies'])
            
            # Choose random damage skill
            skill = random.choice(state['damage_skills'])
            return {
                'action': CombatAction.SKILL,
                'skill': skill,
                'targets': [target]
            }
        
        # Use debuff on highest threat if available
        if state['debuff_skills'] and state['threats']:
            target = state['threats'][0][0]  # Highest threat
            skill = random.choice(state['debuff_skills'])
            
            return {
                'action': CombatAction.SKILL,
                'skill': skill,
                'targets': [target]
            }
        
        # Use buff on self if available
        if state['buff_skills']:
            skill = random.choice(state['buff_skills'])
            return {
                'action': CombatAction.SKILL,
                'skill': skill,
                'targets': [entity]
            }
        
        # Default to attacking highest threat
        if state['threats']:
            target = state['threats'][0][0]  # Highest threat
            return {
                'action': CombatAction.ATTACK,
                'targets': [target]
            }
        
        # No valid action found
        return {
            'action': CombatAction.DEFEND,
            'targets': []
        }
    
    def _choose_action_hard(self, entity, combat, state):
        """
        Choose action for hard difficulty.
        
        Args:
            entity: Entity to choose action for
            combat: Combat instance
            state: Combat state information
            
        Returns:
            Dictionary with action information
        """
        # Hard AI makes optimal choices and uses advanced tactics
        
        # Emergency healing - prioritize healing when health is very low
        if entity.health / entity.max_health < 0.2 and state['healing_skills']:
            heal_skill = max(state['healing_skills'], 
                            key=lambda s: s.power)  # Choose most powerful heal
            targets = [entity]
            return {
                'action': CombatAction.SKILL,
                'skill': heal_skill,
                'targets': targets
            }
        
        # Check if any ally is critically low and heal them
        critical_allies = [a for a in state['allies'] 
                          if a.health / a.max_health < 0.15]
        
        if critical_allies and state['healing_skills']:
            lowest_health_ally = min(critical_allies, 
                                    key=lambda a: a.health / a.max_health)
            heal_skill = max(state['healing_skills'], 
                            key=lambda s: s.power)
            return {
                'action': CombatAction.SKILL,
                'skill': heal_skill,
                'targets': [lowest_health_ally]
            }
        
        # Apply buffs early in the fight
        if state['turn_number'] <= 2 and state['buff_skills']:
            # Choose buff that hasn't been applied yet
            for buff_skill in state['buff_skills']:
                # Check if buff is already applied
                buff_type = buff_skill.effect_type
                already_applied = False
                
                for effect in entity.status_effects:
                    if effect.effect_type == buff_type:
                        already_applied = True
                        break
                
                if not already_applied:
                    return {
                        'action': CombatAction.SKILL,
                        'skill': buff_skill,
                        'targets': [entity]
                    }
        
        # Apply debuffs to high threats without debuffs
        if state['debuff_skills'] and state['threats']:
            for enemy, _ in state['threats']:
                # Check existing debuffs
                enemy_debuffs = [effect.effect_type for effect in enemy.status_effects]
                
                # Find debuff that isn't already applied
                for debuff_skill in state['debuff_skills']:
                    if debuff_skill.effect_type not in enemy_debuffs:
                        return {
                            'action': CombatAction.SKILL,
                            'skill': debuff_skill,
                            'targets': [enemy]
                        }
        
        # Use most powerful damage skill on highest threat
        if state['damage_skills'] and state['threats']:
            target = state['threats'][0][0]  # Highest threat
            
            # Select best damage skill based on target weaknesses
            best_skill = None
            best_damage = 0
            
            for skill in state['damage_skills']:
                estimated_damage = self._estimate_skill_damage(skill, entity, target)
                if estimated_damage > best_damage:
                    best_damage = estimated_damage
                    best_skill = skill
            
            if best_skill:
                return {
                    'action': CombatAction.SKILL,
                    'skill': best_skill,
                    'targets': [target]
                }
        
        # Regular healing if health is below threshold
        if state['low_health'] and state['healing_skills']:
            heal_skill = max(state['healing_skills'], 
                            key=lambda s: s.power)
            targets = [entity]
            return {
                'action': CombatAction.SKILL,
                'skill': heal_skill,
                'targets': targets
            }
        
        # Heal allies if needed
        if state['low_health_allies'] and state['healing_skills']:
            lowest_health_ally = min(state['low_health_allies'], 
                                    key=lambda a: a.health / a.max_health)
            heal_skill = max(state['healing_skills'], 
                            key=lambda s: s.power)
            return {
                'action': CombatAction.SKILL,
                'skill': heal_skill,
                'targets': [lowest_health_ally]
            }
        
        # Defend if low health and no healing available
        if entity.health / entity.max_health < 0.3 and not state['healing_skills']:
            return {
                'action': CombatAction.DEFEND,
                'targets': []
            }
        
        # Default to attacking highest threat
        if state['threats']:
            target = state['threats'][0][0]
            return {
                'action': CombatAction.ATTACK,
                'targets': [target]
            }
        
        # No valid action found
        return {
            'action': CombatAction.DEFEND,
            'targets': []
        }
    
    def _estimate_skill_damage(self, skill, user, target):
        """
        Estimate the damage a skill would do to a target.
        
        Args:
            skill: Skill to estimate
            user: Entity using the skill
            target: Target entity
            
        Returns:
            Estimated damage value
        """
        if not isinstance(skill, DamageSkill):
            return 0
        
        # Base damage calculation
        if skill.damage_type == DamageType.PHYSICAL:
            base_damage = user.physical_attack
        else:
            base_damage = user.magical_attack
        
        # Apply skill power
        damage = base_damage * (skill.power / 100) * (1 + (skill.level - 1) * 0.1)
        
        # Apply target resistance
        resistance = target.get_resistance(skill.damage_type)
        damage *= (1 - resistance / 100)
        
        # Apply defense
        if skill.damage_type == DamageType.PHYSICAL:
            damage = max(1, damage - target.physical_defense * 0.5)
        elif skill.damage_type in [DamageType.MAGICAL, DamageType.FIRE, 
                                  DamageType.ICE, DamageType.LIGHTNING]:
            damage = max(1, damage - target.magical_defense * 0.5)
        
        return damage

class CombatLogManager:
    """Manages and formats combat logs for display."""
    
    def __init__(self, max_log_entries=100):
        """
        Initialize combat log manager.
        
        Args:
            max_log_entries: Maximum number of log entries to keep
        """
        self.logs = []
        self.max_log_entries = max_log_entries
    
    def add_log(self, message, entry_type="info", entity=None):
        """
        Add a log entry.
        
        Args:
            message: Log message
            entry_type: Type of log (info, attack, skill, item, effect, heal, damage)
            entity: Related entity (optional)
        """
        entry = {
            'message': message,
            'type': entry_type,
            'entity': entity.name if entity else None,
            'timestamp': datetime.datetime.now().strftime("%H:%M:%S")
        }
        
        self.logs.append(entry)
        
        # Trim logs if needed
        if len(self.logs) > self.max_log_entries:
            self.logs = self.logs[-self.max_log_entries:]
    
    def log_combat_start(self, combat):
        """
        Log the start of combat.
        
        Args:
            combat: Combat instance
        """
        entities = combat.turn_manager.entities
        player_entities = [e for e in entities if e.team == 0]
        enemy_entities = [e for e in entities if e.team == 1]
        
        player_names = ", ".join([e.name for e in player_entities])
        enemy_names = ", ".join([e.name for e in enemy_entities])
        
        message = f"Combat started! {player_names} vs {enemy_names}"
        self.add_log(message, "info")
    
    def log_turn_start(self, entity, turn_number):
        """
        Log the start of an entity's turn.
        
        Args:
            entity: Entity starting turn
            turn_number: Current turn number
        """
        message = f"Turn {turn_number}: {entity.name}'s turn"
        self.add_log(message, "info", entity)
    
    def log_attack(self, attacker, target, damage, critical=False, missed=False):
        """
        Log an attack action.
        
        Args:
            attacker: Attacking entity
            target: Target entity
            damage: Damage dealt
            critical: Whether the attack was critical
            missed: Whether the attack missed
        """
        if missed:
            message = f"{attacker.name} attacked {target.name} but missed!"
            self.add_log(message, "attack", attacker)
        else:
            crit_text = " (CRITICAL HIT!)" if critical else ""
            message = f"{attacker.name} attacked {target.name} for {damage} damage{crit_text}!"
            self.add_log(message, "attack", attacker)
    
    def log_skill_use(self, user, skill, targets, results):
        """
        Log a skill use action.
        
        Args:
            user: Entity using the skill
            skill: Skill used
            targets: List of target entities
            results: Skill results
        """
        target_names = ", ".join([t.name for t in targets])
        
        # Generic skill message
        message = f"{user.name} used {skill.name} on {target_names}!"
        self.add_log(message, "skill", user)
        
        # Log specific results based on skill type
        if isinstance(skill, DamageSkill):
            for i, target in enumerate(targets):
                result = results['targets'][i]
                damage = result['damage']
                critical = result['critical']
                
                crit_text = " (CRITICAL!)" if critical else ""
                damage_msg = f"{skill.name} dealt {damage} damage to {target.name}{crit_text}!"
                self.add_log(damage_msg, "damage")
                
        elif isinstance(skill, HealingSkill):
            for i, target in enumerate(targets):
                result = results['targets'][i]
                healing = result['healing']
                
                heal_msg = f"{skill.name} healed {target.name} for {healing} HP!"
                self.add_log(heal_msg, "heal")
                
        elif isinstance(skill, BuffSkill) or isinstance(skill, DebuffSkill):
            for i, target in enumerate(targets):
                result = results['targets'][i]
                effect = result['effect']
                duration = result['duration']
                applied = result['applied']
                
                if applied:
                    effect_msg = f"{effect} applied to {target.name} for {duration} turns!"
                    self.add_log(effect_msg, "effect")
                else:
                    if isinstance(skill, DebuffSkill) and 'hit' in result and not result['hit']:
                        resist_msg = f"{target.name} resisted {effect}!"
                        self.add_log(resist_msg, "effect")
                    else:
                        refresh_msg = f"{effect} refreshed on {target.name}!"
                        self.add_log(refresh_msg, "effect")
    
    def log_item_use(self, user, item, targets, results):
        """
        Log an item use action.
        
        Args:
            user: Entity using the item
            item: Item used
            targets: List of target entities
            results: Item results
        """
        target_names = ", ".join([t.name for t in targets])
        
        message = f"{user.name} used {item.name} on {target_names}!"
        self.add_log(message, "item", user)
        
        # Log specific results based on item type
        if isinstance(item, HealingItem):
            for i, target in enumerate(targets):
                result = results['targets'][i]
                healing = result['healing']
                
                heal_msg = f"{item.name} healed {target.name} for {healing} HP!"
                self.add_log(heal_msg, "heal")
    
    def log_defend(self, entity):
        """
        Log a defend action.
        
        Args:
            entity: Entity defending
        """
        message = f"{entity.name} is defending!"
        self.add_log(message, "info", entity)
    
    def log_flee(self, entity, success):
        """
        Log a flee action.
        
        Args:
            entity: Entity attempting to flee
            success: Whether the flee attempt was successful
        """
        if success:
            message = f"{entity.name} successfully fled from combat!"
        else:
            message = f"{entity.name} tried to flee but failed!"
        
        self.add_log(message, "info", entity)
    
    def log_status_effect(self, entity, effect_type, damage=None):
        """
        Log a status effect application or effect.
        
        Args:
            entity: Affected entity
            effect_type: Type of status effect
            damage: Damage dealt by the effect (if applicable)
        """
        if damage:
            message = f"{entity.name} took {damage} damage from {effect_type.name}!"
            self.add_log(message, "damage", entity)
        else:
            message = f"{effect_type.name} affecting {entity.name}!"
            self.add_log(message, "effect", entity)
    
    def log_status_effect_expire(self, entity, effect_type):
        """
        Log a status effect expiration.
        
        Args:
            entity: Affected entity
            effect_type: Type of status effect
        """
        message = f"{effect_type.name} expired on {entity.name}!"
        self.add_log(message, "effect", entity)
    
    def log_death(self, entity):
        """
        Log an entity's death.
        
        Args:
            entity: Entity that died
        """
        message = f"{entity.name} has been defeated!"
        self.add_log(message, "info", entity)
    
    def log_combat_end(self, winners_team):
        """
        Log the end of combat.
        
        Args:
            winners_team: Team identifier of winners
        """
        if winners_team == 0:
            message = "Victory! The players have won the battle!"
        elif winners_team == 1:
            message = "Defeat! The enemies have won the battle!"
        else:
            message = "The battle has ended in a draw!"
        
        self.add_log(message, "info")
    
    def log_rewards(self, rewards):
        """
        Log combat rewards.
        
        Args:
            rewards: Dictionary with reward information
        """
        message = f"Gained {rewards['experience']} XP and {rewards['gold']} gold!"
        self.add_log(message, "info")
        
        if rewards['items']:
            item_names = ", ".join([i for i in rewards['items']])
            item_msg = f"Found items: {item_names}"
            self.add_log(item_msg, "info")
    
    def get_logs(self, count=None, types=None):
        """
        Get filtered logs.
        
        Args:
            count: Number of logs to return (None for all)
            types: List of log types to include (None for all)
            
        Returns:
            List of log entries
        """
        filtered_logs = self.logs
        
        if types:
            filtered_logs = [log for log in filtered_logs if log['type'] in types]
        
        if count:
            filtered_logs = filtered_logs[-count:]
        
        return filtered_logs
    
    def get_formatted_logs(self, count=None, types=None, include_timestamp=True):
        """
        Get formatted logs as strings.
        
        Args:
            count: Number of logs to return (None for all)
            types: List of log types to include (None for all)
            include_timestamp: Whether to include timestamps
            
        Returns:
            List of formatted log strings
        """
        logs = self.get_logs(count, types)
        
        formatted = []
        for log in logs:
            if include_timestamp:
                formatted.append(f"[{log['timestamp']}] {log['message']}")
            else:
                formatted.append(log['message'])
        
        return formatted
    
    def clear_logs(self):
        """Clear all logs."""
        self.logs = []

import datetime
import json
import random
import math
from enum import Enum

class PlayerCharacter(CombatEntity):
    """Player character entity with RPG stats and progression."""
    
    def __init__(self, name, character_class="warrior", level=1):
        """
        Initialize a player character.
        
        Args:
            name: Character name
            character_class: Character class (warrior, mage, rogue, etc.)
            level: Starting level
        """
        super().__init__(name, level, team=0)
        self.character_class = character_class
        self.experience = 0
        self.experience_next_level = 100  # XP needed for next level
        self.gold = 0
        self.inventory = []
        self.equipment = {
            'weapon': None,
            'armor': None,
            'helmet': None,
            'accessory': None
        }
        
        # Set base stats according to class
        self._initialize_class_stats(character_class)
        
        # Apply level-ups
        for _ in range(level - 1):
            self._level_up_stats()
        
        # Add class-specific skills
        self._initialize_class_skills(character_class)
        
        # Update derived stats
        self._update_derived_stats()
    
    def add_experience(self, amount):
        """
        Add experience points and handle level ups.
        
        Args:
            amount: Amount of experience to add
            
        Returns:
            Dict with level up information if leveled up
        """
        self.experience += amount
        
        level_ups = 0
        level_up_stats = []
        
        # Check for level ups
        while self.experience >= self.experience_next_level:
            level_ups += 1
            self.level += 1
            
            # Record current stats before level up
            old_stats = {
                'max_health': self.max_health,
                'max_mana': self.max_mana,
                'strength': self.strength,
                'intelligence': self.intelligence,
                'dexterity': self.dexterity,
                'constitution': self.constitution,
                'speed': self.speed
            }
            
            # Apply level up stat increases
            stats_increased = self._level_up_stats()
            
            # Calculate new stats
            self._update_derived_stats()
            
            # Record stat increases
            stat_increases = {
                'level': self.level,
                'max_health': self.max_health - old_stats['max_health'],
                'max_mana': self.max_mana - old_stats['max_mana'],
                'stats_increased': stats_increased
            }
            
            level_up_stats.append(stat_increases)
            
            # Set new XP threshold (increases with each level)
            self.experience_next_level = int(self.experience_next_level * 1.5)
        
        if level_ups > 0:
            # Fully heal on level up
            self.health = self.max_health
            self.mana = self.max_mana
            
            return {
                'level_ups': level_ups,
                'new_level': self.level,
                'stat_increases': level_up_stats,
                'next_level_xp': self.experience_next_level
            }
        
        return None
    
    def _level_up_stats(self):
        """
        Increase stats based on character class when leveling up.
        
        Returns:
            List of stats that were increased
        """
        stats_increased = []
        
        # Base stat increases
        self.max_health += 10
        self.max_mana += 5
        stats_increased.append('max_health')
        stats_increased.append('max_mana')
        
        # Class-specific stat increases
        if self.character_class == "warrior":
            self.strength += 2
            self.constitution += 1
            if random.random() < 0.5:
                self.dexterity += 1
                stats_increased.append('dexterity')
            stats_increased.append('strength')
            stats_increased.append('constitution')
            
        elif self.character_class == "mage":
            self.intelligence += 2
            self.max_mana += 5  # Extra mana for mages
            if random.random() < 0.5:
                self.dexterity += 1
                stats_increased.append('dexterity')
            stats_increased.append('intelligence')
            stats_increased.append('max_mana')
            
        elif self.character_class == "rogue":
            self.dexterity += 2
            self.strength += 1
            if random.random() < 0.5:
                self.intelligence += 1
                stats_increased.append('intelligence')
            stats_increased.append('dexterity')
            stats_increased.append('strength')
            
        elif self.character_class == "cleric":
            self.intelligence += 1
            self.constitution += 1
            self.max_mana += 3  # Extra mana for clerics
            stats_increased.append('intelligence')
            stats_increased.append('constitution')
            stats_increased.append('max_mana')
            
        else:  # balanced
            # Distribute points randomly
            stats = ['strength', 'intelligence', 'dexterity', 'constitution', 'speed']
            for _ in range(3):
                stat = random.choice(stats)
                if stat == 'strength':
                    self.strength += 1
                elif stat == 'intelligence':
                    self.intelligence += 1
                elif stat == 'dexterity':
                    self.dexterity += 1
                elif stat == 'constitution':
                    self.constitution += 1
                elif stat == 'speed':
                    self.speed += 1
                
                if stat not in stats_increased:
                    stats_increased.append(stat)
        
        return stats_increased
    
    def add_item_to_inventory(self, item):
        """
        Add an item to the character's inventory.
        
        Args:
            item: Item to add
            
        Returns:
            Boolean indicating success
        """
        self.inventory.append(item)
        return True
    
    def remove_item_from_inventory(self, item):
        """
        Remove an item from the character's inventory.
        
        Args:
            item: Item to remove
            
        Returns:
            Boolean indicating success
        """
        if item in self.inventory:
            self.inventory.remove(item)
            return True
        return False
    
    def equip_item(self, item):
        """
        Equip an item and apply its stat bonuses.
        
        Args:
            item: Item to equip
            
        Returns:
            Previously equipped item or None
        """
        if item not in self.inventory:
            return None
        
        slot = item.slot
        previously_equipped = self.equipment[slot]
        
        # Unequip previous item
        if previously_equipped:
            self._apply_item_stats(previously_equipped, remove=True)
            self.inventory.append(previously_equipped)
        
        # Equip new item
        self.equipment[slot] = item
        self._apply_item_stats(item)
        self.inventory.remove(item)
        
        # Update derived stats
        self._update_derived_stats()
        
        return previously_equipped
    
    def unequip_item(self, slot):
        """
        Unequip an item from a slot and remove its stat bonuses.
        
        Args:
            slot: Equipment slot
            
        Returns:
            Unequipped item or None
        """
        if slot not in self.equipment or not self.equipment[slot]:
            return None
        
        item = self.equipment[slot]
        
        # Remove stat bonuses
        self._apply_item_stats(item, remove=True)
        
        # Unequip
        self.equipment[slot] = None
        
        # Add to inventory
        self.inventory.append(item)
        
        # Update derived stats
        self._update_derived_stats()
        
        return item
    
    def _apply_item_stats(self, item, remove=False):
        """
        Apply or remove an item's stat bonuses.
        
        Args:
            item: Item to apply stats for
            remove: Whether to remove (True) or add (False) stats
        """
        multiplier = -1 if remove else 1
        
        for stat, value in item.stat_bonuses.items():
            if stat == 'strength':
                self.strength += value * multiplier
            elif stat == 'intelligence':
                self.intelligence += value * multiplier
            elif stat == 'dexterity':
                self.dexterity += value * multiplier
            elif stat == 'constitution':
                self.constitution += value * multiplier
            elif stat == 'speed':
                self.speed += value * multiplier
            elif stat == 'physical_attack':
                self.physical_attack += value * multiplier
            elif stat == 'magical_attack':
                self.magical_attack += value * multiplier
            elif stat == 'physical_defense':
                self.physical_defense += value * multiplier
            elif stat == 'magical_defense':
                self.magical_defense += value * multiplier
    
    def rest(self):
        """
        Rest to recover health and mana.
        
        Returns:
            Dict with recovery information
        """
        old_health = self.health
        old_mana = self.mana
        
        # Fully restore health and mana
        self.health = self.max_health
        self.mana = self.max_mana
        
        # Clear status effects
        self.status_effects = []
        
        return {
            'health_restored': self.health - old_health,
            'mana_restored': self.mana - old_mana
        }
    
    def use_item_from_inventory(self, item_index, targets=None):
        """
        Use an item from inventory.
        
        Args:
            item_index: Index of item in inventory
            targets: Target entities (default: self)
            
        Returns:
            Item use result or None if invalid
        """
        if item_index < 0 or item_index >= len(self.inventory):
            return None
        
        item = self.inventory[item_index]
        
        # Set default target to self if not specified
        if targets is None:
            targets = [self]
        
        # Use the item
        result = item.use(self, targets)
        
        # Remove if consumable
        if item.consumable and result['success']:
            self.inventory.pop(item_index)
        
        return result
    
    def to_dict(self):
        """Convert to dictionary for serialization."""
        data = super().to_dict()
        data.update({
            'character_class': self.character_class,
            'experience': self.experience,
            'experience_next_level': self.experience_next_level,
            'gold': self.gold,
            'inventory': [item.to_dict() for item in self.inventory],
            'equipment': {
                k: v.to_dict() if v else None for k, v in self.equipment.items()
            }
        })
        return data
    
    @classmethod
    def from_dict(cls, data):
        """Create from dictionary."""
        character = cls(
            data['name'],
            data['character_class'],
            data['level']
        )
        
        character.experience = data['experience']
        character.experience_next_level = data['experience_next_level']
        character.gold = data['gold']
        
        # Base entity properties
        character.max_health = data['max_health']
        character.health = data['health']
        character.max_mana = data['max_mana']
        character.mana = data['mana']
        character.strength = data['strength']
        character.intelligence = data['intelligence']
        character.dexterity = data['dexterity']
        character.constitution = data['constitution']
        character.speed = data['speed']
        character.resistances = {DamageType(k): v for k, v in data['resistances'].items()}
        character.status_effects = [StatusEffectInstance.from_dict(e) for e in data['status_effects']]
        character.is_dead = data['is_dead']
        
        # Equipment and inventory would need to be loaded separately
        
        return character
    
    def _initialize_class_stats(self, character_class):
        """
        Initialize base stats according to character class.
        
        Args:
            character_class: Character class string
        """
        if character_class == "warrior":
            self.strength = 14
            self.intelligence = 8
            self.dexterity = 10
            self.constitution = 12
            self.speed = 9
            
        elif character_class == "mage":
            self.strength = 7
            self.intelligence = 15
            self.dexterity = 9
            self.constitution = 8
            self.speed = 10
            
        elif character_class == "rogue":
            self.strength = 10
            self.intelligence = 10
            self.dexterity = 15
            self.constitution = 8
            self.speed = 12
            
        elif character_class == "cleric":
            self.strength = 9
            self.intelligence = 12
            self.dexterity = 8
            self.constitution = 10
            self.speed = 8
            
        else:  # balanced
            self.strength = 10
            self.intelligence = 10
            self.dexterity = 10
            self.constitution = 10
            self.speed = 10
    
    def _initialize_class_skills(self, character_class):
        """
        Initialize skills according to character class.
        
        Args:
            character_class: Character class string
        """
        if character_class == "warrior":
            # Warrior skills
            self.skills.append(DamageSkill(
                "Power Strike", 
                "A powerful strike that deals 150% physical damage.",
                DamageType.PHYSICAL, 
                150, 
                10, 
                2
            ))
            
            self.skills.append(BuffSkill(
                "Battle Stance", 
                "Increases strength for 3 turns.",
                StatusEffect.STRENGTHENED, 
                3, 
                1.5, 
                15, 
                3
            ))
            
            self.skills.append(DamageSkill(
                "Cleave", 
                "Attacks all enemies for 120% physical damage.",
                DamageType.PHYSICAL, 
                120, 
                20, 
                4
            ))
            
        elif character_class == "mage":
            # Mage skills
            self.skills.append(DamageSkill(
                "Fireball", 
                "Launches a ball of fire dealing 170% fire damage.",
                DamageType.FIRE, 
                170, 
                15, 
                2
            ))
            
            self.skills.append(DamageSkill(
                "Ice Spike", 
                "Launches a spike of ice dealing 150% ice damage with a chance to slow.",
                DamageType.ICE, 
                150, 
                12, 
                2
            ))
            
            self.skills.append(DebuffSkill(
                "Weaken", 
                "Weakens an enemy, reducing their damage for 3 turns.",
                StatusEffect.WEAKENED, 
                3, 
                1.5, 
                18, 
                3
            ))
            
        elif character_class == "rogue":
            # Rogue skills
            self.skills.append(DamageSkill(
                "Backstab", 
                "A precise strike that deals 200% physical damage with high critical chance.",
                DamageType.PHYSICAL, 
                200, 
                12, 
                2
            ))
            
            self.skills.append(BuffSkill(
                "Evasive Stance", 
                "Increases evasion for 3 turns.",
                StatusEffect.HASTED, 
                3, 
                1.5, 
                15, 
                3
            ))
            
            self.skills.append(DamageSkill(
                "Poison Strike", 
                "Attacks with a poisoned weapon dealing 120% physical damage and applying poison.",
                DamageType.POISON, 
                120, 
                18, 
                3
            ))
            
        elif character_class == "cleric":
            # Cleric skills
            self.skills.append(HealingSkill(
                "Heal", 
                "Heals a target for 200% healing power.",
                200, 
                15, 
                2
            ))
            
            self.skills.append(BuffSkill(
                "Divine Protection", 
                "Grants protection to ally for 3 turns.",
                StatusEffect.PROTECTED, 
                3, 
                1.5, 
                18, 
                3
            ))
            
            self.skills.append(DamageSkill(
                "Holy Smite", 
                "Smites an enemy with holy power dealing 150% magical damage.",
                DamageType.MAGICAL, 
                150, 
                20, 
                3
            ))
            
        else:  # balanced
            # Balanced class skills
            self.skills.append(DamageSkill(
                "Focused Strike", 
                "A balanced attack dealing 140% physical damage.",
                DamageType.PHYSICAL, 
                140, 
                10, 
                2
            ))
            
            self.skills.append(HealingSkill(
                "First Aid", 
                "Heals a target for 150% healing power.",
                150, 
                12, 
                3
            ))
            
            self.skills.append(BuffSkill(
                "Focus", 
                "Increases critical chance for 3 turns.",
                StatusEffect.STRENGTHENED, 
                3, 
                1.2, 
                15, 
                3
            ))