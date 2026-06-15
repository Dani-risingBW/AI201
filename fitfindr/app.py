"""
app.py

Gradio interface for FitFindr. The layout and wiring are already set up —
your job is to fill in handle_query() so it calls run_agent() and maps
the session results to the three output panels.
"""

import gradio as gr

from agent import run_agent
from utils.data_loader import get_example_wardrobe, get_empty_wardrobe


# ── query handler ─────────────────────────────────────────────────────────────

def handle_query(user_query: str, wardrobe_choice: str) -> tuple[str, str, str]:
    """
    Called by Gradio when the user submits a query.

    Args:
        user_query:     The text the user typed into the search box.
        wardrobe_choice: Either "Example wardrobe" or "Empty wardrobe (new user)".

    Returns:
        A tuple of three strings:
            (listing_text, outfit_suggestion, fit_card)
        Each string maps to one of the three output panels in the UI.
    """
    # 1. Guard against an empty query (return early with an error message)
    if not user_query or not user_query.strip():
        return "⚠️ Error: Please type a description, size, or budget limit to start searching!", "", ""

    # 2. Select the wardrobe based on wardrobe_choice
    if wardrobe_choice == "Empty wardrobe (new user)":
        selected_wardrobe = get_empty_wardrobe()
    else:
        selected_wardrobe = get_example_wardrobe()

    # 3. Call run_agent() with the query and selected wardrobe
    session = run_agent(query=user_query.strip(), wardrobe=selected_wardrobe)

    # 4. If session["error"] is set, return the error in the first panel and empty strings
    if session.get("error") is not None:
        return f"❌ Early Exit Notice:\n\n{session['error']}", "", ""

    # 5. Otherwise, format session["selected_item"] into a readable listing_text string
    item = session.get("selected_item", {})
    
    # Safely building a beautifully structured item description panel format
    title = item.get("title", "Unknown Item")
    price = item.get("price", 0.0)
    size = item.get("size", "N/A")
    cond = item.get("condition", "N/A")
    platform = item.get("platform", "Unknown")
    desc = item.get("description", "No description provided.")
    tags = ", ".join(item.get("style_tags", []))
    
    # Formulate a dynamic retry notice header if filters were relaxed during Step 1
    retry_header = ""
    if session.get("retry_notes"):
        retry_header = f"⚠️ Notice: {session['retry_notes']}\n{'─' * 40}\n\n"

    listing_text = (
        f"{retry_header}"
        f"🏷️ Title: {title}\n"
        f"💰 Price: ${price:.2f}\n"
        f"📏 Size: {size}\n"
        f"✨ Condition: {cond.capitalize()}\n"
        f"🌐 Sourced From: {platform.capitalize()}\n"
        f"🎨 Tags: {tags}\n\n"
        f"📝 Description:\n{desc}"
    )

    # Pull the saved strings out of session state memory for the remaining panels
    outfit_suggestion = session.get("outfit_suggestion", "No outfit generated.")
    fit_card = session.get("fit_card", "No caption generated.")

    return listing_text, outfit_suggestion, fit_card


# ── interface ─────────────────────────────────────────────────────────────────

EXAMPLE_QUERIES = [
    "vintage graphic tee under $30",
    "90s track jacket in size M",
    "flowy midi skirt under $40",
    "black combat boots size 8",
    "designer ballgown size XXS under $5",   # deliberate no-results test
]

def build_interface():
    with gr.Blocks(title="FitFindr") as demo:
        gr.Markdown("""
# FitFindr 🛍️
Find secondhand pieces and get outfit ideas based on your wardrobe.
Describe what you're looking for — include size and price if you want to filter.
        """)

        with gr.Row():
            query_input = gr.Textbox(
                label="What are you looking for?",
                placeholder="e.g. vintage graphic tee under $30, size M",
                lines=2,
                scale=3,
            )
            wardrobe_choice = gr.Radio(
                choices=["Example wardrobe", "Empty wardrobe (new user)"],
                value="Example wardrobe",
                label="Wardrobe",
                scale=1,
            )

        submit_btn = gr.Button("Find it", variant="primary")

        with gr.Row():
            listing_output = gr.Textbox(
                label="🛍️ Top listing found",
                lines=8,
                interactive=False,
            )
            outfit_output = gr.Textbox(
                label="👗 Outfit idea",
                lines=8,
                interactive=False,
            )
            fitcard_output = gr.Textbox(
                label="✨ Your fit card",
                lines=8,
                interactive=False,
            )

        gr.Examples(
            examples=[[q, "Example wardrobe"] for q in EXAMPLE_QUERIES],
            inputs=[query_input, wardrobe_choice],
            label="Try these queries",
        )

        submit_btn.click(
            fn=handle_query,
            inputs=[query_input, wardrobe_choice],
            outputs=[listing_output, outfit_output, fitcard_output],
        )
        query_input.submit(
            fn=handle_query,
            inputs=[query_input, wardrobe_choice],
            outputs=[listing_output, outfit_output, fitcard_output],
        )

    return demo


if __name__ == "__main__":
    demo = build_interface()
    demo.launch()