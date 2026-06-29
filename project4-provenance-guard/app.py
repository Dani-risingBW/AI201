import os
import re
import math
import uuid
import json
import requests
from datetime import datetime, timezone
from flask import Flask, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

app = Flask(__name__)

# --- DEFENSIVE MIDDLEWARE CONFIGURATION ---
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[],
    storage_uri="memory://"
)

# --- IN-MEMORY DATABASE & TRANSPARENCY DATA STRUCTURES ---
DATABASE = {}
AUDIT_LOG = []

# --- 1. DYNAMIC TRANSPARENCY LABEL GENERATOR ---
def generate_transparency_label(confidence_score):
    """
    Maps dynamic ensemble confidence ranges into verified plain-text strings 
    matching the planning.md safety specification layout.
    """
    if confidence_score < 0.35:
        return (
            "Attribution: Verified Human Content. "
            "This text exhibits natural language variance, expressive structural burstiness, "
            "and contextual transitions characteristic of original human authorship."
        )
    elif confidence_score > 0.75:
        return (
            "Attribution: Automated Content. "
            "Our system has identified highly predictable structural arrangements, "
            "repetitive sentence geometries, and linguistic patterns characteristic of AI-generated text."
        )
    else:
        return (
            "Attribution: Indeterminate / Mixed Content. "
            "Our system detected conflicting structural signals. This text may contain a mixture of "
            "human editing and AI assistance, or it may follow a rigid technical layout that prevents a definitive classification."
        )


# --- DETECTOR PIPELINE SIGNAL MATH ---

def calculate_signal_1_stylometric(text):
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    sentences = [s for s in sentences if s]
    if not sentences:
        return 0.5

    sentence_lengths = []
    all_tokens = []
    for sentence in sentences:
        tokens = re.findall(r'\b\w+\b', sentence.lower())
        if tokens:
            sentence_lengths.append(len(tokens))
            all_tokens.extend(tokens)
        
    total_tokens = len(all_tokens)
    if total_tokens == 0 or not sentence_lengths:
        return 0.5

    mean_length = sum(sentence_lengths) / len(sentence_lengths)
    variance = sum((x - mean_length) ** 2 for x in sentence_lengths) / len(sentence_lengths)
    std_dev = math.sqrt(variance)
    
    burstiness_score = 1.0 - (min(std_dev, 12.0) / 12.0)
    unique_tokens = set(all_tokens)
    ttr = len(unique_tokens) / total_tokens
    ttr_score = 1.0 - ttr

    return round((0.5 * burstiness_score) + (0.5 * ttr_score), 4)


def calculate_signal_2_groq(text):
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return 0.5

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    system_prompt = (
        "You are a linguistic forensic expert specializing in detecting synthetic machine patterns. "
        "Analyze the provided text for abstract conversational signatures and RLHF biases. "
        "Respond strictly with a single JSON object matching this structure: "
        '{"ai_probability": <float between 0.0 and 1.0>}. Do not include commentary.'
    )
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Analyze this text:\n\n{text}"}
        ],
        "temperature": 0.0,
        "response_format": {"type": "json_object"}
    }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        if response.status_code == 200:
            parsed = json.loads(response.json()['choices'][0]['message']['content'])
            return float(parsed.get("ai_probability", 0.5))
        return 0.5
    except Exception:
        return 0.5


def calculate_signal_3_density(text):
    words = re.findall(r'\b\w+\b', text.lower())
    total_tokens = len(words)
    if total_tokens == 0:
        return 0.5
        
    word_counts = {w: words.count(w) for w in words if len(w) > 4}
    if not word_counts:
        return 0.7

    max_repeat = max(word_counts.values())
    unique_substantive = len(word_counts)
    
    loop_factor = min(1.0, max_repeat / (unique_substantive + 1))
    density_factor = 1.0 - (unique_substantive / total_tokens)
    return round((0.4 * loop_factor) + (0.6 * density_factor), 4)


# --- API API SURFACE CORE ROUTING ---

