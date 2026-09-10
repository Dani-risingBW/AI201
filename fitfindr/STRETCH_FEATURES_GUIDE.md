# ThreadScout AI — Stretch Features Implementation Guide

## Overview

This document describes the three stretch features added to ThreadScout AI beyond the core MVP. All stretch features are **non-blocking**, meaning they enhance the user experience but never interrupt the main workflow if they fail.

---

## 🎯 Architecture

### Feature Integration

```
run_agent(query, wardrobe)
    ├─ Core Tools (Required)
    │  ├─ Step 2: Parse query
    │  ├─ Step 3: Search listings (+ 2x retry fallback)
    │  ├─ Step 5: evaluate_price_fairness
    │  ├─ Step 7: suggest_outfit
    │  └─ Step 8: create_fit_card
    │
    └─ Stretch Tools (Non-blocking)
       ├─ Step 9:  price_comparison_analyzer ✦ TOOL 5
       ├─ Step 10: style_profile_manager ✦ TOOL 6
       └─ Step 11: trend_radar ✦ TOOL 7
```

All stretch features wrap in `try/except` blocks. Failures are silent and don't propagate.

---

## 🛠️ Tool 5: price_comparison_analyzer (Stretch)

**Location:** `tools.py:402–520`

### Purpose
Provides **deep market analysis** beyond basic fairness evaluation. Tracks price trends, calculates percentile rankings, performs platform-specific benchmarking, and delivers buyability recommendations.

### Function Signature
```python
def price_comparison_analyzer(
    target_item: dict,
    mock_dataset: list,
    time_window: str = "30_days",  # "7_days", "30_days", or "all_time"
    platform_filter: str | None = None,  # e.g., "Depop", "Grailed"
) -> dict:
```

### Returns
```python
{
    "baseline_price": 48.00,        # Item's actual price
    "market_average": 62.50,        # Average comparable
    "price_trend": "↓ Falling",     # Price momentum
    "percentile_rank": 35,          # 0–100 rank vs comparables
    "platform_comparison": {        # Platform-specific averages
        "Depop": 55.00,
        "Grailed": 70.00,
    },
    "recommendations": "At $48.00, this item is historically undervalued—wait for better stock. Market average: $62.50. You're in the 35th percentile of comparable listings."
}
```

### Integration in UI

**Tab:** "💚 Valuation & Trends" (updated label)

**Display:**
```
📊 PRICE TRENDS (STRETCH)
Trend: ↓ Falling
Percentile: 35th
At $48.00, this item is historically undervalued...
```

### Failure Modes & Handling

| Mode | Behavior |
|------|----------|
| No comparable items | Falls back to all items in category, then returns baseline price |
| Platform filter empty | Expands to all platforms, notes in function |
| Price parsing error | Returns `{"status": "error", ...}`, silently ignored by agent |

---

## 👤 Tool 6: style_profile_manager (Stretch)

**Location:** `tools.py:523–670`

### Purpose
Enables **persistent user style profiles** across sessions. Remembers preferred styles, size ranges, budgets, favorite platforms, and search history. Eliminates need for users to re-describe preferences.

### Function Signature
```python
def style_profile_manager(
    user_id: str,
    action: str,  # "create_profile", "update_profile", "fetch_profile",
                  # "log_search", or "get_style_summary"
    profile_data: dict | None = None,
) -> dict:
```

### Actions

#### 1. `create_profile`
**Input:**
```python
profile_data = {
    "preferred_styles": ["vintage", "grunge", "minimalist"],
    "size_range": {"top": "M", "bottom": "32W", "shoes": "8"},
    "budget_range": {"min": 20, "max": 80},
    "favorite_platforms": ["Depop", "Grailed"],
}
```

**Returns:** `{"status": "success", "profile_id": "user_123"}`

#### 2. `fetch_profile`
**Returns:**
```python
{
    "status": "success",
    "profile": {
        "user_id": "user_123",
        "created_at": "2026-09-10T...",
        "preferred_styles": [...],
        "search_count": 5,
        "past_searches": [
            {"query": "vintage band tee", "timestamp": "..."},
            ...
        ],
        ...
    }
}
```

#### 3. `log_search`
Adds a query to the user's search history.

**Input:**
```python
profile_data = {"query": "vintage graphic tee under $30"}
```

**Returns:** `{"status": "logged", "search_count": 6}`

#### 4. `get_style_summary`
**Returns:**
```python
{
    "status": "success",
    "summary": "User style: vintage, grunge. Favorite platforms: Depop, Grailed. 5 searches logged."
}
```

### Storage

Profiles stored in: **`data/user_profiles/{user_id}.json`**

