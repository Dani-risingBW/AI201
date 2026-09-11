"""
test_stretch_features.py

Comprehensive tests for ThreadScout AI stretch features.
Tests Tool 5, 6, and 7 alongside core tools.

Uses proper pytest assertions to verify tool behavior, catching data inconsistencies
and error conditions that print-based tests would miss.
"""

import pytest
import uuid
from tools import (
    search_listings,
    evaluate_price_fairness,
    price_comparison_analyzer,
    style_profile_manager,
    trend_radar,
)
from utils.data_loader import load_listings


def test_price_comparison_analyzer():
    """Test Tool 5: price_comparison_analyzer with market trends."""
    dataset = load_listings()
    assert dataset, "Dataset should not be empty"

    target_item = dataset[0]
    assert target_item.get("title"), "Target item should have a title"
    assert target_item.get("price"), "Target item should have a price"

    # Test with 30-day window
    result = price_comparison_analyzer(
        target_item=target_item,
        mock_dataset=dataset,
        time_window="30_days",
        platform_filter=None,
    )

    # Assert required fields exist and have correct types
    assert "price_trend" in result, "Result should contain price_trend"
    assert isinstance(
        result["price_trend"], str
    ), "price_trend should be a string"
    assert len(result["price_trend"]) > 0, "price_trend should not be empty"

    assert "market_average" in result, "Result should contain market_average"
    assert isinstance(
        result["market_average"], (int, float)
    ), "market_average should be numeric"
    assert result["market_average"] > 0, "market_average should be positive"

    assert "percentile_rank" in result, "Result should contain percentile_rank"
    assert 0 <= result["percentile_rank"] <= 100, (
        f"percentile_rank should be 0-100, got {result['percentile_rank']}"
    )

    assert "recommendations" in result, "Result should contain recommendations"
    assert isinstance(result["recommendations"], (str, list)), (
        "recommendations should be string or list"
    )

    # Test with platform filter
    platform = target_item.get("platform", "Unknown")
    result_filtered = price_comparison_analyzer(
        target_item=target_item,
        mock_dataset=dataset,
        time_window="30_days",
        platform_filter=platform,
    )

    # Filtered result should also have required fields
    assert "price_trend" in result_filtered, "Filtered result should contain price_trend"
    assert "market_average" in result_filtered, "Filtered result should contain market_average"


def test_style_profile_manager():
    """Test Tool 6: style_profile_manager for persistent preferences."""
    # Use a unique user ID to avoid conflicts between test runs
    user_id = f"test_user_{uuid.uuid4().hex[:8]}"

    # Test 1: Create profile (or update if it already exists)
    profile_data = {
        "preferred_styles": ["vintage", "grunge", "minimalist"],
        "size_range": {"top": "S/M", "bottom": "26W", "shoes": "7"},
        "budget_range": {"min": 15, "max": 75},
        "favorite_platforms": ["Depop", "Grailed"],
    }

    result = style_profile_manager(
        user_id=user_id,
        action="create_profile",
        profile_data=profile_data,
    )

    # If profile already exists, update it instead
    if result.get("status") == "error" and "already exists" in result.get("message", ""):
        result = style_profile_manager(
            user_id=user_id,
            action="update_profile",
            profile_data=profile_data,
        )

    assert result.get("status") == "success", (
        f"Profile creation should succeed (unique ID {user_id}), got status: {result.get('status')}"
    )

    # Test 2: Log a search
    result = style_profile_manager(
        user_id=user_id, action="log_search", profile_data={"query": "vintage band tee under $30"}
    )
    assert result.get("status") in ["success", "logged"], f"Search logging should succeed, got status: {result.get('status')}"
    assert "search_count" in result, "Result should contain search_count"
    assert isinstance(
        result["search_count"], int
    ), "search_count should be an integer"
    assert result["search_count"] >= 1, "search_count should be at least 1 after logging"

    # Test 3: Fetch profile
    result = style_profile_manager(user_id=user_id, action="fetch_profile")
    assert result.get("status") == "success", f"Profile fetch should succeed, got status: {result.get('status')}"

    profile = result.get("profile", {})
    assert profile, "Profile dict should exist and not be empty"
    assert "preferred_styles" in profile, "Profile should contain preferred_styles"
    assert isinstance(
        profile["preferred_styles"], list
    ), "preferred_styles should be a list"

    assert "budget_range" in profile, "Profile should contain budget_range"
    budget = profile["budget_range"]
    assert isinstance(budget, dict), "budget_range should be a dict"
    assert "min" in budget and "max" in budget, "budget_range should have min and max"

    assert "past_searches" in profile, "Profile should contain past_searches"
    assert isinstance(
        profile["past_searches"], list
    ), "past_searches should be a list"
    assert (
        len(profile["past_searches"]) >= 1
    ), "past_searches should have at least one entry after logging"

    # Test 4: Get style summary
    result = style_profile_manager(user_id=user_id, action="get_style_summary")
    assert result.get("status") == "success", f"Style summary should succeed, got status: {result.get('status')}"
    assert "summary" in result, "Result should contain summary"
    assert isinstance(result["summary"], str), "summary should be a string"
    assert len(result["summary"]) > 0, "summary should not be empty"


