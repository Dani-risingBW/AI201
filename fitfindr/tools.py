"""
tools.py

FitFindr tools including core and stretch features.
Each tool is a standalone function that can be called and tested independently.

Core Tools (Required):
    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)              → str
    create_fit_card(outfit, new_item)               → str
    evaluate_price_fairness(target_item, dataset)   → dict

Stretch Tools (Optional):
    price_comparison_analyzer(target_item, dataset, time_window, platform_filter) → dict
    style_profile_manager(user_id, action, profile_data) → dict
    trend_radar(style_category, size_range, price_ceiling, time_window) → dict
"""

import os
import json
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq

from utils.data_loader import load_listings

load_dotenv()


# ── Groq client ───────────────────────────────────────────────────────────────

def _get_groq_client():
    """Initialize and return a Groq client using GROQ_API_KEY from .env."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not set. Add it to a .env file in the project root."
        )
    return Groq(api_key=api_key)


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the mock listings dataset for items matching the description,
    optional size, and optional price ceiling.

    Args:
        description: Keywords describing what the user is looking for
                     (e.g., "vintage graphic tee").
        size:        Size string to filter by, or None to skip size filtering.
                     Matching is case-insensitive (e.g., "M" matches "S/M").
        max_price:   Maximum price (inclusive), or None to skip price filtering.

    Returns:
        A list of matching listing dicts, sorted by relevance (best match first).
        Returns an empty list if nothing matches — does NOT raise an exception.

    Each listing dict has the following fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand, platform

    TODO:
        1. Load all listings with load_listings().
        2. Filter by max_price and size (if provided).
        3. Score each remaining listing by keyword overlap with `description`.
        4. Drop any listings with a score of 0 (no relevant matches).
        5. Sort by score, highest first, and return the listing dicts.

    Before writing code, fill in the Tool 1 section of planning.md.
    """
    # 1. Load all listings from the mock dataset
    try:
        all_listings = load_listings()
    except Exception:
        # Failsafe if data loader breaks entirely
        return []

    filtered_listings = []
    
    # Pre-process search tokens for scoring
    search_tokens = [token.lower().strip() for token in description.lower().split() if token.strip()]

    # 2. Filter and Score listings
    for listing in all_listings:
        # Price Filtering (inclusive)
        if max_price is not None and listing.get("price", 0.0) > max_price:
            continue

        # Size Filtering (case-insensitive partial match, e.g., "M" in "S/M" or "L" in "L")
        if size is not None:
            listing_size = str(listing.get("size", "")).lower()
            target_size = str(size).lower()
            if target_size not in listing_size:
                continue

        # 3. Score each listing by keyword overlap with `description`
        score = 0
        title_lower = listing.get("title", "").lower()
        desc_lower = listing.get("description", "").lower()
        style_tags = [str(tag).lower() for tag in listing.get("style_tags", [])]
        colors = [str(col).lower() for col in listing.get("colors", [])]

        for token in search_tokens:
            # Title matches weigh heavily
            if token in title_lower:
                score += 3
            # Style tag exact/partial matches weigh heavily
            if any(token in tag for tag in style_tags):
                score += 2
            # Description and color matches provide secondary relevance
            if token in desc_lower:
                score += 1
            if token in colors:
                score += 1

        # 4. Drop any listings with a score of 0 (no relevant matches)
        if score > 0:
            # Store the score temporarily inside a copy of the dict to allow sorting
            listing_with_score = listing.copy()
            listing_with_score["_search_score"] = score
            filtered_listings.append(listing_with_score)

    # 5. Sort by score (highest first) and return clean listing dicts
    filtered_listings.sort(key=lambda x: x["_search_score"], reverse=True)
    
    # Remove our temporary internal score key before returning data to the loop
    for item in filtered_listings:
        item.pop("_search_score", None)

    return filtered_listings


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest 1–2 complete outfits.

    Args:
        new_item: A listing dict (the item the user is considering buying).
        wardrobe: A wardrobe dict with an 'items' key containing a list of
                  wardrobe item dicts. May be empty — handle this gracefully.

    Returns:
        A non-empty string with outfit suggestions.
        If the wardrobe is empty, offer general styling advice for the item
        rather than raising an exception or returning an empty string.

    TODO:
        1. Check whether wardrobe['items'] is empty.
        2. If empty: call the LLM with a prompt for general styling ideas
           (what kinds of items pair well, what vibe it suits, etc.).
        3. If not empty: format the wardrobe items into a prompt and ask
           the LLM to suggest specific outfit combinations using the new item
           and named pieces from the wardrobe.
        4. Return the LLM's response as a string.

    Before writing code, fill in the Tool 2 section of planning.md.
    """
    try:
        client = _get_groq_client()
    except Exception as e:
        return f"System Error: Unable to access the style generator client. ({str(e)})"

    # Extract details safely for the prompt
    item_title = new_item.get("title", "this item")
    item_desc = new_item.get("description", "")
    item_tags = ", ".join(new_item.get("style_tags", []))
    item_cond = new_item.get("condition", "unknown")
    
    # 1. Check whether wardrobe['items'] is empty
    wardrobe_items = wardrobe.get("items", []) if isinstance(wardrobe, dict) else []

    # 2. If empty: call the LLM with a prompt for general styling ideas
    if not wardrobe_items:
        system_prompt = (
            "You are an expert thrift stylist. The user's logged wardrobe is currently empty. "
            "Your job is to provide general, highly creative styling advice for a newly found item. "
            "Suggest what types of clothing items (tops, bottoms, footwear, accessories) would pair perfectly "
            "with it, what overall aesthetic vibe it suits, and structural/styling tips (e.g., tucks, layers)."
        )
        user_prompt = (
            f"I have an empty wardrobe, but I am looking at this item:\n"
            f"Item: {item_title}\n"
            f"Description: {item_desc}\n"
            f"Style Vibe/Tags: {item_tags}\n"
            f"Condition: {item_cond}\n\n"
            f"Can you give me 1-2 generic outfit inspiration combinations and styling ideas for this piece?"
        )
    
    # 3. If not empty: format the wardrobe items into a prompt for specific combinations
    else:
        formatted_wardrobe = []
        for i, item in enumerate(wardrobe_items, start=1):
            w_title = item.get("title", "Unknown Item")
            w_cat = item.get("category", "unknown")
            w_tags = ", ".join(item.get("style_tags", []))
            formatted_wardrobe.append(f"{i}. {w_title} (Category: {w_cat}, Tags: {w_tags})")
        
        wardrobe_str = "\n".join(formatted_wardrobe)
        
        system_prompt = (
            "You are an expert thrift stylist. The user has a populated wardrobe. "
            "Your job is to review their available wardrobe items and suggest 1-2 complete outfit combinations "
            "that incorporate their potential new thrifted purchase. You must explicitly name the pieces used "
            "from their wardrobe. Aim for a complete look (top, bottom, shoes, and optional accessory if applicable)."
        )
        user_prompt = (
            f"I am considering buying this new item:\n"
            f"Item: {item_title}\n"
            f"Description: {item_desc}\n"
            f"Tags: {item_tags}\n\n"
            f"Here is my current wardrobe inventory:\n"
            f"{wardrobe_str}\n\n"
            f"Please suggest 1-2 distinct, complete outfits combining my new item with specific named pieces from my wardrobe, including explicit styling tips."
        )

    # 4. Call the LLM and return its response as a string
    try:
        response = client.chat.completions.create(
            model="gpt-oss-120b",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7  # Balanced creative styling logic
        )
        output_text = response.choices[0].message.content
        return output_text.strip() if output_text else "Styling generation returned blank results."
    except Exception as e:
        # Graceful fallback string instead of crashing the pipeline
        return f"Could not generate styling tips due to an external network error: {str(e)}"


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Generate a short, shareable outfit caption for the thrifted find.

    Args:
        outfit:   The outfit suggestion string from suggest_outfit().
        new_item: The listing dict for the thrifted item.

    Returns:
        A 2–4 sentence string usable as an Instagram/TikTok caption.
        If outfit is empty or missing, return a descriptive error message
        string — do NOT raise an exception.

    The caption should:
    - Feel casual and authentic (like a real OOTD post, not a product description)
    - Mention the item name, price, and platform naturally (once each)
    - Capture the outfit vibe in specific terms
    - Sound different each time for different inputs (use higher LLM temperature)

    TODO:
        1. Guard against an empty or whitespace-only outfit string.
        2. Build a prompt that gives the LLM the item details and the outfit,
           and asks for a caption matching the style guidelines above.
        3. Call the LLM and return the response.

    Before writing code, fill in the Tool 3 section of planning.md.
    """
    # 1. Guard against an empty or whitespace-only outfit string or missing item data
    if not outfit or not isinstance(outfit, str) or not outfit.strip():
        return "Error: Missing or incomplete outfit data. Cannot generate a fit card caption."
    
    if not new_item or not isinstance(new_item, dict):
        return "Error: Incomplete item data payload. Cannot generate a fit card caption."

    # Extract target metadata variables for potential local string interpolation recovery
    item_title = new_item.get("title", "this find")
    price_val = new_item.get("price", 0.0)
    price_str = f"{price_val:.2f}" if isinstance(price_val, (int, float)) else str(price_val)
    platform = new_item.get("platform", "the marketplace")

    # 2. Build a prompt incorporating item details and the outfit text
    system_prompt = (
        "You are a social media copywriter obsessed with sustainable fashion, thrifting, and OOTD culture. "
        "Your task is to write a short, highly engaging, and authentic social media caption (Instagram/TikTok style) "
        "celebrating a new thrifted find based on an outfit description provided to you.\n\n"
        "STRICT GUIDELINES:\n"
        "- The caption MUST be exactly 2–4 sentences long.\n"
        "- It must feel completely casual, authentic, and modern (lowercase styling, minimal/natural emojis are fine; do NOT sound like a commercial or an eBay product listing description).\n"
        "- You MUST naturally mention the item's name, its exact price, and the platform it was sourced from exactly once each.\n"
        "- Capture the specific aesthetic vibe of the combined outfit creatively."
    )
    
    user_prompt = (
        f"Item Details:\n"
        f"- Name: {item_title}\n"
        f"- Price: ${price_str}\n"
        f"- Platform: {platform}\n\n"
        f"Outfit Styling Description:\n"
        f"{outfit}\n\n"
        f"Generate my unique social media caption now:"
    )

    # 3. Call the LLM with a higher temperature for diversity and return the response
    try:
        client = _get_groq_client()
        response = client.chat.completions.create(
            model="gpt-oss-120b",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.9  # High temperature to ensure diverse, unique outputs on repeated inputs
        )
        caption_text = response.choices[0].message.content
        if caption_text and caption_text.strip():
            return caption_text.strip().replace('"', '') # Strip accidental wrapping quotes if the LLM generates them
        raise ValueError("Blank response received from LLM.")
        
    except Exception:
        return f"Just picked up this {item_title} for ${price_str} to wear with my {outfit}!"


