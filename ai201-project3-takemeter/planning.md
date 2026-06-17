# Project Planning Template: Community Classification Task

This document serves as the planning blueprint for designing, collecting, annotating, and evaluating a text classification model tailored to a specific online community. 

---

## 1. Community Selection
* **What community did you choose and why?**
  * *[Fill in the community name (e.g., subreddit, forum, Discord server) and your personal or academic motivation for choosing it.]*
* **Why is this community a good fit for a classification task?**
  * *[Explain why this community is suitable. What makes the discourse varied, nuanced, or complex enough to warrant a machine learning classifier rather than simple keyword filtering?]*

---

## 2. Labels & Annotation Guide
* **Label Definitions:**
  * **Label 1: [Name]** — *[Define this label in a complete, unambiguous sentence detailing what types of posts fall into this category.]*
  * **Label 2: [Name]** — *[Define this label in a complete, unambiguous sentence detailing what types of posts fall into this category.]*
  * **Label 3: [Name (Optional)]** — *[Define this label in a complete, unambiguous sentence detailing what types of posts fall into this category.]*
  * **Label 4: [Name (Optional)]** — *[Define this label in a complete, unambiguous sentence detailing what types of posts fall into this category.]*

* **Example Posts per Label:**
  * **Label 1:**
    1. *[Example Post A]*
    2. *[Example Post B]*
  * **Label 2:**
    1. *[Example Post A]*
    2. *[Example Post B]*
  * **Label 3 (If applicable):**
    1. *[Example Post A]*
    2. *[Example Post B]*
  * **Label 4 (If applicable):**
    1. *[Example Post A]*
    2. *[Example Post B]*

---

## 3. Hard Edge Cases & Boundary Disambiguation
* **What type of post will be genuinely ambiguous between two labels?**
  * *[Describe a specific scenario, tone, or overlapping theme where a text snippet could easily be categorized into more than one of your defined labels (e.g., Label 1 vs. Label 2).]*
* **How will you handle it when you encounter it during annotation?**
  * *[Establish clear, deterministic tie-breaking rules or programmatic heuristics to resolve this ambiguity consistently throughout your annotation process.]*

---

## 4. Data Collection Plan
* **Where will you collect examples?**
  * *[Specify the platforms, data extraction methods, APIs, or scraping tools you intend to use to aggregate your dataset.]*
* **Target Sample Size:**
  * *[Specify the number of target samples per label (e.g., 50–100 posts per label to build a balanced dataset).]*
* **Contingency Strategy for Underrepresented Labels:**
  * **What will you do if a specific label is heavily underrepresented after reviewing 200 total raw examples?**
    * *[Outline your mitigation plan (e.g., searching for specific keyword indicators, filtering by specific community sub-flairs, adjusting sorting metrics to top/controversial, or expanding the collection timeline).]*

---

## 5. Evaluation Metrics
* **Selected Metrics & Justification:**
  * *[List the primary evaluation metrics you will calculate (e.g., Precision, Recall, F1-Score, Confusion Matrix) along with standard Accuracy.]*
* **Why are these the right metrics for this specific task?**
  * *[Explain why accuracy alone is insufficient. Detail how false positives vs. false negatives impact the downstream utility of your classifier within this community context.]*

---

## 6. Definition of Success
* **Operational Usefulness:**
  * *[Describe what performance thresholds or behaviors would make this classifier genuinely useful when integrated into a real-world community moderation or analytics tool.]*
* **Deployment Threshold ("Good Enough"):**
  * *[Define the exact minimum performance baseline you would accept to deploy this model (e.g., "An F1-score of 0.80 or higher on the minority class, with no more than a 10% false positive rate on Label 1").]*
* **Evaluation Plan Review:**
  * *[Critique your success criteria: Are they specific, quantifiable, and objective enough that a third party could definitively determine at the end of the project whether you hit them?]*

---

## 7. AI Tool Plan

### A. Label Stress-Testing
* **Prompting Strategy:**
  * *[Plan to feed your label definitions and hard edge case descriptions into an LLM. Ask it to generate 5–10 highly ambiguous boundary posts designed to break your current definitions.]*
* **Refinement Loop:**
  * *[If the AI generates realistic posts that you cannot cleanly classify using your rules, use this space to record how you tightened and revised your definitions before beginning manual annotation.]*

### B. Annotation Assistance
* **Pre-Labeling Framework:**
  * *[Decide if you will use an LLM to automatically pre-label a batch of raw examples before you personally review, verify, and correct them. Note the specific tool/model you plan to use (e.g., GPT-4o via API, Claude 3.5 Sonnet).]*
* **Traceability & Disclosure:**
  * *[Explain how you will systematically track and flags which rows/examples were pre-labeled by AI versus those generated or labeled entirely by hand, ensuring clear disclosure in your final AI usage appendix.]*

### C. Failure Analysis
* **Error Pattern Extraction:**
  * *[Plan to extract all misclassified examples (where ground-truth labels mismatch model predictions) and feed them into an AI tool to isolate thematic or structural patterns in the errors.]*
* **Human Verification Plan:**
  * *[Detail how you will double-check the AI's synthesized failure patterns against the raw text to ensure you aren't hallucinating trends, before writing up your final evaluation report.]*