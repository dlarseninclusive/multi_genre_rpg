import random
import logging
import json
from enum import Enum
from inventory import ItemRarity, ItemType

logger = logging.getLogger("economy")

class CurrencyType(Enum):
    """Different types of currency in the game."""
    GOLD = 0
    SILVER = 1
    COPPER = 2
    GEMS = 3  # Special currency for rare items
    FACTION_TOKEN = 4  # For faction-specific vendors

class EconomicStatus(Enum):
    """Economic conditions that affect prices."""
    PROSPEROUS = 0  # Lower prices for selling, higher for buying
    NORMAL = 1      # Standard prices
    STRUGGLING = 2  # Higher prices for selling, lower for buying
    DESPERATE = 3   # Very high prices, limited inventory
    BOOMING = 4     # Very low prices, abundant inventory

class TradeSkill(Enum):
    """Player skills that affect trading."""
    HAGGLING = 0    # Affects base prices
    APPRAISAL = 1   # Better item identification
    REPUTATION = 2  # Affects merchant disposition
    WHOLESALE = 3   # Better bulk pricing
    SMUGGLING = 4   # Access to black market items

class Merchant:
    """Represents a merchant that buys and sells items."""
    
    def __init__(self, name, location, specialty=None, inventory=None, gold=500):
        """
        Initialize a merchant.
        
        Args:
            name: Merchant name
            location: Location ID where merchant can be found
            specialty: ItemType the merchant specializes in (optional)
            inventory: List of items for sale (optional)
            gold: Amount of gold merchant has available
        """
        self.name = name
        self.location = location
        self.specialty = specialty
        self.inventory = inventory if inventory else []
        self.gold = gold
        self.disposition = 50  # 0-100, affects prices
        self.economic_status = EconomicStatus.NORMAL
        self.price_multipliers = {
            ItemRarity.COMMON: 1.0,
            ItemRarity.UNCOMMON: 2.0,
            ItemRarity.RARE: 4.0,
            ItemRarity.EPIC: 8.0,
            ItemRarity.LEGENDARY: 20.0
        }
        self.buy_multiplier = 0.4  # Merchants buy at 40% of selling price
        self.max_inventory = 30
        self.restock_timer = 0
        self.restock_interval = 24  # In-game hours
        self.accepts_items = True  # Whether merchant buys items from player
        self.black_market = False  # Sells/buys illegal goods
        
        # Store transaction history
        self.transaction_history = []
        
        logger.info(f"Merchant {name} initialized at {location}")
    
    def get_sell_price(self, item, player_skills=None):
        """
        Calculate selling price (merchant to player).
        
        Args:
            item: Item being sold
            player_skills: Dict of player's trade skills and levels
            
        Returns:
            Price in gold
        """
        # Start with base value
        price = item.value
        
        # Apply rarity multiplier
        price *= self.price_multipliers.get(item.rarity, 1.0)
        
        # Apply specialty discount/premium
        if self.specialty and item.item_type == self.specialty:
            # Specialists have better prices for their specialty
            price *= 0.9
        
        # Apply economic status modifier
        if self.economic_status == EconomicStatus.PROSPEROUS:
            price *= 1.2
        elif self.economic_status == EconomicStatus.STRUGGLING:
            price *= 0.8
        elif self.economic_status == EconomicStatus.DESPERATE:
            price *= 0.6
        elif self.economic_status == EconomicStatus.BOOMING:
            price *= 1.5
        
        # Apply disposition modifier
        disposition_mod = 1.0 - (self.disposition - 50) / 500  # ±10% based on 0-100 disposition
        price *= disposition_mod
        
        # Apply player haggling skill
        if player_skills and TradeSkill.HAGGLING in player_skills:
            haggle_level = player_skills[TradeSkill.HAGGLING]
            haggle_discount = haggle_level * 0.02  # 2% discount per level, up to 20%
            price *= max(0.8, 1.0 - haggle_discount)
        
        # Round to nearest whole number
        return max(1, round(price))
    
    def get_buy_price(self, item, player_skills=None):
        """
        Calculate buying price (player to merchant).
        
        Args:
            item: Item being bought
            player_skills: Dict of player's trade skills and levels
            
        Returns:
            Price in gold
        """
        # Start with base value
        price = item.value
        
        # Apply buy multiplier (merchants buy at a discount)
        price *= self.buy_multiplier
        
        # Apply specialty bonus
        if self.specialty and item.item_type == self.specialty:
            # Specialists pay better for their specialty
            price *= 1.2
        
        # Apply economic status modifier
        if self.economic_status == EconomicStatus.PROSPEROUS:
            price *= 0.8
        elif self.economic_status == EconomicStatus.STRUGGLING:
            price *= 1.2
        elif self.economic_status == EconomicStatus.DESPERATE:
            price *= 1.5
        elif self.economic_status == EconomicStatus.BOOMING:
            price *= 0.6
        
        # Apply disposition modifier
        disposition_mod = 1.0 + (self.disposition - 50) / 500  # ±10% based on 0-100 disposition
        price *= disposition_mod
        
        # Apply player haggling skill
        if player_skills and TradeSkill.HAGGLING in player_skills:
            haggle_level = player_skills[TradeSkill.HAGGLING]
            haggle_bonus = haggle_level * 0.02  # 2% bonus per level, up to 20%
            price *= min(1.2, 1.0 + haggle_bonus)
        
        # Round to nearest whole number
        return max(1, round(price))
    
    def sell_item_to_player(self, item_index, player):
        """
        Sell an item to the player.
        
        Args:
            item_index: Index of item in merchant inventory
            player: Player instance
            
        Returns:
            Boolean indicating if transaction was successful
        """
        if item_index < 0 or item_index >= len(self.inventory):
            logger.warning(f"Invalid item index: {item_index}")
            return False
        
        item = self.inventory[item_index]
        
        # Calculate price
        price = self.get_sell_price(item, player.trade_skills if hasattr(player, 'trade_skills') else None)
        
        # Check if player has enough gold
        if player.gold < price:
            logger.debug(f"Player has insufficient gold to buy {item.name} ({price} gold)")
            return False
        
        # Check if player has inventory space
        if len(player.inventory) >= player.max_inventory_slots:
            logger.debug(f"Player inventory is full, can't buy {item.name}")
            return False
        
        # Transfer item and gold
        player.gold -= price
        self.gold += price
        
        # Remove from merchant inventory and add to player inventory
        item = self.inventory.pop(item_index)
        player.inventory.append(item)
        
        # Record transaction
        self.transaction_history.append({
            "type": "sell",
            "item": item.name,
            "price": price,
            "player": player.name
        })
        
        logger.info(f"Merchant {self.name} sold {item.name} to {player.name} for {price} gold")
        return True
    
    def buy_item_from_player(self, item_index, player):
        """
        Buy an item from the player.
        
        Args:
            item_index: Index of item in player inventory
            player: Player instance
            
        Returns:
            Boolean indicating if transaction was successful
        """
        if not self.accepts_items:
            logger.debug(f"Merchant {self.name} does not buy items from players")
            return False
            
        if item_index < 0 or item_index >= len(player.inventory):
            logger.warning(f"Invalid item index: {item_index}")
            return False
        
        item = player.inventory[item_index]
        
        # Check if merchant has inventory space
        if len(self.inventory) >= self.max_inventory:
            logger.debug(f"Merchant inventory is full, can't buy {item.name}")
            return False
        
        # Calculate price
        price = self.get_buy_price(item, player.trade_skills if hasattr(player, 'trade_skills') else None)
        
        # Check if merchant has enough gold
        if self.gold < price:
            logger.debug(f"Merchant has insufficient gold to buy {item.name} ({price} gold)")
            return False
        
        # Transfer item and gold
        player.gold += price
        self.gold -= price
        
        # Remove from player inventory and add to merchant inventory
        item = player.inventory.pop(item_index)
        self.inventory.append(item)
        
        # Record transaction
        self.transaction_history.append({
            "type": "buy",
            "item": item.name,
            "price": price,
            "player": player.name
        })
        
        logger.info(f"Merchant {self.name} bought {item.name} from {player.name} for {price} gold")
        return True
    
    def update_disposition(self, amount):
        """
        Update merchant's disposition toward the player.
        
        Args:
            amount: Amount to change disposition by
        """
        self.disposition = max(0, min(100, self.disposition + amount))
        logger.debug(f"Merchant {self.name} disposition updated to {self.disposition}")
    
    def restock(self, item_factory):
        """
        Restock merchant's inventory with new items.
        
        Args:
            item_factory: ItemFactory instance for creating items
        """
        # Don't exceed max inventory
        space_available = self.max_inventory - len(self.inventory)
        if space_available <= 0:
            return
        
        # Determine how many items to add
        restock_amount = random.randint(3, min(10, space_available))
        
        # Define item levels based on economic status
        level = random.randint(1, 5)
        if self.economic_status == EconomicStatus.BOOMING:
            level += 2
        elif self.economic_status == EconomicStatus.PROSPEROUS:
            level += 1
        
        # Generate items based on specialty
        for _ in range(restock_amount):
            if self.specialty == ItemType.WEAPON:
                item = item_factory.create_weapon(level=level)
            elif self.specialty == ItemType.ARMOR:
                item = item_factory.create_armor(level=level)
            elif self.specialty == ItemType.ACCESSORY:
                item = item_factory.create_accessory(level=level)
            elif self.specialty == ItemType.CONSUMABLE:
                item = item_factory.create_consumable(level=level)
            elif self.specialty == ItemType.MATERIAL:
                item = item_factory.create_material()
            else:
                # Random item type
                item = random.choice([
                    item_factory.create_weapon(level=level),
                    item_factory.create_armor(level=level),
                    item_factory.create_consumable(level=level),
                    item_factory.create_accessory(level=level),
                    item_factory.create_material()
                ])
            
            self.inventory.append(item)
        
        logger.info(f"Merchant {self.name} restocked with {restock_amount} new items")
    
    def update(self, dt, item_factory=None):
        """
        Update merchant state over time.
        
        Args:
            dt: Time delta in in-game hours
            item_factory: ItemFactory instance for creating items (optional)
        """
        # Update restock timer
        self.restock_timer += dt
        
        # Restock inventory if timer expired
        if self.restock_timer >= self.restock_interval and item_factory:
            self.restock(item_factory)
            self.restock_timer = 0
    
    def to_dict(self):
        """Convert to dictionary for serialization."""
        return {
            'name': self.name,
            'location': self.location,
            'specialty': self.specialty.value if self.specialty else None,
            'inventory': [item.to_dict() for item in self.inventory],
            'gold': self.gold,
            'disposition': self.disposition,
            'economic_status': self.economic_status.value,
            'price_multipliers': {k.value: v for k, v in self.price_multipliers.items()},
            'buy_multiplier': self.buy_multiplier,
            'max_inventory': self.max_inventory,
            'restock_timer': self.restock_timer,
            'restock_interval': self.restock_interval,
            'accepts_items': self.accepts_items,
            'black_market': self.black_market,
            'transaction_history': self.transaction_history
        }
    
    @classmethod
    def from_dict(cls, data, item_factory):
        """Create from dictionary."""
        merchant = cls(
            data['name'],
            data['location'],
            ItemType(data['specialty']) if data['specialty'] is not None else None,
            [],  # Empty inventory, will be filled below
            data['gold']
        )
        
        # Set properties
        merchant.disposition = data['disposition']
        merchant.economic_status = EconomicStatus(data['economic_status'])
        merchant.price_multipliers = {ItemRarity(k): v for k, v in data['price_multipliers'].items()}
        merchant.buy_multiplier = data['buy_multiplier']
        merchant.max_inventory = data['max_inventory']
        merchant.restock_timer = data['restock_timer']
        merchant.restock_interval = data['restock_interval']
        merchant.accepts_items = data['accepts_items']
        merchant.black_market = data['black_market']
        merchant.transaction_history = data['transaction_history']
        
        # Restore inventory
        for item_data in data['inventory']:
            item = item_factory.create_item_from_dict(item_data)
            merchant.inventory.append(item)
        
        return merchant

