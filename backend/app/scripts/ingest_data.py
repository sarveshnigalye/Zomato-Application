"""
Hugging Face Dataset Ingestion & Sanitization Pipeline.
Loads data from Hugging Face Hub (ManikaSaini/zomato-restaurant-recommendation) or local cache,
cleans, normalizes, deduplicates, and commits structured records into SQLite storage.
Handles edge cases DATA-01 to DATA-07 specified in Docs/edge-case.md.
"""

import json
import logging
import os
import re
import sys
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Add project root to sys.path if running as standalone script
CURRENT_FILE = Path(__file__).resolve()
SCRIPTS_DIR = CURRENT_FILE.parent
APP_DIR = SCRIPTS_DIR.parent
BACKEND_DIR = APP_DIR.parent
PROJECT_ROOT = BACKEND_DIR.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.config import settings

# Optional third-party imports with graceful fallbacks
try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    pd = None  # type: ignore
    HAS_PANDAS = False

try:
    from backend.app.models.database import Base, Restaurant, engine, SessionLocal, init_db
    HAS_SQLALCHEMY = True
except ImportError:
    HAS_SQLALCHEMY = False

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ingest_data")

# Comprehensive offline seed dataset covering Bangalore & Delhi, multiple cuisines, budget tiers, and edge cases
OFFLINE_SEED_DATA: List[Dict[str, Any]] = [
    {
        "name": "Chianti Italian Restaurant & Wine Lounge",
        "address": "12th Main Rd, HAL 2nd Stage, Indiranagar, Bangalore",
        "location": "Indiranagar",
        "city": "Bangalore",
        "cuisines": "Italian, Pizza, Pasta",
        "rate": "4.5/5",
        "votes": "2840",
        "approx_cost(for two people)": "1,200",
        "online_order": "Yes",
        "book_table": "Yes",
        "rest_type": "Casual Dining, Wine Bar",
        "dish_liked": "Wood-Fired Pizza, Handmade Ravioli, Tiramisu, Sangria",
        "reviews_list": "Exceptional Italian ambience with quick turnaround kitchen. The wood-fired pizza crust is authentic, crisp and airy. Family-friendly seating with attentive staff.",
    },
    {
        "name": "Tossin Pizza",
        "address": "100 Feet Rd, Indiranagar, Bangalore",
        "location": "Indiranagar",
        "city": "Bangalore",
        "cuisines": "Pizza, Fast Food, Italian",
        "rate": "4.3/5",
        "votes": "1450",
        "approx_cost(for two people)": "800",
        "online_order": "Yes",
        "book_table": "No",
        "rest_type": "Quick Bites",
        "dish_liked": "Peri Peri Chicken Pizza, Garlic Bread, Calzone",
        "reviews_list": "Fastest pizza delivery and takeaway in Indiranagar. Great crust, generous toppings and reliable quick service for casual meals.",
    },
    {
        "name": "Corner House Ice Cream",
        "address": "1st Stage, Koramangala, Bangalore",
        "location": "Koramangala",
        "city": "Bangalore",
        "cuisines": "Desserts, Ice Cream",
        "rate": "4.7/5",
        "votes": "8520",
        "approx_cost(for two people)": "400",
        "online_order": "Yes",
        "book_table": "No",
        "rest_type": "Dessert Parlor",
        "dish_liked": "Death By Chocolate, Hot Butterscotch, Almond Fudge",
        "reviews_list": "Iconic dessert spot with unbeatable low budget pricing. Always crowded, family-friendly atmosphere with heavenly Death By Chocolate sundaes.",
    },
    {
        "name": "Empire Restaurant",
        "address": "80 Feet Rd, 4th Block, Koramangala, Bangalore",
        "location": "Koramangala",
        "city": "Bangalore",
        "cuisines": "North Indian, Mughlai, Biryani, Fast Food",
        "rate": "4.1/5",
        "votes": "6120",
        "approx_cost(for two people)": "500",
        "online_order": "Yes",
        "book_table": "No",
        "rest_type": "Quick Bites, Casual Dining",
        "dish_liked": "Ghee Rice, Empire Special Chicken Kebab, Shawarma, Biryani",
        "reviews_list": "Bangalore's late night lifesaver. Fast service, consistent spiced kebabs and reasonable prices. Great for late night hunger pangs.",
    },
    {
        "name": "Windmills Craftworks",
        "address": "331 Road, EPIP Zone, Whitefield, Bangalore",
        "location": "Whitefield",
        "city": "Bangalore",
        "cuisines": "Continental, American, North Indian, Craft Beer",
        "rate": "4.8/5",
        "votes": "7340",
        "approx_cost(for two people)": "2,500",
        "online_order": "No",
        "book_table": "Yes",
        "rest_type": "Microbrewery, Fine Dining",
        "dish_liked": "Craft Beer, Stout, Risotto, Pork Ribs, Blueberry Cheesecake",
        "reviews_list": "A serene microbrewery with live jazz and books. Outstanding high-end ambience, romantic mood lighting, and impeccably curated global food.",
    },
    {
        "name": "Brahmin's Coffee Bar",
        "address": "Ranga Rao Road, Shankarapuram, Basavanagudi, Bangalore",
        "location": "Basavanagudi",
        "city": "Bangalore",
        "cuisines": "South Indian, Street Food",
        "rate": "4.8/5",
        "votes": "9100",
        "approx_cost(for two people)": "150",
        "online_order": "No",
        "book_table": "No",
        "rest_type": "Quick Bites",
        "dish_liked": "Idli Vada, Filter Coffee, Coconut Chutney, Khara Bath",
        "reviews_list": "Legendary South Indian breakfast in old Bangalore. Melt-in-mouth idlis, crisp vadas and fresh coconut chutney served in seconds. Budget friendly and quick.",
    },
    {
        "name": "Toit Brewpub",
        "address": "298, 100 Feet Rd, Near KFC Signal, Indiranagar, Bangalore",
        "location": "Indiranagar",
        "city": "Bangalore",
        "cuisines": "Italian, American, Modern Indian, Craft Beer",
        "rate": "4.7/5",
        "votes": "12400",
        "approx_cost(for two people)": "1,600",
        "online_order": "No",
        "book_table": "Yes",
        "rest_type": "Microbrewery, Casual Dining",
        "dish_liked": "Tin Man, Basmati Blonde, Wood Fired Pizza, Baked Nachos",
        "reviews_list": "Vibrant brewery atmosphere, energetic crowd, pet friendly and delicious wood-fired sourdough pizzas with world-class craft brews.",
    },
    {
        "name": "Saravana Bhavan",
        "address": "Janpath, Connaught Place, New Delhi",
        "location": "Connaught Place",
        "city": "Delhi",
        "cuisines": "South Indian, Vegetarian",
        "rate": "4.2/5",
        "votes": "4300",
        "approx_cost(for two people)": "600",
        "online_order": "Yes",
        "book_table": "No",
        "rest_type": "Casual Dining",
        "dish_liked": "Ghee Roast Dosa, Rava Masala Dosa, Filter Coffee",
        "reviews_list": "Authentic vegetarian South Indian delicacies in central Delhi. Consistent, hygienic and fast-moving family dining.",
    },
    {
        "name": "Bukhara - ITC Maurya",
        "address": "ITC Maurya, Sardar Patel Marg, Diplomatic Enclave, New Delhi",
        "location": "Chanakyapuri",
        "city": "Delhi",
        "cuisines": "North Indian, Mughlai, Kebab",
        "rate": "4.9/5",
        "votes": "5200",
        "approx_cost(for two people)": "6,500",
        "online_order": "No",
        "book_table": "Yes",
        "rest_type": "Fine Dining",
        "dish_liked": "Dal Bukhara, Sikandari Raan, Naan Bukhara, Murgh Malai Kebab",
        "reviews_list": "World-renowned culinary landmark. Slow-cooked 18-hour Dal Bukhara, rustic clay oven ambience and premier luxury dining.",
    },
    {
        "name": "Haldiram's",
        "address": "B-Block, Inner Circle, Connaught Place, New Delhi",
        "location": "Connaught Place",
        "city": "Delhi",
        "cuisines": "Street Food, North Indian, Sweets, Fast Food",
        "rate": "4.0/5",
        "votes": "3100",
        "approx_cost(for two people)": "450",
        "online_order": "Yes",
        "book_table": "No",
        "rest_type": "Quick Bites",
        "dish_liked": "Raj Kachori, Chole Bhature, Pav Bhaji, Rasmalai",
        "reviews_list": "Bustling, affordable street food destination. Quick service, clean environment, ideal for families and casual snacking.",
    },
    {
        "name": "Truffles",
        "address": "93, 4th B Cross, 5th Block, Koramangala, Bangalore",
        "location": "Koramangala",
        "city": "Bangalore",
        "cuisines": "Cafe, American, Burger, Fast Food",
        "rate": "4.6/5",
        "votes": "14200",
        "approx_cost(for two people)": "750",
        "online_order": "Yes",
        "book_table": "No",
        "rest_type": "Casual Dining",
        "dish_liked": "All American Burger, Ferrero Rocher Shake, Peri Peri Chicken Burger",
        "reviews_list": "Beloved youth hangout known for monster burgers, creamy milkshakes, and speedy kitchen turnaround. Unbeatable value for money.",
    },
    {
        "name": "Glen's Bakehouse",
        "address": "297, 100 Feet Rd, Indiranagar, Bangalore",
        "location": "Indiranagar",
        "city": "Bangalore",
        "cuisines": "Cafe, Bakery, Desserts, Italian",
        "rate": "4.4/5",
        "votes": "6200",
        "approx_cost(for two people)": "800",
        "online_order": "Yes",
        "book_table": "No",
        "rest_type": "Cafe, Bakery",
        "dish_liked": "Red Velvet Cupcake, Pot Roast, Sourdough Pizza, Cheesecake",
        "reviews_list": "Charming European style cafe with cozy outdoor garden seating. Phenomenal baked desserts, artisan sourdough, and relaxing ambiance.",
    },
    {
        "name": "Meghana Foods",
        "address": "124, 1st Cross, 5th Block, Koramangala, Bangalore",
        "location": "Koramangala",
        "city": "Bangalore",
        "cuisines": "Biryani, Andhra, North Indian",
        "rate": "4.4/5",
        "votes": "11500",
        "approx_cost(for two people)": "600",
        "online_order": "Yes",
        "book_table": "No",
        "rest_type": "Casual Dining",
        "dish_liked": "Meghana Special Biryani, Boneless Chicken Biryani, Chilli Chicken",
        "reviews_list": "Legendary fiery Andhra biryani. Generous portions, lightning-fast table service, and consistently spicy, flavorful aromatic rice.",
    },
    {
        "name": "Nagarjuna",
        "address": "44/1, Residency Rd, Bangalore",
        "location": "Residency Road",
        "city": "Bangalore",
        "cuisines": "Andhra, South Indian, Biryani",
        "rate": "4.3/5",
        "votes": "5800",
        "approx_cost(for two people)": "800",
        "online_order": "Yes",
        "book_table": "Yes",
        "rest_type": "Casual Dining",
        "dish_liked": "Andhra Meal, Gunpowder Ghee Rice, Chicken Sholay Kebab",
        "reviews_list": "Classic banana leaf Andhra meals with infinite servings of aromatic ghee and gunpowder podi. Authentic, bustling, and flavorful.",
    },
    {
        "name": "Vidyarthi Bhavan",
        "address": "32, Gandhi Bazaar Main Rd, Basavanagudi, Bangalore",
        "location": "Gandhi Bazaar",
        "city": "Bangalore",
        "cuisines": "South Indian",
        "rate": "4.4/5",
        "votes": "9800",
        "approx_cost(for two people)": "200",
        "online_order": "No",
        "book_table": "No",
        "rest_type": "Quick Bites",
        "dish_liked": "Masale Dose, Filter Coffee, Kesari Bath, Rave Vade",
        "reviews_list": "Historic heritage eatery operating since 1943. Iconic thick, crispy, golden ghee masala dosas served with fresh mint coconut chutney.",
    },
    {
        "name": "The Fatty Bao",
        "address": "610, 12th Main Rd, HAL 2nd Stage, Indiranagar, Bangalore",
        "location": "Indiranagar",
        "city": "Bangalore",
        "cuisines": "Asian, Japanese, Chinese, Thai",
        "rate": "4.5/5",
        "votes": "4900",
        "approx_cost(for two people)": "2,000",
        "online_order": "Yes",
        "book_table": "Yes",
        "rest_type": "Asian Gastro-bar, Casual Dining",
        "dish_liked": "Char Siu Bao, Ramen, Dim Sum, Pork Belly, Cocktails",
        "reviews_list": "Playful modern Asian rooftop gastro-bar with vibrant murals. Melt-in-mouth steamed bao buns, flavorful steaming broths, and inventive craft cocktails.",
    },
    {
        "name": "Olive Beach",
        "address": "16, Wood St, Ashok Nagar, Richmond Town, Bangalore",
        "location": "Richmond Town",
        "city": "Bangalore",
        "cuisines": "Mediterranean, European, Italian",
        "rate": "4.6/5",
        "votes": "3800",
        "approx_cost(for two people)": "2,800",
        "online_order": "No",
        "book_table": "Yes",
        "rest_type": "Fine Dining",
        "dish_liked": "Truffle Risotto, Calamari, Mezze Platter, Wood Fired Pizza",
        "reviews_list": "Sun-drenched Mediterranean villa aesthetic with white-washed walls and romantic courtyard alfresco seating. Exquisite artisan European fare.",
    },
    {
        "name": "Karim's",
        "address": "16, Gali Kababian, Jama Masjid, Chandni Chowk, New Delhi",
        "location": "Chandni Chowk",
        "city": "Delhi",
        "cuisines": "Mughlai, North Indian, Kebab",
        "rate": "4.3/5",
        "votes": "6900",
        "approx_cost(for two people)": "800",
        "online_order": "Yes",
        "book_table": "No",
        "rest_type": "Casual Dining",
        "dish_liked": "Mutton Burra Kebab, Butter Chicken, Mutton Korma, Roomali Roti",
        "reviews_list": "Centuries-old royal Mughlai kitchen near Jama Masjid. Charred smoky kebabs and slow-braised velvety curries steeped in rich Old Delhi history.",
    },
    {
        "name": "The Big Chill Cafe",
        "address": "68-A, Khan Market, New Delhi",
        "location": "Khan Market",
        "city": "Delhi",
        "cuisines": "Italian, Continental, Desserts, Pasta",
        "rate": "4.5/5",
        "votes": "8200",
        "approx_cost(for two people)": "1,500",
        "online_order": "Yes",
        "book_table": "No",
        "rest_type": "Casual Dining",
        "dish_liked": "Penne Vodka, Blueberry Cheesecake, Four Cheese Pizza, Belgian Chocolate Shake",
        "reviews_list": "Iconic Delhi institution with retro movie posters and generous bowls of indulgent creamy pasta. Incredible European desserts and lively energy.",
    },
    {
        "name": "Urban Tadka",
        "address": "ITPL Main Rd, Whitefield, Bangalore",
        "location": "Whitefield",
        "city": "Bangalore",
        "cuisines": "North Indian, Mughlai",
        "rate": "NEW",
        "votes": "120",
        "approx_cost(for two people)": "700",
        "online_order": "Yes",
        "book_table": "No",
        "rest_type": "Casual Dining",
        "dish_liked": "Paneer Tikka, Dal Tadka, Garlic Naan",
        "reviews_list": "Newly opened North Indian dining joint serving smoky charcoal tandoori platters and aromatic rich gravies at sensible prices.",
    },
    {
        "name": "Spice Terrace",
        "address": "JW Marriott, 24/1, Vittal Mallya Rd, Lavelle Road, Bangalore",
        "location": "Lavelle Road",
        "city": "Bangalore",
        "cuisines": "North Indian, Seafood",
        "rate": "-",
        "votes": "340",
        "approx_cost(for two people)": "2,400",
        "online_order": "No",
        "book_table": "Yes",
        "rest_type": "Fine Dining",
        "dish_liked": "Seafood Curry, Galouti Kebab, Biryani",
        "reviews_list": "Luxury poolside open-air terrace diner at JW Marriott. Sophisticated ambiance with attentive fine dining hospitality.",
    },
]


