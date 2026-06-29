# How to Run Tests: Complete Guide

**Project:** Provenance Guard - AI Content Detection System  
**Last Updated:** June 29, 2026

---

## 🚀 Quick Start (5 minutes)

### Step 1: Start the Flask Application
```bash
cd c:\Users\Nkiru\AI201\project4-provenance-guard
python app.py
```

**Expected output:**
```
 * Running on http://127.0.0.1:5000
 * Debug mode: on
```

⚠️ **Keep this terminal open!** The app must be running for tests to pass.

### Step 2: Run Automated Tests (in a new terminal)
```bash
cd c:\Users\Nkiru\AI201\project4-provenance-guard
python test_stretch_features.py
```

**Expected duration:** ~15 seconds (includes Groq API calls)

**Expected output:**
```
======================================================
  STRETCH FEATURES TEST SUITE (Features 2 & 3)
======================================================

[FEATURE 2] PROVENANCE CERTIFICATE ISSUANCE
  ✅ PASSED

[FEATURE 2] CREATOR ACCOUNT VERIFICATION
  ✅ PASSED

[FEATURE 3] ANALYTICS DASHBOARD
  ✅ PASSED

[FEATURE 3] SIGNAL CONFLICT DETECTION
  ✅ PASSED

[INTEGRATION] FEATURES 2 & 3 TOGETHER
  ✅ PASSED

======================================================
  ✅ ALL TESTS PASSED
======================================================
```

---

## 📋 Available Tests

### Test File 1: `test_stretch_features.py` ⭐ MAIN TEST SUITE
**Purpose:** Comprehensive testing of Features 2 & 3  
**Duration:** ~15 seconds  
**Requires:** Flask app running + GROQ_API_KEY

```bash
python test_stretch_features.py
```

**What it tests:**
- Feature 2: Certificate issuance (signed with HMAC-SHA256)
- Feature 2: Creator account verification
- Feature 3: Analytics metrics computation
- Feature 3: Signal conflict detection
- Integration: Features working together

---

### Test File 2: `test_milestone_4.py`
**Purpose:** Signal 2 & 3 validation  
**Duration:** ~10 seconds  
**Requires:** Flask app running + GROQ_API_KEY

```bash
python test_milestone_4.py
```

**What it tests:**
- Signal 2 (Groq LLM forensic analysis)
- Signal 3 (Semantic density)
- Baseline samples (human vs AI)
- Edge cases (poetry with repetition, technical docs)

---

### Test File 3: `test_signal.py`
**Purpose:** Ensemble pipeline validation  
**Duration:** ~10 seconds  
**Requires:** Flask app running + GROQ_API_KEY

```bash
python test_signal.py
```

**What it tests:**
- Individual signal isolation
- Baseline human & AI samples
- Advanced stress-test cases
- Ensemble pipeline simulation

---

### Test File 4: `test_signals_2_3.py`
**Purpose:** Quick sanity check for Signals 2 & 3  
**Duration:** ~5 seconds  
**Requires:** GROQ_API_KEY

```bash
python test_signals_2_3.py
```

**What it tests:**
- Signal 2 (LLM probability)
- Signal 3 (Semantic density)
- Basic functionality only

---

## 🔧 Setup & Configuration

### Prerequisites

1. **Python 3.8+**
   ```bash
   python --version
   ```

2. **Virtual Environment** (already created)
   ```bash
   # Activate it
   # Windows:
   .venv\Scripts\activate
   
   # macOS/Linux:
   source .venv/bin/activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set Environment Variables**
   ```bash
   # Create .env file in project root
   GROQ_API_KEY=your_api_key_here
   CERTIFICATE_SECRET=dev-secret-key  # Optional, has default
   ```

### Check Setup

```bash
# Verify Flask is installed
python -c "import flask; print(flask.__version__)"

# Verify requests is installed
python -c "import requests; print(requests.__version__)"

# Test Groq API connection (if key set)
python -c "import os; print('GROQ_API_KEY:', 'SET' if os.environ.get('GROQ_API_KEY') else 'NOT SET')"
```

---

## 📝 Manual Testing with cURL

Run these commands in PowerShell or Git Bash while the Flask app is running.

### Feature 2: Certificates

#### 1. Submit Content
```bash
curl -X POST http://127.0.0.1:5000/submit `
  -H "Content-Type: application/json" `
  -d '{
    "text": "This is my original work about important topics.",
    "creator_id": "test-user-1"
  }'
```