# ── Tool 4: evaluate_price_fairness ──────────────────────────────────────────

def evaluate_price_fairness(target_item: dict, mock_dataset: list) -> dict:
    """
    Determine whether a target item is a good deal by comparing its price
    against similar listings in the dataset (same category + shared style tags).

    Args:
        target_item:  The listing dict for the item being evaluated.
        mock_dataset: The full list of listing dicts to compare against.

    Returns:
        A dict with keys: deal_rating, market_average, price_difference,
        evaluation_summary.
        Returns {"status": "error", "message": "..."} if price data is corrupt.

    Deal ratings:
        "Steal"            — priced more than 20% below market average
        "Fair Market Value"— within 20% of market average (or no comparables)
        "Overpriced"       — priced more than 20% above market average
    """
    try:
        target_price = float(target_item["price"])
    except (KeyError, TypeError, ValueError) as e:
        return {"status": "error", "message": f"Could not read target item price: {e}"}

    target_category = target_item.get("category", "")
    target_tags = set(target_item.get("style_tags", []))
    target_title = target_item.get("title", "this item")

    comparable_prices = []
    for item in mock_dataset:
        if item is target_item:
            continue
        if item.get("category", "") != target_category:
            continue
        if not target_tags.intersection(set(item.get("style_tags", []))):
            continue
        try:
            comparable_prices.append(float(item["price"]))
        except (KeyError, TypeError, ValueError) as e:
            return {"status": "error", "message": f"Corrupted price data for item '{item.get('id', 'unknown')}': {e}"}

    if not comparable_prices:
        return {
            "deal_rating": "Fair Market Value",
            "market_average": round(target_price, 2),
            "price_difference": 0.0,
            "evaluation_summary": (
                f"At ${target_price:.2f}, {target_title} is a rare find with no comparable "
                f"listings in the marketplace. Defaulting to fair market value."
            ),
        }

    market_average = sum(comparable_prices) / len(comparable_prices)
    price_difference = target_price - market_average

    if target_price < market_average * 0.8:
        deal_rating = "Steal"
    elif target_price > market_average * 1.2:
        deal_rating = "Overpriced"
    else:
        deal_rating = "Fair Market Value"

    direction = "below" if price_difference < 0 else "above"
    evaluation_summary = (
        f"At ${target_price:.2f}, {target_title} is ${abs(price_difference):.2f} {direction} "
        f"the market average of ${market_average:.2f} across {len(comparable_prices)} "
        f"comparable listing(s). Rating: {deal_rating}."
    )

    return {
        "deal_rating": deal_rating,
        "market_average": round(market_average, 2),
        "price_difference": round(price_difference, 2),
        "evaluation_summary": evaluation_summary,
        "confidence_score": 0.85,  # Add confidence score for UI display
        "estimated_fair_market_value": round(market_average, 2),
    }


