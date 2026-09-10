# 🚀 ThreadScout AI — Quick Start Guide (With Stretch Features)

## ⚡ What Is This?

ThreadScout AI is a conversational fashion discovery agent that:
- 🔍 Searches secondhand listings intelligently
- 💰 Evaluates price fairness with market analysis
- 👗 Suggests complete outfit combinations
- 📱 Generates Instagram-ready captions
- **📈 [NEW] Tracks market trends & price momentum**
- **👤 [NEW] Remembers your style preferences**
- **🌟 [NEW] Surfaces trending styles in real-time**

---

## 🎯 What's New (Stretch Features)

### Tool 5: price_comparison_analyzer 📊
Market trend analysis with percentile ranking. Tells you if prices are rising/falling and where your item ranks (0–100 percentile).

### Tool 6: style_profile_manager 👤
Persistent user profiles. ThreadScout remembers your preferred styles, size range, budget, and favorite platforms across sessions.

### Tool 7: trend_radar 📈
Real-time trend detection. Surfaces trending hashtags (#VintageY2K, #NinetiestDenim) and keyword spikes (+45% cargo).

---

## 🏃 Quick Start (60 seconds)

### 1. Install Dependencies
```bash
pip install gradio groq python-dotenv
```

### 2. Set Up Environment
Create `.env` file:
```
GROQ_API_KEY=your_api_key_here
```

### 3. Run the App
```bash
python app.py
```

Open browser: **http://localhost:7860**

---

## 💬 Try These Queries

```
"vintage graphic tee under $30"
"90s leather jacket size M"
"Is $48 fair for vintage 501s?"
"black combat boots under $50"
"grunge outfit for fall"
```

---

## 🎨 What You'll See

### Chat (Left Column)
- Natural language conversation with ThreadScout
- Responds with findings, outfit ideas, recommendations

### Results Tabs (Right Column)
1. **🛍️ Item Details** — Title, price, platform, condition, tags
2. **💚 Valuation & Trends** — Deal fairness + price trend analysis ✨ NEW
3. **📱 Social Caption** — Copy/paste-ready Instagram post
4. **👗 Outfit** — Complete styling recommendations
5. **📈 What's Trending** — Trending items & hashtags ✨ NEW

---

## 🧪 Test Stretch Features

```bash
python test_stretch_features.py
```

Runs comprehensive tests for all 3 stretch tools + integration.

---

## 📁 File Overview

| File | Purpose |
|------|---------|
| `app.py` | Gradio UI (5 tabs, editorial aesthetic) |
| `agent.py` | Planning loop (12 steps: 4 core + 3 stretch + setup/return) |
| `tools.py` | All 7 tools (4 core + 3 stretch) |
| `planning.md` | Specs with stretch features documented |
| `STRETCH_FEATURES_GUIDE.md` | Detailed documentation |
| `IMPLEMENTATION_SUMMARY.md` | Complete architecture overview |
| `test_stretch_features.py` | Comprehensive test suite |

---

## 🔧 Architecture at a Glance

```
User Input
    ↓
Query Parser (LLM)
    ↓
Search (with 2x retry fallback)
    ↓
Price Fairness Eval
    ├→ Outfit Suggester
    │   ↓
    │   Caption Generator
    │
    └→ [STRETCH] price_comparison_analyzer
    ├→ [STRETCH] style_profile_manager
    └→ [STRETCH] trend_radar
    
    ↓
Combine All → Session Dict
    ↓
UI Displays (5 Tabs)
```

---

## 💡 Key Features

### Core (MVP)
✅ Smart search with intelligent retry  
✅ AI outfit suggestions  
✅ Social media captions  
✅ Price fairness evaluation  

### Stretch (NEW)
✅ Market trend analysis  
✅ Persistent user profiles  
✅ Trend detection & alerts  
✅ Extended 5-tab UI  
✅ Price percentile ranking  

---

## 🎨 Design

**Aesthetic:** Editorial Vintage Archive (premium lookbook vibe)

**Colors:**
- Parchment background (#FAF7F2)
- Deep forest buttons (#2D4A3E)
- Terracotta accents (#C86D51)
- Sage highlights (#E6F4EA)

**Typography:** Plus Jakarta Sans + JetBrains Mono

---

## ⚙️ Configuration

### Change Model
Edit `agent.py:93`, `tools.py:222`, `tools.py:304`:
```python
model="gpt-oss-120b"  # Currently set
```

### Adjust UI Colors
Edit `app.py:38–46`:
```python
COLORS = {
    "canvas_bg": "#FAF7F2",
    "card_white": "#FFFFFF",
    ...
}
```

### Enable User Profiles
Pass `user_id` to agent:
```python
from agent import run_agent
session = run_agent(
    query="vintage tee",
    wardrobe=wardrobe,
    user_id="nkiruka_ibe@howard.edu"  # Enables Tool 6
)
```

---

## 🛠️ Troubleshooting

### "GROQ_API_KEY not set"
→ Create `.env` file with your Groq API key

### "No listings found"
→ Try broader terms: "vintage", "tops", "accessories"

### Stretch features not showing
→ Check `data/user_profiles/` directory has write permissions

### Trends not appearing
→ They populate from the dataset; try queries with tags like "vintage", "grunge", "minimalist"

---

## 📊 Session Output

Every query returns a dict with:
```python
{
    "query": "...",
    "selected_item": {...},
    "price_context": {...},           # Tool 4
    "outfit_suggestion": "...",        # Tool 2
    "fit_card": "...",                 # Tool 3
    "price_comparison": {...},         # Tool 5 ← STRETCH
    "user_profile": {...},             # Tool 6 ← STRETCH
    "trending_context": {...},         # Tool 7 ← STRETCH
    "error": None
}
```

---

## 🚀 Deployment

### Local Development
```bash
python app.py
```

### Cloud (Hugging Face Spaces)
1. Push to GitHub
2. Create Hugging Face Space
3. Connect repo → auto-deploys
4. Share link

---

## 📚 Learn More

- **STRETCH_FEATURES_GUIDE.md** — Deep dive into each tool
- **IMPLEMENTATION_SUMMARY.md** — Complete architecture
- **planning.md** — Original specs + stretch additions
- **test_stretch_features.py** — Working code examples

---

## ✨ Example Interaction

**You:** "vintage band tee under $30, what's trending?"

**ThreadScout:**
- 🔍 Searches dataset
- 💰 Finds item at $22 (marked as "Steal" — 58% below market)
- 📈 Detects price trend: "↓ Falling" (percentile: 28th)
- 👗 Suggests: "Pair with wide-leg jeans + white platform boots"
- 📱 Generates: "just scored this faded band tee for $22...🖤"
- 🌟 Alerts: "Y2K is exploding! #VintageY2K trending +45%"
- 👤 Logs: Search added to your profile (6 total searches)

**Result:** 5 tabs with all data, ready to use!

---

## 🎯 Next Steps

1. ✅ Run the app locally
2. ✅ Try 3–4 queries
3. ✅ Check out all 5 tabs
4. ✅ Review `STRETCH_FEATURES_GUIDE.md` for deep dives
5. ✅ Run `test_stretch_features.py` to see tests
6. ✅ Deploy to production!

---

## 📞 Support

- Check `.env` file (API key required)
- Read error messages carefully
- Review `STRETCH_FEATURES_GUIDE.md` for detailed docs
- Run tests: `python test_stretch_features.py`

---

**ThreadScout AI is ready to help you discover your next vintage treasure! 🎉**
