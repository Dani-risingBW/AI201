import os
import re
import math
import json
import requests
from dotenv import load_dotenv
load_dotenv()


# --- SIGNAL 2: LLM-BASED FORENSIC ANALYSIS (VIA GROQ) ---
def calculate_signal_2_groq(text):
    """
    Executes a zero-shot system prompt against llama-3.3-70b-versatile via Groq
    to perform linguistic forensic analysis. Returns an AI probability float [0.0 - 1.0].
    """
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("[WARNING] GROQ_API_KEY environment variable not found! Defaulting to 0.5.")
        return 0.5

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    system_prompt = (
        "You are a linguistic forensic expert specializing in detecting synthetic machine patterns. "
        "Analyze the provided text for abstract conversational signatures, RLHF biases, semantic clichés, "
        "and pacing monotony. Respond strictly with a single JSON object matching this structure: "
        '{"ai_probability": <float between 0.0 and 1.0>}. Do not include any pre-text or post-text.'
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
            res_data = response.json()
            content = res_data['choices'][0]['message']['content']
            parsed = json.loads(content)
            return float(parsed.get("ai_probability", 0.5))
        else:
            print(f"[Error] Groq API returned status {response.status_code}. Defaulting to 0.5.")
            return 0.5
    except Exception as e:
        print(f"[Exception] Failed to contact Groq API: {e}. Defaulting to 0.5.")
        return 0.5


# --- SIGNAL 3: SEMANTIC CONSISTENCY & FACT-DENSITY ---
def calculate_signal_3_density(text):
    """
    Measures informational entity-to-token ratio and semantic loop progression over time.
    Scores from 0.0 (dense, conceptual anchors) to 1.0 (empty, repetitive fluff).
    """
    words = re.findall(r'\b\w+\b', text.lower())
    total_tokens = len(words)
    if total_tokens == 0:
        return 0.5
        
    # Track plain-text keywords/noun repetition signatures as an anchor proxy
    word_counts = {}
    for w in words:
        if len(w) > 4: # Focus on substantive vocabulary content roots
            word_counts[w] = word_counts.get(w, 0) + 1
            
    if not word_counts:
        return 0.7  # Empty structural filler phrase layout baseline

    # High frequency of identical content words flags circular looping text patterns
    max_repeat = max(word_counts.values())
    unique_substantive = len(word_counts)
    
    # Mathematical aggregation layout matching your specification criteria
    loop_factor = min(1.0, max_repeat / (unique_substantive + 1))
    density_factor = 1.0 - (unique_substantive / total_tokens)
    
    s3_raw = (0.4 * loop_factor) + (0.6 * density_factor)
    return round(min(1.0, max(0.0, s3_raw)), 4)


# --- CONFLICT-BASED CALIBRATION & ENSEMBLE ENGINE ---
def compute_calibrated_ensemble(s1, s2, s3):
    """
    Applies your specific 3-Signal mathematical weighting, sigmoid boundary stretching,
    and conflict penalty dampening towards the 0.50 anchor zone when metrics fiercely collide.
    """
    # 1. Sigmoid Scaling Core Alignment
    def sigmoid_scale(x, k=10, x0=0.5):
        return 1 / (1 + math.exp(-k * (x - x0)))

    s1_cal = sigmoid_scale(s1)
    
    # 2. Conflict-Based Penalty Dampening Check ($|S_2 - S_1| > 0.6$)
    signal_conflict = abs(s2 - s1)
    
    # Calculate baseline ensemble product layout metrics explicitly
    base_ensemble = (0.25 * s1_cal) + (0.45 * s2) + (0.30 * s3)
    
    if signal_conflict > 0.6:
        # Mathematically dampens and pulls the score down cleanly into the 0.50 uncertainty buffer
        calibrated_score = (base_ensemble + 0.50) / 2
    else:
        calibrated_score = base_ensemble
        
    return round(min(1.0, max(0.0, calibrated_score)), 4)


# --- TEST FLOW EXECUTION ---
if __name__ == "__main__":
    human_sample = (
        """
        ok so i finally tried that new ramen place downtown and honestly? 
        underwhelming. the broth was fine but they put WAY too much sodium in it and 
        i was thirsty for like three hours after. my friend got the spicy version and 
        said it was better. probably won't go back unless someone drags me there
        """
    )
    ai_monotone_sample = (
        """
        Artificial intelligence represents a transformative paradigm shift in modern society. 
        It is important to note that while the benefits of AI are numerous, it is equally 
        essential to consider the ethical implications. Furthermore, stakeholders across 
        various sectors must collaborate to ensure responsible deployment.
        """
    )

    print("=== TESTING MILESTONE 4 ISOLATED ENGINE LAYER ===")
    
    print("\n--- Processing Human Sample ---")
    h_s2 = calculate_signal_2_groq(human_sample)
    h_s3 = calculate_signal_3_density(human_sample)
    print(f"Signal 2 (Groq)    : {h_s2}")
    print(f"Signal 3 (Density) : {h_s3}")
    
    print("\n--- Processing AI Monotone Sample ---")
    a_s2 = calculate_signal_2_groq(ai_monotone_sample)
    a_s3 = calculate_signal_3_density(ai_monotone_sample)
    print(f"Signal 2 (Groq)    : {a_s2}")
    print(f"Signal 3 (Density) : {a_s3}")