def parse_rating(val: Any) -> Tuple[float, bool]:
    """
    Sanitize rate column (DATA-02).
    Parses '4.1/5', '4.3', 'NEW', '-', None into (float_rating, is_rated).
    """
    if val is None:
        return 0.0, False

    if HAS_PANDAS and pd.isna(val):
        return 0.0, False

    val_str = str(val).strip().upper()
    if not val_str or val_str in ("NEW", "-", "OPENING SOON", "NOT RATED", "NAN", "NONE"):
        return 0.0, False

    match = re.search(r"(\d+(?:\.\d+)?)", val_str)
    if match:
        try:
            rating = float(match.group(1))
            rating = max(0.0, min(5.0, round(rating, 2)))
            return rating, True
        except ValueError:
            return 0.0, False

    return 0.0, False


def parse_cost(val: Any, default_cost: int = 500) -> int:
    """
    Sanitize approx_cost(for two people) (DATA-03).
    Strips commas, symbols, and non-digit characters.
    """
    if val is None:
        return default_cost

    if HAS_PANDAS and pd.isna(val):
        return default_cost

    cleaned = re.sub(r"[^\d]", "", str(val))
    if cleaned:
        try:
            cost = int(cleaned)
            return cost if cost > 0 else default_cost
        except ValueError:
            return default_cost

    return default_cost


