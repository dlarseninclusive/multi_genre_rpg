import random
import logging
from enum import Enum

logger = logging.getLogger("inventory")

class ItemRarity(Enum):
    """Item rarity levels."""
    COMMON = 0
    UNCOMMON = 1
    RARE = 2
    EPIC = 3
    LEGENDARY = 4

class ItemType(Enum):
    """Types of items."""
    WEAPON = 0
    ARMOR = 1
    ACCESSORY = 2
    CONSUMABLE = 3
    QUEST = 4
    MATERIAL = 5

class Item:
    """Base class for all items."""
    
    def __init__(self, name, description, item_type, rarity=ItemRarity.COMMON, value=1, weight=1):
        """
        Initialize an item.
        
        Args:
            name: Item name
            description: Item description
            item_type: Type from ItemType enum
            rarity: Rarity from ItemRarity enum
            value: Gold value
            weight: Weight in inventory
        """
        self.name = name
        self.description = description
        self.item_type = item_type
        self.rarity = rarity
        self.value = value
        self.weight = weight
        
        # Default properties
        self.consumable = False
        self.valid_slots = []
        self.stat_bonuses = {}
        
        logger.debug(f"Created item: {name} ({item_type.name}, {rarity.name})")
    
    def use(self, character):
        """
        Use the item (base implementation does nothing).
        
        Args:
            character: Character using the item
            
        Returns:
            Boolean indicating if item was used successfully
        """
        logger.warning(f"Item {self.name} has no use effect")
        return False
    
    def to_dict(self):
        """Convert to dictionary for serialization."""
        return {
            'name': self.name,
            'description': self.description,
            'item_type': self.item_type.value,
            'rarity': self.rarity.value,
            'value': self.value,
            'weight': self.weight,
            'consumable': self.consumable,
            'valid_slots': self.valid_slots,
            'stat_bonuses': self.stat_bonuses,
            'class': self.__class__.__name__
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create from dictionary."""
        item = cls(
            data['name'],
            data['description'],
            ItemType(data['item_type']),
            ItemRarity(data['rarity']),
            data['value'],
            data['weight']
        )
        item.consumable = data['consumable']
        item.valid_slots = data['valid_slots']
        item.stat_bonuses = data['stat_bonuses']
        return item


class Weapon(Item):
    """Weapon item that can be equipped."""
    
    def __init__(self, name, description, weapon_type, damage, rarity=ItemRarity.COMMON, value=10, weight=2):
        """
        Initialize a weapon.
        
        Args:
            name: Weapon name
            description: Weapon description
            weapon_type: Type of weapon (e.g., "Sword", "Bow")
            damage: Base damage
            rarity: Rarity from ItemRarity enum
            value: Gold value
            weight: Weight in inventory
        """
        super().__init__(name, description, ItemType.WEAPON, rarity, value, weight)
        
        self.weapon_type = weapon_type
        self.damage = damage
        
        # Set valid equipment slots based on weapon type
        if weapon_type in ["Dagger", "Sword", "Mace", "Wand", "Staff"]:
            self.valid_slots = ["main_hand", "off_hand"]
        elif weapon_type in ["Greatsword", "Battleaxe", "Greatmace", "Staff"]:
            self.valid_slots = ["main_hand"]  # Two-handed
        elif weapon_type in ["Bow", "Crossbow"]:
            self.valid_slots = ["main_hand"]  # Two-handed ranged
        elif weapon_type in ["Shield"]:
            self.valid_slots = ["off_hand"]
        
        # Add stat bonuses based on weapon type and rarity
        self._generate_stat_bonuses()
        
        logger.debug(f"Created weapon: {name} ({weapon_type}, {damage} damage)")
    
    def _generate_stat_bonuses(self):
        """Generate stat bonuses based on weapon type and rarity."""
        # Base bonus value based on rarity
        base_bonus = self.rarity.value + 1
        
        # Add appropriate stat bonuses based on weapon type
        if self.weapon_type in ["Sword", "Dagger", "Mace", "Battleaxe", "Greatmace"]:
            self.stat_bonuses["strength"] = base_bonus
        elif self.weapon_type in ["Bow", "Crossbow"]:
            self.stat_bonuses["dexterity"] = base_bonus
        elif self.weapon_type in ["Wand", "Staff"]:
            self.stat_bonuses["intelligence"] = base_bonus
        elif self.weapon_type in ["Shield"]:
            self.stat_bonuses["constitution"] = base_bonus
    
    def to_dict(self):
        """Convert to dictionary for serialization."""
        data = super().to_dict()
        data.update({
            'weapon_type': self.weapon_type,
            'damage': self.damage
        })
        return data
    
    @classmethod
    def from_dict(cls, data):
        """Create from dictionary."""
        weapon = cls(
            data['name'],
            data['description'],
            data['weapon_type'],
            data['damage'],
            ItemRarity(data['rarity']),
            data['value'],
            data['weight']
        )
        weapon.valid_slots = data['valid_slots']
        weapon.stat_bonuses = data['stat_bonuses']
        return weapon


class Armor(Item):
    """Armor item that can be equipped."""
    
    def __init__(self, name, description, armor_type, defense, rarity=ItemRarity.COMMON, value=10, weight=3):
        """
        Initialize armor.
        
        Args:
            name: Armor name
            description: Armor description
            armor_type: Type of armor (e.g., "Helmet", "Chestplate")
            defense: Defense value
            rarity: Rarity from ItemRarity enum
            value: Gold value
            weight: Weight in inventory
        """
        super().__init__(name, description, ItemType.ARMOR, rarity, value, weight)
        
        self.armor_type = armor_type
        self.defense = defense
        
        # Set valid equipment slots based on armor type
        if armor_type in ["Helmet", "Hat", "Crown"]:
            self.valid_slots = ["head"]
        elif armor_type in ["Chestplate", "Robe", "Tunic"]:
            self.valid_slots = ["chest"]
        elif armor_type in ["Leggings", "Pants", "Skirt"]:
            self.valid_slots = ["legs"]
        elif armor_type in ["Boots", "Shoes", "Sandals"]:
            self.valid_slots = ["feet"]
        
        # Add stat bonuses based on armor type and rarity
        self._generate_stat_bonuses()
        
        logger.debug(f"Created armor: {name} ({armor_type}, {defense} defense)")
    
    def _generate_stat_bonuses(self):
        """Generate stat bonuses based on armor type and rarity."""
        # Base bonus value based on rarity
        base_bonus = self.rarity.value + 1
        
        # Add appropriate stat bonuses based on armor type
        if self.armor_type in ["Helmet", "Crown"]:
            self.stat_bonuses["intelligence"] = base_bonus
        elif self.armor_type in ["Chestplate"]:
            self.stat_bonuses["constitution"] = base_bonus
        elif self.armor_type in ["Robe"]:
            self.stat_bonuses["wisdom"] = base_bonus
        elif self.armor_type in ["Leggings", "Pants"]:
            self.stat_bonuses["dexterity"] = base_bonus
        elif self.armor_type in ["Boots", "Shoes"]:
            self.stat_bonuses["dexterity"] = base_bonus
    
    def to_dict(self):
        """Convert to dictionary for serialization."""
        data = super().to_dict()
        data.update({
            'armor_type': self.armor_type,
            'defense': self.defense
        })
        return data
    
    @classmethod
    def from_dict(cls, data):
        """Create from dictionary."""
        armor = cls(
            data['name'],
            data['description'],
            data['armor_type'],
            data['defense'],
            ItemRarity(data['rarity']),
            data['value'],
            data['weight']
        )
        armor.valid_slots = data['valid_slots']
        armor.stat_bonuses = data['stat_bonuses']
        return armor


class Accessory(Item):
    """Accessory item that can be equipped."""
    
    def __init__(self, name, description, accessory_type, effect, rarity=ItemRarity.COMMON, value=15, weight=1):
        """
        Initialize an accessory.
        
        Args:
            name: Accessory name
            description: Accessory description
            accessory_type: Type of accessory (e.g., "Ring", "Amulet")
            effect: Description of special effect
            rarity: Rarity from ItemRarity enum
            value: Gold value
            weight: Weight in inventory
        """
        super().__init__(name, description, ItemType.ACCESSORY, rarity, value, weight)
        
        self.accessory_type = accessory_type
        self.effect = effect
        
        # All accessories use the accessory slot
        self.valid_slots = ["accessory"]
        
        # Add stat bonuses based on accessory type and rarity
        self._generate_stat_bonuses()
        
        logger.debug(f"Created accessory: {name} ({accessory_type}, effect: {effect})")
    
    def _generate_stat_bonuses(self):
        """Generate stat bonuses based on accessory type and rarity."""
        # Base bonus value based on rarity
        base_bonus = self.rarity.value + 1
        
        # Add appropriate stat bonuses based on accessory type
        if self.accessory_type == "Ring":
            self.stat_bonuses[random.choice(["dexterity", "intelligence"])] = base_bonus
        elif self.accessory_type == "Amulet":
            self.stat_bonuses[random.choice(["wisdom", "charisma"])] = base_bonus
        elif self.accessory_type == "Belt":
            self.stat_bonuses[random.choice(["strength", "constitution"])] = base_bonus
    
    def to_dict(self):
        """Convert to dictionary for serialization."""
        data = super().to_dict()
        data.update({
            'accessory_type': self.accessory_type,
            'effect': self.effect
        })
        return data
    
    @classmethod
    def from_dict(cls, data):
        """Create from dictionary."""
        accessory = cls(
            data['name'],
            data['description'],
            data['accessory_type'],
            data['effect'],
            ItemRarity(data['rarity']),
            data['value'],
            data['weight']
        )
        accessory.valid_slots = data['valid_slots']
        accessory.stat_bonuses = data['stat_bonuses']
        return accessory


class Consumable(Item):
    """Consumable item that can be used."""
    
    def __init__(self, name, description, consumable_type, effect_value, rarity=ItemRarity.COMMON, value=5, weight=0.5):
        """
        Initialize a consumable.
        
        Args:
            name: Consumable name
            description: Consumable description
            consumable_type: Type of consumable (e.g., "Potion", "Food")
            effect_value: Value for the effect (e.g., health restored)
            rarity: Rarity from ItemRarity enum
            value: Gold value
            weight: Weight in inventory
        """
        super().__init__(name, description, ItemType.CONSUMABLE, rarity, value, weight)
        
        self.consumable_type = consumable_type
        self.effect_value = effect_value
        self.consumable = True
        
        logger.debug(f"Created consumable: {name} ({consumable_type}, effect: {effect_value})")
    
    def use(self, character):
        """
        Use the consumable on a character.
        
        Args:
            character: Character using the consumable
            
        Returns:
            Boolean indicating if item was used successfully
        """
        # Apply effect based on consumable type
        if self.consumable_type == "Health Potion":
            actual_heal = character.heal(self.effect_value, self.name)
            return actual_heal > 0
            
        elif self.consumable_type == "Mana Potion":
            actual_restore = character.restore_mana(self.effect_value)
            return actual_restore > 0
            
        elif self.consumable_type == "Food":
            # Food heals a small amount and applies a temporary stat boost
            character.heal(self.effect_value // 2, self.name)
            character.stats["constitution"].add_modifier(1, self.name, 3)  # +1 con for 3 turns
            return True
            
        elif self.consumable_type == "Antidote":
            # Remove poison status if present
            return character.remove_status_effect("Poisoned")
            
        elif self.consumable_type == "Elixir":
            # Applies multiple effects
            character.heal(self.effect_value, self.name)
            character.restore_mana(self.effect_value, self.name)
            return True
        
        logger.warning(f"Unknown consumable type: {self.consumable_type}")
        return False
    
    def to_dict(self):
        """Convert to dictionary for serialization."""
        data = super().to_dict()
        data.update({
            'consumable_type': self.consumable_type,
            'effect_value': self.effect_value
        })
        return data
    
    @classmethod
    def from_dict(cls, data):
        """Create from dictionary."""
        consumable = cls(
            data['name'],
            data['description'],
            data['consumable_type'],
            data['effect_value'],
            ItemRarity(data['rarity']),
            data['value'],
            data['weight']
        )
        return consumable


class QuestItem(Item):
    """Quest item that cannot be used but is needed for quests."""
    
    def __init__(self, name, description, quest_id, rarity=ItemRarity.COMMON, value=0, weight=0.5):
        """
        Initialize a quest item.
        
        Args:
            name: Item name
            description: Item description
            quest_id: ID of the associated quest
            rarity: Rarity from ItemRarity enum
            value: Gold value
            weight: Weight in inventory
        """
        super().__init__(name, description, ItemType.QUEST, rarity, value, weight)
        
        self.quest_id = quest_id
        
        logger.debug(f"Created quest item: {name} (Quest: {quest_id})")
    
    def to_dict(self):
        """Convert to dictionary for serialization."""
        data = super().to_dict()
        data.update({
            'quest_id': self.quest_id
        })
        return data
    
    @classmethod
    def from_dict(cls, data):
        """Create from dictionary."""
        quest_item = cls(
            data['name'],
            data['description'],
            data['quest_id'],
            ItemRarity(data['rarity']),
            data['value'],
            data['weight']
        )
        return quest_item


class Material(Item):
    """Crafting material used in crafting recipes."""
    
    def __init__(self, name, description, material_type, rarity=ItemRarity.COMMON, value=2, weight=0.5):
        """
        Initialize a crafting material.
        
        Args:
            name: Material name
            description: Material description
            material_type: Type of material (e.g., "Ore", "Herb")
            rarity: Rarity from ItemRarity enum
            value: Gold value
            weight: Weight in inventory
        """
        super().__init__(name, description, ItemType.MATERIAL, rarity, value, weight)
        
        self.material_type = material_type
        
        logger.debug(f"Created material: {name} ({material_type})")
    
    def to_dict(self):
        """Convert to dictionary for serialization."""
        data = super().to_dict()
        data.update({
            'material_type': self.material_type
        })
        return data
    
    @classmethod
    def from_dict(cls, data):
        """Create from dictionary."""
        material = cls(
            data['name'],
            data['description'],
            data['material_type'],
            ItemRarity(data['rarity']),
            data['value'],
            data['weight']
        )
        return material


class ItemFactory:
    """Factory for creating items."""
    
    def __init__(self):
        """Initialize the item factory."""
        # Item templates
        self.weapon_templates = {
            "Sword": {
                "description": "A sharp blade for cutting enemies.",
                "damage_multiplier": 1.0
            },
            "Dagger": {
                "description": "A small, quick blade for precise strikes.",
                "damage_multiplier": 0.7
            },
            "Bow": {
                "description": "A ranged weapon for shooting arrows.",
                "damage_multiplier": 0.9
            },
            "Staff": {
                "description": "A magical staff that channels arcane power.",
                "damage_multiplier": 0.8
            },
            "Wand": {
                "description": "A small magical implement for casting spells.",
                "damage_multiplier": 0.6
            },
            "Mace": {
                "description": "A heavy bludgeoning weapon.",
                "damage_multiplier": 1.1
            },
            "Battleaxe": {
                "description": "A large axe designed for combat.",
                "damage_multiplier": 1.2
            },
            "Shield": {
                "description": "A defensive item to block attacks.",
                "damage_multiplier": 0.4
            }
        }
        
        self.armor_templates = {
            "Helmet": {
                "description": "Protective headgear.",
                "defense_multiplier": 0.8
            },
            "Hat": {
                "description": "Light headwear with minimal protection.",
                "defense_multiplier": 0.4
            },
            "Crown": {
                "description": "A regal headpiece with magical properties.",
                "defense_multiplier": 0.6
            },
            "Chestplate": {
                "description": "Heavy armor for the torso.",
                "defense_multiplier": 1.2
            },
            "Robe": {
                "description": "A flowing garment favored by spellcasters.",
                "defense_multiplier": 0.6
            },
            "Tunic": {
                "description": "Light armor for the upper body.",
                "defense_multiplier": 0.8
            },
            "Leggings": {
                "description": "Armor for the legs.",
                "defense_multiplier": 1.0
            },
            "Pants": {
                "description": "Simple leg coverings with minimal protection.",
                "defense_multiplier": 0.6
            },
            "Boots": {
                "description": "Sturdy footwear for protection.",
                "defense_multiplier": 0.7
            },
            "Shoes": {
                "description": "Light footwear with minimal protection.",
                "defense_multiplier": 0.4
            }
        }
        
        self.accessory_templates = {
            "Ring": {
                "description": "A ring with magical properties.",
                "effects": [
                    "Increases magical power.",
                    "Enhances dexterity.",
                    "Protects against certain elements."
                ]
            },
            "Amulet": {
                "description": "A pendant worn around the neck.",
                "effects": [
                    "Enhances wisdom and insight.",
                    "Provides protection against curses.",
                    "Slowly regenerates health."
                ]
            },
            "Belt": {
                "description": "A belt with special properties.",
                "effects": [
                    "Increases physical strength.",
                    "Enhances constitution.",
                    "Allows carrying more items."
                ]
            }
        }
        
        self.consumable_templates = {
            "Health Potion": {
                "description": "A red potion that restores health.",
                "effect_multiplier": 20
            },
            "Mana Potion": {
                "description": "A blue potion that restores mana.",
                "effect_multiplier": 15
            },
            "Food": {
                "description": "Nourishing food that provides sustenance.",
                "effect_multiplier": 10
            },
            "Antidote": {
                "description": "Cures poison status effects.",
                "effect_multiplier": 1
            },
            "Elixir": {
                "description": "A powerful potion that restores health and mana.",
                "effect_multiplier": 25
            }
        }
        
        self.material_templates = {
            "Ore": {
                "description": "Raw metal ore that can be refined."
            },
            "Wood": {
                "description": "Wooden material used in crafting."
            },
            "Herb": {
                "description": "Medicinal or magical plant."
            },
            "Leather": {
                "description": "Treated animal hide used for armor."
            },
            "Cloth": {
                "description": "Woven fabric for crafting clothes and equipment."
            },
            "Stone": {
                "description": "Hard mineral material used in crafting."
            },
            "Gem": {
                "description": "Precious or semi-precious stone with magical properties."
            }
        }
        
        # Rarity modifiers
        self.rarity_name_prefixes = {
            ItemRarity.COMMON: ["Simple", "Basic", "Plain", "Crude", "Rough"],
            ItemRarity.UNCOMMON: ["Fine", "Quality", "Sturdy", "Solid", "Reliable"],
            ItemRarity.RARE: ["Exceptional", "Superior", "Excellent", "Refined", "Master"],
            ItemRarity.EPIC: ["Mythical", "Legendary", "Ancient", "Heroic", "Divine"],
            ItemRarity.LEGENDARY: ["Godly", "Ultimate", "Supreme", "Perfect", "Transcendent"]
        }
        
        self.rarity_name_suffixes = {
            ItemRarity.UNCOMMON: ["of Quality", "of Skill", "of Craftsmanship"],
            ItemRarity.RARE: ["of Excellence", "of Mastery", "of Power"],
            ItemRarity.EPIC: ["of Legend", "of the Heroes", "of the Ancients"],
            ItemRarity.LEGENDARY: ["of the Gods", "of Destiny", "of Eternity"]
        }
        
        # Value and weight multipliers by rarity
        self.rarity_value_multipliers = {
            ItemRarity.COMMON: 1.0,
            ItemRarity.UNCOMMON: 2.0,
            ItemRarity.RARE: 5.0,
            ItemRarity.EPIC: 10.0,
            ItemRarity.LEGENDARY: 25.0
        }
    
    def _generate_item_name(self, base_type, rarity):
        """
        Generate an item name based on type and rarity.
        
        Args:
            base_type: Base item type (e.g., "Sword", "Helmet")
            rarity: ItemRarity enum value
            
        Returns:
            Generated name string
        """
        name = base_type
        
        # Add prefix for higher rarities
        if rarity != ItemRarity.COMMON:
            prefix = random.choice(self.rarity_name_prefixes.get(rarity, ["Fine"]))
            name = f"{prefix} {name}"
        
        # Add suffix for higher rarities
        if rarity in self.rarity_name_suffixes:
            if random.random() < 0.7:  # 70% chance to add suffix
                suffix = random.choice(self.rarity_name_suffixes[rarity])
                name = f"{name} {suffix}"
        
        return name
    
    def create_weapon(self, weapon_type=None, rarity=None, level=1):
        """
        Create a weapon.
        
        Args:
            weapon_type: Type of weapon (None for random)
            rarity: ItemRarity enum value (None for random)
            level: Item level (affects damage)
            
        Returns:
            Weapon instance
        """
        # Choose random weapon type if not specified
        if weapon_type is None:
            weapon_type = random.choice(list(self.weapon_templates.keys()))
        
        # Choose random rarity if not specified, weighted toward common
        if rarity is None:
            rarity_weights = [70, 20, 7, 2, 1]  # Common to Legendary
            rarity_idx = random.choices(range(len(ItemRarity)), weights=rarity_weights)[0]
            rarity = ItemRarity(rarity_idx)
        
        # Get template
        template = self.weapon_templates.get(weapon_type, self.weapon_templates["Sword"])
        
        # Generate name
        name = self._generate_item_name(weapon_type, rarity)
        
        # Calculate damage based on level and rarity
        base_damage = level * 2
        rarity_multiplier = 1.0 + (rarity.value * 0.25)  # +25% per rarity level
        type_multiplier = template["damage_multiplier"]
        damage = int(base_damage * rarity_multiplier * type_multiplier)
        
        # Calculate value
        value = int(10 * level * self.rarity_value_multipliers[rarity])
        
        # Create weapon
        return Weapon(
            name,
            template["description"],
            weapon_type,
            damage,
            rarity,
            value,
            2.0  # Fixed weight for now
        )
    
    def create_armor(self, armor_type=None, rarity=None, level=1):
        """
        Create armor.
        
        Args:
            armor_type: Type of armor (None for random)
            rarity: ItemRarity enum value (None for random)
            level: Item level (affects defense)
            
        Returns:
            Armor instance
        """
        # Choose random armor type if not specified
        if armor_type is None:
            armor_type = random.choice(list(self.armor_templates.keys()))
        
        # Choose random rarity if not specified, weighted toward common
        if rarity is None:
            rarity_weights = [70, 20, 7, 2, 1]  # Common to Legendary
            rarity_idx = random.choices(range(len(ItemRarity)), weights=rarity_weights)[0]
            rarity = ItemRarity(rarity_idx)
        
        # Get template
        template = self.armor_templates.get(armor_type, self.armor_templates["Chestplate"])
        
        # Generate name
        name = self._generate_item_name(armor_type, rarity)
        
        # Calculate defense based on level and rarity
        base_defense = level * 1.5
        rarity_multiplier = 1.0 + (rarity.value * 0.25)  # +25% per rarity level
        type_multiplier = template["defense_multiplier"]
        defense = int(base_defense * rarity_multiplier * type_multiplier)
        
        # Calculate value
        value = int(10 * level * self.rarity_value_multipliers[rarity])
        
        # Create armor
        return Armor(
            name,
            template["description"],
            armor_type,
            defense,
            rarity,
            value,
            3.0  # Fixed weight for now
        )
    
    def create_accessory(self, accessory_type=None, rarity=None, level=1):
        """
        Create an accessory.
        
        Args:
            accessory_type: Type of accessory (None for random)
            rarity: ItemRarity enum value (None for random)
            level: Item level (affects bonuses)
            
        Returns:
            Accessory instance
        """
        # Choose random accessory type if not specified
        if accessory_type is None:
            accessory_type = random.choice(list(self.accessory_templates.keys()))
        
        # Choose random rarity if not specified, weighted toward common
        if rarity is None:
            rarity_weights = [60, 25, 10, 4, 1]  # Common to Legendary
            rarity_idx = random.choices(range(len(ItemRarity)), weights=rarity_weights)[0]
            rarity = ItemRarity(rarity_idx)
        
        # Get template
        template = self.accessory_templates.get(accessory_type, self.accessory_templates["Ring"])
        
        # Generate name
        name = self._generate_item_name(accessory_type, rarity)
        
        # Choose a random effect
        effect = random.choice(template["effects"])
        
        # Calculate value
        value = int(15 * level * self.rarity_value_multipliers[rarity])
        
        # Create accessory
        return Accessory(
            name,
            template["description"],
            accessory_type,
            effect,
            rarity,
            value,
            1.0  # Fixed weight for now
        )
    
    def create_consumable(self, consumable_type=None, rarity=None, level=1):
        """
        Create a consumable.
        
        Args:
            consumable_type: Type of consumable (None for random)
            rarity: ItemRarity enum value (None for random)
            level: Item level (affects effect strength)
            
        Returns:
            Consumable instance
        """
        # Choose random consumable type if not specified
        if consumable_type is None:
            consumable_type = random.choice(list(self.consumable_templates.keys()))
        
        # Choose random rarity if not specified, weighted toward common
        if rarity is None:
            rarity_weights = [80, 15, 4, 1, 0]  # Common to Epic (no legendary consumables)
            rarity_idx = random.choices(range(len(ItemRarity)), weights=rarity_weights)[0]
            rarity = ItemRarity(rarity_idx)
        
        # Get template
        template = self.consumable_templates.get(
            consumable_type, 
            self.consumable_templates["Health Potion"]
        )
        
        # Generate name
        if rarity == ItemRarity.COMMON:
            name = consumable_type
        else:
            prefix = random.choice(self.rarity_name_prefixes.get(rarity, ["Fine"]))
            name = f"{prefix} {consumable_type}"
        
        # Calculate effect value based on level and rarity
        base_effect = template["effect_multiplier"]
        effect_value = int(base_effect * level * (1.0 + (rarity.value * 0.25)))
        
        # Calculate value
        value = int(5 * level * self.rarity_value_multipliers[rarity])
        
        # Create consumable
        return Consumable(
            name,
            template["description"],
            consumable_type,
            effect_value,
            rarity,
            value,
            0.5  # Fixed weight for now
        )
    
    def create_material(self, material_type=None, rarity=None):
        """
        Create a crafting material.
        
        Args:
            material_type: Type of material (None for random)
            rarity: ItemRarity enum value (None for random)
            
        Returns:
            Material instance
        """
        # Choose random material type if not specified
        if material_type is None:
            material_type = random.choice(list(self.material_templates.keys()))
        
        # Choose random rarity if not specified, weighted toward common
        if rarity is None:
            rarity_weights = [75, 20, 4, 1, 0]  # Common to Epic (no legendary materials)
            rarity_idx = random.choices(range(len(ItemRarity)), weights=rarity_weights)[0]
            rarity = ItemRarity(rarity_idx)
        
        # Get template
        template = self.material_templates.get(material_type, self.material_templates["Ore"])
        
        # Generate name
        if rarity == ItemRarity.COMMON:
            name = material_type
        else:
            prefix = random.choice(self.rarity_name_prefixes.get(rarity, ["Fine"]))
            name = f"{prefix} {material_type}"
        
        # Calculate value
        value = int(2 * self.rarity_value_multipliers[rarity])
        
        # Create material
        return Material(
            name,
            template["description"],
            material_type,
            rarity,
            value,
            0.5  # Fixed weight for now
        )
    
    def create_quest_item(self, name, description, quest_id):
        """
        Create a quest item.
        
        Args:
            name: Item name
            description: Item description
            quest_id: ID of the associated quest
            
        Returns:
            QuestItem instance
        """
        return QuestItem(name, description, quest_id)
    
    def create_random_loot(self, level, count=1):
        """
        Create random loot items.
        
        Args:
            level: Level of the items
            count: Number of items to create
            
        Returns:
            List of random items
        """
        items = []
        
        for _ in range(count):
            # Choose item type with weighted probability
            item_type_weights = [20, 20, 10, 40, 0, 10]  # Weights for each ItemType
            item_type_idx = random.choices(range(len(ItemType)), weights=item_type_weights)[0]
            item_type = ItemType(item_type_idx)
            
            # Create item based on type
            if item_type == ItemType.WEAPON:
                items.append(self.create_weapon(level=level))
            elif item_type == ItemType.ARMOR:
                items.append(self.create_armor(level=level))
            elif item_type == ItemType.ACCESSORY:
                items.append(self.create_accessory(level=level))
            elif item_type == ItemType.CONSUMABLE:
                items.append(self.create_consumable(level=level))
            elif item_type == ItemType.MATERIAL:
                items.append(self.create_material())
        
        return items
    
    def create_item_from_dict(self, data):
        """
        Create an item from dictionary data.
        
        Args:
            data: Dictionary data from item.to_dict()
            
        Returns:
            Item instance of appropriate subclass
        """
        item_class = data.get('class', 'Item')
        
        if item_class == 'Weapon':
            return Weapon.from_dict(data)
        elif item_class == 'Armor':
            return Armor.from_dict(data)
        elif item_class == 'Accessory':
            return Accessory.from_dict(data)
        elif item_class == 'Consumable':
            return Consumable.from_dict(data)
        elif item_class == 'QuestItem':
            return QuestItem.from_dict(data)
        elif item_class == 'Material':
            return Material.from_dict(data)
        else:
            return Item.from_dict(data)
