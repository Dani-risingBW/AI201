"""
TakeMeter — DistilBERT Classifier Local UI
Run: python open_classifier_ui.py
Install: pip install gradio transformers torch pandas openpyxl numpy scikit-learn matplotlib
"""

import os
import re
import json
import pandas as pd
import numpy as np
import torch
import gradio as gr
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from sklearn.metrics import cohen_kappa_score

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

# ── Stretch Features: Test data with human annotations ────────────────────────
STRETCH_FEATURES_TEST_DATA = [
    {
        "title": "Google and FBI file joint lawsuit against Chinese cybercrime ring",
        "body": "Google has filed a joint lawsuit with the FBI against a Chinese cybercrime group...",
        "true_label": 1,
        "annotator1": 1,
        "annotator2": 1,
    },
    {
        "title": "Do you think AI will replace most white-collar jobs?",
        "body": "With rapid advancement of LLMs... curious what this community thinks...",
        "true_label": 0,
        "annotator1": 0,
        "annotator2": 0,
    },
    {
        "title": "OpenAI launches GPT-5 with extended context",
        "body": "OpenAI announced GPT-5 with improvements in reasoning and 1M token context...",
        "true_label": 1,
        "annotator1": 1,
        "annotator2": 1,
    },
    {
        "title": "Is Claude better than GPT-4 for coding tasks?",
        "body": "I've been switching between Claude and GPT-4 for my side projects...",
        "true_label": 0,
        "annotator1": 0,
        "annotator2": 0,
    },
    {
        "title": "1 in 5 Americans believe AI will become more powerful than governments",
        "body": "My colleagues at Johns Hopkins and I ran a survey on AI attitudes...",
        "true_label": 1,
        "annotator1": 1,
        "annotator2": 0,  # Disagreement
    },
]

# ── Lazy model loader (avoids crashing on startup if weights not downloaded) ──
_tokenizer = None
_model = None
_load_error = None


# ── Stretch Features: Inter-annotator Reliability & Confidence Calibration ────
def compute_inter_annotator_reliability(test_data):
    """Compute inter-annotator agreement and Cohen's Kappa."""
    annotator1_labels = [p["annotator1"] for p in test_data]
    annotator2_labels = [p["annotator2"] for p in test_data]

    agreements = sum(1 for a1, a2 in zip(annotator1_labels, annotator2_labels) if a1 == a2)
    simple_agreement = agreements / len(test_data) if test_data else 0

    kappa = cohen_kappa_score(annotator1_labels, annotator2_labels) if test_data else 0

    if kappa >= 0.81:
        interpretation = "Almost Perfect Agreement"
    elif kappa >= 0.61:
        interpretation = "Substantial Agreement"
    elif kappa >= 0.41:
        interpretation = "Moderate Agreement"
    elif kappa >= 0.21:
        interpretation = "Fair Agreement"
    else:
        interpretation = "Slight to Poor Agreement"

    disagreements = []
    for i, (a1, a2) in enumerate(zip(annotator1_labels, annotator2_labels)):
        if a1 != a2:
            disagreements.append({
                "post_num": i + 1,
                "title": test_data[i]["title"][:60],
                "a1": ID_MAP[a1],
                "a2": ID_MAP[a2],
                "true": ID_MAP[test_data[i]["true_label"]],
            })

    return {
        "simple_agreement": f"{simple_agreement:.1%}",
        "cohens_kappa": f"{kappa:.4f}",
        "interpretation": interpretation,
        "num_disagreements": len(disagreements),
        "disagreements_df": pd.DataFrame(disagreements) if disagreements else pd.DataFrame(),
    }


