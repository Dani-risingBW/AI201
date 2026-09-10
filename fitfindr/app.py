"""
app.py – ThreadScout AI

Premium Gradio interface integrating with agent.py backend.
Conversational two-column layout with Editorial Archive aesthetic.
Optimized space usage with compact, readable design.
"""

import gradio as gr
import random

from agent import run_agent
from utils.data_loader import get_example_wardrobe, get_empty_wardrobe


# ── State & Configuration ──────────────────────────────────────────────────────

HASHTAGS = [
    "#VintageVibes",
    "#SecondhandStyle",
    "#SustainableFashion",
    "#ThriftedTreasure",
    "#VintageAesthetic",
    "#EcoChic",
    "#ArchiveFashion",
    "#ThriftFlip",
]

EXAMPLE_QUERIES = [
    "vintage graphic tee under $30",
    "90s track jacket in size M",
    "flowy midi skirt under $40",
    "black combat boots size 8",
    "designer ballgown size XXS under $5",
]

# Editorial Archive Color Palette
COLORS = {
    "canvas_bg": "#FAF7F2",      # Parchment
    "card_white": "#FFFFFF",     # Pure White
    "primary_action": "#2D4A3E", # Deep Forest
    "terracotta": "#C86D51",     # Terracotta
    "sage": "#E6F4EA",           # Sage Mint
    "sage_text": "#137333",      # Sage Text
    "text_primary": "#1F1E1D",   # Ink Black
}


# ── Formatting & Utilities ─────────────────────────────────────────────────────

def build_valuation_html(session: dict) -> str:
    """
    Build styled HTML card for price valuation using session price_context
    + enhanced price_comparison data from stretch feature.
    Optimized for space with compact layout.
    """
    item = session.get("selected_item", {})
    price_context = session.get("price_context", {})
    price_comparison = session.get("price_comparison", {})

    price = item.get("price", 0.0)
    fair_market_value = price_context.get("estimated_fair_market_value", price * 1.5)
    savings = fair_market_value - price
    savings_pct = (savings / fair_market_value * 100) if fair_market_value > 0 else 0

    deal_quality = "🟢 Exceptional" if savings_pct > 40 else (
        "🟡 Good Deal" if savings_pct > 20 else "🟠 Fair Price"
    )

    confidence_score = price_context.get("confidence_score", 0.75)
    confidence_pct = int(confidence_score * 100)

    evaluation = price_context.get("evaluation_summary", "Analysis complete")

    # STRETCH: Add trend and percentile info from price_comparison_analyzer
    price_trend = price_comparison.get("price_trend", "→ Stable")
    percentile = price_comparison.get("percentile_rank", "N/A")
    recommendations = price_comparison.get("recommendations", "")

    # Item details
    title = item.get("title", "Unknown Item")
    platform = item.get("platform", "Unknown")
    condition = item.get("condition", "Unknown")
    size = item.get("size", "N/A")

    html = f"""
    <div style="background: {COLORS['card_white']}; border: 1px solid #E0D9CE; border-radius: 6px; padding: 16px; font-family: 'Plus Jakarta Sans', sans-serif;">
        <div style="margin-bottom: 12px;">
            <h4 style="margin: 0 0 6px 0; color: {COLORS['text_primary']}; font-size: 0.95em; font-weight: 700;">💎 {title}</h4>
            <div style="font-size: 0.8em; color: #666;">
                <span>{platform}</span> • <span>{condition}</span> • <span>Size: {size}</span>
            </div>
        </div>

        <div style="background: {COLORS['canvas_bg']}; padding: 10px; border-radius: 4px; margin-bottom: 10px;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 6px; font-size: 0.9em;">
                <span style="color: #666;">Your Price</span>
                <span style="font-family: 'JetBrains Mono', monospace; font-weight: 700; color: {COLORS['text_primary']};\">${price:.2f}</span>
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 6px; font-size: 0.9em;">
                <span style="color: #666;">Fair Market Value</span>
                <span style="font-family: 'JetBrains Mono', monospace; font-weight: 600; color: #888;">${fair_market_value:.2f}</span>
            </div>
            <div style="display: flex; justify-content: space-between; padding-top: 6px; border-top: 1px solid #D9D3CB; font-size: 0.9em;">
                <span style="color: {COLORS['sage_text']}; font-weight: 600;">✓ You Saved</span>
                <span style="font-family: 'JetBrains Mono', monospace; font-weight: 700; color: {COLORS['sage_text']};\">${savings:.2f}</span>
            </div>
        </div>

        <div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 10px; background: {COLORS['sage']}; border-radius: 4px; margin-bottom: 10px; font-size: 0.85em;">
            <span style="color: {COLORS['sage_text']}; font-weight: 700;">{deal_quality}</span>
            <span style="font-family: 'JetBrains Mono', monospace; color: {COLORS['sage_text']}; font-weight: 700;">Deal: {confidence_pct}%</span>
        </div>

        <div style="font-size: 0.8em; color: #666; line-height: 1.4; border-top: 1px solid #E0D9CE; padding-top: 10px;">
            <p style="margin: 0;">{evaluation}</p>
        </div>

        {'<div style="margin-top: 10px; padding-top: 10px; border-top: 1px solid #E0D9CE;"><div style="font-size: 0.75em; color: #999; font-weight: 600; margin-bottom: 6px;">📊 PRICE TRENDS (STRETCH)</div><div style="display: flex; justify-content: space-between; font-size: 0.8em; margin-bottom: 4px;"><span>Trend:</span><span style="font-weight: 700; color: ' + COLORS['terracotta'] + ';">' + price_trend + '</span></div><div style="display: flex; justify-content: space-between; font-size: 0.8em;"><span>Percentile:</span><span style="font-weight: 700;">' + str(percentile) + 'th</span></div><p style="margin: 6px 0 0 0; font-size: 0.75em; line-height: 1.3; color: #666;">' + recommendations + '</p></div>' if price_comparison else ''}
    </div>
    """
    return html


