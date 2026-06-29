# 🚀 QUICK TEST REFERENCE CARD

## The Fastest Way to Test Everything

### Step 1: Open Terminal #1 - Start Flask App
```powershell
cd c:\Users\Nkiru\AI201\project4-provenance-guard
python app.py
```

**You should see:**
```
 * Running on http://127.0.0.1:5000
 * Debug mode: on
Press CTRL+C to quit
```

✅ **Leave this running!** Go to Step 2.

---

### Step 2: Open Terminal #2 - Run Tests
```powershell
cd c:\Users\Nkiru\AI201\project4-provenance-guard
python test_stretch_features.py
```

**You should see:**
```
======================================================
  ✅ ALL TESTS PASSED
======================================================
```

✅ **Done!** Tests are complete.

---

## Alternative: Test Everything One by One

```powershell
# Terminal 1 (keep running)
python app.py

# Terminal 2 (run these in sequence)
python test_signals_2_3.py           # ~5 sec
python test_signal.py                # ~10 sec
python test_milestone_4.py           # ~10 sec
python test_stretch_features.py      # ~15 sec
```

**Total time:** ~40 seconds

---

## Test Individual Features (Manual with PowerShell)

### Feature 2: Certificates

```powershell
# 1. Submit content
$response = curl -X POST http://127.0.0.1:5000/submit `
  -H "Content-Type: application/json" `
  -d '{
    "text": "This is my work",
    "creator_id": "user1"
  }' -UseBasicParsing | ConvertFrom-Json

$contentId = $response.content_id
Write-Host "Content ID: $contentId"

# 2. File appeal with certificate
curl -X POST http://127.0.0.1:5000/appeal `
  -H "Content-Type: application/json" `
  -d "{
    \"content_id\": \"$contentId\",
    \"creator_reasoning\": \"I wrote this\",
    \"overrule_decision\": \"overrule_to_human\"
  }" -UseBasicParsing | ConvertFrom-Json | ConvertTo-Json

# 3. Verify certificate
curl http://127.0.0.1:5000/certificate/$contentId `
  -UseBasicParsing | ConvertFrom-Json | ConvertTo-Json
```

### Feature 3: Analytics

```powershell
# Get analytics
curl http://127.0.0.1:5000/analytics `
  -UseBasicParsing | ConvertFrom-Json | ConvertTo-Json
```

---

## Test Key Endpoints

```powershell
# All these should return 200 OK

# 1. Submit content
curl -X POST http://127.0.0.1:5000/submit `
  -H "Content-Type: application/json" `
  -d '{"text":"hello world","creator_id":"user1"}'

# 2. View audit log
curl http://127.0.0.1:5000/log

# 3. Get analytics
curl http://127.0.0.1:5000/analytics

# 4. Verify creator
curl -X POST http://127.0.0.1:5000/verify-creator `
  -H "Content-Type: application/json" `
  -d '{"creator_id":"alice"}'
```

---

## Troubleshooting

### Flask app won't start
```powershell
# Check Python version
python --version  # Should be 3.8+

# Check if port 5000 is in use
netstat -ano | findstr :5000

# Kill process if needed
taskkill /PID <PID> /F

# Try different port (edit line 579 in app.py)
```

### Tests are hanging
```powershell
# Kill Flask app and restart
# It might be stuck on Groq API call
# Check your internet connection
```

### "GROQ_API_KEY not found"
```powershell
# Create .env file in project directory
# Add: GROQ_API_KEY=your_key_here
# Restart Flask app
```

---

## What Each Test Does

| Test File | Time | What It Tests |
|-----------|------|---------------|
| `test_signals_2_3.py` | 5s | Signal 2 & 3 basics |
| `test_signal.py` | 10s | Ensemble pipeline |
| `test_milestone_4.py` | 10s | All signals in detail |
| `test_stretch_features.py` | 15s | **Features 2 & 3** ⭐ |

**Run at least `test_stretch_features.py` to verify Features 2 & 3**

---

## Expected Results

### ✅ Success
```
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

✅ ALL TESTS PASSED
```

### ❌ Failure
```
[FEATURE 2] PROVENANCE CERTIFICATE ISSUANCE
  ❌ TEST FAILED: Connection refused

Check: Is Flask running?
```

---

## Summary

| Action | Command | Time |
|--------|---------|------|
| **Start Flask** | `python app.py` | 1s |
| **Run main tests** | `python test_stretch_features.py` | 15s |
| **Run all tests** | Run each test file | 40s |
| **Total for complete test** | All steps | ~56s |

---

## Next: View Results

After tests pass, view documentation:
- **README.md** — Full overview
- **STRETCH_FEATURES_IMPLEMENTATION.md** — Technical details
- **QUICKSTART_STRETCH_FEATURES.md** — More examples

---

**Ready to test? Start with Step 1 above!** ⬆️