**Copy the `content_id` from response** — you'll need it next.

#### 2. File Appeal with Overrule
```bash
curl -X POST http://127.0.0.1:5000/appeal `
  -H "Content-Type: application/json" `
  -d '{
    "content_id": "PASTE_CONTENT_ID_HERE",
    "creator_reasoning": "I wrote this myself from personal experience.",
    "overrule_decision": "overrule_to_human"
  }'
```

**Expected response includes:**
```json
{
  "certificate_issued": true,
  "provenance_certificate": {
    "certificate_id": "uuid...",
    "display_badge_text": "✓ Verified Original Human Content",
    "signature": "hmac-sha256-hex-string..."
  }
}
```

#### 3. Retrieve Certificate
```bash
curl http://127.0.0.1:5000/certificate/PASTE_CONTENT_ID_HERE
```

**Expected response:**
```json
{
  "certificate": {...},
  "is_valid": true,
  "verified": true
}
```

#### 4. Verify Creator Account
```bash
curl -X POST http://127.0.0.1:5000/verify-creator `
  -H "Content-Type: application/json" `
  -d '{"creator_id": "verified-author-alice"}'
```

**Expected response:**
```json
{
  "status": "success",
  "provenance_credential": "Verified Human Account"
}
```

### Feature 3: Analytics

#### Get Real-Time Metrics
```bash
curl http://127.0.0.1:5000/analytics
```

**Expected response:**
```json
{
  "summary": {
    "total_processed_submissions": 15,
    "system_status": "operational"
  },
  "distribution_patterns": {
    "likely_human_percentage": 60.0,
    "uncertain_mixed_percentage": 20.0,
    "likely_ai_percentage": 20.0
  },
  "appeals_telemetry": {
    "total_appeals_submitted": 2,
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

### View Audit Log
```bash
curl http://127.0.0.1:5000/log
```

---

## 🎯 Testing Workflows

### Workflow 1: Full Feature 2 Test (Certificates)
```bash
# Terminal 1: Start Flask
python app.py

# Terminal 2: Run test suite
python test_stretch_features.py

# OR manually:
# 1. Submit content
# 2. File appeal with overrule_decision: "overrule_to_human"
# 3. Retrieve certificate
# 4. Verify signature
```

### Workflow 2: Full Feature 3 Test (Analytics)
```bash
# Terminal 1: Start Flask
python app.py

# Terminal 2: Run test suite
python test_stretch_features.py

# OR manually:
# 1. Submit multiple content pieces
# 2. File some appeals
# 3. Fetch /analytics
# 4. Verify metrics are computed correctly
```

### Workflow 3: Complete End-to-End Test
```bash
# Terminal 1: Start Flask
python app.py

# Terminal 2: Run all tests in sequence
python test_stretch_features.py
python test_milestone_4.py
python test_signal.py
python test_signals_2_3.py
```

### Workflow 4: Performance Test
```bash
# Run tests multiple times to check consistency
for ($i=1; $i -le 5; $i++) {
    Write-Host "Run $i..."
    python test_stretch_features.py
    Start-Sleep -Seconds 2
}
```

---

## ⚠️ Common Issues & Troubleshooting

### Issue: "Connection refused"
```
Error: Failed to connect to http://127.0.0.1:5000
```
**Solution:** Start the Flask app first
```bash
python app.py
```

### Issue: "GROQ_API_KEY not found"
```
[WARNING] GROQ_API_KEY environment variable not found!
Signal 2 will use a fallback value of 0.5 for testing purposes.
```
**Solution:** Set your Groq API key in `.env`
```bash
GROQ_API_KEY=gsk_YOUR_KEY_HERE
```

### Issue: "Port 5000 already in use"
```
OSError: [Errno 48] Address already in use
```
**Solution:** Kill the existing process or use different port
```bash
# Windows: Find and kill process on port 5000
netstat -ano | findstr :5000
taskkill /PID <PID> /F

