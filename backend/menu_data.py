import difflib

MENU_CATEGORIES = [
    "Burgers", "Breakfast", "Snacks & Sides", 
    "Happy Meal", "Desserts", "Beverages", "McCafé"
]

MENU_ITEMS = [
    # Burgers
    {"id": "b1", "name": "McAloo Tikki Burger", "category": "Burgers", "price": 59},
    {"id": "b2", "name": "McVeggie Burger", "category": "Burgers", "price": 109},
    {"id": "b3", "name": "Veg Surprise Burger", "category": "Burgers", "price": 69},
    {"id": "b4", "name": "Crispy Veggie Burger", "category": "Burgers", "price": 89},
    {"id": "b5", "name": "McChicken Burger", "category": "Burgers", "price": 129},
    {"id": "b6", "name": "Veg Maharaja Mac", "category": "Burgers", "price": 199},
    {"id": "b7", "name": "McSpicy Chicken Burger", "category": "Burgers", "price": 189},
    {"id": "b8", "name": "Chicken McGrill Burger", "category": "Burgers", "price": 79},
    {"id": "b9", "name": "McEgg Burger", "category": "Burgers", "price": 59},
    {"id": "b10", "name": "McSpicy Paneer Burger", "category": "Burgers", "price": 179},
    {"id": "b11", "name": "Filet O Fish Burger", "category": "Burgers", "price": 169},
    {"id": "b12", "name": "Chicken Maharaja Mac", "category": "Burgers", "price": 209},
    {"id": "b13", "name": "McCrispy Chicken Burger", "category": "Burgers", "price": 199},
    {"id": "b14", "name": "The Cheesy Chicken Burger", "category": "Burgers", "price": 149},
    {"id": "b15", "name": "The Cheesy Mushroom Burger", "category": "Burgers", "price": 149},
    {"id": "b16", "name": "Butter Paneer Grilled Burger", "category": "Burgers", "price": 169},
    
    # Breakfast
    {"id": "bf1", "name": "Veg McMuffin", "category": "Breakfast", "price": 89},
    {"id": "bf2", "name": "Veg Supreme McMuffin", "category": "Breakfast", "price": 109},
    {"id": "bf3", "name": "Hot Cake", "category": "Breakfast", "price": 119},
    {"id": "bf4", "name": "Hash Brown", "category": "Breakfast", "price": 45},
    {"id": "bf5", "name": "Egg & Cheese Muffin", "category": "Breakfast", "price": 99},
    {"id": "bf6", "name": "Egg & Sausage McMuffin", "category": "Breakfast", "price": 129},
    {"id": "bf7", "name": "Sausage McMuffin", "category": "Breakfast", "price": 109},

    # Snacks & Sides
    {"id": "s1", "name": "McSpicy Paneer Wrap", "category": "Snacks & Sides", "price": 199},
    {"id": "s2", "name": "McFlavor Fries (PeriPeri)", "category": "Snacks & Sides", "price": 99},
    {"id": "s3", "name": "Pizza McPuff", "category": "Snacks & Sides", "price": 45},
    {"id": "s4", "name": "Chicken Puff", "category": "Snacks & Sides", "price": 55},
    {"id": "s5", "name": "Spicy Chicken Wrap", "category": "Snacks & Sides", "price": 209},
    {"id": "s6", "name": "Chicken McNuggets", "category": "Snacks & Sides", "price": 149},
    {"id": "s7", "name": "Our World Famous Fries", "category": "Snacks & Sides", "price": 79},
    {"id": "s8", "name": "Egg McWrap", "category": "Snacks & Sides", "price": 149},
    {"id": "s9", "name": "Tandoori Chicken McWrap", "category": "Snacks & Sides", "price": 219},
    {"id": "s10", "name": "Aloo Tikki McWrap", "category": "Snacks & Sides", "price": 139},

    # Happy Meal
    {"id": "h1", "name": "HappyMeal Chicken McGrill", "category": "Happy Meal", "price": 249},
    {"id": "h2", "name": "HappyMeal McAloo Tikki Burger", "category": "Happy Meal", "price": 219},
    {"id": "h3", "name": "HappyMeal McVeggie", "category": "Happy Meal", "price": 269},
    {"id": "h4", "name": "HappyMeal Chicken McNugget", "category": "Happy Meal", "price": 289},

    # Desserts
    {"id": "d1", "name": "Soft Serve Cone", "category": "Desserts", "price": 20},
    {"id": "d2", "name": "Mango McSwirl", "category": "Desserts", "price": 49},
    {"id": "d3", "name": "Chocolate McSwirl", "category": "Desserts", "price": 49},
    {"id": "d4", "name": "Butterscotch McSwirl", "category": "Desserts", "price": 49},
    {"id": "d5", "name": "Bobaaa Sundae", "category": "Desserts", "price": 99},
    {"id": "d6", "name": "Mango Soft Serve Sundae", "category": "Desserts", "price": 89},
    {"id": "d7", "name": "Sundae (Chocolate)", "category": "Desserts", "price": 89},
    {"id": "d8", "name": "Sundae (Strawberry)", "category": "Desserts", "price": 89},
    {"id": "d9", "name": "Sundae (Chocolate Brownie)", "category": "Desserts", "price": 119},
    {"id": "d10", "name": "McFlurry (Oreo)", "category": "Desserts", "price": 99},
    {"id": "d11", "name": "McFlurry (Choco Crunch)", "category": "Desserts", "price": 109},

    # Beverages
    {"id": "v1", "name": "Hot Coffee (Black)", "category": "Beverages", "price": 60},
    {"id": "v2", "name": "Coca-Cola", "category": "Beverages", "price": 60},
    {"id": "v3", "name": "Fanta", "category": "Beverages", "price": 60},
    {"id": "v4", "name": "Sprite", "category": "Beverages", "price": 60},
    {"id": "v5", "name": "Bobaaa Sprite", "category": "Beverages", "price": 119},
    {"id": "v6", "name": "Bobaaa Blast", "category": "Beverages", "price": 129},
    {"id": "v7", "name": "McFloat (Coca-Cola)", "category": "Beverages", "price": 79},
    {"id": "v8", "name": "McFloat (Fanta)", "category": "Beverages", "price": 79},
    {"id": "v9", "name": "Cold Coffee", "category": "Beverages", "price": 99},
    {"id": "v10", "name": "Cold Coffee Mcfloat", "category": "Beverages", "price": 119},
    {"id": "v11", "name": "Iced Tea", "category": "Beverages", "price": 69},
    {"id": "v12", "name": "Masala Chai", "category": "Beverages", "price": 49},
    {"id": "v13", "name": "Minute Maid Pulpy Orange", "category": "Beverages", "price": 75},
    {"id": "v14", "name": "Coke Zero", "category": "Beverages", "price": 65},
    {"id": "v15", "name": "Chocolate Milk Shake", "category": "Beverages", "price": 139},

    # McCafé
    {"id": "c1", "name": "Cappuccino", "category": "McCafé", "price": 129},
    {"id": "c2", "name": "Latte", "category": "McCafé", "price": 139},
    {"id": "c3", "name": "Iced Americano", "category": "McCafé", "price": 119},
    {"id": "c4", "name": "Americano", "category": "McCafé", "price": 99},
    {"id": "c5", "name": "Mocha", "category": "McCafé", "price": 149},
    {"id": "c6", "name": "Espresso", "category": "McCafé", "price": 79},
    {"id": "c7", "name": "Macchiato", "category": "McCafé", "price": 119},
    {"id": "c8", "name": "Velvety Hot Chocolate", "category": "McCafé", "price": 159},
    {"id": "c9", "name": "Cold Coffee Frappe", "category": "McCafé", "price": 199},
    {"id": "c10", "name": "Caramel Frappe", "category": "McCafé", "price": 209},
    {"id": "c11", "name": "Chocolate Shake", "category": "McCafé", "price": 179},
    {"id": "c12", "name": "Strawberry Shake", "category": "McCafé", "price": 179},
    {"id": "c13", "name": "Vanilla Oreo Shake", "category": "McCafé", "price": 189},
    {"id": "c14", "name": "Iced Latte", "category": "McCafé", "price": 149},
    {"id": "c15", "name": "Iced Coffee", "category": "McCafé", "price": 129},
    {"id": "c16", "name": "Watermelon Cooler", "category": "McCafé", "price": 119},
    {"id": "c17", "name": "Peach Iced Tea", "category": "McCafé", "price": 119},
    {"id": "c18", "name": "Skillet Cookies", "category": "McCafé", "price": 99},
    {"id": "c19", "name": "Garlic Marinara Toasty", "category": "McCafé", "price": 89},
    {"id": "c20", "name": "Butter Croissant", "category": "McCafé", "price": 109},
    {"id": "c21", "name": "Strawberry Cheesecake", "category": "McCafé", "price": 169},
]

