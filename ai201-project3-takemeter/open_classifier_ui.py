"""
TakeMeter — DistilBERT Classifier Local UI
Run: python open_classifier_ui.py
Install: pip install gradio transformers torch pandas openpyxl
"""

import os
import re
import pandas as pd
import torch
import gradio as gr
from transformers import AutoTokenizer, AutoModelForSequenceClassification

# ── Model configuration ──────────────────────────────────────────────────────
MODEL_PATH = "./my_fine_tuned_distilbert"
ID_MAP = {0: "Question/Opinion", 1: "AI_Info/News"}

SAMPLE_POSTS = [
    (
        "Title: 1 in 5 Americans believe AI systems will become more powerful than governments, new poll finds\n"
        "Body:My colleagues at Johns Hopkins and I ran a national survey on AI attitudes and some of the results are quite surprising. Check out a write-up here."  
        "[https://hub.jhu.edu/2026/06/15/americans-strongly-support-regulations-on-ai/](https://hub.jhu.edu/2026/06/15/americans-strongly-support-regulations-on-ai/)"
    ),
    (
        "Title: Trump tells Axios he no longer views Anthropic as national security threat\n"
        "Body: Trump tells Axios he no longer views Anthropic as national security threat "
        "https://www.reuters.com/world/us/trump-tells-axios-he-no-longer-views-anthropic-national-"
        "security-threat-2026-06-19/"
    ),
    (
        "Title: Do you think AI will replace most white-collar jobs in the next 5 years?\n"
        "Body: With the rapid advancement of LLMs and autonomous agents, it seems like a lot of "
        "knowledge work is becoming automatable. Curious what this community thinks — are we heading "
        "toward mass displacement or will new roles emerge fast enough to absorb the shift?"
    ),
    (
        "Title: OpenAI launches GPT-5 with extended context and improved reasoning\n"
        "Body: OpenAI today announced the release of GPT-5, claiming significant improvements in "
        "multi-step reasoning, coding ability, and a 1M token context window. The model is available "
        "immediately to ChatGPT Plus subscribers and via the API."
    ),
    (
        "Title: Is Claude actually better than GPT-4 for coding tasks?\n"
        "Body: I have been switching back and forth between Claude and GPT-4 for my side projects. "
        "Claude seems to write cleaner boilerplate but GPT-4 handles debugging prompts better in my "
        "experience. What are others seeing?"
    ),
    (
        "Title: Meta releases Llama 4 Scout and Maverick open weights\n"
        "Body: Meta AI announced the open release of Llama 4 Scout (17B active parameters, 109B total "
        "with MoE) and Llama 4 Maverick. Both models are available under the Llama 4 Community License "
        "and can be downloaded from Hugging Face."
    ),
]

# ── Lazy model loader (avoids crashing on startup if weights not downloaded) ──
_tokenizer = None
_model = None
_load_error = None


def _load_model():
    global _tokenizer, _model, _load_error
    if _model is not None:
        return True
    if _load_error:
        return False
    if not os.path.isdir(MODEL_PATH):
        _load_error = (
            f"Model folder not found: {os.path.abspath(MODEL_PATH)}\n\n"
            "Steps to fix:\n"
            "1. Run the Colab notebook through Section 3 to fine-tune your model.\n"
            "2. Run the last cell in Section 6 to download 'my_fine_tuned_distilbert.zip'.\n"
            "3. Unzip it so the folder 'my_fine_tuned_distilbert/' sits next to this script."
        )
        return False
    try:
        print("Loading tokenizer and model weights...")
        _tokenizer = AutoTokenizer.from_pretrained("distilbert-base-uncased")
        _model = AutoModelForSequenceClassification.from_pretrained(MODEL_PATH)
        _model.eval()
        print("Model ready.")
        return True
    except Exception as exc:
        _load_error = f"Failed to load model:\n{exc}"
        return False


# ── Core inference helpers ────────────────────────────────────────────────────
def _parse_title_body(text: str):
    text = str(text)
    title_m = re.search(r"(?:Title:\s*)(.*?)(?:\nBody:|$)", text, re.DOTALL | re.IGNORECASE)
    body_m = re.search(r"(?:Body:\s*)(.*)", text, re.DOTALL | re.IGNORECASE)
    title = title_m.group(1).strip() if title_m else text.split("\n")[0]
    body = body_m.group(1).strip() if body_m else "\n".join(text.split("\n")[1:])
    return title, body


def _run_inference(texts: list[str]) -> pd.DataFrame:
    if not _load_model():
        return pd.DataFrame({"Error": [_load_error]})

    tokenizer = _tokenizer
    model = _model
    assert tokenizer is not None and model is not None

    rows = []
    for raw in texts:
        raw = str(raw).strip()
        if not raw:
            continue
        title, body = _parse_title_body(raw)
        formatted = f"Title: {title}\nBody: {body}"
        inputs = tokenizer(formatted, return_tensors="pt", truncation=True, max_length=512)
        with torch.no_grad():
            logits = model(**inputs).logits
            probs = torch.softmax(logits, dim=1).flatten().tolist()
        pred_id = int(torch.argmax(logits, dim=1).item())
        rows.append({
            "Title": title,
            "Body": (body[:120] + "...") if len(body) > 120 else body,
            "Predicted Label": ID_MAP[pred_id],
            "Confidence": round(probs[pred_id], 4),
        })
    return pd.DataFrame(rows) if rows else pd.DataFrame(
        columns=["Title", "Body", "Predicted Label", "Confidence"]
    )