class BlackMarket(Merchant):
    """Specialized merchant for illegal or rare goods."""
    
    def __init__(self, name, location, inventory=None, gold=1000):
        """
        Initialize a black market merchant.
        
        Args:
            name: Merchant name
            location: Location ID where merchant can be found
            inventory: List of items for sale (optional)
            gold: Amount of gold merchant has available
        """
        super().__init__(name, location, None, inventory, gold)
        
        # Black market specific settings
        self.black_market = True
        self.disposition = 20  # More wary of strangers
        self.buy_multiplier = 0.6  # Pays better for items
        self.price_multipliers = {
            ItemRarity.COMMON: 2.0,      # Common items are overpriced
            ItemRarity.UNCOMMON: 2.5,
            ItemRarity.RARE: 3.0,
            ItemRarity.EPIC: 5.0,
            ItemRarity.LEGENDARY: 15.0   # Better deal than normal merchants
        }
        self.required_reputation = 30  # Reputation needed to trade
        self.fence_stolen_goods = True  # Can sell stolen items
        
        logger.info(f"Black market merchant {name} initialized at {location}")
    
    def can_trade_with_player(self, player):
        """
        Check if player can trade with this merchant.
        
        Args:
            player: Player instance
            
        Returns:
            Boolean indicating if player can trade
        """
        # Check if player has required reputation
        if hasattr(player, 'faction_reputation'):
            thieves_rep = player.faction_reputation.get('thieves_guild', 0)
            return thieves_rep >= self.required_reputation
        
        return False
    
    def sell_stolen_item(self, item_index, player):
        """
        Sell a stolen item to the black market.
        
        Args:
            item_index: Index of item in player inventory
            player: Player instance
            
        Returns:
            Boolean indicating if transaction was successful
        """
        if not self.fence_stolen_goods:
            return False
            
        if item_index < 0 or item_index >= len(player.inventory):
            return False
        
        item = player.inventory[item_index]
        
        # Check if item is stolen
        is_stolen = getattr(item, 'stolen', False)
        if not is_stolen:
            return False
        
        # Calculate price (lower for stolen goods)
        price = self.get_buy_price(item, player.trade_skills if hasattr(player, 'trade_skills') else None)
        price = int(price * 0.7)  # 30% penalty for stolen goods
        
        # Complete transaction
        if self.gold < price:
            return False
        
        player.gold += price
        self.gold -= price
        
        item = player.inventory.pop(item_index)
        self.inventory.append(item)
        
        # Clear stolen flag
        item.stolen = False
        
        # Record transaction
        self.transaction_history.append({
            "type": "fence",
            "item": item.name,
            "price": price,
            "player": player.name
        })
        
        logger.info(f"Black market {self.name} fenced stolen {item.name} for {price} gold")
        return True

