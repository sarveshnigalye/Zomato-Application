"""
Self-contained zero-dependency SQLite seed script.
Uses standard library sqlite3 to create the exact schema and populate seed data into
data/processed/restaurants.db without requiring external pip packages.
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
PROCESSED_DATA_DIR = PROJECT_ROOT / "data" / "processed"
DB_PATH = PROCESSED_DATA_DIR / "restaurants.db"

SEED_RESTAURANTS = [
    {
        "name": "Chianti Italian Restaurant & Wine Lounge",
        "address": "12th Main Rd, HAL 2nd Stage, Indiranagar, Bangalore",
        "location": "Indiranagar",
        "city": "Bangalore",
        "cuisines": ["Italian", "Pizza", "Pasta"],
        "primary_cuisine": "Italian",
        "average_cost_for_two": 1200,
        "budget_tier": "medium",
        "aggregate_rating": 4.5,
        "is_rated": 1,
        "votes": 2840,
        "has_online_delivery": 1,
        "has_table_booking": 1,
        "highlights": ["Casual Dining", "Wine Bar", "Wood-Fired Pizza", "Handmade Ravioli", "Tiramisu"],
        "reviews_summary": "Exceptional Italian ambience with quick turnaround kitchen. The wood-fired pizza crust is authentic, crisp and airy. Family-friendly seating with attentive staff.",
        "synthetic_profile": "Chianti Italian Restaurant & Wine Lounge is a Italian, Pizza, Pasta dining place located in Indiranagar, Bangalore. Budget tier: medium (average cost for two: ₹1200). Rating: 4.5 stars with 2840 reviews. Popular features: Casual Dining, Wine Bar, Wood-Fired Pizza, Handmade Ravioli, Tiramisu. Atmosphere & highlights: Exceptional Italian ambience with quick turnaround kitchen. The wood-fired pizza crust is authentic, crisp and airy. Family-friendly seating with attentive staff.",
    },
    {
        "name": "Tossin Pizza",
        "address": "100 Feet Rd, Indiranagar, Bangalore",
        "location": "Indiranagar",
        "city": "Bangalore",
        "cuisines": ["Pizza", "Fast Food", "Italian"],
        "primary_cuisine": "Pizza",
        "average_cost_for_two": 800,
        "budget_tier": "medium",
        "aggregate_rating": 4.3,
        "is_rated": 1,
        "votes": 1450,
        "has_online_delivery": 1,
        "has_table_booking": 0,
        "highlights": ["Quick Bites", "Peri Peri Chicken Pizza", "Garlic Bread", "Calzone"],
        "reviews_summary": "Fastest pizza delivery and takeaway in Indiranagar. Great crust, generous toppings and reliable quick service for casual meals.",
        "synthetic_profile": "Tossin Pizza is a Pizza, Fast Food, Italian dining place located in Indiranagar, Bangalore. Budget tier: medium (average cost for two: ₹800). Rating: 4.3 stars with 1450 reviews. Popular features: Quick Bites, Peri Peri Chicken Pizza, Garlic Bread, Calzone. Atmosphere & highlights: Fastest pizza delivery and takeaway in Indiranagar. Great crust, generous toppings and reliable quick service for casual meals.",
    },
    {
        "name": "Corner House Ice Cream",
        "address": "1st Stage, Koramangala, Bangalore",
        "location": "Koramangala",
        "city": "Bangalore",
        "cuisines": ["Desserts", "Ice Cream"],
        "primary_cuisine": "Desserts",
        "average_cost_for_two": 400,
        "budget_tier": "low",
        "aggregate_rating": 4.7,
        "is_rated": 1,
        "votes": 8520,
        "has_online_delivery": 1,
        "has_table_booking": 0,
        "highlights": ["Dessert Parlor", "Death By Chocolate", "Hot Butterscotch", "Almond Fudge"],
        "reviews_summary": "Iconic dessert spot with unbeatable low budget pricing. Always crowded, family-friendly atmosphere with heavenly Death By Chocolate sundaes.",
        "synthetic_profile": "Corner House Ice Cream is a Desserts, Ice Cream dining place located in Koramangala, Bangalore. Budget tier: low (average cost for two: ₹400). Rating: 4.7 stars with 8520 reviews. Popular features: Dessert Parlor, Death By Chocolate, Hot Butterscotch, Almond Fudge. Atmosphere & highlights: Iconic dessert spot with unbeatable low budget pricing. Always crowded, family-friendly atmosphere with heavenly Death By Chocolate sundaes.",
    },
    {
        "name": "Empire Restaurant",
        "address": "80 Feet Rd, 4th Block, Koramangala, Bangalore",
        "location": "Koramangala",
        "city": "Bangalore",
        "cuisines": ["North Indian", "Mughlai", "Biryani", "Fast Food"],
        "primary_cuisine": "North Indian",
        "average_cost_for_two": 500,
        "budget_tier": "low",
        "aggregate_rating": 4.1,
        "is_rated": 1,
        "votes": 6120,
        "has_online_delivery": 1,
        "has_table_booking": 0,
        "highlights": ["Quick Bites", "Casual Dining", "Ghee Rice", "Empire Special Chicken Kebab", "Shawarma"],
        "reviews_summary": "Bangalore's late night lifesaver. Fast service, consistent spiced kebabs and reasonable prices. Great for late night hunger pangs.",
        "synthetic_profile": "Empire Restaurant is a North Indian, Mughlai, Biryani, Fast Food dining place located in Koramangala, Bangalore. Budget tier: low (average cost for two: ₹500). Rating: 4.1 stars with 6120 reviews. Popular features: Quick Bites, Casual Dining, Ghee Rice, Empire Special Chicken Kebab, Shawarma. Atmosphere & highlights: Bangalore's late night lifesaver. Fast service, consistent spiced kebabs and reasonable prices. Great for late night hunger pangs.",
    },
    {
        "name": "Windmills Craftworks",
        "address": "331 Road, EPIP Zone, Whitefield, Bangalore",
        "location": "Whitefield",
        "city": "Bangalore",
        "cuisines": ["Continental", "American", "North Indian", "Craft Beer"],
        "primary_cuisine": "Continental",
        "average_cost_for_two": 2500,
        "budget_tier": "high",
        "aggregate_rating": 4.8,
        "is_rated": 1,
        "votes": 7340,
        "has_online_delivery": 0,
        "has_table_booking": 1,
        "highlights": ["Microbrewery", "Fine Dining", "Craft Beer", "Risotto", "Stout"],
        "reviews_summary": "A serene microbrewery with live jazz and books. Outstanding high-end ambience, romantic mood lighting, and impeccably curated global food.",
        "synthetic_profile": "Windmills Craftworks is a Continental, American, North Indian, Craft Beer dining place located in Whitefield, Bangalore. Budget tier: high (average cost for two: ₹2500). Rating: 4.8 stars with 7340 reviews. Popular features: Microbrewery, Fine Dining, Craft Beer, Risotto, Stout. Atmosphere & highlights: A serene microbrewery with live jazz and books. Outstanding high-end ambience, romantic mood lighting, and impeccably curated global food.",
    },
    {
        "name": "Brahmin's Coffee Bar",
        "address": "Ranga Rao Road, Shankarapuram, Basavanagudi, Bangalore",
        "location": "Basavanagudi",
        "city": "Bangalore",
        "cuisines": ["South Indian", "Street Food"],
        "primary_cuisine": "South Indian",
        "average_cost_for_two": 150,
        "budget_tier": "low",
        "aggregate_rating": 4.8,
        "is_rated": 1,
        "votes": 9100,
        "has_online_delivery": 0,
        "has_table_booking": 0,
        "highlights": ["Quick Bites", "Idli Vada", "Filter Coffee", "Coconut Chutney"],
        "reviews_summary": "Legendary South Indian breakfast in old Bangalore. Melt-in-mouth idlis, crisp vadas and fresh coconut chutney served in seconds. Budget friendly and quick.",
        "synthetic_profile": "Brahmin's Coffee Bar is a South Indian, Street Food dining place located in Basavanagudi, Bangalore. Budget tier: low (average cost for two: ₹150). Rating: 4.8 stars with 9100 reviews. Popular features: Quick Bites, Idli Vada, Filter Coffee, Coconut Chutney. Atmosphere & highlights: Legendary South Indian breakfast in old Bangalore. Melt-in-mouth idlis, crisp vadas and fresh coconut chutney served in seconds. Budget friendly and quick.",
    },
    {
        "name": "Toit Brewpub",
        "address": "298, 100 Feet Rd, Near KFC Signal, Indiranagar, Bangalore",
        "location": "Indiranagar",
        "city": "Bangalore",
        "cuisines": ["Italian", "American", "Modern Indian", "Craft Beer"],
        "primary_cuisine": "Italian",
        "average_cost_for_two": 1600,
        "budget_tier": "high",
        "aggregate_rating": 4.7,
        "is_rated": 1,
        "votes": 12400,
        "has_online_delivery": 0,
        "has_table_booking": 1,
        "highlights": ["Microbrewery", "Casual Dining", "Tin Man", "Wood Fired Pizza", "Baked Nachos"],
        "reviews_summary": "Vibrant brewery atmosphere, energetic crowd, pet friendly and delicious wood-fired sourdough pizzas with world-class craft brews.",
        "synthetic_profile": "Toit Brewpub is a Italian, American, Modern Indian, Craft Beer dining place located in Indiranagar, Bangalore. Budget tier: high (average cost for two: ₹1600). Rating: 4.7 stars with 12400 reviews. Popular features: Microbrewery, Casual Dining, Tin Man, Wood Fired Pizza, Baked Nachos. Atmosphere & highlights: Vibrant brewery atmosphere, energetic crowd, pet friendly and delicious wood-fired sourdough pizzas with world-class craft brews.",
    },
    {
        "name": "Saravana Bhavan",
        "address": "Janpath, Connaught Place, New Delhi",
        "location": "Connaught Place",
        "city": "Delhi",
        "cuisines": ["South Indian", "Vegetarian"],
        "primary_cuisine": "South Indian",
        "average_cost_for_two": 600,
        "budget_tier": "medium",
        "aggregate_rating": 4.2,
        "is_rated": 1,
        "votes": 4300,
        "has_online_delivery": 1,
        "has_table_booking": 0,
        "highlights": ["Casual Dining", "Ghee Roast Dosa", "Rava Masala Dosa", "Filter Coffee"],
        "reviews_summary": "Authentic vegetarian South Indian delicacies in central Delhi. Consistent, hygienic and fast-moving family dining.",
        "synthetic_profile": "Saravana Bhavan is a South Indian, Vegetarian dining place located in Connaught Place, Delhi. Budget tier: medium (average cost for two: ₹600). Rating: 4.2 stars with 4300 reviews. Popular features: Casual Dining, Ghee Roast Dosa, Rava Masala Dosa, Filter Coffee. Atmosphere & highlights: Authentic vegetarian South Indian delicacies in central Delhi. Consistent, hygienic and fast-moving family dining.",
    },
    {
        "name": "Bukhara - ITC Maurya",
        "address": "ITC Maurya, Sardar Patel Marg, Diplomatic Enclave, New Delhi",
        "location": "Chanakyapuri",
        "city": "Delhi",
        "cuisines": ["North Indian", "Mughlai", "Kebab"],
        "primary_cuisine": "North Indian",
        "average_cost_for_two": 6500,
        "budget_tier": "high",
        "aggregate_rating": 4.9,
        "is_rated": 1,
        "votes": 5200,
        "has_online_delivery": 0,
        "has_table_booking": 1,
        "highlights": ["Fine Dining", "Dal Bukhara", "Sikandari Raan", "Naan Bukhara", "Murgh Malai Kebab"],
        "reviews_summary": "World-renowned culinary landmark. Slow-cooked 18-hour Dal Bukhara, rustic clay oven ambience and premier luxury dining.",
        "synthetic_profile": "Bukhara - ITC Maurya is a North Indian, Mughlai, Kebab dining place located in Chanakyapuri, Delhi. Budget tier: high (average cost for two: ₹6500). Rating: 4.9 stars with 5200 reviews. Popular features: Fine Dining, Dal Bukhara, Sikandari Raan, Naan Bukhara, Murgh Malai Kebab. Atmosphere & highlights: World-renowned culinary landmark. Slow-cooked 18-hour Dal Bukhara, rustic clay oven ambience and premier luxury dining.",
    },
    {
        "name": "Haldiram's",
        "address": "B-Block, Inner Circle, Connaught Place, New Delhi",
        "location": "Connaught Place",
        "city": "Delhi",
        "cuisines": ["Street Food", "North Indian", "Sweets", "Fast Food"],
        "primary_cuisine": "Street Food",
        "average_cost_for_two": 450,
        "budget_tier": "low",
        "aggregate_rating": 4.0,
        "is_rated": 1,
        "votes": 3100,
        "has_online_delivery": 1,
        "has_table_booking": 0,
        "highlights": ["Quick Bites", "Raj Kachori", "Chole Bhature", "Pav Bhaji", "Rasmalai"],
        "reviews_summary": "Bustling, affordable street food destination. Quick service, clean environment, ideal for families and casual snacking.",
        "synthetic_profile": "Haldiram's is a Street Food, North Indian, Sweets, Fast Food dining place located in Connaught Place, Delhi. Budget tier: low (average cost for two: ₹450). Rating: 4.0 stars with 3100 reviews. Popular features: Quick Bites, Raj Kachori, Chole Bhature, Pav Bhaji, Rasmalai. Atmosphere & highlights: Bustling, affordable street food destination. Quick service, clean environment, ideal for families and casual snacking.",
    },
]


def seed_database():
    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    # Enable WAL mode
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("PRAGMA synchronous=NORMAL;")

    # Create tables
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS restaurants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name VARCHAR(255) NOT NULL,
        address TEXT,
        location VARCHAR(255) NOT NULL,
        city VARCHAR(100) NOT NULL DEFAULT 'Bangalore',
        cuisines TEXT NOT NULL DEFAULT '[]',
        primary_cuisine VARCHAR(100),
        average_cost_for_two INTEGER NOT NULL,
        budget_tier VARCHAR(50) NOT NULL,
        aggregate_rating REAL NOT NULL DEFAULT 0.0,
        is_rated BOOLEAN NOT NULL DEFAULT 1,
        votes INTEGER NOT NULL DEFAULT 0,
        has_online_delivery BOOLEAN NOT NULL DEFAULT 0,
        has_table_booking BOOLEAN NOT NULL DEFAULT 0,
        highlights TEXT NOT NULL DEFAULT '[]',
        reviews_summary TEXT,
        synthetic_profile TEXT,
        created_at TIMESTAMP NOT NULL,
        updated_at TIMESTAMP NOT NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS query_feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        recommendation_id VARCHAR(100),
        restaurant_id INTEGER,
        user_query TEXT,
        rating_score INTEGER,
        comment TEXT,
        created_at TIMESTAMP NOT NULL
    );
    """)

    # Create indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_restaurants_name ON restaurants(name);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_restaurants_location ON restaurants(location);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_restaurants_city ON restaurants(city);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_restaurants_budget_tier ON restaurants(budget_tier);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_restaurants_aggregate_rating ON restaurants(aggregate_rating);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_location_budget ON restaurants(location, budget_tier);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_city_budget ON restaurants(city, budget_tier);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_budget_rating ON restaurants(budget_tier, aggregate_rating);")

    # Clear and insert seed data
    cursor.execute("DELETE FROM restaurants;")
    now = datetime.utcnow().isoformat()

    insert_sql = """
    INSERT INTO restaurants (
        name, address, location, city, cuisines, primary_cuisine,
        average_cost_for_two, budget_tier, aggregate_rating, is_rated, votes,
        has_online_delivery, has_table_booking, highlights, reviews_summary,
        synthetic_profile, created_at, updated_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """

    for r in SEED_RESTAURANTS:
        cursor.execute(
            insert_sql,
            (
                r["name"],
                r["address"],
                r["location"],
                r["city"],
                json.dumps(r["cuisines"]),
                r["primary_cuisine"],
                r["average_cost_for_two"],
                r["budget_tier"],
                r["aggregate_rating"],
                r["is_rated"],
                r["votes"],
                r["has_online_delivery"],
                r["has_table_booking"],
                json.dumps(r["highlights"]),
                r["reviews_summary"],
                r["synthetic_profile"],
                now,
                now,
            ),
        )

    conn.commit()

    cursor.execute("SELECT COUNT(*) FROM restaurants;")
    count = cursor.fetchone()[0]
    conn.close()
    print(f"Successfully seeded {count} restaurants into {DB_PATH}")
    return count


if __name__ == "__main__":
    seed_database()