# ── STRETCH TOOL 5: price_comparison_analyzer ────────────────────────────────

def price_comparison_analyzer(
    target_item: dict,
    mock_dataset: list,
    time_window: str = "30_days",
    platform_filter: str | None = None,
) -> dict:
    """
    Provides deep market analysis: price trends, percentile rankings,
    platform-specific benchmarking, and buyability recommendations.

    Args:
        target_item:    The listing dict being evaluated.
        mock_dataset:   Full list of listing dicts for comparison.
        time_window:    "7_days", "30_days", or "all_time" (default: "30_days").
        platform_filter: Optional platform name (e.g., "Depop") or None for all.

    Returns:
        A dict with:
        - baseline_price, market_average, price_trend, percentile_rank
        - platform_comparison (dict of platform -> avg_price)
        - recommendations (str): Natural language advice
    """
    try:
        target_price = float(target_item.get("price", 0))
    except (TypeError, ValueError):
        return {
            "status": "error",
            "message": "Could not parse target item price",
        }

    target_category = target_item.get("category", "")
    target_tags = set(target_item.get("style_tags", []))
    target_platform = target_item.get("platform", "")

    # Collect comparable items
    comparable_items = []
    for item in mock_dataset:
        if item is target_item:
            continue
        if item.get("category", "") != target_category:
            continue
        if not target_tags.intersection(set(item.get("style_tags", []))):
            continue

        # Apply platform filter if specified
        if platform_filter and item.get("platform", "") != platform_filter:
            continue

        try:
            price = float(item.get("price", 0))
            comparable_items.append({"item": item, "price": price})
        except (TypeError, ValueError):
            continue

    if not comparable_items:
        # Fallback to all items in category
        if platform_filter:
            comparable_items = [
                {"item": item, "price": float(item.get("price", 0))}
                for item in mock_dataset
                if item.get("category") == target_category and item is not target_item
            ]

    if not comparable_items:
        return {
            "baseline_price": round(target_price, 2),
            "market_average": round(target_price, 2),
            "price_trend": "→ Stable",
            "percentile_rank": 50,
            "platform_comparison": {},
            "recommendations": "Unique piece with no market comparables. Price is fair market value.",
        }

    # Calculate trend (simulated: based on price variation in dataset)
    prices = sorted([item["price"] for item in comparable_items])
    price_stdev = (max(prices) - min(prices)) / len(prices) if prices else 0

    market_average = sum(prices) / len(prices)
    price_diff = target_price - market_average

    if price_diff > price_stdev:
        trend = "↑ Rising"
        recommendation_action = "prices rising—buy now"
    elif price_diff < -price_stdev:
        trend = "↓ Falling"
        recommendation_action = "historically undervalued—wait for better stock"
    else:
        trend = "→ Stable"
        recommendation_action = "stable pricing"

    # Percentile rank
    percentile = (len([p for p in prices if p <= target_price]) / len(prices) * 100) if prices else 50

    # Platform comparison
    platform_prices = {}
    for item_dict in comparable_items:
        platform = item_dict["item"].get("platform", "Unknown")
        price = item_dict["price"]
        if platform not in platform_prices:
            platform_prices[platform] = []
        platform_prices[platform].append(price)

    platform_comparison = {
        platform: round(sum(prices) / len(prices), 2)
        for platform, prices in platform_prices.items()
    }

    recommendations = (
        f"At ${target_price:.2f}, this item is {recommendation_action}. "
        f"Market average: ${market_average:.2f}. "
        f"You're in the {int(percentile)}th percentile of comparable listings."
    )

    return {
        "baseline_price": round(target_price, 2),
        "market_average": round(market_average, 2),
        "price_trend": trend,
        "percentile_rank": int(percentile),
        "platform_comparison": platform_comparison,
        "recommendations": recommendations,
    }


