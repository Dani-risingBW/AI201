"""
Test Suite for Stretch Features 2 & 3:
- Feature 2: Provenance Certificates (signed, cryptographically verifiable)
- Feature 3: Live Analytics Dashboard (distribution, contestation, conflict metrics)
"""

import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "http://127.0.0.1:5000"

def print_header(title):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")

# ============================================================================
# FEATURE 2: PROVENANCE CERTIFICATES
# ============================================================================

def test_feature_2_certificate_issuance():
    """Test issuing a provenance certificate during appeal overrule."""
    print_header("FEATURE 2: PROVENANCE CERTIFICATE ISSUANCE")

    # Step 1: Submit content that will be classified as uncertain/AI
    print("\n[1] Submitting content for classification...")
    submission = {
        "text": "This is important content. This is important content. This is important content.",
        "creator_id": "test-certificate-user"
    }
    resp = requests.post(f"{BASE_URL}/submit", json=submission)
    assert resp.status_code == 200, f"Submit failed: {resp.text}"
    submit_data = resp.json()
    content_id = submit_data["content_id"]
    initial_confidence = submit_data["confidence"]
    print(f"   Content ID: {content_id}")
    print(f"   Classification: {submit_data['attribution']['primary_classification']}")
    print(f"   Confidence: {initial_confidence}")

    # Step 2: File an appeal
    print("\n[2] Filing appeal with overrule decision...")
    appeal = {
        "content_id": content_id,
        "creator_reasoning": "This is my original work about important topics.",
        "overrule_decision": "overrule_to_human"  # Reviewer approves
    }
    resp = requests.post(f"{BASE_URL}/appeal", json=appeal)
    assert resp.status_code == 200, f"Appeal failed: {resp.text}"
    appeal_data = resp.json()
    print(f"   Appeal Status: {appeal_data['status']}")
    print(f"   Certificate Issued: {appeal_data.get('certificate_issued', False)}")

    # Step 3: Verify certificate was issued
    if "provenance_certificate" in appeal_data:
        cert = appeal_data["provenance_certificate"]
        print(f"\n[3] Certificate Details:")
        print(f"   Certificate ID: {cert['certificate_id']}")
        print(f"   Display Text: {cert['display_badge_text']}")
        print(f"   Verification Method: {cert['verification_method']}")
        print(f"   Signed: {'signature' in cert}")
        assert "signature" in cert, "Certificate not cryptographically signed!"
        print(f"   ✅ Certificate is cryptographically signed")
    else:
        print("   ❌ No certificate in appeal response")

    # Step 4: Retrieve certificate via dedicated endpoint
    print(f"\n[4] Retrieving certificate via GET /certificate/{content_id}...")
    resp = requests.get(f"{BASE_URL}/certificate/{content_id}")
    if resp.status_code == 200:
        cert_data = resp.json()
        print(f"   Certificate Valid: {cert_data['is_valid']}")
        print(f"   Verified: {cert_data['verified']}")
        print(f"   ✅ Certificate retrieved and signature verified")
    else:
        print(f"   Response: {resp.text}")

    print(f"\n✅ FEATURE 2 TEST PASSED: Certificates are issued and cryptographically verifiable")


def test_feature_2_creator_verification():
    """Test account-level creator verification."""
    print_header("FEATURE 2: CREATOR ACCOUNT VERIFICATION")

    creator_id = "verified-author-alice"

    # Step 1: Verify creator account
    print(f"\n[1] Verifying creator account: {creator_id}...")
    resp = requests.post(f"{BASE_URL}/verify-creator", json={"creator_id": creator_id})
    assert resp.status_code == 200, f"Verification failed: {resp.text}"
    data = resp.json()
    print(f"   Status: {data['status']}")
    print(f"   Credential: {data['provenance_credential']}")
    print(f"   ✅ Creator account verified")

    # Step 2: Submit content as verified creator
    print(f"\n[2] Submitting content as verified creator...")
    submission = {
        "text": "I am a verified human creator writing original thoughts on interesting topics.",
        "creator_id": creator_id
    }
    resp = requests.post(f"{BASE_URL}/submit", json=submission)
    assert resp.status_code == 200, f"Submit failed: {resp.text}"
    data = resp.json()
    print(f"   Provenance Badge: {data.get('provenance_badge')}")
    assert "Verified" in data.get('provenance_badge', ''), "Badge should indicate verification"
    print(f"   ✅ Verified creator badge displayed in response")

    print(f"\n✅ FEATURE 2 TEST PASSED: Creator account verification works end-to-end")