def build_item_details_html(session: dict) -> str:
    """Build detailed item card with all metadata."""
    item = session.get("selected_item", {})
    title = item.get("title", "Unknown Item")
    price = item.get("price", 0.0)
    size = item.get("size", "N/A")
    condition = item.get("condition", "Unknown")
    platform = item.get("platform", "Unknown")
    desc = item.get("description", "No description provided.")
    tags = ", ".join(item.get("style_tags", []))

    retry_header = ""
    if session.get("retry_notes"):
        retry_header = f'<div style="background: #FEF3E6; border-left: 3px solid {COLORS["terracotta"]}; padding: 8px 12px; margin-bottom: 10px; border-radius: 3px; font-size: 0.85em; color: #666;">⚠️ {session["retry_notes"]}</div>'

    html = f"""
    <div style="background: {COLORS['card_white']}; border: 1px solid #E0D9CE; border-radius: 6px; padding: 14px; font-family: 'Plus Jakarta Sans', sans-serif;">
        {retry_header}

        <div style="margin-bottom: 10px;">
            <h4 style="margin: 0 0 8px 0; color: {COLORS['text_primary']}; font-size: 1em; font-weight: 700;">🛍️ {title}</h4>

            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 10px;">
                <div style="background: {COLORS['canvas_bg']}; padding: 8px; border-radius: 4px;">
                    <div style="font-size: 0.75em; color: #999; font-weight: 600;">PRICE</div>
                    <div style="font-family: 'JetBrains Mono', monospace; font-size: 1.2em; font-weight: 700; color: {COLORS['primary_action']};\">${price:.2f}</div>
                </div>
                <div style="background: {COLORS['canvas_bg']}; padding: 8px; border-radius: 4px;">
                    <div style="font-size: 0.75em; color: #999; font-weight: 600;">SIZE</div>
                    <div style="font-family: 'JetBrains Mono', monospace; font-size: 1.2em; font-weight: 700; color: {COLORS['primary_action']};\"{size}</div>
                </div>
            </div>

            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 10px; font-size: 0.9em;">
                <div>
                    <span style="color: #999; font-weight: 600;">Condition</span><br/>
                    <span style="color: {COLORS['text_primary']}; font-weight: 600;">{condition.capitalize()}</span>
                </div>
                <div>
                    <span style="color: #999; font-weight: 600;">Platform</span><br/>
                    <span style="color: {COLORS['text_primary']}; font-weight: 600;">{platform.capitalize()}</span>
                </div>
            </div>

            {f'<div style="margin-bottom: 10px;"><span style="color: #999; font-weight: 600; font-size: 0.85em;">TAGS</span><br/><div style="font-size: 0.85em; color: {COLORS["text_primary"]}; margin-top: 4px;">{tags}</div></div>' if tags else ''}

            <div style="background: {COLORS['canvas_bg']}; padding: 10px; border-radius: 4px; font-size: 0.85em;">
                <span style="color: #999; font-weight: 600;">DESCRIPTION</span>
                <p style="margin: 6px 0 0 0; color: {COLORS['text_primary']}; line-height: 1.4;">{desc}</p>
            </div>
        </div>
    </div>
    """
    return html