# Or modify app.py line ~580 to use different port:
app.run(host='127.0.0.1', port=5001, debug=True)
```

### Issue: Test hangs or times out
**Solution:** The test is waiting for Groq API response
- Check your internet connection
- Verify GROQ_API_KEY is valid
- Increase timeout in code if needed (currently 10 seconds)

### Issue: "Certificate signature invalid"
```
Error: Certificate signature verification failed
```
**Solution:** Ensure CERTIFICATE_SECRET environment variable matches
```bash
# All instances should use same secret
echo $env:CERTIFICATE_SECRET
```

---

## 📊 Expected Test Results

### Quick Test (~5 sec)
```bash
python test_signals_2_3.py
```
✅ Both signals compute without error

### Medium Test (~15 sec)
```bash
python test_stretch_features.py
```
✅ All 5 test functions pass  
✅ Certificates issued & verified  
✅ Analytics metrics computed  

### Full Test Suite (~40 sec)
```bash
python test_milestone_4.py
python test_signal.py
python test_signals_2_3.py
python test_stretch_features.py
```
✅ All tests pass  
✅ ~35-40 total HTTP requests made  
✅ ~5-10 Groq API calls  

---

## 🔍 What to Look For

### Successful Test Indicators ✅

1. **No errors in console output**
   - No red text
   - No stack traces
   - No "FAILED" messages

2. **Response status codes**
   - 200 OK (successful requests)
   - 400 Bad Request (validation errors - expected)
   - 404 Not Found (missing resources - expected in some tests)

3. **Metrics in analytics response**
   - `total_processed_submissions` > 0
   - `human_percentage` + `uncertain_percentage` + `ai_percentage` ≈ 100%
   - `certificates_issued` ≥ 0

4. **Certificate verification**
   - `is_valid: true` from `/certificate/{id}`
   - `signature` field present in certificate
   - `display_badge_text` = "✓ Verified Original Human Content"

### Test Failure Indicators ❌

1. **Exception stack traces**
   - Indicates code error
   - Check error message and line number

2. **Connection refused**
   - Flask app not running
   - Start with `python app.py`

3. **Invalid JSON in response**
   - Check request format
   - Verify Content-Type header is set

4. **Certificate verification failed**
   - CERTIFICATE_SECRET mismatch
   - Certificate was modified/tampered

---

## 📈 Performance Expectations

| Operation | Time | Notes |
|-----------|------|-------|
| Submit content | 1-2 sec | Includes Groq API call |
| File appeal | <100ms | Local operation |
| Issue certificate | <1ms | HMAC-SHA256 |
| Verify certificate | <1ms | Constant-time comparison |
| Get analytics | <100ms | Scans in-memory structures |
| Full test suite | ~15 sec | 5 tests, some API calls |

---

## 🎓 Learning Tests in Order

1. **Start here:** `test_signals_2_3.py` (basic signal validation)
2. **Then:** `test_signal.py` (ensemble logic)
3. **Then:** `test_milestone_4.py` (signal behaviors)
4. **Finally:** `test_stretch_features.py` (features 2 & 3)

Each test builds on knowledge from the previous one.

---

## 📚 Documentation References

- **README.md** — Full project documentation
- **QUICKSTART_STRETCH_FEATURES.md** — Testing with cURL examples
- **STRETCH_FEATURES_IMPLEMENTATION.md** — Technical implementation details
- **app.py** — Source code with inline comments

---

## ✅ Verification Checklist

Before considering testing complete:

- [ ] Flask app starts without errors: `python app.py`
- [ ] `test_stretch_features.py` passes all tests
- [ ] Analytics endpoint returns valid metrics: `curl http://127.0.0.1:5000/analytics`
- [ ] Certificate can be issued and verified
- [ ] Creator account verification works
- [ ] No warnings in console output
- [ ] All 4 test files run without hanging

**Once all items checked:** ✅ Testing complete and ready for submission!

---

## 🆘 Need Help?

1. **Check console output** — Error messages are descriptive
2. **Review QUICKSTART_STRETCH_FEATURES.md** — Has cURL examples
3. **Check .env file** — Ensure GROQ_API_KEY is set
4. **Verify Flask is running** — Check terminal for "Running on..."
5. **Restart everything** — Kill Flask and test, then retry

**If still stuck:** Trace through the test code to understand what's being tested, then manually run that operation with cURL.