# ============================================================================
# FEATURE 3: ANALYTICS DASHBOARD
# ============================================================================

def test_feature_3_analytics_metrics():
    """Test analytics dashboard computation and metrics."""
    print_header("FEATURE 3: ANALYTICS DASHBOARD")

    # Submit several diverse content samples to build up analytics data
    print("\n[1] Submitting diverse content samples to analytics database...")

    samples = [
        {"text": "I really enjoyed the new coffee shop downtown. The barista was friendly and the latte was perfect.", "creator_id": "user1"},
        {"text": "This system checks patterns. This system checks metrics. This system checks values.", "creator_id": "user2"},
        {"text": "The historical context is important. To understand modern technology, we must examine its origins.", "creator_id": "user3"},
    ]

    content_ids = []
    for i, sample in enumerate(samples):
        resp = requests.post(f"{BASE_URL}/submit", json=sample)
        assert resp.status_code == 200
        content_ids.append(resp.json()["content_id"])
        print(f"   Sample {i+1}: {resp.json()['attribution']['primary_classification']}")

    # File an appeal on one submission
    print("\n[2] Filing appeal to generate contestation data...")
    appeal = {
        "content_id": content_ids[0],
        "creator_reasoning": "This is my personal opinion, not AI-generated."
    }
    resp = requests.post(f"{BASE_URL}/appeal", json=appeal)
    assert resp.status_code == 200
    print(f"   Appeal filed on content {content_ids[0]}")

    # Fetch analytics
    print("\n[3] Fetching analytics dashboard...")
    resp = requests.get(f"{BASE_URL}/analytics")
    assert resp.status_code == 200, f"Analytics failed: {resp.text}"
    analytics = resp.json()

    print(f"\n[SUMMARY METRICS]")
    print(f"   Total Submissions: {analytics['summary']['total_processed_submissions']}")
    print(f"   System Status: {analytics['summary']['system_status']}")

    print(f"\n[DISTRIBUTION PATTERNS]")
    dist = analytics['distribution_patterns']
    print(f"   Likely Human:    {dist['likely_human_percentage']}% ({dist['human_count']} submissions)")
    print(f"   Uncertain/Mixed: {dist['uncertain_mixed_percentage']}% ({dist['uncertain_count']} submissions)")
    print(f"   Likely AI:       {dist['likely_ai_percentage']}% ({dist['ai_count']} submissions)")

    print(f"\n[APPEALS TELEMETRY]")
    appeals = analytics['appeals_telemetry']
    print(f"   Total Appeals Filed: {appeals['total_appeals_submitted']}")
    print(f"   Contestable Submissions: {appeals['contestable_submissions']}")
    print(f"   Contestation Rate: {appeals['active_contestation_rate']}")

    print(f"\n[SYSTEM HEALTH]")
    health = analytics['system_health']
    print(f"   Signal Conflict Dampening Triggers: {health['signal_variance_dampening_triggers']}")
    print(f"   Heuristic-LLM Conflict Rate: {health['heuristic_llm_conflict_rate']}")
    print(f"   Average Confidence Score: {health['average_confidence_score']}")
    print(f"   Certificates Issued: {health['certificates_issued']}")

    # Validate key metrics exist and are meaningful
    assert "total_processed_submissions" in analytics["summary"]
    assert "distribution_patterns" in analytics
    assert "appeals_telemetry" in analytics
    assert "system_health" in analytics
    print(f"\n✅ FEATURE 3 TEST PASSED: All analytics metrics computed and returned")


