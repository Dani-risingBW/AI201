"""
agent.py

The FitFindr planning loop. Orchestrates the three tools in response to a
natural language user query, passing state between them via a session dict.
"""

import os
import json
from dotenv import load_dotenv
from groq import Groq

from tools import search_listings, suggest_outfit, create_fit_card, evaluate_price_fairness
from utils.data_loader import load_listings

load_dotenv()

# Helper to reuse your verified Groq Client initialization
def _get_agent_groq_client():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not set. Add it to a .env file.")
    return Groq(api_key=api_key)


# ── session state ─────────────────────────────────────────────────────────────

def _new_session(query: str, wardrobe: dict) -> dict:
    """
    Initialize and return a fresh session dict for one user interaction.
    """
    return {
        "query": query,               # original user query
        "parsed": {},                # extracted description / size / max_price
        "search_results": [],        # list of matching listing dicts
        "selected_item": None,       # top result, passed into suggest_outfit
        "wardrobe": wardrobe,        # user's wardrobe dict
        "price_context": None,       # dict returned by evaluate_price_fairness
        "outfit_suggestion": None,   # string returned by suggest_outfit
        "fit_card": None,            # string returned by create_fit_card
        "error": None,               # set if the interaction ended early
        "retry_notes": None,         # keeps track of relaxed criteria changes
    }


# ── planning loop ─────────────────────────────────────────────────────────────

def run_agent(query: str, wardrobe: dict) -> dict:
    """
    Main agent entry point. Runs the FitFindr planning loop for a single
    user interaction and returns the completed session dict.
    """
    # Step 1: Initialize the session
    session = _new_session(query, wardrobe)

    # Step 2: Parse the user's query using structured LLM entity extraction
    try:
        client = _get_agent_groq_client()
        system_prompt = (
            "You are an expert data parsing utility for a fashion app. Your job is to extract "
            "search keys from a natural language user query. You MUST respond with a raw JSON object "
            "containing exactly these three keys, and absolutely no additional conversational text:\n"
            "- 'description' (string, the clothing type/vibe/color keywords)\n"
            "- 'size' (string or null if not explicitly mentioned)\n"
            "- 'max_price' (float/number or null if not explicitly mentioned)\n\n"
            "Example query: 'vintage graphic tee under $30, size M'\n"
            "Output: {\"description\": \"vintage graphic tee\", \"size\": \"M\", \"max_price\": 30.0}"
        )
        
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ],
            temperature=0.0 # Force maximum consistency
        )
        
        # 1. Safely grab the content text, default to an empty dictionary string if None
        raw_content = response.choices[0].message.content
        content_text = raw_content.strip() if raw_content else "{}"
        
        # 2. Parse the verified text string
        parsed_data = json.loads(content_text)
        session["parsed"] = {
            "description": parsed_data.get("description", query),
            "size": parsed_data.get("size"),
            "max_price": parsed_data.get("max_price")
        }
    except Exception as e:
        # Fallback tracking if parser breaks: dump query directly into description
        session["parsed"] = {"description": query, "size": None, "max_price": None}

    # Pull variables out for the search phase loops
    desc = session["parsed"]["description"]
    size = session["parsed"]["size"]
    max_price = session["parsed"]["max_price"]

    # Step 3: Call search_listings() with the parsed parameters + 2x Fallback Retry Loop
    results = search_listings(description=desc, size=size, max_price=max_price)

    # Fallback Retry 1: Loosen size constraint if empty
    if not results and size is not None:
        session["retry_notes"] = "No matches found with your size constraint. Trying to loosen filters..."
        results = search_listings(description=desc, size=None, max_price=max_price)

    # Fallback Retry 2: Loosen price constraint if still empty
    if not results and max_price is not None:
        session["retry_notes"] = f"No matches under ${max_price}, but I adjusted filters to see what fits your budget..."
        results = search_listings(description=desc, size=None, max_price=None)

    # If completely empty after retries, trigger early failure exit branch
    if not results:
        session["error"] = (
            "I couldn't find any items matching your request in our database even after relaxing search criteria. "
            "💡 Try using broader keywords like 'tops', 'accessories', or styles like 'vintage' and 'grunge'."
        )
        return session # Early exit: Do NOT proceed to suggest_outfit unconditionally

    # Save search list matching happy path branches
    session["search_results"] = results

    # Step 4: Select the item to use (top result)
    session["selected_item"] = results[0]

    # Step 5: Call evaluate_price_fairness() — non-blocking per planning spec
    try:
        full_dataset = load_listings()
        price_result = evaluate_price_fairness(session["selected_item"], full_dataset)
        if price_result.get("status") == "error":
            session["price_context"] = {"evaluation_summary": "Price analysis unavailable for this item."}
        else:
            session["price_context"] = price_result
    except Exception:
        session["price_context"] = {"evaluation_summary": "Price analyzer encountered an unexpected error."}

    # Step 7: Call suggest_outfit() with the selected item and wardrobe
    # Check wardrobe status to evaluate early termination requirements
    wardrobe_items = wardrobe.get("items", []) if isinstance(wardrobe, dict) else []
    if not wardrobe_items:
        session["error"] = (
            "An outfit cannot be suggested because you have nothing in your wardrobe! "
            "Try adding a few basic pieces into your profile first so I can build a fit."
        )
        return session # Early exit: Block downstream generation tasks gracefully

    outfit_text = suggest_outfit(new_item=session["selected_item"], wardrobe=wardrobe)
    
    # Check for style mismatch strings or API errors returned from Tool 2
    if "System Error" in outfit_text or "Could not generate styling" in outfit_text:
        session["error"] = f"Outfit generation failed downstream: {outfit_text}"
        return session

    session["outfit_suggestion"] = outfit_text

    # Step 8: Call create_fit_card() with the outfit suggestion and selected item
    card_text = create_fit_card(outfit=session["outfit_suggestion"], new_item=session["selected_item"])
    session["fit_card"] = card_text

    # Step 9: Return the session dict
    return session


# ── CLI test ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe, get_empty_wardrobe

    print("=== Happy path: graphic tee ===\n")
    session = run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    )
    if session["error"]:
        print(f"Error: {session['error']}")
    else:
        if session.get("retry_notes"):
            print(f"⚠️ Note: {session['retry_notes']}")
        print(f"Found: {session['selected_item']['title']}")
        print(f"Price: ${session['selected_item']['price']}")
        print(f"\nOutfit:\n{session['outfit_suggestion']}")
        print(f"\nFit card:\n{session['fit_card']}")

    print("\n\n=== No-results path ===\n")
    session2 = run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    )
    print(f"Error message: {session2['error']}")

    print("\n\n=== Empty wardrobe branch ===\n")
    session3 = run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_empty_wardrobe(),
    )
    print(f"Error message: {session3['error']}")