def compute_confidence_calibration(predictions):
    """Analyze confidence calibration: do 90% confident predictions really get it right 90% of time?"""
    if not predictions:
        return {"error": "No predictions available"}

    confidences = np.array([p["confidence"] for p in predictions])
    correctness = np.array([1 if p["predicted_label"] == p["true_label"] else 0 for p in predictions])

    overall_accuracy = correctness.mean()

    bins = [0.0, 0.6, 0.7, 0.8, 0.9, 1.0]
    bin_labels = ["0-60%", "60-70%", "70-80%", "80-90%", "90-100%"]
    bin_data = []

    for i in range(len(bins) - 1):
        mask = (confidences >= bins[i]) & (confidences < bins[i+1])
        if mask.sum() > 0:
            bin_accuracy = correctness[mask].mean()
            bin_expected = (bins[i] + bins[i+1]) / 2
            count = int(mask.sum())
            bin_data.append({
                "Confidence Bin": bin_labels[i],
                "Accuracy": f"{bin_accuracy:.1%}",
                "Expected": f"{bin_expected:.1%}",
                "Count": count,
            })

    ece = 0
    for i in range(len(bins) - 1):
        mask = (confidences >= bins[i]) & (confidences < bins[i+1])
        if mask.sum() > 0:
            bin_accuracy = correctness[mask].mean()
            bin_confidence = confidences[mask].mean()
            weight = mask.sum() / len(predictions)
            ece += weight * abs(bin_confidence - bin_accuracy)

    if ece < 0.05:
        calibration_status = "✓ Well-Calibrated"
    elif ece < 0.1:
        calibration_status = "⚠ Reasonably Calibrated"
    else:
        calibration_status = "✗ Poorly Calibrated"

    return {
        "overall_accuracy": f"{overall_accuracy:.1%}",
        "ece": f"{ece:.4f}",
        "calibration_status": calibration_status,
        "bin_df": pd.DataFrame(bin_data),
    }


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


def analyze_stretch_features_iaa():
    """Callback for inter-annotator reliability analysis."""
    results = compute_inter_annotator_reliability(STRETCH_FEATURES_TEST_DATA)

    summary_text = (
        f"**Simple Agreement Rate:** {results['simple_agreement']}\n"
        f"**Cohen's Kappa:** {results['cohens_kappa']}\n"
        f"**Interpretation:** {results['interpretation']}\n"
        f"**Disagreements Found:** {results['num_disagreements']}"
    )

    return summary_text, results["disagreements_df"]


def analyze_stretch_features_calibration():
    """Callback for confidence calibration analysis."""
    if not _load_model():
        return "Model not loaded", pd.DataFrame()

    tokenizer = _tokenizer
    model = _model
    assert tokenizer is not None and model is not None

    predictions = []
    for post in STRETCH_FEATURES_TEST_DATA:
        title = post["title"]
        body = post["body"]
        formatted = f"Title: {title}\nBody: {body}"

        inputs = tokenizer(formatted, return_tensors="pt", truncation=True, max_length=512)
        with torch.no_grad():
            logits = model(**inputs).logits
            probs = torch.softmax(logits, dim=1).flatten().tolist()

        pred_id = int(torch.argmax(logits, dim=1).item())
        confidence = max(probs)

        predictions.append({
            "predicted_label": pred_id,
            "confidence": confidence,
            "true_label": post["true_label"],
        })

    results = compute_confidence_calibration(predictions)

    summary_text = (
        f"**Overall Accuracy:** {results['overall_accuracy']}\n"
        f"**Expected Calibration Error (ECE):** {results['ece']}\n"
        f"**Status:** {results['calibration_status']}\n\n"
        f"*A well-calibrated model's confidence matches its accuracy. "
        f"ECE < 0.05 indicates excellent calibration.*"
    )

    return summary_text, results["bin_df"]


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

    with gr.Tab("Stretch Features Analysis"):
        gr.Markdown(
            "## 🎁 Stretch Features Implementation\n"
            "Analysis of inter-annotator reliability and confidence calibration."
        )

        gr.Markdown("### 1. Inter-Annotator Reliability")
        gr.Markdown(
            "Evaluates agreement between human annotators using Cohen's Kappa. "
            "Tests whether labeling guidelines are clear and consistent."
        )
        iaa_btn = gr.Button("Compute Inter-Annotator Reliability", variant="primary")
        iaa_summary = gr.Markdown()
        iaa_table = gr.Dataframe(wrap=True)
        iaa_btn.click(
            fn=analyze_stretch_features_iaa,
            outputs=[iaa_summary, iaa_table]
        )

        gr.Markdown("---")

        gr.Markdown("### 2. Confidence Calibration")
        gr.Markdown(
            "Checks if model confidence scores align with actual accuracy. "
            "A 90% confident prediction should be correct ~90% of the time."
        )
        cal_btn = gr.Button("Analyze Confidence Calibration", variant="primary")
        cal_summary = gr.Markdown()
        cal_table = gr.Dataframe(wrap=True)
        cal_btn.click(
            fn=analyze_stretch_features_calibration,
            outputs=[cal_summary, cal_table]
        )


if __name__ == "__main__":
    demo.launch(inbrowser=True)