def find_item_by_name(query_name: str):
    """
    Fuzzy match to find the closest menu item.
    """
    if not query_name:
        return None
        
    names = [item["name"].lower() for item in MENU_ITEMS]
    query = query_name.lower()
    
    # Try exact match first
    for item in MENU_ITEMS:
        if query == item["name"].lower():
            return item
            
    # Try substring match
    for item in MENU_ITEMS:
        if query in item["name"].lower():
            return item
            
    # Fallback to difflib
    matches = difflib.get_close_matches(query, names, n=1, cutoff=0.5)
    if matches:
        match_name = matches[0]
        for item in MENU_ITEMS:
            if item["name"].lower() == match_name:
                return item
                
    return None

def get_item_by_id(item_id: str):
    for item in MENU_ITEMS:
        if item["id"] == item_id:
            return item
    return None

# Common spoken synonyms that don't literally match a category name
_CATEGORY_SYNONYMS = {
    "drinks": "Beverages",
    "drink": "Beverages",
    "beverage": "Beverages",
    "soda": "Beverages",
    "sodas": "Beverages",
    "coffee": "McCafé",
    "cafe": "McCafé",
    "mccafe": "McCafé",
    "mc cafe": "McCafé",
    "sweets": "Desserts",
    "dessert": "Desserts",
    "ice cream": "Desserts",
    "sides": "Snacks & Sides",
    "snacks": "Snacks & Sides",
    "fries": "Snacks & Sides",
    "kids meal": "Happy Meal",
    "kids": "Happy Meal",
    "burger": "Burgers",
}

def find_category_by_name(query_name: str):
    """
    Fuzzy match spoken category names (e.g. "drinks", "coffee") onto the
    real MENU_CATEGORIES list. Returns the exact category string, or None
    if nothing reasonably matches (never invents a category).
    """
    if not query_name:
        return None

    query = query_name.strip().lower()

    # Exact match
    for cat in MENU_CATEGORIES:
        if query == cat.lower():
            return cat

    # Synonym match
    if query in _CATEGORY_SYNONYMS:
        return _CATEGORY_SYNONYMS[query]

    # Substring match (either direction)
    for cat in MENU_CATEGORIES:
        if query in cat.lower() or cat.lower() in query:
            return cat

    # Fuzzy fallback
    matches = difflib.get_close_matches(query, [c.lower() for c in MENU_CATEGORIES], n=1, cutoff=0.6)
    if matches:
        for cat in MENU_CATEGORIES:
            if cat.lower() == matches[0]:
                return cat

    return None
