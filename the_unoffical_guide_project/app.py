"""Milestone 5 — Grounded generation + Conversational Gradio interface for The Unofficial Guide.

Architecture:
    User question + Chat History
      -> Standalone Query Rewriter (Groq LLM)
      -> retrieve() top-K chunks with rewritten query (vector_store.py)
      -> Context Assembler (numbered, source-tagged segments)
      -> Groq grounded generation with sliding history
      -> Streamed/Returned to Gradio Chatbot with deduplicated sources
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
MAX_HISTORY_TURNS = 5  # Sliding window: keeps the last 5 turns (10 messages: user + assistant)

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

REPHRASE_SYSTEM_PROMPT = (
    "Given the conversation history and the latest user question, rephrase the "
    "question into a standalone search query that can be understood without the history. "
    "Resolve all pronouns (e.g. 'they', 'it', 'that office') to their actual entities. "
    "Do NOT answer the question. Return ONLY the standalone question."
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


def _rephrase_query(client: Groq, query: str, history: list[dict]) -> str:
    """Uses chat history to reformulate pronoun-heavy follow-ups into standalone queries."""
    if not history:
        return query

    # Gradio history is already formatted as [{'role': '...', 'content': '...'}, ...]
    # Slice the last turns for sliding window (each turn = 2 messages: user + assistant)
    sliding_history = history[-(MAX_HISTORY_TURNS * 2):]

    messages = [{"role": "system", "content": REPHRASE_SYSTEM_PROMPT}]
    messages.extend(sliding_history)
    messages.append({"role": "user", "content": query})

    try:
        resp = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            temperature=0.0,
        )
        standalone = resp.choices[0].message.content.strip()
        return standalone or query
    except Exception as e:
        print(f"[Query Rephrase Error]: {e}")
        return query


def _format_context(hits: list[dict]) -> str:
    """Assemble retrieved chunks into numbered, source-tagged segments."""
    blocks = []
    for h in hits:
        blocks.append(f"[Segment {h['rank']} | source: {h['source_origin']}]\n{h['text']}")
    return "\n\n".join(blocks)


def _dedup_sources(hits: list[dict]) -> list[dict]:
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


def chat_turn(query: str, history: list[dict], k: int = TOP_K) -> tuple[list[dict], list[dict]]:
    """Conversational RAG turn: rewrites query, retrieves, maintains window, and generates answer.
    
    Returns:
        (updated_history, deduplicated_sources)
    """
    query = (query or "").strip()
    history = list(history or [])
    if not query:
        return history, []

    try:
        client = _get_client()
    except Exception as e:
        history.append({"role": "user", "content": query})
        history.append({"role": "assistant", "content": f"[Client initialization error]: {e}"})
        return history, []

    # 1. Reformulate query for ChromaDB semantic retrieval
    search_query = _rephrase_query(client, query, history)

    # 2. Retrieve grounded chunks
    hits = retrieve(search_query, k=k)
    if not hits:
        history.append({"role": "user", "content": query})
        history.append({"role": "assistant", "content": REFUSAL})
        return history, []

    # 3. Assemble message payload with sliding history
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Append recent conversational history (sliding window)
    messages.extend(history[-(MAX_HISTORY_TURNS * 2):])

    # Append latest grounded query payload
    user_payload = (
        f"Context segments:\n\n{_format_context(hits)}\n\n"
        f"Question: {query}"
    )
    messages.append({"role": "user", "content": user_payload})

    # 4. Generate answer
    try:
        resp = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            temperature=0.2,
        )
        answer = resp.choices[0].message.content.strip()
    except Exception as e:
        answer = f"[Generation error]: {e}"

    sources = [] if answer == REFUSAL else _dedup_sources(hits)
    
    history.append({"role": "user", "content": query})
    history.append({"role": "assistant", "content": answer})
    return history, sources


# ==========================================
# GRADIO INTERFACE
# ==========================================
with gr.Blocks(title="The Unofficial Guide — Howard University") as demo:
    gr.Markdown(
        "# 🦬 The Unofficial Guide to Howard University\n"
        "Ask about financial aid, registration, campus offices, or professors. "
        "Answers come **only** from the ingested source documents, with conversational memory."
    )

    chatbot = gr.Chatbot(label="Conversation", height=450)
    sources_output = gr.JSON(label="Sources Used for Last Answer (deduplicated)")

    with gr.Row():
        query_input = gr.Textbox(
            label="Ask a question or follow-up",
            placeholder="e.g. How do I clear a financial hold on Workday?",
            scale=8,
            lines=1,
        )
        submit_btn = gr.Button("Send", variant="primary", scale=1)
        clear_btn = gr.Button("Clear Chat", scale=1)

    def _user_submit(user_msg, chat_hist):
        updated_hist, sources = chat_turn(user_msg, chat_hist)
        return "", updated_hist, sources

    submit_btn.click(
        _user_submit,
        inputs=[query_input, chatbot],
        outputs=[query_input, chatbot, sources_output],
    )
    query_input.submit(
        _user_submit,
        inputs=[query_input, chatbot],
        outputs=[query_input, chatbot, sources_output],
    )
    clear_btn.click(lambda: ([], []), inputs=None, outputs=[chatbot, sources_output])

    gr.Examples(
        examples=[
            "What is the best way to contact financial aid as a first-year student?",
            "Where is that office located?",
            "Tell me more about the Howard University financial aid crisis.",
            "How do I clear a financial hold on Workday?",
            "Which professors do students rate highly?",
        ],
        inputs=query_input,
    )

if __name__ == "__main__":
    demo.launch()