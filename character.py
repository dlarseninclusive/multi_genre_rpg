import random
import logging
from enum import Enum

logger = logging.getLogger("character")

class Race(Enum):
    """Character races."""
    HUMAN = 0
    ELF = 1
    DWARF = 2
    ORC = 3

class CharacterClass(Enum):
    """Character classes."""
    WARRIOR = 0
    MAGE = 1
    ROGUE = 2
    CLERIC = 3

class Stat:
    """Representation of a single character stat with base value and modifiers."""
    
    def __init__(self, base_value=10):
        """
        Initialize a stat.
        
        Args:
            base_value: Base value for the stat
        """
        self.base_value = base_value
        self.modifiers = []  # List of (value, source, duration)
    
    @property
    def value(self):
        """Get the total value including all modifiers."""
        total = self.base_value
        
        # Add all active modifiers
        for mod_value, _, _ in self.modifiers:
            total += mod_value
        
        return total
    
    def add_modifier(self, value, source, duration=None):
        """
        Add a modifier to this stat.
        
        Args:
            value: Modifier value
            source: Source of the modifier (e.g., "Magic Sword")
            duration: Optional duration in turns (None for permanent)
        """
        self.modifiers.append((value, source, duration))
    
    def remove_modifier(self, source):
        """
        Remove all modifiers from a specific source.
        
        Args:
            source: Source to remove modifiers from
        """
        self.modifiers = [mod for mod in self.modifiers if mod[1] != source]
    
    def update(self):
        """Update the stat, reducing durations of temporary modifiers."""
        # Keep track of modifiers to keep
        kept_modifiers = []
        
        for value, source, duration in self.modifiers:
            # Keep permanent modifiers
            if duration is None:
                kept_modifiers.append((value, source, duration))
            # Reduce duration for temporary modifiers
            elif duration > 1:
                kept_modifiers.append((value, source, duration - 1))
            # Remove expired modifiers
            else:
                logger.debug(f"Modifier {value} from {source} expired")
        
        self.modifiers = kept_modifiers
    
    def to_dict(self):
        """Convert to dictionary for serialization."""
        return {
            'base_value': self.base_value,
            'modifiers': self.modifiers
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create from dictionary."""
        stat = cls(data['base_value'])
        stat.modifiers = data['modifiers']
        return stat

class Character:
    """Player or NPC character."""
    
    def __init__(self, name, race, character_class):
        """
        Initialize a character.
        
        Args:
            name: Character name
            race: Character race (from Race enum)
            character_class: Character class (from CharacterClass enum)
        """
        self.name = name
        self.race = race
        self.character_class = character_class
        
        # Initialize stats
        self.stats = {
            'strength': Stat(),
            'dexterity': Stat(),
            'constitution': Stat(),
            'intelligence': Stat(),
            'wisdom': Stat(),
            'charisma': Stat()
        }
        
        # Set racial stat bonuses
        self._apply_racial_bonuses()
        
        # Set class stat bonuses
        self._apply_class_bonuses()
        
        # Derived attributes
        self.max_health = 10 + self.stats['constitution'].value
        self.health = self.max_health
        self.max_mana = 10 + self.stats['intelligence'].value
        self.mana = self.max_mana
        
        # Level and experience
        self.level = 1
        self.experience = 0
        self.next_level_exp = 100
        
        # Equipment slots
        self.equipment = {
            'head': None,
            'chest': None,
            'legs': None,
            'feet': None,
            'main_hand': None,
            'off_hand': None,
            'accessory': None
        }
        
        # Inventory
        self.inventory = []
        self.max_inventory_slots = 20
        
        # Skills and abilities
        self.skills = self._get_starting_skills()
        
        # Status effects
        self.status_effects = []  # List of (effect, source, duration)
        
        logger.info(f"Created character: {name} ({race.name} {character_class.name})")
    
    def _apply_racial_bonuses(self):
        """Apply stat bonuses based on race."""
        if self.race == Race.HUMAN:
            # Humans get +1 to all stats
            for stat in self.stats.values():
                stat.add_modifier(1, "Human Versatility")
        
        elif self.race == Race.ELF:
            # Elves get +2 Dexterity, +2 Intelligence, -1 Constitution
            self.stats['dexterity'].add_modifier(2, "Elven Grace")
            self.stats['intelligence'].add_modifier(2, "Elven Wisdom")
            self.stats['constitution'].add_modifier(-1, "Elven Frailty")
        
        elif self.race == Race.DWARF:
            # Dwarves get +2 Constitution, +1 Strength, -1 Charisma
            self.stats['constitution'].add_modifier(2, "Dwarven Resilience")
            self.stats['strength'].add_modifier(1, "Dwarven Tough")
            self.stats['charisma'].add_modifier(-1, "Dwarven Gruffness")
        
        elif self.race == Race.ORC:
            # Orcs get +3 Strength, +1 Constitution, -2 Intelligence, -1 Charisma
            self.stats['strength'].add_modifier(3, "Orcish Might")
            self.stats['constitution'].add_modifier(1, "Orcish Toughness")
            self.stats['intelligence'].add_modifier(-2, "Orcish Simple-mindedness")
            self.stats['charisma'].add_modifier(-1, "Orcish Intimidation")
    
    def _apply_class_bonuses(self):
        """Apply stat bonuses based on character class."""
        if self.character_class == CharacterClass.WARRIOR:
            # Warriors get +2 Strength, +1 Constitution
            self.stats['strength'].add_modifier(2, "Warrior Training")
            self.stats['constitution'].add_modifier(1, "Warrior Toughness")
        
        elif self.character_class == CharacterClass.MAGE:
            # Mages get +2 Intelligence, +1 Wisdom
            self.stats['intelligence'].add_modifier(2, "Mage Study")
            self.stats['wisdom'].add_modifier(1, "Mage Knowledge")
        
        elif self.character_class == CharacterClass.ROGUE:
            # Rogues get +2 Dexterity, +1 Charisma
            self.stats['dexterity'].add_modifier(2, "Rogue Agility")
            self.stats['charisma'].add_modifier(1, "Rogue Charm")
        
        elif self.character_class == CharacterClass.CLERIC:
            # Clerics get +2 Wisdom, +1 Charisma
            self.stats['wisdom'].add_modifier(2, "Cleric Faith")
            self.stats['charisma'].add_modifier(1, "Cleric Presence")
    
    def _get_starting_skills(self):
        """Get starting skills based on character class."""
        skills = []
        
        if self.character_class == CharacterClass.WARRIOR:
            skills = ["Slash", "Defend", "Taunt"]
        
        elif self.character_class == CharacterClass.MAGE:
            skills = ["Fireball", "Magic Shield", "Analyze"]
        
        elif self.character_class == CharacterClass.ROGUE:
            skills = ["Backstab", "Pickpocket", "Detect Traps"]
        
        elif self.character_class == CharacterClass.CLERIC:
            skills = ["Heal", "Smite", "Bless"]
        
        return skills
    
    def gain_experience(self, amount):
        """
        Add experience points and handle level up.
        
        Args:
            amount: Amount of experience to add
        
        Returns:
            Boolean indicating if level up occurred
        """
        self.experience += amount
        logger.info(f"{self.name} gained {amount} experience ({self.experience}/{self.next_level_exp})")
        
        if self.experience >= self.next_level_exp:
            self._level_up()
            return True
        return False

    def gain_combat_experience(self, enemies_defeated):
        """
        Gain experience from defeated enemies.
        
        Args:
            enemies_defeated: List of defeated enemy entities
            
        Returns:
            Total XP gained
        """
        total_xp = 0
        for enemy in enemies_defeated:
            xp = enemy.level * 10
            if enemy.level > self.level:
                xp = int(xp * 1.5)
            elif enemy.level < self.level - 3:
                xp = max(1, xp // 2)
            total_xp += xp
        self.gain_experience(total_xp)
        return total_xp
    
    def _level_up(self):
        """Handle level up effects."""
        self.level += 1
        logger.info(f"{self.name} reached level {self.level}!")
        
        # Increase stats based on character class
        if self.character_class == CharacterClass.WARRIOR:
            self.stats['strength'].base_value += 2
            self.stats['constitution'].base_value += 1
        
        elif self.character_class == CharacterClass.MAGE:
            self.stats['intelligence'].base_value += 2
            self.stats['wisdom'].base_value += 1
        
        elif self.character_class == CharacterClass.ROGUE:
            self.stats['dexterity'].base_value += 2
            self.stats['charisma'].base_value += 1
        
        elif self.character_class == CharacterClass.CLERIC:
            self.stats['wisdom'].base_value += 2
            self.stats['charisma'].base_value += 1
        
        # Increase health and mana
        old_max_health = self.max_health
        old_max_mana = self.max_mana
        
        self.max_health = 10 + (self.level * 5) + self.stats['constitution'].value
        self.max_mana = 10 + (self.level * 3) + self.stats['intelligence'].value
        
        # Heal to full on level up
        self.health = self.max_health
        self.mana = self.max_mana
        
        logger.info(f"Health increased: {old_max_health} -> {self.max_health}")
        logger.info(f"Mana increased: {old_max_mana} -> {self.max_mana}")
        
        # Calculate next level experience requirement
        self.next_level_exp = int(self.next_level_exp * 1.5)
    
    def equip(self, item, slot):
        """
        Equip an item to a slot.
        
        Args:
            item: Item to equip
            slot: Slot to equip to
            
        Returns:
            Item that was previously equipped (None if slot was empty)
        """
        if slot not in self.equipment:
            logger.warning(f"Invalid equipment slot: {slot}")
            return None
        
        # Check if item can be equipped to this slot
        if slot not in item.valid_slots:
            logger.warning(f"Cannot equip {item.name} to {slot}")
            return None
        
        # Store previously equipped item
        old_item = self.equipment[slot]
        
        # Apply stat changes
        if old_item:
            # Remove old item bonuses
            for stat_name, bonus in old_item.stat_bonuses.items():
                if stat_name in self.stats:
                    self.stats[stat_name].remove_modifier(old_item.name)
        
        # Add new item bonuses
        for stat_name, bonus in item.stat_bonuses.items():
            if stat_name in self.stats:
                self.stats[stat_name].add_modifier(bonus, item.name)
        
        # Update equipment
        self.equipment[slot] = item
        
        # Remove item from inventory if it was there
        if item in self.inventory:
            self.inventory.remove(item)
        
        logger.info(f"{self.name} equipped {item.name} to {slot}")
        return old_item
    
    def unequip(self, slot):
        """
        Unequip an item from a slot.
        
        Args:
            slot: Slot to unequip from
            
        Returns:
            Item that was unequipped (None if slot was empty)
        """
        if slot not in self.equipment:
            logger.warning(f"Invalid equipment slot: {slot}")
            return None
        
        # Get equipped item
        item = self.equipment[slot]
        
        if not item:
            logger.warning(f"No item equipped in {slot}")
            return None
        
        # Remove stat bonuses
        for stat_name, bonus in item.stat_bonuses.items():
            if stat_name in self.stats:
                self.stats[stat_name].remove_modifier(item.name)
        
        # Update equipment
        self.equipment[slot] = None
        
        # Add to inventory if there's space
        if len(self.inventory) < self.max_inventory_slots:
            self.inventory.append(item)
            logger.info(f"{self.name} unequipped {item.name} from {slot} to inventory")
            return item
        else:
            logger.warning(f"Inventory full, cannot add {item.name}")
            return item
    
    def add_to_inventory(self, item):
        """
        Add an item to inventory.
        
        Args:
            item: Item to add
            
        Returns:
            Boolean indicating success
        """
        if len(self.inventory) >= self.max_inventory_slots:
            logger.warning(f"Cannot add {item.name} to inventory: full")
            return False
        
        self.inventory.append(item)
        logger.info(f"{self.name} added {item.name} to inventory")
        return True
    
    def remove_from_inventory(self, item):
        """
        Remove an item from inventory.
        
        Args:
            item: Item to remove
            
        Returns:
            Boolean indicating success
        """
        if item in self.inventory:
            self.inventory.remove(item)
            logger.info(f"{self.name} removed {item.name} from inventory")
            return True
        else:
            logger.warning(f"Cannot remove {item.name} from inventory: not found")
            return False
    
    def use_item(self, item):
        """
        Use an item from inventory.
        
        Args:
            item: Item to use
            
        Returns:
            Boolean indicating if item was used successfully
        """
        if item not in self.inventory:
            logger.warning(f"Cannot use {item.name}: not in inventory")
            return False
        
        # Apply item effects
        used = item.use(self)
        
        if used:
            # Remove if consumable
            if item.consumable:
                self.inventory.remove(item)
                logger.info(f"{self.name} used and consumed {item.name}")
            else:
                logger.info(f"{self.name} used {item.name}")
            
            return True
        else:
            logger.warning(f"Could not use {item.name}")
            return False
    
    def take_damage(self, amount, source=None):
        """
        Damage the character.
        
        Args:
            amount: Amount of damage
            source: Source of the damage (for logging)
            
        Returns:
            Actual damage taken
        """
        # Apply damage reduction from armor, etc.
        # For simplicity, we'll just use a flat reduction based on constitution
        damage_reduction = max(0, self.stats['constitution'].value // 4)
        actual_damage = max(1, amount - damage_reduction)
        
        self.health -= actual_damage
        
        if source:
            logger.info(f"{self.name} took {actual_damage} damage from {source} ({self.health}/{self.max_health})")
        else:
            logger.info(f"{self.name} took {actual_damage} damage ({self.health}/{self.max_health})")
        
        # Check for death
        if self.health <= 0:
            self.health = 0
            logger.info(f"{self.name} was defeated!")
        
        return actual_damage
    
    def heal(self, amount, source=None):
        """
        Heal the character.
        
        Args:
            amount: Amount to heal
            source: Source of healing (for logging)
            
        Returns:
            Actual amount healed
        """
        old_health = self.health
        self.health = min(self.max_health, self.health + amount)
        actual_heal = self.health - old_health
        
        if source:
            logger.info(f"{self.name} healed {actual_heal} from {source} ({self.health}/{self.max_health})")
        else:
            logger.info(f"{self.name} healed {actual_heal} ({self.health}/{self.max_health})")
        
        return actual_heal
    
    def spend_mana(self, amount):
        """
        Spend mana for a spell/ability.
        
        Args:
            amount: Amount of mana to spend
            
        Returns:
            Boolean indicating if there was enough mana
        """
        if self.mana >= amount:
            self.mana -= amount
            logger.info(f"{self.name} spent {amount} mana ({self.mana}/{self.max_mana})")
            return True
        else:
            logger.warning(f"{self.name} tried to spend {amount} mana but only has {self.mana}")
            return False
    
    def restore_mana(self, amount):
        """
        Restore mana.
        
        Args:
            amount: Amount of mana to restore
            
        Returns:
            Actual amount restored
        """
        old_mana = self.mana
        self.mana = min(self.max_mana, self.mana + amount)
        actual_restore = self.mana - old_mana
        
        logger.info(f"{self.name} restored {actual_restore} mana ({self.mana}/{self.max_mana})")
        return actual_restore
    
    def add_status_effect(self, effect, source, duration):
        """
        Add a status effect to the character.
        
        Args:
            effect: Effect name
            source: Source of the effect
            duration: Duration in turns
        """
        self.status_effects.append((effect, source, duration))
        logger.info(f"{self.name} gained status effect: {effect} from {source} for {duration} turns")
    
    def remove_status_effect(self, effect):
        """
        Remove a status effect.
        
        Args:
            effect: Effect name to remove
            
        Returns:
            Boolean indicating if effect was removed
        """
        for i, (eff, src, dur) in enumerate(self.status_effects):
            if eff == effect:
                del self.status_effects[i]
                logger.info(f"{self.name} lost status effect: {effect}")
                return True
        
        logger.warning(f"{self.name} tried to remove status effect {effect} but doesn't have it")
        return False
    
    def update_status_effects(self):
        """Update status effects, reducing durations."""
        new_effects = []
        
        for effect, source, duration in self.status_effects:
            # Reduce duration
            if duration > 1:
                new_effects.append((effect, source, duration - 1))
            else:
                logger.info(f"{self.name}'s status effect {effect} from {source} expired")
        
        self.status_effects = new_effects
    
    def update(self):
        """Update character state for a new turn."""
        # Update all stats
        for stat in self.stats.values():
            stat.update()
        
        # Update status effects
        self.update_status_effects()
    
    def to_dict(self):
        """Convert to dictionary for serialization."""
        return {
            'name': self.name,
            'race': self.race.value,
            'character_class': self.character_class.value,
            'stats': {k: v.to_dict() for k, v in self.stats.items()},
            'health': self.health,
            'max_health': self.max_health,
            'mana': self.mana,
            'max_mana': self.max_mana,
            'level': self.level,
            'experience': self.experience,
            'next_level_exp': self.next_level_exp,
            'equipment': {k: v.to_dict() if v else None for k, v in self.equipment.items()},
            'inventory': [item.to_dict() for item in self.inventory],
            'skills': self.skills,
            'status_effects': self.status_effects
        }
    
    @classmethod
    def from_dict(cls, data, item_factory):
        """
        Create character from dictionary.
        
        Args:
            data: Dictionary data
            item_factory: Function to create items from dictionary
        """
        character = cls(
            data['name'],
            Race(data['race']),
            CharacterClass(data['character_class'])
        )
        
        # Restore stats
        for stat_name, stat_data in data['stats'].items():
            character.stats[stat_name] = Stat.from_dict(stat_data)
        
        # Restore other properties
        character.health = data['health']
        character.max_health = data['max_health']
        character.mana = data['mana']
        character.max_mana = data['max_mana']
        character.level = data['level']
        character.experience = data['experience']
        character.next_level_exp = data['next_level_exp']
        
        # Restore equipment
        for slot, item_data in data['equipment'].items():
            if item_data:
                character.equipment[slot] = item_factory(item_data)
        
        # Restore inventory
        character.inventory = [item_factory(item_data) for item_data in data['inventory']]
        
        # Restore skills and status effects
        character.skills = data['skills']
        character.status_effects = data['status_effects']
        
        return character


class CharacterFactory:
    """Factory for creating characters with random names and attributes."""
    
    def __init__(self):
        """Initialize the character factory."""
        # Name generation data
        self.name_prefixes = {
            Race.HUMAN: ["Al", "Bran", "Cal", "Don", "Ed", "Fran", "Greg", "Hen", "Ian", "Jo"],
            Race.ELF: ["Aer", "Bel", "Cel", "Del", "El", "Fae", "Gal", "Hal", "Il", "Jal"],
            Race.DWARF: ["Bor", "Dur", "Gar", "Gim", "Kaz", "Mor", "Nor", "Thor", "Thr", "Ul"],
            Race.ORC: ["Bru", "Gru", "Kra", "Kru", "Mug", "Nar", "Org", "Rok", "Ug", "Zug"]
        }
        
        self.name_suffixes = {
            Race.HUMAN: ["bert", "don", "fred", "gar", "man", "ric", "son", "ton", "vic", "win"],
            Race.ELF: ["arian", "driel", "ithil", "lian", "mar", "nor", "rian", "thien", "wyn", "zar"],
            Race.DWARF: ["ar", "din", "drin", "grim", "li", "lin", "min", "nor", "rin", "thor"],
            Race.ORC: ["ak", "gar", "gash", "grub", "kk", "mar", "nak", "rag", "rok", "zog"]
        }
    
    def generate_name(self, race):
        """
        Generate a random name based on race.
        
        Args:
            race: Character race
            
        Returns:
            Random name string
        """
        prefix = random.choice(self.name_prefixes.get(race, self.name_prefixes[Race.HUMAN]))
        suffix = random.choice(self.name_suffixes.get(race, self.name_suffixes[Race.HUMAN]))
        return prefix + suffix
    
    def create_character(self, name=None, race=None, character_class=None):
        """
        Create a character with optional random attributes.
        
        Args:
            name: Character name (None for random)
            race: Character race (None for random)
            character_class: Character class (None for random)
            
        Returns:
            New Character instance
        """
        # Choose random race if not specified
        if race is None:
            race = random.choice(list(Race))
        
        # Choose random class if not specified
        if character_class is None:
            character_class = random.choice(list(CharacterClass))
        
        # Generate name if not specified
        if name is None:
            name = self.generate_name(race)
        
        return Character(name, race, character_class)

