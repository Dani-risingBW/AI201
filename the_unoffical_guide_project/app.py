"""Milestone 5 — Grounded generation + Gradio interface for The Unofficial Guide.

Architecture (from planning.md):
    User question
      -> retrieve() top-K chunks (vector_store.py, cosine, all-MiniLM-L6-v2)
      -> Context Assembler (numbered, source-tagged segments)
      -> Groq openai/gpt-oss-120b (grounded generation)
      -> {answer, deduplicated sources}

Grounding guarantees:
  * The model is instructed to answer ONLY from the retrieved context.
  * If the context lacks the answer, it returns the exact REFUSAL sentence.
  * Source attribution is computed programmatically from the retrieved chunks
    (not parsed out of the model's text), so it cannot be hallucinated.
"""

import os

from dotenv import load_dotenv
from groq import Groq
import gradio as gr

from vector_store import retrieve, TOP_K

load_dotenv()

# ==========================================
# CONFIGURATION
# ==========================================
GROQ_MODEL = "openai/gpt-oss-120b"
REFUSAL = "I'm sorry, but I cannot find that information in the provided source documents."

SYSTEM_PROMPT = (
    "You are 'The Unofficial Guide' to Howard University administration, helping "
    "students navigate financial aid, registration, and campus offices.\n"
    "Rules you must follow strictly:\n"
    "1. Answer ONLY using the numbered context segments provided by the user. "
    "Do not use any outside or prior knowledge.\n"
    "2. If the context segments contain information relevant to the question, "
    "use it to answer — summarize and combine across segments as needed, even if "
    "the information is partial or informal (e.g. a student video transcript).\n"
    "3. ONLY if none of the segments are relevant to the question, reply with "
    f"EXACTLY this sentence and nothing else: \"{REFUSAL}\"\n"
    "4. Be concise, practical, and student-friendly. When the context contains "
    "specific contacts, steps, links, or email templates, surface them.\n"
    "5. Do not invent names, offices, phone numbers, or policies that are not in "
    "the context."
)


def _get_client() -> Groq:
    """Lazily build the Groq client so importing this module never crashes when
    the key is absent (the UI surfaces a friendly error instead)."""
    key = os.getenv("GROQ_API_KEY")
    if not key or key == "your_key_here":
        raise RuntimeError(
            "GROQ_API_KEY is not set. Copy .env.example to .env and add your "
            "free key from https://console.groq.com"
        )
    return Groq(api_key=key)


def _format_context(hits) -> str:
    """Assemble retrieved chunks into numbered, source-tagged segments."""
    blocks = []
    for h in hits:
        blocks.append(f"[Segment {h['rank']} | source: {h['source_origin']}]\n{h['text']}")
    return "\n\n".join(blocks)


def _dedup_sources(hits) -> list:
    """Programmatic, deduplicated source attribution: one entry per source,
    keeping its best (highest) similarity. Order preserved by first appearance."""
    best = {}
    order = []
    for h in hits:
        src = h["source_origin"]
        if src not in best:
            best[src] = h["similarity"]
            order.append(src)
        else:
            best[src] = max(best[src], h["similarity"])
    return [{"source": s, "top_similarity": best[s]} for s in order]


def answer_question(query: str, k: int = TOP_K) -> dict:
    """Retrieve, ground, and generate. Returns {"answer": str, "sources": list}."""
    query = (query or "").strip()
    if not query:
        return {"answer": "Please enter a question.", "sources": []}

    hits = retrieve(query, k=k)
    if not hits:
        return {"answer": REFUSAL, "sources": []}

    user_msg = (
        f"Context segments:\n\n{_format_context(hits)}\n\n"
        f"Question: {query}"
    )

    try:
        client = _get_client()
        resp = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.2,
        )
        answer = resp.choices[0].message.content.strip()
    except Exception as e:
        return {"answer": f"[Generation error] {e}", "sources": []}

    # If the model refused, do not attribute any sources.
    sources = [] if answer == REFUSAL else _dedup_sources(hits)
    return {"answer": answer, "sources": sources}


# ==========================================
# GRADIO INTERFACE
# ==========================================
def _ui_handler(query: str):
    result = answer_question(query)
    return result["answer"], result["sources"]


with gr.Blocks(title="The Unofficial Guide — Howard University") as demo:
    gr.Markdown(
        "# 🦬 The Unofficial Guide to Howard University\n"
        "Ask about financial aid, registration, campus offices, or professors. "
        "Answers come **only** from the ingested source documents."
    )
    query_input = gr.Textbox(
        label="Ask a question",
        placeholder="e.g. How do I clear a financial hold on Workday?",
        lines=2,
    )
    submit_btn = gr.Button("Submit", variant="primary")
    answer_output = gr.Textbox(label="Answer", lines=6)
    sources_output = gr.JSON(label="Sources Used (deduplicated)")

    submit_btn.click(_ui_handler, inputs=query_input, outputs=[answer_output, sources_output])
    query_input.submit(_ui_handler, inputs=query_input, outputs=[answer_output, sources_output])

    gr.Examples(
        examples=[
            "What is the best way to contact financial aid as a first-year student?",
            "Tell me more about the Howard University financial aid crisis.",
            "How do I clear a financial hold on Workday?",
            "Which professors do students rate highly?",
        ],
        inputs=query_input,
    )


if __name__ == "__main__":
    demo.launch()