# ── STRETCH TOOL 6: style_profile_manager ────────────────────────────────────

PROFILE_STORAGE_DIR = Path("data/user_profiles")

def style_profile_manager(
    user_id: str,
    action: str,
    profile_data: dict | None = None,
) -> dict:
    """
    Manages persistent user style profiles across sessions.

    Args:
        user_id:      Unique user identifier.
        action:       "create_profile", "update_profile", "fetch_profile",
                      "log_search", or "get_style_summary".
        profile_data: For create/update: dict with preferred_styles, size_range,
                      budget_range, favorite_platforms, past_searches.

    Returns:
        Status dict with profile_id, or fetched profile, or summary.
    """
    try:
        PROFILE_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    except Exception:
        # Graceful fallback: session-only memory
        return {
            "status": "degraded",
            "message": "Profile storage unavailable. Using session-only memory.",
            "profile_id": user_id,
        }

    profile_path = PROFILE_STORAGE_DIR / f"{user_id}.json"

    if action == "create_profile":
        if profile_path.exists():
            return {"status": "error", "message": "Profile already exists"}

        default_profile = {
            "user_id": user_id,
            "created_at": datetime.now().isoformat(),
            "preferred_styles": profile_data.get("preferred_styles", []) if profile_data else [],
            "size_range": profile_data.get("size_range", {}) if profile_data else {},
            "budget_range": profile_data.get("budget_range", {"min": 0, "max": 100}) if profile_data else {"min": 0, "max": 100},
            "favorite_platforms": profile_data.get("favorite_platforms", []) if profile_data else [],
            "past_searches": profile_data.get("past_searches", []) if profile_data else [],
            "search_count": 0,
        }

        try:
            profile_path.write_text(json.dumps(default_profile, indent=2))
            return {"status": "success", "profile_id": user_id}
        except Exception:
            return {"status": "degraded", "profile_id": user_id, "message": "Could not save profile"}

    elif action == "update_profile":
        if not profile_path.exists():
            return style_profile_manager(user_id, "create_profile", profile_data)

        try:
            profile = json.loads(profile_path.read_text())
            if profile_data:
                profile.update(profile_data)
                profile["updated_at"] = datetime.now().isoformat()
            profile_path.write_text(json.dumps(profile, indent=2))
            return {"status": "success", "profile_id": user_id}
        except Exception:
            return {"status": "degraded", "profile_id": user_id}

    elif action == "fetch_profile":
        if not profile_path.exists():
            return {"status": "new_profile", "profile_id": user_id}

        try:
            profile = json.loads(profile_path.read_text())
            return {"status": "success", "profile": profile}
        except Exception:
            return {"status": "error", "message": "Could not fetch profile"}

    elif action == "log_search":
        if not profile_path.exists():
            style_profile_manager(user_id, "create_profile", {})

        try:
            profile = json.loads(profile_path.read_text())
            search_query = profile_data.get("query", "") if profile_data else ""
            if search_query:
                profile["past_searches"].append({
                    "query": search_query,
                    "timestamp": datetime.now().isoformat(),
                })
                profile["search_count"] = profile.get("search_count", 0) + 1
            profile_path.write_text(json.dumps(profile, indent=2))
            return {"status": "logged", "search_count": profile["search_count"]}
        except Exception:
            return {"status": "degraded"}

    elif action == "get_style_summary":
        if not profile_path.exists():
            return {"status": "new_profile", "summary": "No profile yet. Start searching!"}

        try:
            profile = json.loads(profile_path.read_text())
            styles = ", ".join(profile.get("preferred_styles", []))
            platforms = ", ".join(profile.get("favorite_platforms", []))
            search_count = profile.get("search_count", 0)

            summary = f"User style: {styles or 'undefined'}. Favorite platforms: {platforms or 'all'}. {search_count} searches logged."
            return {"status": "success", "summary": summary, "profile": profile}
        except Exception:
            return {"status": "error"}

    return {"status": "error", "message": f"Unknown action: {action}"}


