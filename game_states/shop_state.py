import pygame
import logging
from game_state import GameState

logger = logging.getLogger("shop")

class ShopState(GameState):
    """
    Game state for shopping and trading.
    
    This state handles:
    - Buying items from merchants
    - Selling items to merchants
    - Item browsing and information
    """
    
    def __init__(self, state_manager, event_bus, settings):
        super().__init__(state_manager, event_bus, settings)
        self.shop_name = "General Store"
        self.shop_id = None
        self.merchant = None
        self.item_list = []
        self.player_inventory = []
        self.selected_tab = "buy"  # buy, sell
        self.selected_item_index = 0
        self.player_gold = 0
        self.font = None
        self.font_large = None
        self.font_small = None
        
        logger.info("ShopState initialized")
        
    def enter(self, data=None):
        super().enter(data)
        
        # Initialize fonts
        pygame.font.init()
        self.font = pygame.font.SysFont(None, 24)
        self.font_large = pygame.font.SysFont(None, 32)
        self.font_small = pygame.font.SysFont(None, 18)
        
        if data:
            self.shop_name = data.get("shop_name", "General Store")
            self.shop_id = data.get("shop_id")
        
        # Get player character
        player_character = self.state_manager.get_persistent_data("player_character")
        if player_character:
            self.player_gold = getattr(player_character, "gold", 0)
            self.player_inventory = getattr(player_character, "inventory", [])
        
        # Load merchant data
        self._load_merchant()
        
        # Show notification
        self.event_bus.publish("show_notification", {
            "title": self.shop_name,
            "message": "Welcome! Take a look at my wares.",
            "duration": 2.0
        })
        
        logger.info(f"Entered shop: {self.shop_name}")
    
    def exit(self):
        super().exit()
        logger.info(f"Exited shop: {self.shop_name}")
    
    def handle_event(self, event):
        if not super().handle_event(event):
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    # Return to town
                    self.pop_state()
                    return True
                
                elif event.key == pygame.K_TAB:
                    # Switch tabs
                    self.selected_tab = "sell" if self.selected_tab == "buy" else "buy"
                    self.selected_item_index = 0
                    return True
                
                elif event.key == pygame.K_UP:
                    # Move selection up
                    items = self.item_list if self.selected_tab == "buy" else self.player_inventory
                    if items:
                        self.selected_item_index = (self.selected_item_index - 1) % len(items)
                    return True
                
                elif event.key == pygame.K_DOWN:
                    # Move selection down
                    items = self.item_list if self.selected_tab == "buy" else self.player_inventory
                    if items:
                        self.selected_item_index = (self.selected_item_index + 1) % len(items)
                    return True
                
                elif event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                    # Buy or sell item
                    if self.selected_tab == "buy":
                        self._buy_selected_item()
                    else:
                        self._sell_selected_item()
                    return True
        
        return False
    
    def update(self, dt):
        super().update(dt)
    
    def render(self, screen):
        # Fill background
        screen.fill((30, 30, 50))
        
        # Draw shop name
        shop_text = self.font_large.render(self.shop_name, True, (255, 255, 255))
        shop_rect = shop_text.get_rect(midtop=(screen.get_width() // 2, 20))
        screen.blit(shop_text, shop_rect)
        
        # Draw tabs
        self._draw_tabs(screen)
        
        # Draw item list
        if self.selected_tab == "buy":
            self._draw_buy_list(screen)
        else:
            self._draw_sell_list(screen)
        
        # Draw player gold
        gold_text = self.font.render(f"Your Gold: {self.player_gold}", True, (255, 215, 0))
        gold_rect = gold_text.get_rect(bottomleft=(20, screen.get_height() - 20))
        screen.blit(gold_text, gold_rect)
        
        # Draw help text
        help_text = self.font_small.render(
            "UP/DOWN: Select | ENTER: Buy/Sell | TAB: Switch Tab | ESC: Exit",
            True, (200, 200, 200)
        )
        help_rect = help_text.get_rect(midbottom=(screen.get_width() // 2, screen.get_height() - 20))
        screen.blit(help_text, help_rect)
    
    def _draw_tabs(self, screen):
        """Draw buy/sell tabs."""
        tab_width = 100
        tab_height = 30
        tab_y = 60
        
        # Buy tab
        buy_rect = pygame.Rect((screen.get_width() // 2) - tab_width - 5, tab_y, tab_width, tab_height)
        buy_color = (80, 80, 120) if self.selected_tab == "buy" else (50, 50, 80)
        pygame.draw.rect(screen, buy_color, buy_rect)
        pygame.draw.rect(screen, (100, 100, 150), buy_rect, 2)
        
        buy_text = self.font.render("Buy", True, (255, 255, 255))
        buy_text_rect = buy_text.get_rect(center=buy_rect.center)
        screen.blit(buy_text, buy_text_rect)
        
        # Sell tab
        sell_rect = pygame.Rect((screen.get_width() // 2) + 5, tab_y, tab_width, tab_height)
        sell_color = (80, 80, 120) if self.selected_tab == "sell" else (50, 50, 80)
        pygame.draw.rect(screen, sell_color, sell_rect)
        pygame.draw.rect(screen, (100, 100, 150), sell_rect, 2)
        
        sell_text = self.font.render("Sell", True, (255, 255, 255))
        sell_text_rect = sell_text.get_rect(center=sell_rect.center)
        screen.blit(sell_text, sell_text_rect)
    
    def _draw_buy_list(self, screen):
        """Draw the list of items for sale."""
        list_rect = pygame.Rect(50, 100, screen.get_width() - 100, screen.get_height() - 200)
        pygame.draw.rect(screen, (40, 40, 60), list_rect)
        pygame.draw.rect(screen, (100, 100, 150), list_rect, 2)
        
        # Draw header
        header_y = list_rect.top + 10
        name_text = self.font.render("Item", True, (200, 200, 255))
        screen.blit(name_text, (list_rect.left + 20, header_y))
        
        price_text = self.font.render("Price", True, (200, 200, 255))
        price_rect = price_text.get_rect(right=list_rect.right - 20)
        screen.blit(price_text, (price_rect.left, header_y))
        
        # Draw separator
        pygame.draw.line(
            screen, (100, 100, 150),
            (list_rect.left + 10, header_y + 25),
            (list_rect.right - 10, header_y + 25),
            1
        )
        
        # Draw items
        item_y = header_y + 40
        item_height = 30
        
        for i, item in enumerate(self.item_list):
            # Highlight selected item
            if i == self.selected_item_index:
                highlight_rect = pygame.Rect(
                    list_rect.left + 5,
                    item_y - 5,
                    list_rect.width - 10,
                    item_height
                )
                pygame.draw.rect(screen, (60, 60, 100), highlight_rect)
            
            # Draw item name
            name = getattr(item, "name", f"Item {i+1}")
            item_text = self.font.render(name, True, (255, 255, 255))
            screen.blit(item_text, (list_rect.left + 20, item_y))
            
            # Draw item price
            price = getattr(item, "price", 0)
            price_text = self.font.render(f"{price} gold", True, (255, 215, 0))
            price_rect = price_text.get_rect(right=list_rect.right - 20)
            screen.blit(price_text, (price_rect.left, item_y))
            
            item_y += item_height
            
            # Stop if we run out of space
            if item_y > list_rect.bottom - 20:
                break
        
        # Draw selected item details
        if self.item_list and 0 <= self.selected_item_index < len(self.item_list):
            selected_item = self.item_list[self.selected_item_index]
            self._draw_item_details(screen, selected_item)
    
    def _draw_sell_list(self, screen):
        """Draw the list of player's items to sell."""
        list_rect = pygame.Rect(50, 100, screen.get_width() - 100, screen.get_height() - 200)
        pygame.draw.rect(screen, (40, 40, 60), list_rect)
        pygame.draw.rect(screen, (100, 100, 150), list_rect, 2)
        
        # Draw header
        header_y = list_rect.top + 10
        name_text = self.font.render("Item", True, (200, 200, 255))
        screen.blit(name_text, (list_rect.left + 20, header_y))
        
        price_text = self.font.render("Value", True, (200, 200, 255))
        price_rect = price_text.get_rect(right=list_rect.right - 20)
        screen.blit(price_text, (price_rect.left, header_y))
        
        # Draw separator
        pygame.draw.line(
            screen, (100, 100, 150),
            (list_rect.left + 10, header_y + 25),
            (list_rect.right - 10, header_y + 25),
            1
        )
        
        # Draw items
        item_y = header_y + 40
        item_height = 30
        
        if not self.player_inventory:
            # Show message if inventory is empty
            empty_text = self.font.render("Your inventory is empty", True, (150, 150, 150))
            empty_rect = empty_text.get_rect(center=(list_rect.centerx, list_rect.centery))
            screen.blit(empty_text, empty_rect)
        else:
            for i, item in enumerate(self.player_inventory):
                # Highlight selected item
                if i == self.selected_item_index:
                    highlight_rect = pygame.Rect(
                        list_rect.left + 5,
                        item_y - 5,
                        list_rect.width - 10,
                        item_height
                    )
                    pygame.draw.rect(screen, (60, 60, 100), highlight_rect)
                
                # Draw item name
                name = getattr(item, "name", f"Item {i+1}")
                item_text = self.font.render(name, True, (255, 255, 255))
                screen.blit(item_text, (list_rect.left + 20, item_y))
                
                # Draw item sell value
                price = getattr(item, "price", 0) // 2  # Sell for half price
                price_text = self.font.render(f"{price} gold", True, (255, 215, 0))
                price_rect = price_text.get_rect(right=list_rect.right - 20)
                screen.blit(price_text, (price_rect.left, item_y))
                
                item_y += item_height
                
                # Stop if we run out of space
                if item_y > list_rect.bottom - 20:
                    break
            
            # Draw selected item details
            if self.player_inventory and 0 <= self.selected_item_index < len(self.player_inventory):
                selected_item = self.player_inventory[self.selected_item_index]
                self._draw_item_details(screen, selected_item)
    
    def _draw_item_details(self, screen, item):
        """Draw details for the selected item."""
        details_rect = pygame.Rect(
            50,
            screen.get_height() - 90,
            screen.get_width() - 100,
            70
        )
        pygame.draw.rect(screen, (50, 50, 70), details_rect)
        pygame.draw.rect(screen, (100, 100, 150), details_rect, 2)
        
        # Draw item name
        name = getattr(item, "name", "Unknown Item")
        name_text = self.font.render(name, True, (200, 200, 255))
        screen.blit(name_text, (details_rect.left + 20, details_rect.top + 10))
        
        # Draw item description
        description = getattr(item, "description", "No description available.")
        desc_text = self.font_small.render(description, True, (180, 180, 180))
        screen.blit(desc_text, (details_rect.left + 20, details_rect.top + 35))
        
        # Draw item stats if available
        if hasattr(item, "stats"):
            stats = item.stats
            stats_text = self.font_small.render(
                f"Stats: {stats}",
                True, (150, 200, 150)
            )
            screen.blit(stats_text, (details_rect.left + 20, details_rect.top + 55))
    
    def _load_merchant(self):
        """Load merchant data based on shop_id."""
        # This would be replaced with actual merchant loading code
        # For now, create a basic merchant with sample items
        self.merchant = {
            "name": "Shopkeeper",
            "shop_id": self.shop_id,
            "greeting": "Welcome to my shop!"
        }
        
        # Create sample items
        self.item_list = []
        
        # Sample weapons
        self.item_list.append(self._create_sample_item("Iron Sword", "A basic iron sword", 50, "weapon"))
        self.item_list.append(self._create_sample_item("Wooden Bow", "A simple wooden bow", 40, "weapon"))
        
        # Sample armor
        self.item_list.append(self._create_sample_item("Leather Armor", "Basic leather protection", 45, "armor"))
        self.item_list.append(self._create_sample_item("Iron Shield", "A sturdy iron shield", 35, "armor"))
        
        # Sample potions
        self.item_list.append(self._create_sample_item("Health Potion", "Restores 50 health", 20, "consumable"))
        self.item_list.append(self._create_sample_item("Mana Potion", "Restores 50 mana", 20, "consumable"))
        
        # Sample materials
        self.item_list.append(self._create_sample_item("Iron Ingot", "Used for crafting", 15, "material"))
        self.item_list.append(self._create_sample_item("Leather", "Used for crafting", 10, "material"))
    
    def _create_sample_item(self, name, description, price, item_type):
        """Create a sample item for the shop."""
        return type('Item', (), {
            'name': name,
            'description': description,
            'price': price,
            'type': item_type,
            'stats': f"{item_type.capitalize()} +5"
        })
    
    def _buy_selected_item(self):
        """Buy the selected item."""
        if not self.item_list or self.selected_item_index >= len(self.item_list):
            return
        
        selected_item = self.item_list[self.selected_item_index]
        price = getattr(selected_item, "price", 0)
        
        # Check if player has enough gold
        if self.player_gold < price:
            self.event_bus.publish("show_notification", {
                "title": "Cannot Buy",
                "message": "You don't have enough gold!",
                "duration": 2.0
            })
            return
        
        # Buy the item
        self.player_gold -= price
        self.player_inventory.append(selected_item)
        
        # Update player character
        player_character = self.state_manager.get_persistent_data("player_character")
        if player_character:
            player_character.gold = self.player_gold
            player_character.inventory = self.player_inventory
            self.state_manager.set_persistent_data("player_character", player_character)
        
        # Show notification
        self.event_bus.publish("show_notification", {
            "title": "Item Purchased",
            "message": f"You bought {selected_item.name} for {price} gold.",
            "duration": 2.0
        })
        
        logger.info(f"Player bought {selected_item.name} for {price} gold")
    
    def _sell_selected_item(self):
        """Sell the selected item."""
        if not self.player_inventory or self.selected_item_index >= len(self.player_inventory):
            return
        
        selected_item = self.player_inventory[self.selected_item_index]
        price = getattr(selected_item, "price", 0) // 2  # Sell for half price
        
        # Sell the item
        self.player_gold += price
        self.player_inventory.pop(self.selected_item_index)
        
        # Adjust selected index if needed
        if self.player_inventory and self.selected_item_index >= len(self.player_inventory):
            self.selected_item_index = len(self.player_inventory) - 1
        
        # Update player character
        player_character = self.state_manager.get_persistent_data("player_character")
        if player_character:
            player_character.gold = self.player_gold
            player_character.inventory = self.player_inventory
            self.state_manager.set_persistent_data("player_character", player_character)
        
        # Show notification
        self.event_bus.publish("show_notification", {
            "title": "Item Sold",
            "message": f"You sold {selected_item.name} for {price} gold.",
            "duration": 2.0
        })
        
        logger.info(f"Player sold {selected_item.name} for {price} gold")