class Shop:
    """Represents a shop with associated merchants and services."""
    
    def __init__(self, name, location_id, shop_type="general", merchants=None):
        """
        Initialize a shop.
        
        Args:
            name: Shop name
            location_id: ID of location containing shop
            shop_type: Type of shop (general, weapons, armor, magic, etc.)
            merchants: List of merchant objects
        """
        self.name = name
        self.location_id = location_id
        self.shop_type = shop_type
        self.merchants = merchants if merchants else []
        self.hours = {
            "open": 8,   # 8 AM
            "close": 20  # 8 PM
        }
        self.open_days = [0, 1, 2, 3, 4, 5, 6]  # 0-6, all days
        self.specials = {}  # Day -> discount mapping
        self.reputation_requirement = 0
        self.quality_level = 1  # 1-5, affects item quality
        
        logger.info(f"Shop {name} of type {shop_type} initialized at location {location_id}")
    
    def is_open(self, time_of_day, day_of_week):
        """
        Check if shop is currently open.
        
        Args:
            time_of_day: Current hour (0-23)
            day_of_week: Current day (0-6)
            
        Returns:
            Boolean indicating if shop is open
        """
        return (day_of_week in self.open_days and 
                self.hours["open"] <= time_of_day < self.hours["close"])
    
    def get_discount(self, day_of_week):
        """
        Get any special discount for the current day.
        
        Args:
            day_of_week: Current day (0-6)
            
        Returns:
            Discount multiplier (1.0 = no discount)
        """
        return self.specials.get(day_of_week, 1.0)
    
    def add_merchant(self, merchant):
        """
        Add a merchant to the shop.
        
        Args:
            merchant: Merchant instance
        """
        self.merchants.append(merchant)
        logger.debug(f"Added merchant {merchant.name} to shop {self.name}")
    
    def remove_merchant(self, merchant_name):
        """
        Remove a merchant from the shop.
        
        Args:
            merchant_name: Name of merchant to remove
            
        Returns:
            Boolean indicating if merchant was removed
        """
        for i, merchant in enumerate(self.merchants):
            if merchant.name == merchant_name:
                self.merchants.pop(i)
                logger.debug(f"Removed merchant {merchant_name} from shop {self.name}")
                return True
        
        return False
    
    def update(self, dt, item_factory=None):
        """
        Update shop and its merchants.
        
        Args:
            dt: Time delta in in-game hours
            item_factory: ItemFactory instance for creating items (optional)
        """
        for merchant in self.merchants:
            merchant.update(dt, item_factory)
    
    def to_dict(self):
        """Convert to dictionary for serialization."""
        return {
            'name': self.name,
            'location_id': self.location_id,
            'shop_type': self.shop_type,
            'merchants': [merchant.to_dict() for merchant in self.merchants],
            'hours': self.hours,
            'open_days': self.open_days,
            'specials': {str(k): v for k, v in self.specials.items()},
            'reputation_requirement': self.reputation_requirement,
            'quality_level': self.quality_level
        }
    
    @classmethod
    def from_dict(cls, data, item_factory):
        """Create from dictionary."""
        shop = cls(
            data['name'],
            data['location_id'],
            data['shop_type'],
            []  # Empty merchants list, will be filled below
        )
        
        # Set properties
        shop.hours = data['hours']
        shop.open_days = data['open_days']
        shop.specials = {int(k): v for k, v in data['specials'].items()}
        shop.reputation_requirement = data['reputation_requirement']
        shop.quality_level = data['quality_level']
        
        # Restore merchants
        for merchant_data in data['merchants']:
            merchant = Merchant.from_dict(merchant_data, item_factory)
            shop.merchants.append(merchant)
        
        return shop