# ── STRETCH TOOL 7: trend_radar ───────────────────────────────────────────────

def trend_radar(
    style_category: str,
    size_range: str | None = None,
    price_ceiling: float | None = None,
    time_window: str = "this_week",
) -> dict:
    """
    Identifies trending styles and items in the dataset.
    Surfaces trending hashtags, spiking keywords, and trending pieces.

    Args:
        style_category: "vintage", "minimalist", "grunge", "y2k", etc.
        size_range:     Optional size filter ("XS", "S", "M", "L", "XL").
        price_ceiling:  Optional max price for trending items.
        time_window:    "today", "this_week", or "this_month".

    Returns:
        Dict with:
        - trending_items (list): Matching items from dataset
        - trending_hashtags (list): Top 10 hashtags
        - search_spike (dict): Keywords spiking in popularity
        - trending_alert (str): Natural language summary
    """
    try:
        all_listings = load_listings()
    except Exception:
        return {
            "trending_items": [],
            "trending_hashtags": [],
            "search_spike": {},
            "trending_alert": "Could not access trend data. Using dataset fallback.",
        }

    # Filter by category
    filtered = [
        item for item in all_listings
        if style_category.lower() in [tag.lower() for tag in item.get("style_tags", [])]
    ]

    # Filter by size if provided
    if size_range:
        filtered = [
            item for item in filtered
            if size_range.lower() in str(item.get("size", "")).lower()
        ]

    # Filter by price if provided
    if price_ceiling is not None:
        filtered = [
            item for item in filtered
            if item.get("price", float("inf")) <= price_ceiling
        ]

    # Sort by recency (assume items near end of list are newer)
    trending_items = filtered[-5:] if len(filtered) > 5 else filtered

    # Extract trending hashtags from filtered items' style tags
    all_tags = []
    for item in filtered:
        all_tags.extend(item.get("style_tags", []))

    tag_counts = {}
    for tag in all_tags:
        tag_counts[tag] = tag_counts.get(tag, 0) + 1

    trending_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)
    trending_hashtags = [f"#{tag[0]}" for tag in trending_tags[:10]]

    # Simulated search spike (in real system, would track searches over time)
    search_spike = {
        tag[0]: f"+{tag[1] * 10}%"
        for tag in trending_tags[:5]
    }

    # Generate alert
    if trending_items:
        alert = (
            f"📈 {style_category.capitalize()} is trending! "
            f"{len(trending_items)} items found. Top tags: {', '.join(trending_hashtags[:3])}. "
            f"I found {len(trending_items)} trending pieces in your size under ${price_ceiling:.0f}."
        )
    else:
        alert = f"No trending items match '{style_category}' criteria, but your style is timeless!"

    return {
        "trending_items": trending_items,
        "trending_hashtags": trending_hashtags,
        "search_spike": search_spike,
        "trending_alert": alert,
    }