@app.route('/submit', methods=['POST'])
@limiter.limit("10 per minute;100 per day")
def submit_content():
    if not request.is_json:
        return jsonify({"error": "Bad Request", "message": "Payload format must be JSON."}), 400
        
    data = request.get_json()
    raw_text = data.get("text")
    creator_id = data.get("creator_id")
    
    if not raw_text or not isinstance(raw_text, str):
        return jsonify({"error": "Unprocessable Entity", "message": "Missing required string field 'text'."}), 422
    if not creator_id or not isinstance(creator_id, str):
        return jsonify({"error": "Unprocessable Entity", "message": "Missing required string field 'creator_id'."}), 422

    # Run Analysis
    s1 = calculate_signal_1_stylometric(raw_text)
    s2 = calculate_signal_2_groq(raw_text)
    s3 = calculate_signal_3_density(raw_text)

    # Compute Ensemble Weighting Matrices
    s1_sigmoid = 1 / (1 + math.exp(-10 * (s1 - 0.5)))
    confidence_score = (0.25 * s1_sigmoid) + (0.45 * s2) + (0.30 * s3)
    
    if abs(s2 - s1) > 0.6:
        confidence_score = (confidence_score + 0.50) / 2
        
    confidence_score = round(min(1.0, max(0.0, confidence_score)), 4)

    # Evaluate dynamic ranges via our standalone generator
    label_text = generate_transparency_label(confidence_score)
    
    if confidence_score < 0.35:
        classification = "likely_human"
    elif confidence_score > 0.75:
        classification = "likely_ai"
    else:
        classification = "uncertain"

    content_id = str(uuid.uuid4())
    
    # Persist entry record to state storage
    DATABASE[content_id] = {
        "content_id": content_id,
        "creator_id": creator_id,
        "text_preview": raw_text[:60] + "...",
        "signal_scores": {"s1": s1, "s2": s2, "s3": s3},
        "confidence": confidence_score,
        "label": label_text,
        "status": "classified",
        "appeal_filed": False,
        "appeal_reasoning": None,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    }
    
    # Save Transaction Event Entry
    AUDIT_LOG.append({
        "event_type": "CONTENT_SUBMISSION_PROCESSED",
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "content_id": content_id,
        "creator_id": creator_id,
        "confidence": confidence_score,
        "meta": {
            "signal_scores": {
                "signal_1_stylometric": s1,
                "signal_2_groq_llm": s2,
                "signal_3_density": s3
            },
            "assigned_tier": classification,
            "status": "classified",
            "appeal_filed": False
        }
    })

    return jsonify({
        "content_id": content_id,
        "attribution": {
            "signal_1_score": s1,
            "signal_2_score": s2,
            "signal_3_score": s3,
            "primary_classification": classification
        },
        "confidence": confidence_score,
        "label": label_text
    }), 200


# --- 2. THE TRANSITIONAL POST /APPEAL ENDPOINT ---
@app.route('/appeal', methods=['POST'])
def appeal_content():
    """
    Accepts content_id and reasoning to transition text classifications 
    into a manual human evaluation review queue lifecycle.
    """
    if not request.is_json:
        return jsonify({"error": "Bad Request", "message": "Payload format must be JSON."}), 400

    data = request.get_json()
    content_id = data.get("content_id")
    creator_reasoning = data.get("creator_reasoning")

    # Verify both parameters exist and are structurally correct
    if not content_id or not isinstance(content_id, str):
        return jsonify({"error": "Unprocessable Entity", "message": "Missing required field 'content_id'."}), 422
    if not creator_reasoning or not isinstance(creator_reasoning, str) or not creator_reasoning.strip():
        return jsonify({"error": "Unprocessable Entity", "message": "Missing required field 'creator_reasoning'."}), 422

    # Verify document record tracking existence
    if content_id not in DATABASE:
        return jsonify({"error": "Not Found", "message": "The specified content_id does not exist."}), 404

    record = DATABASE[content_id]

    # Block double-appealing loops
    if record.get("appeal_filed") is True:
        return jsonify({"error": "Conflict", "message": "An appeal transaction has already been processed for this content identifier."}), 409

    # Apply State Transition mutations atomically
    record["status"] = "under_review"
    record["appeal_filed"] = True
    record["appeal_reasoning"] = creator_reasoning

    # Append complete historical validation trail to our audit system logs
    AUDIT_LOG.append({
        "event_type": "CONTENT_APPEAL_FILED",
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "content_id": content_id,
        "creator_id": record["creator_id"],
        "confidence": record["confidence"],
        "meta": {
            "original_signal_scores": record["signal_scores"],
            "status": "under_review",
            "appeal_filed": True,
            "appeal_reasoning": creator_reasoning
        }
    })

    return jsonify({
        "status": "success",
        "message": "Appeal successfully filed. Content state has transitioned to 'under_review'.",
        "content_id": content_id
    }), 200


@app.route('/log', methods=['GET'])
def get_audit_log():
    return jsonify({"entries": AUDIT_LOG}), 200


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)