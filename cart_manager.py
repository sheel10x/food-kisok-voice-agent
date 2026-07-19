from typing import Dict, List, Any
import logging

logger = logging.getLogger("moshi.cart")

class CartManager:
    def __init__(self):
        self.items = []  # List of dicts: {"item": item_dict, "quantity": int, "cart_id": str}
        self.declined_categories = set()
        self.cart_counter = 0

    def add_item(self, item: dict, quantity: int = 1) -> str:
        self.cart_counter += 1
        cart_item_id = f"c_{self.cart_counter}"
        self.items.append({
            "cart_id": cart_item_id,
            "item": item,
            "quantity": quantity
        })
        logger.info(f"Added to cart: {quantity}x {item['name']}")
        return cart_item_id

    def remove_item(self, cart_id: str) -> bool:
        for i, ci in enumerate(self.items):
            if ci["cart_id"] == cart_id:
                del self.items[i]
                logger.info(f"Removed cart item: {cart_id}")
                return True
        return False
        
    def remove_by_name(self, name: str) -> bool:
        # Removes the first matching item by name (useful for voice)
        for i, ci in enumerate(self.items):
            if ci["item"]["name"].lower() == name.lower():
                del self.items[i]
                logger.info(f"Removed cart item by name: {name}")
                return True
        return False

    def get_total(self) -> int:
        return sum(ci["item"]["price"] * ci["quantity"] for ci in self.items)

    def mark_declined(self, category: str):
        self.declined_categories.add(category)
        logger.info(f"Upsell category declined: {category}")

    def get_missing_upsells(self) -> List[str]:
        """
        Returns a list of suggested categories based on current cart.
        Logic:
        - Burgers -> Beverages or Snacks & Sides
        - Beverages -> Desserts
        - Breakfast -> McCafé
        """
        categories_in_cart = {ci["item"]["category"] for ci in self.items}
        suggestions = set()

        if "Burgers" in categories_in_cart:
            if "Beverages" not in categories_in_cart and "Beverages" not in self.declined_categories:
                suggestions.add("Beverages")
            if "Snacks & Sides" not in categories_in_cart and "Snacks & Sides" not in self.declined_categories:
                suggestions.add("Snacks & Sides")
                
        if "Beverages" in categories_in_cart:
            if "Desserts" not in categories_in_cart and "Desserts" not in self.declined_categories:
                suggestions.add("Desserts")
                
        if "Breakfast" in categories_in_cart:
            if "McCafé" not in categories_in_cart and "McCafé" not in self.declined_categories:
                suggestions.add("McCafé")

        return list(suggestions)

    def to_dict(self) -> dict:
        return {
            "items": [
                {
                    "cart_id": ci["cart_id"],
                    "id": ci["item"]["id"],
                    "name": ci["item"]["name"],
                    "price": ci["item"]["price"],
                    "quantity": ci["quantity"],
                    "category": ci["item"]["category"]
                }
                for ci in self.items
            ],
            "total": self.get_total(),
            "missing_upsells": self.get_missing_upsells()
        }
