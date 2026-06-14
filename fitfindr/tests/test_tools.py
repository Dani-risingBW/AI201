import pytest
from unittest.mock import MagicMock, patch
from tools import search_listings, suggest_outfit, create_fit_card

# ── MOCK DATA BASELINES ───────────────────────────────────────────────────────

@pytest.fixture
def mock_dataset_fixtures():
    """Sample dataset entries mirroring the format of lst_033 and lst_034."""
    return [
        {
            "id": "lst_033",
            "title": "Vintage Band Tee — Faded Grey",
            "description": "Faded grey band-style tee with distressed graphic. Fits boxy.",
            "category": "tops",
            "style_tags": ["vintage", "grunge", "band tee"],
            "size": "L",
            "condition": "fair",
            "price": 19.00,
            "colors": ["grey"],
            "brand": None,
            "platform": "depop"
        },
        {
            "id": "lst_034",
            "title": "Bucket Hat — Reversible, Brown Plaid",
            "description": "Reversible bucket hat — plaid on one side, solid tan on the other.",
            "category": "accessories",
            "style_tags": ["90s", "streetwear", "accessories"],
            "size": "One Size",
            "condition": "excellent",
            "price": 14.00,
            "colors": ["brown", "tan"],
            "brand": None,
            "platform": "thredUp"
        },
        {
            "id": "lst_099",
            "title": "Designer Leather Jacket",
            "description": "Premium luxury statement leather jacket.",
            "category": "outerwear",
            "style_tags": ["minimalist", "luxury"],
            "size": "M",
            "condition": "excellent",
            "price": 150.00,
            "colors": ["black"],
            "brand": "LuxuryBrand",
            "platform": "grailed"
        }
    ]


# ── TEST SUITE: TOOL 1 (search_listings) ──────────────────────────────────────

@patch("tools.load_listings")
def test_search_listings_happy_path(mock_load, mock_dataset_fixtures):
    """Verifies standard keyword matching, sorting, and constraints filter correctly."""
    mock_load.return_value = mock_dataset_fixtures
    
    # Search for something matching lst_033 perfectly
    results = search_listings(description="vintage grunge", size="L", max_price=30.00)
    
    assert len(results) == 1
    assert results[0]["id"] == "lst_033"
    assert results[0]["price"] == 19.00


@patch("tools.load_listings")
def test_search_listings_case_insensitive_partial_size(mock_load, mock_dataset_fixtures):
    """Verifies size strings map gracefully to partial text bounds (e.g. 'one size')."""
    mock_load.return_value = mock_dataset_fixtures
    
    results = search_listings(description="hat", size="one size", max_price=20.00)
    assert len(results) == 1
    assert results[0]["id"] == "lst_034"


@patch("tools.load_listings")
def test_search_listings_price_ceiling_exclusion(mock_load, mock_dataset_fixtures):
    """Verifies that items exceeding the max_price parameter are omitted entirely."""
    mock_load.return_value = mock_dataset_fixtures
    
    # Looking for a jacket but limit is $50 (The mock jacket is $150)
    results = search_listings(description="leather jacket", size="M", max_price=50.00)
    assert results == []


@patch("tools.load_listings")
def test_search_listings_returns_empty_on_no_match(mock_load, mock_dataset_fixtures):
    """Verifies zero relevant scores return [] rather than raising an error."""
    mock_load.return_value = mock_dataset_fixtures
    
    results = search_listings(description="neon scuba suit", size="S", max_price=10.00)
    assert results == []


@patch("tools.load_listings")
def test_search_listings_data_loader_fault_tolerance(mock_load):
    """Verifies that if load_listings crashes, the tool handles it safely and returns []."""
    mock_load.side_effect = RuntimeError("Database file unreachable")
    
    results = search_listings(description="anything", size="M", max_price=20.00)
    assert results == []


# ── TEST SUITE: TOOL 2 (suggest_outfit) ───────────────────────────────────────

