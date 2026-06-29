# Quick Start: Testing Stretch Features 2 & 3

## Prerequisites

1. Flask app is running:
```bash
python app.py
```

The app will start on `http://127.0.0.1:5000`

## Testing Flow

### Option 1: Automated Test Suite (Recommended)

```bash
python test_stretch_features.py
```

This runs all tests for Features 2 and 3 automatically. Expected runtime: ~15 seconds.

### Option 2: Manual Testing with cURL

#### Feature 2: Provenance Certificates

**Step 1: Submit content**
```bash
curl -X POST http://127.0.0.1:5000/submit \
  -H "Content-Type: application/json" \
  -d '{
    "text": "This is my original work about important topics.",
    "creator_id": "test-user-1"
  }'
```

Response:
```json
{
  "content_id": "abc123...",
  "attribution": {...},
  "confidence": 0.45,
  "label": "Attribution: Indeterminate...",
  "provenance_badge": "Standard User"
}
```

**Step 2: File appeal with overrule decision**
```bash
curl -X POST http://127.0.0.1:5000/appeal \
  -H "Content-Type: application/json" \
  -d '{
    "content_id": "abc123...",
    "creator_reasoning": "I wrote this myself from personal experience.",
    "overrule_decision": "overrule_to_human"
  }'
```

Response:
```json
{
  "status": "success",
  "certificate_issued": true,
  "provenance_certificate": {
    "certificate_id": "cert-uuid-xxx",
    "content_id": "abc123...",
    "display_badge_text": "✓ Verified Original Human Content",
    "signature": "hmac-sha256-hex-string..."
  }
}
```

**Step 3: Retrieve certificate**
```bash
curl http://127.0.0.1:5000/certificate/abc123...
```

Response:
```json
{
  "certificate": {...},
  "is_valid": true,
  "verified": true
}
```

**Step 4: Verify creator account**
```bash
curl -X POST http://127.0.0.1:5000/verify-creator \
  -H "Content-Type: application/json" \
  -d '{"creator_id": "verified-author-alice"}'
```

Response:
```json
{
  "status": "success",
  "provenance_credential": "Verified Human Account"
}
```

#### Feature 3: Analytics Dashboard

**Fetch analytics at any time:**
```bash
curl http://127.0.0.1:5000/analytics
```

Response:
```json
{
  "summary": {
    "total_processed_submissions": 15,
    "system_status": "operational"
  },
  "distribution_patterns": {
    "likely_human_percentage": 60.0,
    "uncertain_mixed_percentage": 20.0,
    "likely_ai_percentage": 20.0,
    "human_count": 9,
    "uncertain_count": 3,
    "ai_count": 3
  },
  "appeals_telemetry": {
    "total_appeals_submitted": 2,
    "contestable_submissions": 6,
    "active_contestation_rate": "33.33%"
  },
  "system_health": {
    "signal_variance_dampening_triggers": 1,
    "heuristic_llm_conflict_rate": "6.67%",
    "average_confidence_score": 0.4251,
    "certificates_issued": 1
  }
}
```

---

## Key Observations

### Feature 2: Certificates

1. **Signature Verification:** Every certificate includes an HMAC-SHA256 signature computed over its content. The signature prevents tampering.

2. **Two Pathways:**
   - **Content-level:** Issue certificate during appeal overrule
   - **Account-level:** Verify creator account, display badge on all future submissions

3. **Certificate Structure:**
   - `certificate_id`: Unique UUID for tracking
   - `content_id`: Links to original submission
   - `creator_id`: Identifies creator
   - `verification_method`: How it was verified (e.g., "human_appeal_overrule")
   - `signature`: HMAC-SHA256 hex string for tamper detection

### Feature 3: Analytics

1. **Distribution Patterns:** Shows % breakdown of human/uncertain/AI classifications. Helps detect threshold drift.

2. **Contestation Rate:** `appeals / (AI + Uncertain) * 100`
   - Indicates creator dissatisfaction with marginal classifications
   - Rising contestation → system may be over-aggressive

3. **Signal Conflicts:** Tracks how often Signal 2 (LLM) disagrees with Signal 1 (Stylometric) by >0.6
   - High conflict rate → signal calibration is working (admits uncertainty)
   - Low conflict rate → signals are well-aligned (but may miss edge cases)

4. **Average Confidence:** Overall system confidence across all submissions
   - Trending up → system becoming more aggressive on AI flagging
   - Trending down → system becoming more permissive on human content

---

## Example Workflow: End-to-End

```bash
# 1. Submit content (will be uncertain)
CONTENT_ID=$(curl -s -X POST http://127.0.0.1:5000/submit \
  -H "Content-Type: application/json" \
  -d '{
    "text": "This text exhibits both human and AI characteristics. This is important. This is important.",
    "creator_id": "workflow-user"
  }' | jq -r '.content_id')

echo "Submitted: $CONTENT_ID"

# 2. Check analytics before appeal
echo "=== Analytics BEFORE appeal ==="
curl -s http://127.0.0.1:5000/analytics | jq '.appeals_telemetry'

# 3. File appeal with overrule
curl -s -X POST http://127.0.0.1:5000/appeal \
  -H "Content-Type: application/json" \
  -d "{
    \"content_id\": \"$CONTENT_ID\",
    \"creator_reasoning\": \"I wrote this myself.\",
    \"overrule_decision\": \"overrule_to_human\"
  }" | jq '.provenance_certificate'

# 4. Check analytics after appeal
echo "=== Analytics AFTER appeal ==="
curl -s http://127.0.0.1:5000/analytics | jq '.system_health'

# 5. Retrieve certificate directly
echo "=== Certificate Retrieved ==="
curl -s http://127.0.0.1:5000/certificate/$CONTENT_ID | jq '.is_valid'
```

---

## Troubleshooting

### "Connection refused"
- Make sure Flask app is running: `python app.py`
- Check it's listening on port 5000

### "Certificate not found" (404)
- Content must have been verified via appeal overrule
- Use `POST /appeal` with `overrule_decision: "overrule_to_human"`

### Analytics showing zero metrics
- Submit some content first: `POST /submit`
- File an appeal: `POST /appeal`
- Then check: `GET /analytics`

### Signature verification fails
- This should not happen with the built-in implementation
- If it does, the certificate may have been tampered with
- Check the CERTIFICATE_SECRET environment variable matches

---

## Expected Test Duration

- Automated test suite: ~15 seconds (includes Groq API calls)
- Manual testing: ~2-5 minutes for full workflow
- Analytics refresh: <100ms (local computation)

---

## What's Next?

After testing stretch features:

1. **Review README.md** for full documentation
2. **Check STRETCH_FEATURES_IMPLEMENTATION.md** for technical details
3. **Examine test_stretch_features.py** for test examples
4. **Review app.py** to see implementation code

For production deployment:
- Add authentication to `/analytics` and certificate operations
- Migrate from in-memory to SQLite database
- Build reviewer dashboard for appeal overrule workflow
- Add monitoring/alerting on key metrics (contestation rate, conflicts)
