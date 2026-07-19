export const MENU_CATEGORIES = [
  "Burgers", "Breakfast", "Snacks & Sides", 
  "Happy Meal", "Desserts", "Beverages", "McCafé"
];

// Icon + one-line description shown in the left category rail.
export const CATEGORY_META = {
  "Burgers":        { icon: "🍔", blurb: "Stacked, grilled, classic" },
  "Breakfast":      { icon: "🥪", blurb: "Muffins, cakes & hash" },
  "Snacks & Sides":  { icon: "🍟", blurb: "Fries, wraps & nuggets" },
  "Happy Meal":     { icon: "🎁", blurb: "Meals made for kids" },
  "Desserts":       { icon: "🍨", blurb: "Sundaes, swirls & McFlurry" },
  "Beverages":      { icon: "🥤", blurb: "Cold drinks & shakes" },
  "McCafé":         { icon: "☕", blurb: "Coffee, pastries & more" },
};

export const MENU_ITEMS = [
  // Burgers
  { id: "b1", name: "McAloo Tikki Burger", category: "Burgers", price: 59, image: "🍔" },
  { id: "b2", name: "McVeggie Burger", category: "Burgers", price: 109, image: "🍔" },
  { id: "b3", name: "Veg Surprise Burger", category: "Burgers", price: 69, image: "🍔" },
  { id: "b4", name: "Crispy Veggie Burger", category: "Burgers", price: 89, image: "🍔" },
  { id: "b5", name: "McChicken Burger", category: "Burgers", price: 129, image: "🍔" },
  { id: "b6", name: "Veg Maharaja Mac", category: "Burgers", price: 199, image: "🍔" },
  { id: "b7", name: "McSpicy Chicken Burger", category: "Burgers", price: 189, image: "🍔" },
  { id: "b8", name: "Chicken McGrill Burger", category: "Burgers", price: 79, image: "🍔" },
  { id: "b9", name: "McEgg Burger", category: "Burgers", price: 59, image: "🍔" },
  { id: "b10", name: "McSpicy Paneer Burger", category: "Burgers", price: 179, image: "🍔" },
  { id: "b11", name: "Filet O Fish Burger", category: "Burgers", price: 169, image: "🐟" },
  { id: "b12", name: "Chicken Maharaja Mac", category: "Burgers", price: 209, image: "🍔" },
  { id: "b13", name: "McCrispy Chicken Burger", category: "Burgers", price: 199, image: "🍔" },
  { id: "b14", name: "The Cheesy Chicken Burger", category: "Burgers", price: 149, image: "🍔" },
  { id: "b15", name: "The Cheesy Mushroom Burger", category: "Burgers", price: 149, image: "🍔" },
  { id: "b16", name: "Butter Paneer Grilled Burger", category: "Burgers", price: 169, image: "🍔" },
  
  // Breakfast
  { id: "bf1", name: "Veg McMuffin", category: "Breakfast", price: 89, image: "🥪" },
  { id: "bf2", name: "Veg Supreme McMuffin", category: "Breakfast", price: 109, image: "🥪" },
  { id: "bf3", name: "Hot Cake", category: "Breakfast", price: 119, image: "🥞" },
  { id: "bf4", name: "Hash Brown", category: "Breakfast", price: 45, image: "🥔" },
  { id: "bf5", name: "Egg & Cheese Muffin", category: "Breakfast", price: 99, image: "🥪" },
  { id: "bf6", name: "Egg & Sausage McMuffin", category: "Breakfast", price: 129, image: "🥪" },
  { id: "bf7", name: "Sausage McMuffin", category: "Breakfast", price: 109, image: "🥪" },

  // Snacks & Sides
  { id: "s1", name: "McSpicy Paneer Wrap", category: "Snacks & Sides", price: 199, image: "🌯" },
  { id: "s2", name: "McFlavor Fries (PeriPeri)", category: "Snacks & Sides", price: 99, image: "🍟" },
  { id: "s3", name: "Pizza McPuff", category: "Snacks & Sides", price: 45, image: "🥟" },
  { id: "s4", name: "Chicken Puff", category: "Snacks & Sides", price: 55, image: "🥟" },
  { id: "s5", name: "Spicy Chicken Wrap", category: "Snacks & Sides", price: 209, image: "🌯" },
  { id: "s6", name: "Chicken McNuggets", category: "Snacks & Sides", price: 149, image: "🍗" },
  { id: "s7", name: "Our World Famous Fries", category: "Snacks & Sides", price: 79, image: "🍟" },
  { id: "s8", name: "Egg McWrap", category: "Snacks & Sides", price: 149, image: "🌯" },
  { id: "s9", name: "Tandoori Chicken McWrap", category: "Snacks & Sides", price: 219, image: "🌯" },
  { id: "s10", name: "Aloo Tikki McWrap", category: "Snacks & Sides", price: 139, image: "🌯" },

  // Happy Meal
  { id: "h1", name: "HappyMeal Chicken McGrill", category: "Happy Meal", price: 249, image: "🎁" },
  { id: "h2", name: "HappyMeal McAloo Tikki Burger", category: "Happy Meal", price: 219, image: "🎁" },
  { id: "h3", name: "HappyMeal McVeggie", category: "Happy Meal", price: 269, image: "🎁" },
  { id: "h4", name: "HappyMeal Chicken McNugget", category: "Happy Meal", price: 289, image: "🎁" },

  // Desserts
  { id: "d1", name: "Soft Serve Cone", category: "Desserts", price: 20, image: "🍦" },
  { id: "d2", name: "Mango McSwirl", category: "Desserts", price: 49, image: "🍦" },
  { id: "d3", name: "Chocolate McSwirl", category: "Desserts", price: 49, image: "🍦" },
  { id: "d4", name: "Butterscotch McSwirl", category: "Desserts", price: 49, image: "🍦" },
  { id: "d5", name: "Bobaaa Sundae", category: "Desserts", price: 99, image: "🍨" },
  { id: "d6", name: "Mango Soft Serve Sundae", category: "Desserts", price: 89, image: "🍨" },
  { id: "d7", name: "Sundae (Chocolate)", category: "Desserts", price: 89, image: "🍨" },
  { id: "d8", name: "Sundae (Strawberry)", category: "Desserts", price: 89, image: "🍨" },
  { id: "d9", name: "Sundae (Chocolate Brownie)", category: "Desserts", price: 119, image: "🍨" },
  { id: "d10", name: "McFlurry (Oreo)", category: "Desserts", price: 99, image: "🍧" },
  { id: "d11", name: "McFlurry (Choco Crunch)", category: "Desserts", price: 109, image: "🍧" },

  // Beverages
  { id: "v1", name: "Hot Coffee (Black)", category: "Beverages", price: 60, image: "☕" },
  { id: "v2", name: "Coca-Cola", category: "Beverages", price: 60, image: "🥤" },
  { id: "v3", name: "Fanta", category: "Beverages", price: 60, image: "🥤" },
  { id: "v4", name: "Sprite", category: "Beverages", price: 60, image: "🥤" },
  { id: "v5", name: "Bobaaa Sprite", category: "Beverages", price: 119, image: "🧋" },
  { id: "v6", name: "Bobaaa Blast", category: "Beverages", price: 129, image: "🧋" },
  { id: "v7", name: "McFloat (Coca-Cola)", category: "Beverages", price: 79, image: "🥤" },
  { id: "v8", name: "McFloat (Fanta)", category: "Beverages", price: 79, image: "🥤" },
  { id: "v9", name: "Cold Coffee", category: "Beverages", price: 99, image: "🧋" },
  { id: "v10", name: "Cold Coffee Mcfloat", category: "Beverages", price: 119, image: "🧋" },
  { id: "v11", name: "Iced Tea", category: "Beverages", price: 69, image: "🍹" },
  { id: "v12", name: "Masala Chai", category: "Beverages", price: 49, image: "☕" },
  { id: "v13", name: "Minute Maid Pulpy Orange", category: "Beverages", price: 75, image: "🧃" },
  { id: "v14", name: "Coke Zero", category: "Beverages", price: 65, image: "🥤" },
  { id: "v15", name: "Chocolate Milk Shake", category: "Beverages", price: 139, image: "🥤" },

  // McCafé
  { id: "c1", name: "Cappuccino", category: "McCafé", price: 129, image: "☕" },
  { id: "c2", name: "Latte", category: "McCafé", price: 139, image: "☕" },
  { id: "c3", name: "Iced Americano", category: "McCafé", price: 119, image: "🧊" },
  { id: "c4", name: "Americano", category: "McCafé", price: 99, image: "☕" },
  { id: "c5", name: "Mocha", category: "McCafé", price: 149, image: "☕" },
  { id: "c6", name: "Espresso", category: "McCafé", price: 79, image: "☕" },
  { id: "c7", name: "Macchiato", category: "McCafé", price: 119, image: "☕" },
  { id: "c8", name: "Velvety Hot Chocolate", category: "McCafé", price: 159, image: "☕" },
  { id: "c9", name: "Cold Coffee Frappe", category: "McCafé", price: 199, image: "🥤" },
  { id: "c10", name: "Caramel Frappe", category: "McCafé", price: 209, image: "🥤" },
  { id: "c11", name: "Chocolate Shake", category: "McCafé", price: 179, image: "🥤" },
  { id: "c12", name: "Strawberry Shake", category: "McCafé", price: 179, image: "🥤" },
  { id: "c13", name: "Vanilla Oreo Shake", category: "McCafé", price: 189, image: "🥤" },
  { id: "c14", name: "Iced Latte", category: "McCafé", price: 149, image: "🧊" },
  { id: "c15", name: "Iced Coffee", category: "McCafé", price: 129, image: "🧊" },
  { id: "c16", name: "Watermelon Cooler", category: "McCafé", price: 119, image: "🍉" },
  { id: "c17", name: "Peach Iced Tea", category: "McCafé", price: 119, image: "🍑" },
  { id: "c18", name: "Skillet Cookies", category: "McCafé", price: 99, image: "🍪" },
  { id: "c19", name: "Garlic Marinara Toasty", category: "McCafé", price: 89, image: "🍞" },
  { id: "c20", name: "Butter Croissant", category: "McCafé", price: 109, image: "🥐" },
  { id: "c21", name: "Strawberry Cheesecake", category: "McCafé", price: 169, image: "🍰" },
];