Example file structure:
```json
{
  "user_id": "user_123",
  "created_at": "2026-09-10T14:30:00",
  "preferred_styles": ["vintage", "grunge"],
  "size_range": {"top": "M", "bottom": "32W", "shoes": "8"},
  "budget_range": {"min": 20, "max": 80},
  "favorite_platforms": ["Depop", "Grailed"],
  "past_searches": [
    {"query": "vintage band tee under $30", "timestamp": "2026-09-10T14:35:00"}
  ],
  "search_count": 1,
  "updated_at": "2026-09-10T14:35:00"
}
```

### Integration in Agent

**In agent.py:**
```python
# Step 10 in run_agent()
if session.get("user_id"):
    style_profile_manager(user_id, "log_search", {"query": query})
    profile_result = style_profile_manager(user_id, "fetch_profile")
    session["user_profile"] = profile_result.get("profile")
```

**Pass `user_id` to run_agent():**
```python
session = run_agent(
    query="vintage graphic tee",
    wardrobe=wardrobe,
    user_id="nkiruka_ibe@howard.edu"
)
```

### Failure Modes & Handling

| Mode | Behavior |
|------|----------|
| Storage directory unavailable | Graceful degradation: returns `{"status": "degraded"}`, profile kept in session-only memory |
| User profile doesn't exist | Auto-creates new blank profile |
| Corrupted JSON file | Returns error, doesn't crash agent |
| File write fails | Non-blocking, session continues without saving |

---

## 📈 Tool 7: trend_radar (Stretch)

**Location:** `tools.py:673–760`

### Purpose
Detects **trending fashion styles** in real-time. Scans the dataset for popular items, surfacing trending hashtags, keyword spikes, and curated pieces. Alerts users to emerging trends matching their profile.

### Function Signature
```python
def trend_radar(
    style_category: str,      # "vintage", "minimalist", "grunge", "y2k", etc.
    size_range: str | None = None,     # "M", "L", etc.
    price_ceiling: float | None = None, # Max price for trending items
    time_window: str = "this_week",    # "today", "this_week", or "this_month"
) -> dict:
```

### Returns
```python
{
    "trending_items": [item1, item2, item3],  # Curated matching pieces
    "trending_hashtags": [
        "#VintageY2K",
        "#NinetiestDemin",
        "#ThriftedFinds",
        ...
    ],
    "search_spike": {
        "90s": "+45%",
        "cargo": "+32%",
        "mini-bag": "+28%",
    },
    "trending_alert": "📈 Y2K is exploding right now! 📈 Cargo pants and mini bags are spiking. I found 3 trending pieces in your size under $50."
}
```

### Integration in UI

**New Tab:** "📈 What's Trending"

**Component:** `build_trends_html()` in app.py (lines 159–206)

**Display:**
```
📈 Trending Now
Y2K is exploding right now! Cargo pants and mini bags are spiking. 
I found 3 trending pieces in your size under $50.

TOP HASHTAGS
#VintageY2K #NinetiestDenim #ThriftedFinds #VintageAesthetic #EcoChic

🔥 KEYWORD SPIKES
90s +45%, cargo +32%, mini-bag +28%
```

### Integration in Agent

**In agent.py (Step 11):**
```python
# Extract dominant style from selected item
style_tags = session["selected_item"].get("style_tags", [])
trending_category = style_tags[0] if style_tags else "vintage"

trend_result = trend_radar(
    style_category=trending_category,
    size_range=size,
    price_ceiling=item_price * 1.5,
    time_window="this_week"
)
session["trending_context"] = trend_result
```

### Failure Modes & Handling

| Mode | Behavior |
|------|----------|
| External trend API down | Falls back to analyzing mock dataset for recently added items |
| No items match criteria | Returns empty list with message: "No trending items match your criteria, but your style is timeless!" |
| Category not in dataset | Returns data for most similar category |
| Data loading fails | Returns empty trends, message informs user |

---

## 🧪 Testing

### Run All Stretch Tests
```bash
python test_stretch_features.py
```

**Output:**
```
🚀 ThreadScout AI — Stretch Feature Test Suite
Testing Tools 5, 6, 7 + Integration

================================================================================
TEST: price_comparison_analyzer (STRETCH TOOL 5)
================================================================================

📊 Analyzing: Faded Band Tee...
   Price: $22.00

✓ Result:
  - Trend: ↓ Falling
  - Market Average: $38.50
  - Percentile Rank: 28th
  - Recommendation: At $22.00, this item is historically undervalued...

[Tests continue for Tools 6 & 7...]

✅ Test suite complete!
```

### Test Individual Features