def build_trends_html(session: dict) -> str:
    """Build HTML card showing trending items and style alerts (STRETCH)."""
    trending_context = session.get("trending_context", {})

    if not trending_context:
        return f"""
        <div style="text-align: center; padding: 20px; color: #999; background: {COLORS['canvas_bg']}; border: 1px dashed #E0D9CE; border-radius: 6px;">
            <p style="margin: 0; font-size: 0.95em;">Trend data unavailable</p>
        </div>
        """

    alert = trending_context.get("trending_alert", "")
    hashtags = trending_context.get("trending_hashtags", [])
    spikes = trending_context.get("search_spike", {})

    hashtags_str = " ".join(hashtags[:5]) if hashtags else "No trend data"
    spikes_str = ", ".join([f"{k} {v}" for k, v in list(spikes.items())[:3]]) if spikes else "N/A"

    html = f"""
    <div style="background: {COLORS['card_white']}; border: 1px solid #E0D9CE; border-radius: 6px; padding: 14px; font-family: 'Plus Jakarta Sans', sans-serif;">
        <div style="margin-bottom: 10px;">
            <h4 style="margin: 0 0 8px 0; color: {COLORS['text_primary']}; font-size: 1em; font-weight: 700;">📈 Trending Now</h4>
            <p style="margin: 0; font-size: 0.85em; line-height: 1.4; color: {COLORS['text_primary']};">{alert}</p>
        </div>

        <div style="background: {COLORS['canvas_bg']}; padding: 10px; border-radius: 4px; margin-bottom: 10px;">
            <div style="font-size: 0.75em; color: #999; font-weight: 600; margin-bottom: 6px;">TOP HASHTAGS</div>
            <div style="font-size: 0.8em; color: {COLORS['text_primary']}; line-height: 1.4;">
                {hashtags_str}
            </div>
        </div>

        <div style="background: {COLORS['canvas_bg']}; padding: 10px; border-radius: 4px;">
            <div style="font-size: 0.75em; color: #999; font-weight: 600; margin-bottom: 6px;">🔥 KEYWORD SPIKES</div>
            <div style="font-size: 0.8em; color: {COLORS['text_primary']};">
                {spikes_str}
            </div>
        </div>
    </div>
    """
    return html