# ── Gradio callback functions ─────────────────────────────────────────────────
def infer_single(text: str):
    return _run_inference([text])


def infer_multi(text: str):
    """Split on blank lines or '---' separators so users can paste many posts."""
    blocks = re.split(r"\n---+\n|\n{2,}", text.strip())
    return _run_inference([b for b in blocks if b.strip()])


def infer_samples():
    return _run_inference(SAMPLE_POSTS)


def infer_file(file_path):
    if file_path is None:
        return pd.DataFrame({"Error": ["No file uploaded."]})
    try:
        path = file_path if isinstance(file_path, str) else file_path.name
        df_in = pd.read_csv(path) if path.endswith(".csv") else pd.read_excel(path)
    except Exception as exc:
        return pd.DataFrame({"Error": [str(exc)]})

    title_col = next((c for c in df_in.columns if "title" in c.lower()), df_in.columns[0])
    body_col = next(
        (c for c in df_in.columns if "body" in c.lower()),
        df_in.columns[1] if len(df_in.columns) > 1 else df_in.columns[0],
    )
    combined = [
        f"Title: {row[title_col]}\nBody: {'' if pd.isna(row[body_col]) else row[body_col]}"
        for _, row in df_in.iterrows()
    ]
    return _run_inference(combined)


def check_model_status():
    ready = _load_model()
    if ready:
        return "Model loaded and ready."
    return f"Not loaded — {_load_error}"


# ── UI layout ─────────────────────────────────────────────────────────────────
SAMPLE_PLACEHOLDER = "\n\n".join(SAMPLE_POSTS[:2])
MULTI_PLACEHOLDER = (
    "Title: First post title here\nBody: First post body here...\n\n---\n\n"
    "Title: Second post title here\nBody: Second post body here..."
)

with gr.Blocks(title="TakeMeter Classifier", theme=gr.themes.Soft()) as demo:
    gr.Markdown("# TakeMeter — r/ArtificialIntelligence Classifier")
    gr.Markdown(
        "Fine-tuned `distilbert-base-uncased` pipeline · labels: **Question/Opinion** | **AI_Info/News**"
    )

    with gr.Row():
        status_btn = gr.Button("Check model status", size="sm")
        status_out = gr.Textbox(label="", lines=1, interactive=False)
    status_btn.click(fn=check_model_status, outputs=status_out)

    gr.Markdown("---")

    with gr.Tab("Sample Posts"):
        gr.Markdown(
            "Runs the 6 built-in sample posts from r/ArtificialIntelligence through the classifier."
        )
        sample_btn = gr.Button("Run sample posts", variant="primary")
        sample_table = gr.Dataframe(
            headers=["Title", "Body", "Predicted Label", "Confidence"],
            wrap=True,
        )
        sample_btn.click(fn=infer_samples, outputs=sample_table)

    with gr.Tab("Single Post"):
        gr.Markdown("Paste one post (Title + Body block).")
        single_in = gr.Textbox(
            label="Post text",
            placeholder=SAMPLE_POSTS[0],
            lines=8,
        )
        single_btn = gr.Button("Classify", variant="primary")
        single_table = gr.Dataframe(
            headers=["Title", "Body", "Predicted Label", "Confidence"],
            wrap=True,
        )
        single_btn.click(fn=infer_single, inputs=single_in, outputs=single_table)

    with gr.Tab("Multiple Posts"):
        gr.Markdown(
            "Paste several posts separated by a blank line or `---`. "
            "Each block should start with `Title:` then `Body:`."
        )
        multi_in = gr.Textbox(
            label="Post blocks",
            placeholder=MULTI_PLACEHOLDER,
            lines=16,
        )
        multi_btn = gr.Button("Classify all", variant="primary")
        multi_table = gr.Dataframe(
            headers=["Title", "Body", "Predicted Label", "Confidence"],
            wrap=True,
        )
        multi_btn.click(fn=infer_multi, inputs=multi_in, outputs=multi_table)

    with gr.Tab("Batch Upload (.csv / .xlsx)"):
        gr.Markdown(
            "Upload a spreadsheet. The script auto-detects columns containing "
            "`title` and `body` in their names (case-insensitive)."
        )
        file_in = gr.File(label="Upload file", file_types=[".csv", ".xlsx"])
        file_btn = gr.Button("Process file", variant="primary")
        file_table = gr.Dataframe(
            headers=["Title", "Body", "Predicted Label", "Confidence"],
            wrap=True,
        )
        file_btn.click(fn=infer_file, inputs=file_in, outputs=file_table)


if __name__ == "__main__":
    demo.launch(inbrowser=True)