class EconomyManager:
    """Manages game economy, shops, and merchants."""
    
    def __init__(self, event_bus, item_factory):
        """
        Initialize the economy manager.
        
        Args:
            event_bus: EventBus instance for game events
            item_factory: ItemFactory instance for creating items
        """
        self.event_bus = event_bus
        self.item_factory = item_factory
        self.shops = {}  # location_id -> list of shops
        self.merchants = {}  # merchant_name -> merchant object
        self.item_base_values = {}  # Default values for items by type and rarity
        self.economic_conditions = {}  # location_id -> economic status
        self.exchange_rates = {
            CurrencyType.GOLD: 1.0,
            CurrencyType.SILVER: 0.1,
            CurrencyType.COPPER: 0.01,
            CurrencyType.GEMS: 100.0,
            CurrencyType.FACTION_TOKEN: 10.0
        }
        
        # Initialize base values for items
        self._initialize_item_base_values()
        
        # Subscribe to events
        self.event_bus.subscribe("time_changed", self.handle_time_changed)
        self.event_bus.subscribe("location_changed", self.handle_location_changed)
        self.event_bus.subscribe("shop_transaction", self.handle_shop_transaction)
        
        logger.info("EconomyManager initialized")
    
    def _initialize_item_base_values(self):
        """Set up default values for items by type and rarity."""
        # Base values for different item types
        for item_type in ItemType:
            self.item_base_values[item_type] = {
                ItemRarity.COMMON: 10,
                ItemRarity.UNCOMMON: 50,
                ItemRarity.RARE: 200,
                ItemRarity.EPIC: 1000,
                ItemRarity.LEGENDARY: 5000
            }
        
        # Adjust values for specific types
        # Weapons and armor are more valuable
        self.item_base_values[ItemType.WEAPON][ItemRarity.COMMON] = 15
        self.item_base_values[ItemType.ARMOR][ItemRarity.COMMON] = 15
        
        # Consumables are less valuable
        self.item_base_values[ItemType.CONSUMABLE][ItemRarity.COMMON] = 5
        
        # Quest items have fixed values
        self.item_base_values[ItemType.QUEST] = {rarity: 0 for rarity in ItemRarity}
        
        logger.debug("Item base values initialized")
    
    def register_shop(self, shop):
        """
        Register a shop in the economy.
        
        Args:
            shop: Shop instance
        """
        location_id = shop.location_id
        
        if location_id not in self.shops:
            self.shops[location_id] = []
        
        self.shops[location_id].append(shop)
        
        # Register all merchants from this shop
        for merchant in shop.merchants:
            self.merchants[merchant.name] = merchant
        
        logger.info(f"Registered shop {shop.name} at location {location_id}")
    
    def get_shops_at_location(self, location_id):
        """
        Get all shops at a location.
        
        Args:
            location_id: Location ID
            
        Returns:
            List of shops at the location
        """
        return self.shops.get(location_id, [])
    
    def get_merchant(self, merchant_name):
        """
        Get a merchant by name.
        
        Args:
            merchant_name: Name of merchant
            
        Returns:
            Merchant instance or None if not found
        """
        return self.merchants.get(merchant_name)
    
    def update_economic_condition(self, location_id, condition):
        """
        Update economic condition for a location.
        
        Args:
            location_id: Location ID
            condition: New EconomicStatus
        """
        old_condition = self.economic_conditions.get(location_id)
        self.economic_conditions[location_id] = condition
        
        # Update all shops and merchants at this location
        if location_id in self.shops:
            for shop in self.shops[location_id]:
                for merchant in shop.merchants:
                    merchant.economic_status = condition
        
        logger.info(f"Updated economic condition at location {location_id} from {old_condition} to {condition}")
        
        # Notify about change
        self.event_bus.publish("economic_condition_changed", {
            "location_id": location_id,
            "old_condition": old_condition,
            "new_condition": condition
        })
    
    def convert_currency(self, amount, from_type, to_type):
        """
        Convert between currency types.
        
        Args:
            amount: Amount to convert
            from_type: Source CurrencyType
            to_type: Target CurrencyType
            
        Returns:
            Converted amount
        """
        # Get exchange rates
        from_rate = self.exchange_rates[from_type]
        to_rate = self.exchange_rates[to_type]
        
        # Convert to gold value then to target currency
        gold_value = amount * from_rate
        converted = gold_value / to_rate
        
        return converted
    
    def update(self, dt, current_time, day_of_week):
        """
        Update economy state.
        
        Args:
            dt: Time delta in in-game hours
            current_time: Current hour (0-23)
            day_of_week: Current day (0-6)
        """
        # Update all shops
        for shops_list in self.shops.values():
            for shop in shops_list:
                # Only update if shop is open
                if shop.is_open(current_time, day_of_week):
                    shop.update(dt, self.item_factory)
    
    def handle_time_changed(self, data):
        """
        Handle time changed event.
        
        Args:
            data: Event data containing time information
        """
        # Update economy based on new time
        current_time = data.get("hour", 12)
        day_of_week = data.get("day_of_week", 0)
        dt = data.get("delta", 0)
        
        self.update(dt, current_time, day_of_week)
    
    def handle_location_changed(self, data):
        """
        Handle location changed event.
        
        Args:
            data: Event data containing location information
        """
        # Update shops at the new location
        location_id = data.get("location_id")
        
        if location_id in self.shops:
            logger.debug(f"Player entered location {location_id} with {len(self.shops[location_id])} shops")
    
    def handle_shop_transaction(self, data):
        """
        Handle shop transaction event.
        
        Args:
            data: Event data containing transaction information
        """
        # Update merchant disposition based on transaction
        merchant_name = data.get("merchant_name")
        transaction_type = data.get("transaction_type")
        value = data.get("value", 0)
        
        merchant = self.get_merchant(merchant_name)
        if merchant:
            # Increase disposition slightly for larger transactions
            disposition_change = min(5, max(1, value // 100))
            merchant.update_disposition(disposition_change)
    
    def generate_shop(self, location_id, shop_type="general", quality_level=None):
        """
        Generate a new shop for a location.
        
        Args:
            location_id: Location ID
            shop_type: Type of shop to generate
            quality_level: Quality level (1-5) or None for random
            
        Returns:
            Newly created Shop instance
        """
        # Determine quality level if not specified
        if quality_level is None:
            quality_level = random.randint(1, 5)
        
        # Generate shop name
        shop_name = self._generate_shop_name(shop_type)
        
        # Create shop instance
        shop = Shop(shop_name, location_id, shop_type)
        shop.quality_level = quality_level
        
        # Add merchants based on shop type
        self._add_merchants_to_shop(shop)
        
        # Register the shop
        self.register_shop(shop)
        
        return shop
    
    def _generate_shop_name(self, shop_type):
        """
        Generate a shop name based on shop type.
        
        Args:
            shop_type: Type of shop
            
        Returns:
            Generated shop name
        """
        # First parts of shop names
        first_parts = {
            "general": ["The General", "Traveler's", "Village", "Market", "Trading"],
            "weapons": ["The Armory", "Blades", "Warrior's", "Steel", "Combat"],
            "armor": ["The Shield", "Defender's", "Iron", "Protector's", "Guardian"],
            "magic": ["Arcane", "Mystic", "Wizard's", "Enchanted", "Spellbound"],
            "alchemy": ["The Cauldron", "Alchemist's", "Potion", "Elixir", "Remedy"],
            "blacksmith": ["The Forge", "Smith's", "Anvil", "Hammer", "Metal"],
            "tailor": ["Fine", "Silken", "Tailor's", "Thread", "Fashion"],
            "inn": ["The Resting", "Traveler's", "Cozy", "Golden", "Sleeping"],
            "jeweler": ["Glittering", "Gem", "Golden", "Precious", "Jewel"]
        }
        
        # Second parts of shop names
        second_parts = {
            "general": ["Store", "Goods", "Emporium", "Supply", "Post"],
            "weapons": ["Weapons", "Arsenal", "Armory", "Blades", "Arms"],
            "armor": ["Armor", "Shields", "Protection", "Defense", "Plate"],
            "magic": ["Scrolls", "Magic", "Wonders", "Mysteries", "Artifacts"],
            "alchemy": ["Potions", "Brews", "Mixtures", "Tonics", "Concoctions"],
            "blacksmith": ["Smithy", "Forge", "Workshop", "Ironworks", "Metalworks"],
            "tailor": ["Clothier", "Garments", "Textiles", "Tailoring", "Fabrics"],
            "inn": ["Inn", "Tavern", "Lodge", "Rest", "Quarters"],
            "jeweler": ["Gems", "Jewelry", "Treasures", "Trinkets", "Adornments"]
        }
        
        # Get appropriate parts for this shop type or use general if type not found
        first = random.choice(first_parts.get(shop_type, first_parts["general"]))
        second = random.choice(second_parts.get(shop_type, second_parts["general"]))
        
        # Sometimes add an adjective
        adjectives = ["Golden", "Silver", "Rusty", "Fine", "Grand", "Royal", "Humble", "Ancient", "Swift", "Brave"]
        if random.random() < 0.3:
            adj = random.choice(adjectives)
            return f"The {adj} {first} {second}"
        
        return f"The {first} {second}"
    
    def _add_merchants_to_shop(self, shop):
        """
        Add appropriate merchants to a shop.
        
        Args:
            shop: Shop to add merchants to
        """
        # Determine number of merchants based on shop type
        num_merchants = 1
        if shop.shop_type == "general":
            num_merchants = random.randint(1, 3)
        elif shop.shop_type == "inn":
            num_merchants = random.randint(2, 4)
        
        # Add merchants
        for i in range(num_merchants):
            # Generate merchant name
            first_names = ["John", "Mary", "Robert", "Linda", "William", "Elizabeth", "James", "Jennifer", "Michael", "Susan"]
            last_names = ["Smith", "Johnson", "Williams", "Jones", "Brown", "Davis", "Miller", "Wilson", "Moore", "Taylor"]
            merchant_name = f"{random.choice(first_names)} {random.choice(last_names)}"
            
            # Determine specialty based on shop type
            specialty = None
            if shop.shop_type == "weapons":
                specialty = ItemType.WEAPON
            elif shop.shop_type == "armor":
                specialty = ItemType.ARMOR
            elif shop.shop_type == "magic" or shop.shop_type == "alchemy":
                specialty = ItemType.CONSUMABLE
            elif shop.shop_type == "jeweler":
                specialty = ItemType.ACCESSORY
            elif shop.shop_type == "blacksmith":
                specialty = random.choice([ItemType.WEAPON, ItemType.ARMOR])
            
            # Create merchant
            gold = random.randint(300, 1000) * shop.quality_level
            merchant = Merchant(merchant_name, shop.location_id, specialty, [], gold)
            
            # Adjust merchant based on shop quality
            merchant.price_multipliers = {
                k: v * (0.8 + shop.quality_level * 0.1) 
                for k, v in merchant.price_multipliers.items()
            }
            
            # Stock initial inventory
            merchant.restock(self.item_factory)
            
            # Add to shop
            shop.add_merchant(merchant)
    
    def generate_town_economy(self, town_id, size="medium", prosperity=None):
        """
        Generate economy for an entire town.
        
        Args:
            town_id: Town location ID
            size: Size of town ("small", "medium", "large")
            prosperity: EconomicStatus or None for random
            
        Returns:
            List of shops created for the town
        """
        # Determine prosperity if not specified
        if prosperity is None:
            prosperity = random.choice(list(EconomicStatus))
        
        # Set economic condition
        self.update_economic_condition(town_id, prosperity)
        
        # Determine number and types of shops based on town size
        shops_to_create = []
        
        if size == "small":
            shops_to_create = [
                "general",
                "inn",
                random.choice(["blacksmith", "weapons"])
            ]
        elif size == "medium":
            shops_to_create = [
                "general",
                "inn",
                "blacksmith",
                "weapons",
                "armor",
                random.choice(["magic", "alchemy", "jeweler"])
            ]
        else:  # large
            shops_to_create = [
                "general",
                "general",  # Two general stores
                "inn",
                "blacksmith",
                "weapons",
                "armor",
                "magic",
                "alchemy",
                "jeweler",
                "tailor"
            ]
        
        # Create shops
        created_shops = []
        for shop_type in shops_to_create:
            # Quality level based on prosperity
            quality_modifier = {
                EconomicStatus.DESPERATE: -1,
                EconomicStatus.STRUGGLING: 0,
                EconomicStatus.NORMAL: 1,
                EconomicStatus.PROSPEROUS: 2,
                EconomicStatus.BOOMING: 3
            }
            
            base_quality = {"small": 1, "medium": 2, "large": 3}[size]
            quality = max(1, min(5, base_quality + quality_modifier[prosperity]))
            
            shop = self.generate_shop(town_id, shop_type, quality)
            created_shops.append(shop)
        
        # Set up some specials for shops
        for shop in created_shops:
            # 30% chance for a shop to have a special discount day
            if random.random() < 0.3:
                special_day = random.randint(0, 6)
                discount = random.choice([0.9, 0.85, 0.8])  # 10-20% off
                shop.specials[special_day] = discount
        
        # Add a black market for medium and large towns (if prospering or desperate)
        if size != "small" and prosperity in [EconomicStatus.DESPERATE, EconomicStatus.BOOMING]:
            if random.random() < 0.7:  # 70% chance
                self._add_black_market(town_id)
        
        logger.info(f"Generated economy for {size} town {town_id} with {len(created_shops)} shops")
        return created_shops
    
    def _add_black_market(self, location_id):
        """
        Add a black market to a location.
        
        Args:
            location_id: Location ID
            
        Returns:
            Created black market shop
        """
        # Create shop instance
        names = ["Shadow Market", "Dark Exchange", "Hidden Wares", "Clandestine Goods", "The Undermarket"]
        shop_name = random.choice(names)
        
        shop = Shop(shop_name, location_id, "black_market")
        shop.quality_level = random.randint(3, 5)  # Higher quality exotic goods
        shop.hours = {"open": 22, "close": 4}  # Night hours
        
        # Add black market merchant
        merchant_names = ["Shady Dealer", "Fence", "Smuggler", "Broker", "Underground Merchant"]
        merchant_name = random.choice(merchant_names)
        merchant = BlackMarket(merchant_name, location_id, [], 2000)
        
        # Stock initial inventory
        merchant.restock(self.item_factory)
        
        # Add some rare/special items
        for _ in range(3):
            level = random.randint(3, 10)  # Higher level items
            
            # Generate rare/exotic item
            if random.random() < 0.7:
                # Pick a higher rarity
                rarity = random.choice([ItemRarity.RARE, ItemRarity.EPIC, ItemRarity.LEGENDARY])
                
                # Create item of random type with specified rarity
                item_type = random.choice([ItemType.WEAPON, ItemType.ARMOR, ItemType.ACCESSORY])
                
                if item_type == ItemType.WEAPON:
                    item = self.item_factory.create_weapon(level=level, rarity=rarity)
                elif item_type == ItemType.ARMOR:
                    item = self.item_factory.create_armor(level=level, rarity=rarity)
                else:
                    item = self.item_factory.create_accessory(level=level, rarity=rarity)
            else:
                # Create special consumable
                item = self.item_factory.create_consumable("Elixir", ItemRarity.RARE, level)
            
            merchant.inventory.append(item)
        
        # Add to shop
        shop.add_merchant(merchant)
        
        # Register the shop
        self.register_shop(shop)
        
        logger.info(f"Added black market {shop_name} to location {location_id}")
        return shop
    
    def to_dict(self):
        """Convert to dictionary for serialization."""
        return {
            'shops': {
                location_id: [shop.to_dict() for shop in shops] 
                for location_id, shops in self.shops.items()
            },
            'economic_conditions': {
                str(location_id): condition.value 
                for location_id, condition in self.economic_conditions.items()
            },
            'exchange_rates': {
                currency.value: rate 
                for currency, rate in self.exchange_rates.items()
            }
        }
    
    @classmethod
    def from_dict(cls, data, event_bus, item_factory):
        """Create from dictionary."""
        manager = cls(event_bus, item_factory)
        
        # Restore exchange rates
        for currency_val, rate in data['exchange_rates'].items():
            manager.exchange_rates[CurrencyType(int(currency_val))] = rate
        
        # Restore economic conditions
        for location_id, condition_val in data['economic_conditions'].items():
            manager.economic_conditions[location_id] = EconomicStatus(condition_val)
        
        # Restore shops
        for location_id, shops_data in data['shops'].items():
            for shop_data in shops_data:
                shop = Shop.from_dict(shop_data, item_factory)
                manager.register_shop(shop)
        
        return manager


class PriceAdjuster:
    """Helper class to adjust prices based on various factors."""
    
    @staticmethod
    def adjust_for_faction_reputation(base_price, faction_name, reputation, is_buying=True):
        """
        Adjust price based on faction reputation.
        
        Args:
            base_price: Base price to adjust
            faction_name: Name of faction
            reputation: Reputation level with faction
            is_buying: Whether player is buying (vs. selling)
            
        Returns:
            Adjusted price
        """
        # No adjustment for neutral reputation
        if reputation == 0:
            return base_price
        
        # Calculate adjustment percentage
        # Max 25% discount at 100 reputation, 25% markup at -100
        adjustment = -0.25 * (reputation / 100)
        
        # When selling, effect is reversed
        if not is_buying:
            adjustment = -adjustment
            
        # Apply adjustment
        return int(base_price * (1 + adjustment))
    
    @staticmethod
    def adjust_for_player_skills(base_price, player_skills, is_buying=True):
        """
        Adjust price based on player's trading skills.
        
        Args:
            base_price: Base price to adjust
            player_skills: Dict of player's skills and levels
            is_buying: Whether player is buying (vs. selling)
            
        Returns:
            Adjusted price
        """
        # Start with base price
        price = base_price
        
        # Apply haggling skill (better prices overall)
        if TradeSkill.HAGGLING in player_skills:
            haggle_level = player_skills[TradeSkill.HAGGLING]
            modifier = max(0.75, 1.0 - (haggle_level * 0.025))  # Up to 25% discount
            if is_buying:
                price *= modifier
            else:
                # When selling, higher prices (inverse of discount)
                price *= (2 - modifier)
        
        # Apply wholesale skill (better bulk prices)
        if TradeSkill.WHOLESALE in player_skills and player_skills[TradeSkill.WHOLESALE] > 0:
            # This would be applied elsewhere for bulk purchases
            pass
        
        # Apply appraisal skill (identifies true value)
        if TradeSkill.APPRAISAL in player_skills and player_skills[TradeSkill.APPRAISAL] > 3:
            # This is more about item identification than price
            pass
        
        return int(price)
    
    @staticmethod
    def adjust_for_quantity(base_price, quantity, is_buying=True):
        """
        Adjust price based on quantity (bulk discount/premium).
        
        Args:
            base_price: Base price to adjust
            quantity: Number of items
            is_buying: Whether player is buying (vs. selling)
            
        Returns:
            Adjusted total price
        """
        # No adjustment for single items
        if quantity <= 1:
            return base_price
        
        # Calculate total base price
        total = base_price * quantity
        
        # Apply bulk discount/premium
        if quantity < 5:
            discount = 0.02  # 2% discount for small quantities
        elif quantity < 10:
            discount = 0.05  # 5% discount for medium quantities
        elif quantity < 25:
            discount = 0.1   # 10% discount for large quantities
        else:
            discount = 0.15  # 15% discount for huge quantities
        
        # When selling in bulk, give smaller bonuses
        if not is_buying:
            discount /= 2
        
        # Apply discount
        return int(total * (1 - discount))


class BlackMarketGenerator:
    """Utility for generating black market items and quests."""
    
    def __init__(self, item_factory):
        """
        Initialize the black market generator.
        
        Args:
            item_factory: ItemFactory instance for creating items
        """
        self.item_factory = item_factory
    
    def generate_contraband(self, level=1, rarity=None):
        """
        Generate a contraband item.
        
        Args:
            level: Item level
            rarity: ItemRarity or None for random
            
        Returns:
            Item instance with contraband flag
        """
        # Choose random rarity weighted toward rarer items
        if rarity is None:
            weights = [10, 30, 40, 15, 5]  # Common to Legendary
            rarity_idx = random.choices(range(len(ItemRarity)), weights=weights)[0]
            rarity = ItemRarity(rarity_idx)
        
        # Generate random item type
        item_type = random.choice([ItemType.WEAPON, ItemType.ARMOR, ItemType.ACCESSORY, ItemType.CONSUMABLE])
        
        # Create item based on type
        if item_type == ItemType.WEAPON:
            item = self.item_factory.create_weapon(level=level, rarity=rarity)
        elif item_type == ItemType.ARMOR:
            item = self.item_factory.create_armor(level=level, rarity=rarity)
        elif item_type == ItemType.ACCESSORY:
            item = self.item_factory.create_accessory(level=level, rarity=rarity)
        else:
            item = self.item_factory.create_consumable(level=level, rarity=rarity)
        
        # Add contraband flag
        item.contraband = True
        
        # Add some special descriptors to name
        contraband_prefixes = ["Smuggled", "Illegal", "Contraband", "Forbidden", "Restricted"]
        item.name = f"{random.choice(contraband_prefixes)} {item.name}"
        
        return item
    
    def generate_stolen_item(self, level=1):
        """
        Generate a stolen item.
        
        Args:
            level: Item level
            
        Returns:
            Item instance with stolen flag
        """
        # Create random item with stolen flag
        rarity_weights = [60, 25, 10, 4, 1]  # Common to Legendary
        rarity_idx = random.choices(range(len(ItemRarity)), weights=rarity_weights)[0]
        rarity = ItemRarity(rarity_idx)
        
        item_type = random.choice([ItemType.WEAPON, ItemType.ARMOR, ItemType.ACCESSORY])
        
        if item_type == ItemType.WEAPON:
            item = self.item_factory.create_weapon(level=level, rarity=rarity)
        elif item_type == ItemType.ARMOR:
            item = self.item_factory.create_armor(level=level, rarity=rarity)
        else:
            item = self.item_factory.create_accessory(level=level, rarity=rarity)
        
        # Mark as stolen
        item.stolen = True
        
        return item
    
    def generate_fence_quest(self, town_id, difficulty=1):
        """
        Generate a quest to fence stolen goods.
        
        Args:
            town_id: Town location ID
            difficulty: Quest difficulty (1-10)
            
        Returns:
            Dict with quest information
        """
        # Generate stolen items to fence
        item_count = max(1, min(5, difficulty))
        stolen_items = [self.generate_stolen_item(level=difficulty) for _ in range(item_count)]
        
        # Calculate reward
        total_value = sum(item.value for item in stolen_items)
        reward = int(total_value * 1.5)  # 50% bonus for the risk
        
        # Create quest data
        quest = {
            'title': f"Fence {item_count} Stolen Items",
            'description': f"A shady character needs you to fence {item_count} stolen items with the local black market dealer.",
            'difficulty': difficulty,
            'location_id': town_id,
            'reward_gold': reward,
            'reward_reputation': {'thieves_guild': 5 * difficulty},
            'stolen_items': stolen_items,
            'time_limit': 24 * 3  # 3 days
        }
        
        return quest
    
    def generate_smuggling_quest(self, start_town_id, end_town_id, difficulty=1):
        """
        Generate a quest to smuggle contraband between towns.
        
        Args:
            start_town_id: Starting town location ID
            end_town_id: Destination town location ID
            difficulty: Quest difficulty (1-10)
            
        Returns:
            Dict with quest information
        """
        # Generate contraband to smuggle
        item_count = max(1, min(3, difficulty))
        contraband = [self.generate_contraband(level=difficulty) for _ in range(item_count)]
        
        # Calculate reward
        total_value = sum(item.value for item in contraband)
        risk_factor = difficulty / 5  # 0.2 to 2.0
        reward = int(total_value * (1.5 + risk_factor))  # Higher difficulty = higher reward
        
        # Create quest data
        quest = {
            'title': f"Smuggle Contraband to {end_town_id}",
            'description': f"Transport {item_count} contraband items from {start_town_id} to {end_town_id} without getting caught by guards.",
            'difficulty': difficulty,
            'start_location_id': start_town_id,
            'end_location_id': end_town_id,
            'reward_gold': reward,
            'reward_reputation': {'thieves_guild': 10 * difficulty},
            'contraband': contraband,
            'guard_encounters': difficulty,
            'time_limit': 24 * 7  # 7 days
        }
        
        return quest


# Usage example:
# economy_manager = EconomyManager(event_bus, item_factory)
# economy_manager.generate_town_economy("town1", "medium")
#
# # Get shops in town
# shops = economy_manager.get_shops_at_location("town1")
#
# # Find a merchant
# merchant = economy_manager.get_merchant("John Smith")
#
# # Player buys item from merchant
# merchant.sell_item_to_player(0, player)
#
# # Player sells item to merchant
# merchant.buy_item_from_player(0, player)