```python
# Test Tool 5
from tools import price_comparison_analyzer
from utils.data_loader import load_listings

dataset = load_listings()
result = price_comparison_analyzer(dataset[0], dataset)
print(result["price_trend"])

# Test Tool 6
from tools import style_profile_manager

style_profile_manager("user_123", "create_profile", {
    "preferred_styles": ["vintage"],
    "budget_range": {"min": 20, "max": 80}
})

# Test Tool 7
from tools import trend_radar

result = trend_radar("vintage", size_range="M", price_ceiling=50)
print(result["trending_alert"])
```

---

## 🎨 Frontend Integration

### Updated UI Components

**app.py Changes:**

1. **build_valuation_html()** (lines 51–120)
   - Now displays price trends, percentile rank, and recommendations
   - Section labeled "📊 PRICE TRENDS (STRETCH)"

2. **build_trends_html()** (lines 159–206) — NEW
   - Displays trending items, hashtags, keyword spikes
   - Called from handle_query()

3. **handle_query()** (lines 248–298)
   - Returns 6 outputs instead of 5
   - Added `trends_html` for new tab

4. **build_interface()** (lines 346–602)
   - New Tab 5: "📈 What's Trending"
   - Updated Tab 2: "💚 Valuation & Trends" (was "Valuation")
   - All 5 tabs wired to event handlers

### Tab Structure
```
Left Column: Chat          Right Column: Results
             ║             ┌────────────────────┐
             ║             │ Tabs (5):          │
             ║             │ 🛍️ Item Details  │
             ║             │ 💚 Valuation     │ + Price Trends (Tool 5)
             ║             │ 📱 Social        │
             ║             │ 👗 Outfit        │
             ║             │ 📈 Trending      │ ← Tool 7
             ║             └────────────────────┘
```

---

## 📊 Session State

### Extended `session` Dictionary

```python
session = {
    # Core
    "query": str,
    "parsed": dict,
    "search_results": list,
    "selected_item": dict,
    "wardrobe": dict,

    # Core Outputs
    "price_context": dict,
    "outfit_suggestion": str,
    "fit_card": str,

    # STRETCH OUTPUTS
    "price_comparison": dict,        # Tool 5
    "user_profile": dict,            # Tool 6
    "trending_context": dict,        # Tool 7

    # Error Handling
    "error": str | None,
    "retry_notes": str | None,
}
```

---

## 🔄 Data Flow Example

### Complete Interaction with Stretch Features

**User Query:** "vintage graphic tee under $30"

```
1. Parse query → {"description": "vintage graphic tee", "max_price": 30.0}

2. Search → [item1, item2, item3]
   (If empty, retry with loosened constraints)

3. evaluate_price_fairness(item1)
   → {"deal_rating": "Steal", "market_average": 52.00, ...}

4. [STRETCH] price_comparison_analyzer(item1)
   → {"price_trend": "↓ Falling", "percentile_rank": 28, ...}

5. suggest_outfit(item1, wardrobe) → "Pair with jeans and white sneakers..."

6. create_fit_card(...) → "just scored this faded band tee for $22..."

7. [STRETCH] style_profile_manager("user_123", "log_search", ...)
   → {"status": "logged", "search_count": 6}

8. [STRETCH] trend_radar("vintage", price_ceiling=45)
   → {"trending_items": [...], "trending_hashtags": [...], ...}

Final Session → app.py displays all 5 tabs with rich data
```

---

## 🚀 Running ThreadScout AI

### With Stretch Features
```bash
python app.py
```

Navigate to `http://localhost:7860`

- Chat with ThreadScout on the left
- View 5 tabs on the right with all outputs (core + stretch)
- Click "Hunt ✦" to run full agent with stretch enhancements

### CLI Testing
```bash
python agent.py  # Runs happy path + error cases

# Output shows session dict with price_comparison, user_profile, trending_context
```

---

## 📋 Checklist

- ✅ Tool 5: price_comparison_analyzer implemented
- ✅ Tool 6: style_profile_manager implemented
- ✅ Tool 7: trend_radar implemented
- ✅ All tools non-blocking with graceful degradation
- ✅ Integrated into agent.py planning loop
- ✅ UI updated with new tabs and data displays
- ✅ Comprehensive test suite created
- ✅ Full documentation provided

---

## 🎯 Next Steps

1. **Deploy:** Push to production with stretch features enabled by default
2. **Monitor:** Track feature usage via user_profile logs
3. **Iterate:** Collect user feedback on trending recommendations
4. **Scale:** Add external API integrations (Instagram, TikTok) for real-time trends
5. **Personalize:** Use style_profile data to auto-populate search suggestions

---

**ThreadScout AI is now fully operational with MVP + Stretch Features! 🚀✨**