@patch("tools._get_groq_client")
def test_suggest_outfit_empty_wardrobe(mock_get_client, mock_dataset_fixtures):
    """Verifies empty wardrobe routes logic down a generic inspirational path without LLM failure."""
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    
    # Configure mock LLM response text
    mock_client.chat.completions.create.return_value.choices[0].message.content = (
        "Since your wardrobe is empty, try pairing this item with generic wide-leg denim and white sneakers."
    )
    
    target_item = mock_dataset_fixtures[0]
    empty_wardrobe = {"items": []}
    
    response = suggest_outfit(new_item=target_item, wardrobe=empty_wardrobe)
    
    assert "empty" in response or "generic" in response
    assert isinstance(response, str)
    mock_client.chat.completions.create.assert_called_once()


@patch("tools._get_groq_client")
def test_suggest_outfit_populated_wardrobe_happy_path(mock_get_client, mock_dataset_fixtures):
    """Verifies that item context and wardrobe components are successfully bundled into prompts."""
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_client.chat.completions.create.return_value.choices[0].message.content = (
        "Outfit Suggestion: Pair your Vintage Band Tee with your Baggy Black Jeans and Chunky Sneakers."
    )
    
    target_item = mock_dataset_fixtures[0]
    user_wardrobe = {
        "items": [
            {"title": "Baggy Black Jeans", "category": "bottoms", "style_tags": ["90s", "grunge"]},
            {"title": "Chunky Sneakers", "category": "shoes", "style_tags": ["streetwear"]}
        ]
    }
    
    response = suggest_outfit(new_item=target_item, wardrobe=user_wardrobe)
    
    assert "Baggy Black Jeans" in response or "Outfit Suggestion" in response
    assert isinstance(response, str)


@patch("tools._get_groq_client")
def test_suggest_outfit_api_failure_handling(mock_get_client, mock_dataset_fixtures):
    """Ensures that Groq network/API timeout exceptions return an informative fallback error string."""
    mock_get_client.side_effect = Exception("Groq API rate limit exceeded")
    
    target_item = mock_dataset_fixtures[0]
    response = suggest_outfit(new_item=target_item, wardrobe={"items": []})
    
    assert "System Error" in response or "Unable to access" in response
    assert isinstance(response, str)


# ── TEST SUITE: TOOL 3 (create_fit_card) ──────────────────────────────────────

@patch("tools._get_groq_client")
def test_create_fit_card_happy_path(mock_get_client, mock_dataset_fixtures):
    """Validates generation of unique, short social media captions using incoming metrics."""
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_client.chat.completions.create.return_value.choices[0].message.content = (
        "just thrifted this faded grey band tee off depop for $19.00! perfectly matched with my baggy jeans 🖤"
    )
    
    outfit_str = "Pair your Vintage Band Tee with your Baggy Black Jeans and Chunky Sneakers."
    target_item = mock_dataset_fixtures[0]
    
    caption = create_fit_card(outfit=outfit_str, new_item=target_item)
    
    assert "depop" in caption.lower()
    assert "$19" in caption
    assert isinstance(caption, str)


def test_create_fit_card_guards_against_missing_or_empty_inputs():
    """Asserts that whitespace-only strings or empty dict values yield safe error descriptions instead of crashes."""
    bad_outfit = "   "
    valid_item = {"title": "Tee", "price": 10.0, "platform": "vinted"}
    
    # Empty outfit string test
    res1 = create_fit_card(outfit=bad_outfit, new_item=valid_item)
    assert "Error" in res1
    
    # Missing item payload test
    res2 = create_fit_card(outfit="Good Outfit Description", new_item={})
    assert "Error" in res2


@patch("tools._get_groq_client")
def test_create_fit_card_llm_failure_recovery_path(mock_get_client, mock_dataset_fixtures):
    """Checks that a connection break triggers local string interpolation instead of failing standard pipeline."""
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_client.chat.completions.create.side_effect = RuntimeWarning("Groq Service Timeout")
    
    outfit_str = "Pair your Vintage Band Tee with your Baggy Black Jeans and Chunky Sneakers."
    target_item = mock_dataset_fixtures[0]
    
    caption = create_fit_card(outfit=outfit_str, new_item=target_item)
    
    # The programmatic string fallback fallback text criteria checklist:
    assert "thrifted this absolute gem" in caption or "just picked up this" in caption.lower()
    assert "depop" in caption.lower()
    assert "19.00" in caption