def generate_social_caption(session: dict) -> str:
    """Generate Instagram-ready caption from session data."""
    item = session.get("selected_item", {})
    fit_card = session.get("fit_card", "")

    title = item.get("title", "Vintage Find")
    price = item.get("price", 0.0)
    platform = item.get("platform", "Secondhand")

    hashtag_selection = " ".join(random.sample(HASHTAGS, 4))

    caption = f"""✦ Archival Find ✦

Just scored this editorial piece:
{title} | ${price:.2f}

Sourced from {platform}

{fit_card}

{hashtag_selection}

#ThreadScout"""

    return caption


def handle_query(user_query: str, wardrobe_choice: str, chat_history: list) -> tuple[list, str, str, str, str, str]:
    """
    Main query handler integrating with agent.py backend (core + stretch features).

    Returns:
        (updated_chat_history, item_details_html, valuation_html, social_caption, outfit_suggestion, trends_html)
    """
    if not user_query or not user_query.strip():
        error_msg = "⚠️ Please describe what you're looking for (style, size, budget)."
        chat_history.append({"role": "user", "content": user_query})
        chat_history.append({"role": "assistant", "content": error_msg})
        return chat_history, "", "", "", "", ""

    # Select wardrobe
    selected_wardrobe = (
        get_empty_wardrobe()
        if wardrobe_choice == "Empty wardrobe (new user)"
        else get_example_wardrobe()
    )

    # Call agent backend with stretch features enabled
    session = run_agent(query=user_query.strip(), wardrobe=selected_wardrobe)

    # Build assistant response message
    if session.get("error"):
        assistant_message = f"❌ {session['error']}"
    else:
        item = session.get("selected_item", {})
        title = item.get("title", "Unknown Item")
        price = item.get("price", 0.0)
        assistant_message = f"✦ Found: **{title}** at **${price:.2f}**\n\nCheck the details and valuation on the right."

    # Update chat history
    chat_history.append({"role": "user", "content": user_query})
    chat_history.append({"role": "assistant", "content": assistant_message})

    # Build outputs only if successful
    if session.get("error"):
        return chat_history, "", "", "", "", ""

    item_details_html = build_item_details_html(session)
    valuation_html = build_valuation_html(session)
    social_caption = generate_social_caption(session)
    outfit_suggestion = session.get("outfit_suggestion", "No outfit generated.")
    trends_html = build_trends_html(session)  # STRETCH: trends

    return chat_history, item_details_html, valuation_html, social_caption, outfit_suggestion, trends_html


# ── Interface ──────────────────────────────────────────────────────────────────

