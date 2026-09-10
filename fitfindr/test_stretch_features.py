"""
test_stretch_features.py

Comprehensive tests for ThreadScout AI stretch features.
Tests Tool 5, 6, and 7 alongside core tools.
"""

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
    print("\n" + "=" * 80)
    print("TEST: price_comparison_analyzer (STRETCH TOOL 5)")
    print("=" * 80)

    dataset = load_listings()
    target_item = dataset[0] if dataset else {}

    if target_item:
        print(f"\n📊 Analyzing: {target_item.get('title', 'Unknown')}")
        print(f"   Price: ${target_item.get('price', 0):.2f}")

        # Test with 30-day window
        result = price_comparison_analyzer(
            target_item=target_item,
            mock_dataset=dataset,
            time_window="30_days",
            platform_filter=None,
        )

        print("\n✓ Result:")
        print(f"  - Trend: {result.get('price_trend', 'N/A')}")
        print(f"  - Market Average: ${result.get('market_average', 'N/A'):.2f}")
        print(f"  - Percentile Rank: {result.get('percentile_rank', 'N/A')}th")
        print(f"  - Recommendation: {result.get('recommendations', 'N/A')}")

        # Test with platform filter
        print("\n📍 Testing platform filter...")
        platform = target_item.get("platform", "Unknown")
        result_filtered = price_comparison_analyzer(
            target_item=target_item,
            mock_dataset=dataset,
            time_window="30_days",
            platform_filter=platform,
        )
        print(f"  ✓ Platform comparison for '{platform}': Complete")


def test_style_profile_manager():
    """Test Tool 6: style_profile_manager for persistent preferences."""
    print("\n" + "=" * 80)
    print("TEST: style_profile_manager (STRETCH TOOL 6)")
    print("=" * 80)

    user_id = "test_user_001"

    # Test 1: Create profile
    print(f"\n1️⃣ Creating profile for {user_id}...")
    result = style_profile_manager(
        user_id=user_id,
        action="create_profile",
        profile_data={
            "preferred_styles": ["vintage", "grunge", "minimalist"],
            "size_range": {"top": "S/M", "bottom": "26W", "shoes": "7"},
            "budget_range": {"min": 15, "max": 75},
            "favorite_platforms": ["Depop", "Grailed"],
        }
    )
    print(f"   Status: {result.get('status')}")

    # Test 2: Log a search
    print(f"\n2️⃣ Logging search query...")
    result = style_profile_manager(
        user_id=user_id,
        action="log_search",
        profile_data={"query": "vintage band tee under $30"}
    )
    print(f"   Status: {result.get('status')}")
    print(f"   Search Count: {result.get('search_count', 0)}")

    # Test 3: Fetch profile
    print(f"\n3️⃣ Fetching profile...")
    result = style_profile_manager(
        user_id=user_id,
        action="fetch_profile"
    )
    if result.get("status") == "success":
        profile = result.get("profile", {})
        print(f"   ✓ Profile loaded")
        print(f"     - Styles: {profile.get('preferred_styles', [])}")
        print(f"     - Budget: ${profile.get('budget_range', {}).get('min')} - ${profile.get('budget_range', {}).get('max')}")
        print(f"     - Past searches: {len(profile.get('past_searches', []))}")

    # Test 4: Get style summary
    print(f"\n4️⃣ Generating style summary...")
    result = style_profile_manager(
        user_id=user_id,
        action="get_style_summary"
    )
    if result.get("status") == "success":
        print(f"   Summary: {result.get('summary', 'N/A')}")


def test_trend_radar():
    """Test Tool 7: trend_radar for fashion trend awareness."""
    print("\n" + "=" * 80)
    print("TEST: trend_radar (STRETCH TOOL 7)")
    print("=" * 80)

    # Test 1: Vintage trends
    print(f"\n1️⃣ Scanning for 'vintage' trends...")
    result = trend_radar(
        style_category="vintage",
        size_range="M",
        price_ceiling=50.0,
        time_window="this_week"
    )

    print(f"   Trending Items Found: {len(result.get('trending_items', []))}")
    print(f"   Alert: {result.get('trending_alert', 'N/A')}")

    hashtags = result.get("trending_hashtags", [])
    if hashtags:
        print(f"   Top Hashtags: {' '.join(hashtags[:3])}")

    spikes = result.get("search_spike", {})
    if spikes:
        print(f"   Keyword Spikes: {spikes}")

    # Test 2: Minimalist trends
    print(f"\n2️⃣ Scanning for 'minimalist' trends...")
    result = trend_radar(
        style_category="minimalist",
        size_range=None,
        price_ceiling=100.0,
        time_window="this_month"
    )
    print(f"   Trending Items Found: {len(result.get('trending_items', []))}")
    print(f"   Alert: {result.get('trending_alert', 'N/A')}")


def test_integrated_flow():
    """Test all stretch features in an integrated workflow."""
    print("\n" + "=" * 80)
    print("TEST: INTEGRATED FLOW (Core + Stretch Features)")
    print("=" * 80)

    from agent import run_agent
    from utils.data_loader import get_example_wardrobe

    print(f"\n🎯 Running integrated agent with stretch features...")
    session = run_agent(
        query="vintage graphic tee under $30",
        wardrobe=get_example_wardrobe()
    )

    print(f"\n✓ Session Complete:")
    print(f"  - Item Found: {session.get('selected_item', {}).get('title', 'None')}")
    print(f"  - Price Context: {'✓' if session.get('price_context') else '✗'}")
    print(f"  - Price Comparison (STRETCH): {'✓' if session.get('price_comparison') else '✗'}")
    print(f"  - Trending Context (STRETCH): {'✓' if session.get('trending_context') else '✗'}")
    print(f"  - Outfit Suggestion: {'✓' if session.get('outfit_suggestion') else '✗'}")
    print(f"  - Fit Card: {'✓' if session.get('fit_card') else '✗'}")

    # Display stretch feature data
    if session.get("price_comparison"):
        print(f"\n💚 Price Comparison (Tool 5):")
        pc = session["price_comparison"]
        print(f"    - Trend: {pc.get('price_trend')}")
        print(f"    - Percentile: {pc.get('percentile_rank')}th")

    if session.get("trending_context"):
        print(f"\n📈 Trending Context (Tool 7):")
        tc = session["trending_context"]
        print(f"    - Alert: {tc.get('trending_alert')}")
        print(f"    - Top Tags: {tc.get('trending_hashtags', [])[:3]}")


if __name__ == "__main__":
    print("\n" + "🚀 ThreadScout AI — Stretch Feature Test Suite")
    print("Testing Tools 5, 6, 7 + Integration\n")

    try:
        test_price_comparison_analyzer()
    except Exception as e:
        print(f"❌ Price Comparison failed: {e}")

    try:
        test_style_profile_manager()
    except Exception as e:
        print(f"❌ Style Profile failed: {e}")

    try:
        test_trend_radar()
    except Exception as e:
        print(f"❌ Trend Radar failed: {e}")

    try:
        test_integrated_flow()
    except Exception as e:
        print(f"❌ Integrated flow failed: {e}")

    print("\n" + "=" * 80)
    print("✅ Test suite complete!")
    print("=" * 80)