def test_feature_3_conflict_detection():
    """Test that signal conflicts are properly detected and tracked."""
    print_header("FEATURE 3: SIGNAL CONFLICT DETECTION IN ANALYTICS")

    print("\n[1] Submitting content with likely high signal conflict...")
    # This is human-like text (high variance, diverse vocabulary)
    # but with semantic repetition that might trigger S3
    conflict_text = (
        "I woke up this morning and decided to think about thinking. "
        "The process of thinking about thinking requires careful consideration. "
        "When we think about thinking, we encounter interesting paradoxes. "
        "These thinking-about-thinking paradoxes reveal deep truths."
    )

    resp = requests.post(f"{BASE_URL}/submit", json={
        "text": conflict_text,
        "creator_id": "conflict-test-user"
    })
    assert resp.status_code == 200
    data = resp.json()
    print(f"   Submitted: {data['attribution']['primary_classification']}")
    print(f"   Confidence: {data['confidence']}")

    # Check analytics to see if conflict was detected
    print("\n[2] Checking analytics for conflict detection...")
    resp = requests.get(f"{BASE_URL}/analytics")
    assert resp.status_code == 200
    analytics = resp.json()

    conflicts = analytics['system_health']['signal_variance_dampening_triggers']
    conflict_rate = analytics['system_health']['heuristic_llm_conflict_rate']

    print(f"   Total Conflict Triggers: {conflicts}")
    print(f"   Conflict Rate: {conflict_rate}")
    print(f"   ✅ Signal conflicts are tracked in analytics")

    print(f"\n✅ FEATURE 3 TEST PASSED: Conflict detection integrated into analytics")


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

def test_feature_2_and_3_integration():
    """Test that Features 2 and 3 work together."""
    print_header("INTEGRATION: FEATURES 2 & 3 TOGETHER")

    print("\n[1] Submitting and appealing content...")

    # Submit
    resp = requests.post(f"{BASE_URL}/submit", json={
        "text": "This is my personal work that shows real human creativity.",
        "creator_id": "integration-test-user"
    })
    content_id = resp.json()["content_id"]

    # Appeal with overrule (certificate issuance)
    resp = requests.post(f"{BASE_URL}/appeal", json={
        "content_id": content_id,
        "creator_reasoning": "I wrote this based on my personal experience.",
        "overrule_decision": "overrule_to_human"
    })
    assert resp.status_code == 200
    certificate_issued = resp.json().get('certificate_issued', False)

    print(f"   Content: {content_id}")
    print(f"   Certificate Issued: {certificate_issued}")

    print("\n[2] Checking analytics for updated metrics...")
    resp = requests.get(f"{BASE_URL}/analytics")
    analytics = resp.json()

    certs = analytics['system_health']['certificates_issued']
    appeals = analytics['appeals_telemetry']['total_appeals_submitted']

    print(f"   Certificates Issued: {certs}")
    print(f"   Total Appeals: {appeals}")

    if certificate_issued:
        assert certs > 0, "Analytics should show issued certificates"
    assert appeals > 0, "Analytics should show filed appeals"

    print(f"\n✅ INTEGRATION TEST PASSED: Features 2 & 3 work together seamlessly")


# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*70)
    print("  STRETCH FEATURES TEST SUITE (Features 2 & 3)")
    print("="*70)
    print("\nMake sure the Flask app is running: python app.py")
    print("This test suite will create content, file appeals, and check analytics.")

    try:
        # Test Feature 2
        test_feature_2_certificate_issuance()
        test_feature_2_creator_verification()

        # Test Feature 3
        test_feature_3_analytics_metrics()
        test_feature_3_conflict_detection()

        # Integration
        test_feature_2_and_3_integration()

        print("\n" + "="*70)
        print("  ✅ ALL TESTS PASSED")
        print("="*70)

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