CUSTOM_CSS = f"""
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap');

* {{
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    box-sizing: border-box;
}}

body {{
    background-color: {COLORS['canvas_bg']} !important;
    margin: 0 !important;
    padding: 0 !important;
}}

.gradio-container {{
    max-width: 100% !important;
    margin: 0 !important;
    padding: 0 !important;
    background-color: {COLORS['canvas_bg']} !important;
}}

.gradio-page {{
    gap: 0 !important;
}}

/* Spacing optimizations */
.block {{
    padding: 0 !important;
    margin: 0 !important;
}}

.group {{
    padding: 0 !important;
    margin: 0 !important;
    border: none !important;
}}

/* Header styling */
h1, h2, h3 {{
    color: {COLORS['text_primary']} !important;
    font-weight: 700 !important;
    margin: 0 !important;
}}

h2 {{
    font-size: 1.3em !important;
    margin-bottom: 12px !important;
}}

/* Primary Button */
.primary {{
    background-color: {COLORS['primary_action']} !important;
    border: none !important;
    color: white !important;
    font-weight: 600 !important;
    padding: 10px 20px !important;
    border-radius: 4px !important;
    height: auto !important;
}}

.primary:hover {{
    background: linear-gradient(135deg, {COLORS['primary_action']}, #1E332B) !important;
    box-shadow: 0 2px 8px rgba(45, 74, 62, 0.2) !important;
}}

/* Textbox styling */
.textbox input,
.textbox textarea,
textarea,
input[type="text"] {{
    background-color: {COLORS['card_white']} !important;
    border: 1px solid #E0D9CE !important;
    border-radius: 4px !important;
    color: {COLORS['text_primary']} !important;
    font-size: 0.95em !important;
    padding: 10px !important;
}}

.textbox input:focus,
textarea:focus,
input[type="text"]:focus {{
    border-color: {COLORS['primary_action']} !important;
    box-shadow: 0 0 0 2px {COLORS['canvas_bg']}, 0 0 0 4px {COLORS['primary_action']} !important;
}}

/* Chatbot */
.chatbot {{
    background-color: {COLORS['card_white']} !important;
    border: 1px solid #E0D9CE !important;
    border-radius: 6px !important;
    padding: 12px !important;
}}

.message {{
    border-radius: 4px !important;
    margin: 6px 0 !important;
    padding: 10px !important;
}}

.message.user {{
    background: #F5F1EA !important;
    color: {COLORS['text_primary']} !important;
}}

.message.assistant {{
    background: {COLORS['sage']} !important;
    color: {COLORS['sage_text']} !important;
}}

/* Label styling */
.label {{
    color: {COLORS['text_primary']} !important;
    font-weight: 600 !important;
    font-size: 0.9em !important;
    margin-bottom: 6px !important;
}}

.info {{
    font-size: 0.8em !important;
    color: #999 !important;
    margin-top: 4px !important;
}}

/* Radio buttons */
.radio-group {{
    gap: 12px !important;
}}

.radio-label {{
    font-size: 0.95em !important;
}}

/* Scrollbar */
::-webkit-scrollbar {{
    width: 6px;
    height: 6px;
}}

::-webkit-scrollbar-track {{
    background: {COLORS['canvas_bg']};
}}

::-webkit-scrollbar-thumb {{
    background: #D9D3CB;
    border-radius: 3px;
}}

::-webkit-scrollbar-thumb:hover {{
    background: #B8AFA0;
}}

/* Reduce white space in rows/columns */
.row {{
    gap: 12px !important;
    margin: 0 !important;
    padding: 0 !important;
}}

.column {{
    padding: 0 12px !important;
    gap: 12px !important;
}}

.column:first-child {{
    padding-left: 16px !important;
}}

.column:last-child {{
    padding-right: 16px !important;
}}

/* Markdown */
.markdown {{
    color: {COLORS['text_primary']} !important;
}}

/* Accent colors for emphasis */
.accent-primary {{
    color: {COLORS['primary_action']} !important;
}}

.accent-terracotta {{
    color: {COLORS['terracotta']} !important;
}}

.accent-sage {{
    color: {COLORS['sage_text']} !important;
}}
"""


