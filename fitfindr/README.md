# FitFindr

A conversational AI agent that searches secondhand clothing listings, evaluates price fairness, suggests outfit combinations, and generates shareable social media captions — all from a single natural language query.

---

## Setup

```bash
pip install -r requirements.txt
```

Create a `.env` file in the project root with your Groq API key (free at [console.groq.com](https://console.groq.com)):

```
GROQ_API_KEY=your_key_here
```

Run the Gradio UI:

```bash
python app.py
```

Run the agent directly from the terminal:

```bash
python agent.py
```

---

## Tool Inventory

### Tool 1 — `search_listings`

**Purpose:** Searches the mock secondhand listings dataset for items that match a natural language description, filtered by size and price ceiling. Returns results sorted by relevance so the agent always picks the best match first.

**Inputs:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `description` | `str` | Keywords describing what the user wants (e.g., `"vintage graphic tee"`) |
| `size` | `str \| None` | Size string to filter by; case-insensitive partial match (e.g., `"M"` matches `"S/M"`). `None` skips size filtering. |
| `max_price` | `float \| None` | Inclusive price ceiling. `None` skips price filtering. |

**Output:** `list[dict]` — matching listing dicts sorted by relevance score (highest first). Empty list if nothing matches. Each dict contains: `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, `platform`.

**Scoring:** title match = +3 pts, style tag match = +2 pts, description match = +1 pt, color match = +1 pt. Listings with a score of 0 are dropped.

---

### Tool 2 — `suggest_outfit`

**Purpose:** Uses the Groq LLM to suggest 1–2 complete outfit combinations for a thrifted item. When the wardrobe has items, the LLM names specific pieces from the wardrobe. When the wardrobe is empty, the LLM pivots to general styling inspiration (what types of bottoms, shoes, and accessories would pair well, and what vibe the item suits).

**Inputs:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `new_item` | `dict` | The listing dict for the item the user is considering buying |
| `wardrobe` | `dict` | A wardrobe dict with an `"items"` key containing a list of wardrobe item dicts |

**Output:** `str` — a non-empty natural language outfit suggestion. Returns a `"System Error: ..."` string if the Groq client cannot be initialized; returns a `"Could not generate styling tips..."` string if the API call itself fails at runtime.

---

### Tool 3 — `create_fit_card`

**Purpose:** Generates a 2–4 sentence Instagram/TikTok-style caption for the thrifted find, written in a casual OOTD voice. Mentions the item name, price, and platform naturally. Uses a higher LLM temperature (0.9) so the output feels different each time.

**Inputs:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `outfit` | `str` | The outfit suggestion string returned by `suggest_outfit` |
| `new_item` | `dict` | The listing dict for the thrifted item |

**Output:** `str` — a ready-to-paste social media caption. Returns `"Error: Missing or incomplete outfit data..."` if `outfit` is empty or whitespace-only. Returns `"Error: Incomplete item data payload..."` if `new_item` is empty. If the LLM call fails at runtime, falls back to a local string template: `"Just picked up this [Item Title] for $[Price] to wear with my [Outfit]!"`.

---

### Tool 4 — `evaluate_price_fairness`

**Purpose:** Determines whether a target item is a steal, fair market value, or overpriced by comparing its price against similar listings in the dataset (same category and at least one shared style tag).

**Inputs:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `target_item` | `dict` | The listing dict for the item being evaluated |
| `mock_dataset` | `list` | The full list of listing dicts to compare against (loaded via `load_listings()`) |

**Output:** `dict` with four keys:

| Key | Type | Description |
|-----|------|-------------|
| `deal_rating` | `str` | `"Steal"`, `"Fair Market Value"`, or `"Overpriced"` |
| `market_average` | `float` | Average price of comparable listings |
| `price_difference` | `float` | Target price minus market average (negative = below average) |
| `evaluation_summary` | `str` | Human-readable sentence describing the result |

Returns `{"status": "error", "message": "..."}` if the target item's price field is missing or corrupt. If no comparable listings exist, defaults to `"Fair Market Value"` using the item's own price as the baseline and notes in the summary that it is a rare find.

**Rating thresholds:** Steal = more than 20% below average; Overpriced = more than 20% above average; Fair Market Value = within that range.

---

## Planning Loop

The agent runs in `agent.py` as a linear pipeline with branching error exits. All state is tracked in a single session dict. Here is the step-by-step logic:

**Step 1 — Parse the query.**
The LLM extracts three fields from the user's natural language input: `description`, `size`, and `max_price`. If parsing fails (API error or malformed JSON), the full raw query is used as the description and both filters are set to `None`.

**Step 2 — Search for listings (with 2-retry fallback).**
`search_listings` is called with the parsed parameters. If results come back empty and a size filter was active, the agent drops the size filter and retries. If still empty and a price filter was active, the agent drops the price filter and retries. If all three attempts return empty, the agent sets `session["error"]` with a message explaining what happened and what broader terms to try, then returns early without calling any downstream tools.

**Step 3 — Evaluate price fairness (non-blocking).**
`evaluate_price_fairness` is called with the top result and the full dataset. If it fails for any reason (missing price key, dataset error), the agent saves a fallback summary string to `session["price_context"]` and continues. This step never causes an early exit.

**Step 4 — Suggest an outfit.**
`suggest_outfit` is called with the selected item and the user's wardrobe. If the LLM client cannot be initialized, the returned error string triggers `session["error"]` and an early exit. On success, the suggestion is saved to `session["outfit_suggestion"]`.

**Step 5 — Generate the fit card.**
`create_fit_card` is called with the outfit suggestion and selected item. The result (including any programmatic fallback) is saved to `session["fit_card"]`.

**Step 6 — Return the session dict.**
`app.py` reads `session["error"]` first; if set, it displays the error in the first panel and leaves the other two empty. Otherwise it formats the item details, outfit suggestion, and fit card into the three output panels.

---

## State Management

All data produced during a session is stored in a single dict created by `_new_session()` at the start of each `run_agent()` call. The keys are pre-declared with `None` or empty defaults so downstream reads never raise `KeyError`.

```python
{
    "query":            str,     # original user input
    "parsed":           dict,    # extracted description / size / max_price
    "search_results":   list,    # all matching listings from search step
    "selected_item":    dict,    # top search result, passed to all later tools
    "wardrobe":         dict,    # user's wardrobe, passed to suggest_outfit
    "price_context":    dict,    # output of evaluate_price_fairness
    "outfit_suggestion": str,    # output of suggest_outfit
    "fit_card":         str,     # output of create_fit_card
    "error":            str,     # set on early exit; None on success
    "retry_notes":      str,     # describes any filter relaxations from retry loop
}
```

Each tool is called with values read directly from the session dict, and writes its output back into the session dict before the next step runs. The `error` key is the single early-exit signal — any step that encounters a unrecoverable failure sets it and the function returns the session immediately. `app.py` checks `session["error"]` before touching any other key.

---

## Error Handling

### `search_listings`
| Failure | Behavior |
|---------|----------|
| `load_listings()` raises an exception | `try/except` catches it and returns `[]` — tool never crashes the session |
| No results on initial query | Agent retries up to 2 times with progressively looser filters |
| No results after 2 retries | `session["error"]` is set; agent exits before calling any downstream tool |

**Concrete example from testing:**
Query `"designer ballgown size XXS under $5"` against the mock dataset returns `[]` on all three attempts. The agent set:
```
retry_notes: "No matches under $5.0, but I adjusted filters to see what fits your budget..."
error: "I couldn't find any items matching your request in our database even after relaxing
        search criteria. 💡 Try using broader keywords like 'tops', 'accessories', or styles
        like 'vintage' and 'grunge'."
```
The outfit and fit card steps were never reached.

---

### `evaluate_price_fairness`
| Failure | Behavior |
|---------|----------|
| Target item has no `price` key or non-numeric value | Returns `{"status": "error", "message": "..."}` |
| A dataset item has a corrupt price field | Returns `{"status": "error", "message": "..."}` identifying the bad item ID |
| No listings share the item's category and at least one style tag | Returns `deal_rating: "Fair Market Value"` at the item's own price |

This tool is **non-blocking** in the agent: any error response causes the agent to write a fallback summary to `session["price_context"]` and continue to the outfit step rather than exiting.

**Concrete example from testing (no-comparables path):**
Running `evaluate_price_fairness` on `lst_034` (Bucket Hat — `accessories`, tags `["90s", "streetwear", "accessories"]`) against the full 40-item dataset found no other accessories listings sharing those tags. The tool returned:
```python
{
    "deal_rating": "Fair Market Value",
    "market_average": 14.00,
    "price_difference": 0.0,
    "evaluation_summary": "At $14.00, Bucket Hat — Reversible, Brown Plaid is a rare find
                           with no comparable listings in the marketplace. Defaulting to
                           fair market value."
}
```

---

### `suggest_outfit`
| Failure | Behavior |
|---------|----------|
| Groq client cannot initialize (missing API key) | Returns `"System Error: Unable to access the style generator client. (...)"` |
| LLM API call raises an exception at runtime | Returns `"Could not generate styling tips due to an external network error: ..."` |
| Either error string detected by agent | Agent sets `session["error"]` and returns early |

**Concrete example from testing:**
Patching `_get_groq_client` to raise `Exception("Groq API rate limit exceeded")` in the test suite returned:
```
"System Error: Unable to access the style generator client. (Groq API rate limit exceeded)"
```
The agent caught this string, set `session["error"]`, and the fit card step was skipped entirely.

---

### `create_fit_card`
| Failure | Behavior |
|---------|----------|
| `outfit` is empty string or whitespace-only | Returns `"Error: Missing or incomplete outfit data. Cannot generate a fit card caption."` |
| `new_item` is an empty dict or not a dict | Returns `"Error: Incomplete item data payload. Cannot generate a fit card caption."` |
| LLM call raises any exception | Falls back to local template: `"Just picked up this [Item] for $[Price] to wear with my [Outfit]!"` |

This tool never causes an early exit in the agent — even the fallback string is a valid caption that gets shown to the user.

**Concrete example from testing:**
Patching `chat.completions.create` with `side_effect=RuntimeWarning("Groq Service Timeout")` on a call with `lst_033` (Vintage Band Tee, $19.00) produced:
```
"Just picked up this Vintage Band Tee — Faded Grey for $19.00 to wear with my
 Pair your Vintage Band Tee with your Baggy Black Jeans and Chunky Sneakers.!"
```

---

## Spec Reflection

### What changed from the plan and why

**`suggest_outfit` — empty wardrobe behavior**
The original `planning.md` spec said: *"If the wardrobe is empty, respond to the user telling them that an outfit cannot be suggested… to try adding more things into your wardrobe."* The implementation calls the LLM anyway and asks for general styling inspiration instead of stopping. This was kept deliberately — a user with an empty wardrobe still gets useful output (what types of bottoms, shoes, and accessories pair well with the item), which is better than a dead end. The planning spec was updated to match.

**`create_fit_card` — fallback string**
The initial implementation used the string `"thrifted this absolute gem of a {item_title}..."`. This was replaced to match the spec's exact template: `"Just picked up this [Item] for $[Price] to wear with my [Outfit]!"`. The original string was a stylistic riff that drifted away from the plan without adding functional value.

**`evaluate_price_fairness` — thresholds not defined in spec**
The planning spec described the three rating labels (Steal, Fair Market Value, Overpriced) but gave no numeric thresholds. The implementation uses ±20% of the market average as the boundary. This is a reasonable retail convention — a listing more than 20% below average is a genuine deal; more than 20% above starts to look overpriced relative to what else is available.

**`price_context` missing from session schema**
The `_new_session()` function and the planning loop were originally written without a `price_context` key. The `evaluate_price_fairness` tool existed in `tools.py` but was never called by the agent, so `session["price_context"]` was always `None`. This was caught by `verify_state.py` (Stage 2 assertion failure) and fixed by adding the key to `_new_session()` and wiring the tool call into the agent between item selection and outfit suggestion.

---

## AI Usage

### Instance 1 — Identifying and fixing two runtime bugs in `tools.py`

**What I gave the AI:** The full `tools.py` source and `tests/test_tools.py`. I asked it to fix all the problems.

**What it produced:** It identified two bugs:
1. In `search_listings`, the `colors` list comprehension used `tag` as the loop variable but referenced `col` in the expression body — a `NameError` that would crash on any listing that had a color field.
2. Inside `suggest_outfit`, a duplicate nested function definition (copied from the docstring template) was declared but never called, and left dead code in the middle of the outer function body.

**What I kept vs. overrode:** Both fixes were accepted as-is after reviewing the diffs. The `colors` fix was a clear typo. The nested function removal was a straightforward cleanup. No override was needed.

---

### Instance 2 — Resolving the `suggest_outfit` spec-vs-implementation conflict

**What I gave the AI:** The `planning.md` Tool 2 spec section (which said empty wardrobe → return an error and stop) and the actual `suggest_outfit` implementation (which called the LLM for general styling advice instead). I asked it to make the two consistent.

**What it produced:** The AI presented two options: (A) change the code to match the spec by returning an error message without calling the LLM, or (B) change the spec to match the code by describing the general-styling-advice path as the intended behavior. It noted that option A would break the existing test for empty wardrobe since the test asserted the LLM was called exactly once.

**What I overrode:** I chose option B — keep the implementation, update the spec. The LLM-calling behavior is more useful to the user than a dead end. The AI then updated both the Tool 2 failure mode paragraph and the Planning Loop Step 3 section in `planning.md` to reflect the actual behavior. The key edit I directed was ensuring the spec made clear that the LLM prompt *changes* for empty wardrobe (switches to general inspiration) rather than being skipped entirely.

---

## Project Structure

```
fitfindr/
├── data/
│   ├── listings.json           # 40 mock secondhand listings
│   └── wardrobe_schema.json    # Wardrobe format + example wardrobe
├── utils/
│   └── data_loader.py          # load_listings(), get_example_wardrobe(), etc.
├── tests/
│   ├── test_tools.py           # 15 unit tests covering all 4 tools
│   └── verify_state.py         # End-to-end state flow verification script
├── tools.py                    # The 4 tool functions
├── agent.py                    # Planning loop (run_agent)
├── app.py                      # Gradio UI
├── planning.md                 # Design spec and architecture diagram
└── .env                        # GROQ_API_KEY (not committed)
```

Run all unit tests:

```bash
python -m pytest tests/test_tools.py -v
```

Run the state verification script:

```bash
python -m tests.verify_state
```
