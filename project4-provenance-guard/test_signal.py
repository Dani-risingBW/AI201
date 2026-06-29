import os
import math
from dotenv import load_dotenv
load_dotenv()
from app import (
    calculate_signal_1_stylometric, 
    calculate_signal_2_groq, 
    calculate_signal_3_density
)

# --- 1. BASELINE SAMPLES (Expected Standard Behaviors) ---
human_sample = """
ok so i finally tried that new ramen place downtown and honestly? 
underwhelming. the broth was fine but they put WAY too much sodium in it and 
i was thirsty for like three hours after. my friend got the spicy version and 
said it was better. probably won't go back unless someone drags me there
"""

ai_monotone_sample = """
This system checks text layout patterns. 
This system checks text layout structures. 
This system checks text layout metrics. 
This system checks text layout choices.
This system checks text layout values.
"""

# --- 2. ADVANCED STRESS-TEST SAMPLES (Testing Edge Cases) ---
# Edge Case 1: Human poem with intentional repetition (Monotone loop structure)
human_poetic_repetition = """
I wake to sleep, and take my waking slow. We think by feeling. What is there to know? 
I learn by going where I have to go. We think by feeling. Great nature has another thing to do to you and me. 
I feel my fate in what I cannot fear. I learn by going where I have to go.
"""
# Edge Case 2: AI technical documentation guide with code snippet layout variations
ai_prompt_engineered_code = """
When executing a structured migration sequence inside an active cluster database environment, engineers often encounter immediate thread deadlocks. To resolve this structural breakdown, pass the configuration object dynamically into your routing mechanism.

def initialize_cluster_node(node_id, state_allocation):
    if not node_id or state_allocation == 'HALT':
        raise ClusterFailureException("Node deployment aborted dynamically.")
    return [uuid.uuid4() for _ in range(5)]

Furthermore, parsing raw configuration dictionaries dynamically eliminates initial environment overhead. It is important to note that this routine stabilizes network topology.
"""

# --- ENSEMBLE ENGINE SIMULATION FOR VALIDATION ---
def run_full_ensemble_pipeline(text, sample_name):
    print(f"\n--- Processing: {sample_name} ---")
    
    # 1. Gather Individual Signal Scores
    s1 = calculate_signal_1_stylometric(text)
    s2 = calculate_signal_2_groq(text)
    s3 = calculate_signal_3_density(text)
    
    print(f"  [Raw] Signal 1 (Stylometric)      : {s1}")
    print(f"  [Raw] Signal 2 (Groq LLM Forensic): {s2}")
    print(f"  [Raw] Signal 3 (Semantic Density) : {s3}")
    
    # 2. Apply Sigmoid Calibration Scaling on Signal 1
    s1_sigmoid = 1 / (1 + math.exp(-10 * (s1 - 0.5)))
    
    # 3. Calculate Weighted Combination
    confidence_score = (0.25 * s1_sigmoid) + (0.45 * s2) + (0.30 * s3)
    
    # 4. Check for Conflict-Based Penalty Dampening ($|S_2 - S_1| > 0.6$)
    if abs(s2 - s1) > 0.6:
        confidence_score = (confidence_score + 0.50) / 2
        print("  ⚠️ Signal Conflict Detected! Applied 0.50 Baseline Penalty Dampening.")
        
    confidence_score = round(min(1.0, max(0.0, confidence_score)), 4)
    
    # 5. Evaluate Asymmetric Thresholding Tier
    if confidence_score < 0.35:
        tier = "LIKELY HUMAN"
    elif confidence_score > 0.75:
        tier = "LIKELY AI"
    else:
        tier = "UNCERTAIN / MIXED BUFFER"
        
    print(f"  >> FINAL ENSEMBLE CONFIDENCE SCORE : {confidence_score}")
    print(f"  >> ASSIGNED PLATFORM ATTRIBUTION   : {tier}")
    return confidence_score


if __name__ == "__main__":
    print("=====================================================")
    print("=== RUNNING MILESTONE 4 COMPLETE ENSEMBLE PIPELINE ===")
    print("=====================================================")
    
    # Check for API key presence
    if not os.environ.get("GROQ_API_KEY"):
        print("\n[WARNING] GROQ_API_KEY not found in environment variables!")
        print("Signal 2 will use a fallback value of 0.5 for testing purposes.\n")
        
    # Execute calculations over all text variants
    run_full_ensemble_pipeline(human_sample, "Baseline Human Sample")
    run_full_ensemble_pipeline(ai_monotone_sample, "Baseline AI Monotone Sample")
    run_full_ensemble_pipeline(human_poetic_repetition, "Edge Case 1: Poetic Repetition Loop")
    run_full_ensemble_pipeline(ai_prompt_engineered_code, "Edge Case 2: AI Technical Documentation")