def assign_budget_tier(cost: int) -> str:
    """
    Assign strict canonical budget tier (DATA-04):
    low: <= 500
    medium: 501 - 1500
    high: > 1500
    """
    if cost <= settings.BUDGET_LOW_MAX:
        return "low"
    elif cost <= settings.BUDGET_MEDIUM_MAX:
        return "medium"
    else:
        return "high"


def parse_cuisines(val: Any) -> Tuple[List[str], str]:
    """
    Normalize cuisines (DATA-05).
    Trims, title-cases, deduplicates, and returns (cuisines_list, primary_cuisine).
    """
    if val is None:
        return ["Multi-Cuisine"], "Multi-Cuisine"

    if HAS_PANDAS and pd.isna(val):
        return ["Multi-Cuisine"], "Multi-Cuisine"

    parts = [part.strip().title() for part in str(val).split(",") if part.strip()]
    unique_cuisines: List[str] = []
    for c in parts:
        if c and c not in unique_cuisines:
            unique_cuisines.append(c)

    if not unique_cuisines:
        unique_cuisines = ["Multi-Cuisine"]

    primary = unique_cuisines[0]
    return unique_cuisines, primary


def synthesize_highlights(rest_type: Any, dish_liked: Any, cuisines: List[str]) -> List[str]:
    """
    Synthesize highlights from rest_type, dish_liked, and cuisine cues (DATA-06).
    Guarantees that highlights is never empty.
    """
    tags: List[str] = []

    # Process rest_type
    if rest_type is not None:
        if not (HAS_PANDAS and pd.isna(rest_type)):
            for item in str(rest_type).split(","):
                cleaned = item.strip().title()
                if cleaned and cleaned not in tags:
                    tags.append(cleaned)

    # Process dish_liked
    if dish_liked is not None:
        if not (HAS_PANDAS and pd.isna(dish_liked)):
            for item in str(dish_liked).split(","):
                cleaned = item.strip().title()
                if cleaned and cleaned not in tags:
                    tags.append(cleaned)

    # If sparse, inject top cuisines
    if len(tags) < 2:
        for c in cuisines:
            tag_name = f"{c} Specials"
            if tag_name not in tags:
                tags.append(tag_name)
            if len(tags) >= 3:
                break

    if not tags:
        tags = ["Casual Dining", "Popular Menu"]

    return tags[:8]