def test_trend_radar():
    """Test Tool 7: trend_radar for fashion trend awareness."""
    # Test 1: Vintage trends with size constraint
    result = trend_radar(
        style_category="vintage",
        size_range="M",
        price_ceiling=50.0,
        time_window="this_week",
    )

    assert "trending_items" in result, "Result should contain trending_items"
    assert isinstance(result["trending_items"], list), "trending_items should be a list"

    assert "trending_alert" in result, "Result should contain trending_alert"
    assert isinstance(result["trending_alert"], str), "trending_alert should be a string"

    assert "trending_hashtags" in result, "Result should contain trending_hashtags"
    assert isinstance(
        result["trending_hashtags"], list
    ), "trending_hashtags should be a list"

    assert "search_spike" in result, "Result should contain search_spike"
    assert isinstance(
        result["search_spike"], dict
    ), "search_spike should be a dict"

    # Test 2: Minimalist trends without size constraint
    result = trend_radar(
        style_category="minimalist",
        size_range=None,
        price_ceiling=100.0,
        time_window="this_month",
    )

    assert "trending_items" in result, "Result should contain trending_items"
    assert isinstance(result["trending_items"], list), "trending_items should be a list"

    assert "trending_alert" in result, "Result should contain trending_alert"
    assert isinstance(result["trending_alert"], str), "trending_alert should be a string"

    # Test 3: Edge case - very low price ceiling
    result_low_price = trend_radar(
        style_category="vintage", size_range=None, price_ceiling=10.0, time_window="this_week"
    )
    assert isinstance(result_low_price, dict), "Should return dict even with low price ceiling"
    assert "trending_items" in result_low_price, "Should have trending_items field"


def test_integrated_flow():
    """Test all stretch features in an integrated workflow without user_id."""
    from agent import run_agent
    from utils.data_loader import get_example_wardrobe

    session = run_agent(
        query="vintage graphic tee under $30", wardrobe=get_example_wardrobe()
    )

    # Assert core features work
    assert not session.get("error"), f"Session should not have error, got: {session.get('error')}"
    assert session.get("selected_item"), "Should find a selected item"
    assert session["selected_item"].get("title"), "Selected item should have a title"
    assert session.get("outfit_suggestion"), "Should generate outfit suggestion"
    assert session.get("fit_card"), "Should generate fit card"

    # Assert price context (core tool)
    assert session.get("price_context"), "Should have price context from evaluate_price_fairness"
    assert isinstance(session["price_context"], dict), "price_context should be a dict"

    # Assert stretch features are available
    assert "price_comparison" in session, "Session should have price_comparison field"
    assert "user_profile" in session, "Session should have user_profile field"
    assert "trending_context" in session, "Session should have trending_context field"


def test_integrated_flow_with_user_id():
    """Test integrated flow WITH user_id to activate Tool 6 (style_profile_manager)."""
    from agent import run_agent
    from utils.data_loader import get_example_wardrobe

    user_id = "integration_test_user_001"
    session = run_agent(
        query="vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
        user_id=user_id,  # <-- This now gets passed through correctly
    )

    # Assert core features work
    assert not session.get("error"), f"Session should not have error, got: {session.get('error')}"
    assert session.get("selected_item"), "Should find a selected item"
    assert session.get("outfit_suggestion"), "Should generate outfit suggestion"

    # Assert user_id was captured in session
    assert session.get("user_id") == user_id, f"Session should capture user_id, got: {session.get('user_id')}"

    # Assert Tool 6 (style_profile_manager) was activated because user_id is set
    # This is the critical fix: user_id now flows through run_agent -> _new_session
    assert (
        session.get("user_profile") is not None
    ), "user_profile should be populated when user_id is provided (Tool 6 activation)"
    assert isinstance(
        session["user_profile"], dict
    ), "user_profile should be a dict when available"

    # Assert other stretch features
    assert (
        session.get("trending_context") is not None
    ), "trending_context should be populated"
    assert isinstance(
        session["trending_context"], dict
    ), "trending_context should be a dict"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
