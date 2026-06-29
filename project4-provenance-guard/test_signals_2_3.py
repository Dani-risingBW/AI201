import os

from test_milestone_4 import calculate_signal_2_groq, calculate_signal_3_density
s2_ai_sample = "It is important to remember that navigating complex academic or administrative systems requires diligent attention to detail. Furthermore, setting precise organizational boundaries can significantly enhance your operational efficiency. In conclusion, it is vital to approach these procedural challenges with structural clarity and absolute patience."

s3_loop_sample = "This system checks text layout patterns. This system checks text layout structures. This system checks text layout metrics. This system checks text layout choices.This system checks text layout values."

print("=== VERIFYING ENGINE SEPARATION LAYERS ===")

# Test Signal 2
if os.environ.get("GROQ_API_KEY"):
    score_s2 = calculate_signal_2_groq(s2_ai_sample)
    print(f"Signal 2 (LLM Forensic) Test -> Score: {score_s2} (Expected: High -> > 0.75)")
else:
    print("[Skipped] Set your GROQ_API_KEY environment variable to test Signal 2 live.")

# Test Signal 3
score_s3 = calculate_signal_3_density(s3_loop_sample)
print(f"Signal 3 (Semantic Density) Test -> Score: {score_s3} (Expected: High -> > 0.75)")