def infer_city(location_str: str, address_str: str) -> str:
    """Infer canonical city from location and address strings."""
    combined = f"{location_str} {address_str}".lower()
    if any(k in combined for k in ["delhi", "new delhi", "connaught place", "hauz khas", "chanakyapuri", "chandni chowk", "pandara", "khan market"]):
        return "Delhi"
    if any(k in combined for k in ["mumbai", "bandra", "andheri", "colaba", "juhu"]):
        return "Mumbai"
    return "Bangalore"


def generate_restaurant_profile(row: Dict[str, Any]) -> str:
    """
    Generate rich synthetic profile for semantic vector embedding (Task 2.1).
    """
    cuisines_str = ", ".join(row.get("cuisines", []))
    highlights_str = ", ".join(row.get("highlights", []))
    reviews_preview = str(row.get("reviews_summary") or "Known for quality food and customer service.")[:200]
    
    return (
        f"{row.get('name')} is a {cuisines_str} dining place located in {row.get('location')}, {row.get('city')}. "
        f"Budget tier: {row.get('budget_tier')} (average cost for two: ₹{row.get('average_cost_for_two')}). "
        f"Rating: {row.get('aggregate_rating')} stars with {row.get('votes')} reviews. "
        f"Popular features: {highlights_str}. "
        f"Atmosphere & highlights: {reviews_preview}"
    )