def build_interface():
    with gr.Blocks(title="ThreadScout AI", css=CUSTOM_CSS, fill_height=True) as demo:

        # ────────────────────────────────────────────────────────────────────────
        # HEADER (Compact)
        # ────────────────────────────────────────────────────────────────────────
        gr.HTML(
            f"""
            <div style="background: {COLORS['card_white']}; border-bottom: 2px solid {COLORS['terracotta']}; padding: 16px; margin: 0;">
                <h1 style="margin: 0; font-size: 2em; color: {COLORS['text_primary']}; font-weight: 700; letter-spacing: -0.5px;">
                    ✦ ThreadScout AI
                </h1>
                <p style="margin: 6px 0 0 0; color: #666; font-size: 0.95em; font-weight: 400;">
                    Discover vintage. Evaluate fairness. Curate fits. Generate captions.
                </p>
            </div>
            """
        )

        # ────────────────────────────────────────────────────────────────────────
        # TWO-COLUMN LAYOUT (Optimized Space)
        # ────────────────────────────────────────────────────────────────────────
        with gr.Row(equal_height=False):

            # LEFT COLUMN: Conversational Search (~40%)
            with gr.Column(scale=40, min_width=450):
                gr.Markdown("### 🎯 Conversational Search")

                # Chat history
                chatbot = gr.Chatbot(
                    height=480,
                    label="ThreadScout Concierge",
                    show_label=True,
                )

                # Input row - Compact
                with gr.Row():
                    query_input = gr.Textbox(
                        placeholder="Describe your search...",
                        show_label=False,
                        scale=5,
                        lines=1,
                    )
                    submit_btn = gr.Button("Hunt ✦", variant="primary", scale=1)

                # Wardrobe selection - More compact
                wardrobe_choice = gr.Radio(
                    choices=["Example wardrobe", "Empty wardrobe (new user)"],
                    value="Example wardrobe",
                    label="Wardrobe",
                    info="Select your collection",
                    scale=2,
                )

                # Quick starts - Compact
                gr.Examples(
                    examples=[[q] for q in EXAMPLE_QUERIES],
                    inputs=[query_input],
                    label="📌 Quick Starts",
                    run_on_click=False,
                )

            # RIGHT COLUMN: Results (~60%)
            with gr.Column(scale=60, min_width=550):
                gr.Markdown("### 📊 Results & Deliverables")

                # Five result sections in tabs for compact space usage
                with gr.Tabs():

                    # TAB 1: Item Details
                    with gr.Tab(label="🛍️ Item Details"):
                        item_details_output = gr.HTML(
                            value=f"""
                            <div style="text-align: center; padding: 30px; color: #999; background: {COLORS['canvas_bg']}; border: 1px dashed #E0D9CE; border-radius: 6px;">
                                <p style="margin: 0; font-size: 0.95em;">Submit a query to see item details</p>
                            </div>
                            """,
                        )

                    # TAB 2: Valuation (with price trends from stretch feature)
                    with gr.Tab(label="💚 Valuation & Trends"):
                        valuation_output = gr.HTML(
                            value=f"""
                            <div style="text-align: center; padding: 30px; color: #999; background: {COLORS['canvas_bg']}; border: 1px dashed #E0D9CE; border-radius: 6px;">
                                <p style="margin: 0; font-size: 0.95em;">Submit a query to see price analysis + market trends</p>
                            </div>
                            """,
                        )

                    # TAB 3: Social Caption
                    with gr.Tab(label="📱 Social Caption"):
                        social_output = gr.Textbox(
                            lines=8,
                            interactive=False,
                            placeholder="Your ready-to-post caption will appear here...",
                            show_label=False,
                        )

                    # TAB 4: Outfit Suggestion
                    with gr.Tab(label="👗 Outfit"):
                        outfit_output = gr.Textbox(
                            lines=8,
                            interactive=False,
                            placeholder="Your outfit suggestion will appear here...",
                            show_label=False,
                        )

                    # TAB 5: Trending Styles (STRETCH FEATURE)
                    with gr.Tab(label="📈 What's Trending"):
                        trends_output = gr.HTML(
                            value=f"""
                            <div style="text-align: center; padding: 30px; color: #999; background: {COLORS['canvas_bg']}; border: 1px dashed #E0D9CE; border-radius: 6px;">
                                <p style="margin: 0; font-size: 0.95em;">Trending styles & hashtags will appear here</p>
                            </div>
                            """,
                        )

        # ────────────────────────────────────────────────────────────────────────
        # EVENT HANDLERS
        # ────────────────────────────────────────────────────────────────────────
        submit_btn.click(
            fn=handle_query,
            inputs=[query_input, wardrobe_choice, chatbot],
            outputs=[chatbot, item_details_output, valuation_output, social_output, outfit_output, trends_output],
        ).then(fn=lambda: "", outputs=query_input)

        query_input.submit(
            fn=handle_query,
            inputs=[query_input, wardrobe_choice, chatbot],
            outputs=[chatbot, item_details_output, valuation_output, social_output, outfit_output, trends_output],
        ).then(fn=lambda: "", outputs=query_input)

    return demo


if __name__ == "__main__":
    demo = build_interface()
    demo.launch()