def sanitize_row(raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Sanitize and validate an individual dataset row."""
    name = str(raw.get("name", "")).strip()
    if not name or name.lower() in ("nan", "none"):
        return None

    location = str(raw.get("location") or raw.get("address") or "Bangalore").strip()
    address = str(raw.get("address") or location).strip()
    city = infer_city(location, address)

    rating, is_rated = parse_rating(raw.get("rate"))
    cost = parse_cost(raw.get("approx_cost(for two people)"))
    budget_tier = assign_budget_tier(cost)
    cuisines_list, primary_cuisine = parse_cuisines(raw.get("cuisines"))
    highlights_list = synthesize_highlights(
        raw.get("rest_type"),
        raw.get("dish_liked"),
        cuisines_list,
    )

    # Votes integer parsing
    try:
        votes = int(re.sub(r"[^\d]", "", str(raw.get("votes", "0"))))
    except (ValueError, TypeError):
        votes = 0

    # Online order and table booking boolean conversions
    online_order_raw = str(raw.get("online_order", "")).strip().lower()
    has_online_delivery = online_order_raw in ("yes", "true", "1")

    book_table_raw = str(raw.get("book_table", "")).strip().lower()
    has_table_booking = book_table_raw in ("yes", "true", "1")

    reviews_summary = str(raw.get("reviews_list") or raw.get("reviews_summary") or "").strip()
    if reviews_summary.lower() in ("nan", "none", "[]"):
        reviews_summary = ""

    cleaned_dict = {
        "name": name,
        "address": address,
        "location": location,
        "city": city,
        "cuisines": cuisines_list,
        "primary_cuisine": primary_cuisine,
        "average_cost_for_two": cost,
        "budget_tier": budget_tier,
        "aggregate_rating": rating,
        "is_rated": is_rated,
        "votes": votes,
        "has_online_delivery": has_online_delivery,
        "has_table_booking": has_table_booking,
        "highlights": highlights_list,
        "reviews_summary": reviews_summary,
    }

    # Generate synthetic text profile for ChromaDB embeddings
    cleaned_dict["synthetic_profile"] = generate_restaurant_profile(cleaned_dict)
    return cleaned_dict


def fetch_raw_records() -> List[Dict[str, Any]]:
    """
    Acquire raw dataset records from:
    1. Local cached CSV at settings.RAW_DATA_PATH
    2. Hugging Face datasets library (datasets.load_dataset)
    3. Direct CSV download from Hugging Face Hub URL
    4. Built-in verified offline seed dataset (DATA-01)
    """
    raw_csv_path = Path(settings.RAW_DATA_PATH)

    # 1. Check local cache first
    if raw_csv_path.exists() and raw_csv_path.stat().st_size > 0:
        logger.info(f"Loading cached dataset from {raw_csv_path}")
        try:
            if HAS_PANDAS:
                df = pd.read_csv(raw_csv_path)
                return df.to_dict(orient="records")
            else:
                import csv
                with open(raw_csv_path, mode="r", encoding="utf-8", errors="ignore") as f:
                    reader = csv.DictReader(f)
                    return list(reader)
        except Exception as e:
            logger.warning(f"Failed to read local cache: {e}. Trying Hugging Face Hub...")

    # 2. Attempt Hugging Face datasets library load (Task 1.4)
    try:
        from datasets import load_dataset
        logger.info(f"Downloading dataset '{settings.HF_DATASET_NAME}' from Hugging Face Hub...")
        hf_ds = load_dataset(settings.HF_DATASET_NAME, split="train")
        records = [dict(row) for row in hf_ds]
        
        # Cache locally
        raw_csv_path.parent.mkdir(parents=True, exist_ok=True)
        if HAS_PANDAS:
            pd.DataFrame(records).to_csv(raw_csv_path, index=False)
        logger.info(f"Successfully cached dataset ({len(records)} rows) to {raw_csv_path}")
        return records
    except Exception as e:
        logger.warning(f"Hugging Face datasets download failed or library not available: {e}.")

    # 3. Fallback: Direct CSV download from Hugging Face Hub (Task 1.4)
    direct_csv_url = f"https://huggingface.co/datasets/{settings.HF_DATASET_NAME}/resolve/main/zomato.csv"
    logger.info(f"Attempting fallback direct CSV download from {direct_csv_url}...")
    try:
        raw_csv_path.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(
            direct_csv_url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AntigravityIngest/1.0"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            # Download up to 20MB for fast local index or full stream
            chunk_size = 64 * 1024
            max_bytes = 20 * 1024 * 1024
            downloaded = 0
            with open(raw_csv_path, "wb") as out_f:
                while True:
                    chunk = resp.read(chunk_size)
                    if not chunk:
                        break
                    out_f.write(chunk)
                    downloaded += len(chunk)
                    if downloaded >= max_bytes:
                        break
        logger.info(f"Successfully downloaded direct CSV ({downloaded / (1024*1024):.1f} MB) to {raw_csv_path}")
        if HAS_PANDAS:
            df = pd.read_csv(raw_csv_path, on_bad_lines="skip")
            return df.to_dict(orient="records")
        else:
            import csv
            with open(raw_csv_path, mode="r", encoding="utf-8", errors="ignore") as f:
                reader = csv.DictReader(f)
                return list(reader)
    except Exception as e:
        logger.warning(f"Direct CSV download failed or offline ({e}).")

    # 4. Final offline fallback: Verified built-in seed dataset
    logger.info("Using built-in verified offline seed dataset.")
    raw_csv_path.parent.mkdir(parents=True, exist_ok=True)
    if HAS_PANDAS:
        pd.DataFrame(OFFLINE_SEED_DATA).to_csv(raw_csv_path, index=False)
    return OFFLINE_SEED_DATA


def run_ingestion_sqlite3(sanitized_records: List[Dict[str, Any]], db_path: Path) -> int:
    """
    Fallback SQLite ingestion using standard library sqlite3.
    Ensures zero-dependency operation while matching the exact SQLAlchemy schema and WAL pragmas.
    """
    import sqlite3
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("PRAGMA synchronous=NORMAL;")
    cursor.execute("PRAGMA busy_timeout=5000;")

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

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_restaurants_name ON restaurants(name);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_restaurants_location ON restaurants(location);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_restaurants_city ON restaurants(city);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_restaurants_budget_tier ON restaurants(budget_tier);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_restaurants_aggregate_rating ON restaurants(aggregate_rating);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_location_budget ON restaurants(location, budget_tier);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_city_budget ON restaurants(city, budget_tier);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_budget_rating ON restaurants(budget_tier, aggregate_rating);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cost_rating ON restaurants(average_cost_for_two, aggregate_rating);")

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

    for r in sanitized_records:
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
                1 if r["is_rated"] else 0,
                r["votes"],
                1 if r["has_online_delivery"] else 0,
                1 if r["has_table_booking"] else 0,
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
    return count


def run_ingestion(max_rows: Optional[int] = None) -> int:
    """
    Execute full ingestion: Fetch -> Sanitize -> Deduplicate -> Commit to SQLite.
    Returns total number of inserted records.
    """
    settings.ensure_directories()
    raw_records = fetch_raw_records()
    logger.info(f"Total raw records loaded: {len(raw_records)}")

    if max_rows and len(raw_records) > max_rows:
        raw_records = raw_records[:max_rows]
        logger.info(f"Subsampled to {max_rows} rows for processing.")

    # Deduplication map: key = (lower(name), lower(location), lower(address)) (DATA-07)
    dedup_map: Dict[Tuple[str, str, str], Dict[str, Any]] = {}

    for row_dict in raw_records:
        sanitized = sanitize_row(row_dict)
        if not sanitized:
            continue

        dedup_key = (
            sanitized["name"].lower().strip(),
            sanitized["location"].lower().strip(),
            sanitized["address"].lower().strip(),
        )

        # Retain record with higher vote count if duplicate exists
        if dedup_key in dedup_map:
            if sanitized["votes"] > dedup_map[dedup_key]["votes"]:
                dedup_map[dedup_key] = sanitized
        else:
            dedup_map[dedup_key] = sanitized

    sanitized_records = list(dedup_map.values())
    logger.info(f"Sanitized and deduplicated unique records: {len(sanitized_records)}")

    db_path = Path(settings.SQLITE_DB_PATH) if hasattr(settings, "SQLITE_DB_PATH") else PROJECT_ROOT / "data" / "processed" / "restaurants.db"

    # Use SQLAlchemy if available
    if HAS_SQLALCHEMY:
        try:
            init_db()
            session = SessionLocal()
            try:
                existing_count = session.query(Restaurant).count()
                if existing_count >= 10 and os.environ.get("FORCE_RESEED") != "1":
                    logger.info(f"Database already populated ({existing_count} restaurants present). Skipping re-seed.")
                    return existing_count

                session.query(Restaurant).delete()
                session.commit()

                batch_size = 500
                for i in range(0, len(sanitized_records), batch_size):
                    batch = sanitized_records[i : i + batch_size]
                    db_objects = [
                        Restaurant(
                            name=r["name"],
                            address=r["address"],
                            location=r["location"],
                            city=r["city"],
                            cuisines=json.dumps(r["cuisines"]),
                            primary_cuisine=r["primary_cuisine"],
                            average_cost_for_two=r["average_cost_for_two"],
                            budget_tier=r["budget_tier"],
                            aggregate_rating=r["aggregate_rating"],
                            is_rated=r["is_rated"],
                            votes=r["votes"],
                            has_online_delivery=r["has_online_delivery"],
                            has_table_booking=r["has_table_booking"],
                            highlights=json.dumps(r["highlights"]),
                            reviews_summary=r["reviews_summary"],
                            synthetic_profile=r["synthetic_profile"],
                        )
                        for r in batch
                    ]
                    session.bulk_save_objects(db_objects)
                    session.commit()
                    logger.info(f"Committed batch {i + len(batch)}/{len(sanitized_records)}")

                total_in_db = session.query(Restaurant).count()
                logger.info(f"SQLAlchemy ingestion complete. Total rows in SQLite DB: {total_in_db}")
                return total_in_db
            except Exception as e:
                session.rollback()
                logger.warning(f"SQLAlchemy bulk insert error ({e}). Falling back to sqlite3 standard driver...")
            finally:
                session.close()
        except Exception as e:
            logger.warning(f"SQLAlchemy initialization failed ({e}). Falling back to standard sqlite3...")

    # Fallback to direct sqlite3 driver
    total_in_db = run_ingestion_sqlite3(sanitized_records, db_path)
    logger.info(f"Direct SQLite3 ingestion complete. Total verified rows in DB: {total_in_db}")
    return total_in_db


if __name__ == "__main__":
    count = run_ingestion()
    print(f"Successfully populated restaurants.db with {count} restaurants.")
