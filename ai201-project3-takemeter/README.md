# `r/ArtificialInteligence` Content Classifier: README.md

This repository contains the complete engineering pipeline, dataset configurations, and fine-tuning mechanics for an NLP text classification model explicitly tailored to the `r/ArtificialInteligence` Reddit community. The model isolates factual, high-signal information streams from subjective, open-ended community discussions.

---

## Demo

[![Watch the demo](https://cdn.loom.com/sessions/thumbnails/710eab0c59c441a8be70f312a3626dec-with-play.gif)](https://www.loom.com/share/710eab0c59c441a8be70f312a3626dec)

👉 **[Click here to watch the live video demo if the thumbnail above doesn't load](https://www.loom.com/share/710eab0c59c441a8be70f312a3626dec)**

---

## 1. Project Overview & Community Selection

### Why `r/ArtificialInteligence`?
With artificial intelligence advancing exponentially, information streams suffer from severe signal-to-noise pollution. In modern tech ecosystems, yesterday's "facts" can quickly be proven false, while speculation frequently masquerades as breaking updates. This project targets the `r/ArtificialInteligence` subreddit to build an automated, real-time filtering engine.

### Operational Objectives
This tool is engineered to serve two core user types:
* **Researchers/Enthusiasts:** Provides a pristine, noise-free feed of verified technical advancements, corporate press announcements, and peer-reviewed releases.
* **Community Participants:** Groups personal viewpoints, troubleshooting inquiries, and ongoing philosophical debates into a dedicated, highly interactive discussion hub.

---

## 2. Taxonomy & Annotation Guide

The dataset is classified into two mutually exclusive labels:

### Label 0: `Question/Opinion`
* **Definition:** A linguistic or conceptual expression used to seek information, clarification, or provoke thought; or an expression leveraged for exploration and understanding. This also includes personal beliefs, viewpoints, or judgments about an AI topic, expressed clearly and supported with reasons, personal anecdotes, or persuasive intent.
* **Example 1:** *"If one of the issues with DatCenters is water usage, why not incorporate desalination into the water cooling systems and build the data centers near the ocean..."*
* **Example 2:** *"As I look at the scale of the data center build out... it doesn’t seem to be factoring in how LLM workflows are changing and the possibility of local models bearing the brunt of processing on-device..."*

### Label 1: `AI_Info/News`
* **Definition:** Writing explicitly designed to provide objective, factual information about a specific topic to educate, explain, describe, or report real-world industry developments.
* **Example 1:** *"Trump tells Axios he no longer views Anthropic as national security threat https://www.reuters.com/world/us/trump-tells-axios-he-no-longer-views-anthropic-national-security-threat-2026-06-19/"*
* **Example 2:** *"Five Chinese AI labs cut inference token prices in a single week, with the steepest reductions reported up to 99%. It is the latest escalation in a domestic price war as labs fight for developer share. Source : https://aiweekly.co/alerts/five-chinese-ai-labs-cut-token-prices-up-to-99"*

---

## 3. Boundary Disambiguation & Hard Edge Cases

Reddit threads are inherently blended. Users routinely share a breaking news link but attach an exhaustive personal opinion. To guarantee deterministic annotations, the pipeline enforces three explicit structural tie-breaking rules:

* **The Primary Intent Rule (50% Volume Rule):** If a post blends news and personal critique, the text volume is calculated. If subjective speculation, emotional rants, or personal critiques take up 50% or more of the overall text block, it is explicitly classified as `0 [Question/Opinion]`.
* **The Call-to-Action / Question Dominance Rule:** If a post presents factual news but concludes with an open-ended community prompt (e.g., *"Thoughts?"*, *"What do you all think this means?"*), it is overridden and classified as `0 [Question/Opinion]`, as its functional intent is to spark a debate rather than simply inform.
* **The "Pure Source" Exception:** If a post simply links to an outbound domain or copies a corporate headline/press release verbatim with negligible commentary (less than 1–2 sentences of personal thoughts), it is automatically tagged as `1 [AI_Info/News]`.

### Dataset Heuristic Shift (Refinement Loop)
During bulk processing, a massive 71% natural class imbalance was uncovered. Many users post high-signal software libraries or step-by-step tutorials using conversational pronouns (e.g., *"I built an open-source tool, what do you think?"*). To protect the data pool from starvation, the volume rule was refined: **Explicit tool deployment documentations, code repositories, or step-by-step technical guides are classified as `1 [AI_Info/News]` if an outbound destination project URL or reproducible code block is present, regardless of conversational framing.**

---

## 4. Data Collection & Pre-Labeling Framework

### Scraping Architecture
Data collection was executed using the Apify automated scraping infrastructure, targeting the main feed of `r/ArtificialInteligence`. 
* **Master Dataset Size:** 506 unique, non-duplicate entries.
* **Natural Class Balance:** 362 `Question/Opinion` rows (71.5%) vs. 144 `AI_Info/News` rows (28.5%).

### Strategic Contingency for Imbalance Handling
To ensure sufficient representation of the rarer news class, a multi-tiered collection roadmap was deployed:
1.  **Subreddit Flair Targets:** Filtering via mandatory community flairs (`📰 News`, `🔬 Research`, `🤖 New Model/Tool`).
2.  **Linguistic Anchor Seeding:** Target queries using anchor phrases (`source:`, `announced`, `arxiv.org`, `reuters.com`).
3.  **Sorting Parameter Pivots:** Shifting scraping targets from the chronological `New` feed to `Top (Past Month)` where high-signal news naturally clusters due to upvote metrics.

### AI Pre-Labeling & Traceability Disclosure
Initial baseline passes were accelerated using a programmatic zero-shot LLM framework running **Llama 3.3 70B** via the **Groq API** (`llama-3.3-70b-versatile`) with `temperature=0.0`. 
To ensure strict transparency, the data schema utilizes a dedicated `notes` column. The API automatically logs the exact rule applied during inference (e.g., *“Call-to-Action Rule applied”*). Any subsequent manual overrides or human validation checks rewrite this block to read *“Human Verified”*, providing clean data lineage for auditing.

---

## 5. Evaluation Metrics & Deployment Thresholds

### Selected Metrics & Strategic Justification
* **Primary Metric:** **Macro F1-Score**. This metric calculates the harmonic mean of precision and recall for both classes independently and averages them equally. This prevents the dominant `Question/Opinion` class from masking a failing grade on the rarer news class.
* **Baseline Trend Tracking:** **Classification Accuracy**, measuring the overall percentage of stable correct classifications.
* **Per-Class Precision & Recall:** Critical due to the distinct consequences of directional errors:
    * *News False Positive:* Pollutes the informative feed with subjective rants, completely destroying user utility.
    * *News False Negative:* Erroneously hides breaking technological shifts or peer-reviewed papers inside the discussion feed.

### Production Deployment Thresholds
To be deemed "good enough" for deployment, the model must clear these quantitative blocks:
1.  **Macro F1-Score:** >= 0.82 across both classes.
2.  **Label 1 [AI_Info/News] Precision:** >= 0.85 (guaranteeing a false positive leak rate under 15%). This is enforced by elevating the model's classification probability threshold from 0.50 to 0.70.
3.  **Baseline Outperformance:** Must beat a majority-class guessing baseline by at least 35% on the Macro F1 matrix.

---

## 6. Performance Logs & Comparative Metrics

Below is the structured empirical performance comparison between the baseline Few-Shot LLM workflow and the fine-tuned `distilbert-base-uncased` classifier.

### Overall Accuracy Comparison
* **Baseline Zero-Shot/Few-Shot Model:** `80.3%`
* **Fine-Tuned DistilBERT Model:** `85.5%`

### Detailed Per-Class Metrics

#### 1. Baseline Model Metrics
```
                  precision    recall  f1-score   support

Question/Opinion       0.93      0.78      0.85        55
    AI_Info/News       0.60      0.86      0.71        21

        macro avg       0.77      0.82      0.78        76
```

#### 2. Fine-Tuned DistilBERT Model Metrics
```
                  precision    recall  f1-score   support

Question/Opinion       0.91      0.89      0.90        55
    AI_Info/News       0.73      0.76      0.74        21

        macro avg       0.82      0.83      0.82        76
```

### Fine-Tuned Model Confusion Matrix
Below is the structural textual breakdown of the fine-tuned model's predictions evaluated across the test dataset partition:

| | Predicted: `Question/Opinion` (0) | Predicted: `AI_Info/News` (1) |
| :--- | :---: | :---: |
| **True: `Question/Opinion` (0)** | **49** (True Negatives) | **6** (False Positives) |
| **True: `AI_Info/News` (1)** | **5** (False Negatives) | **16** (True Positives) |

---

## 7. Automated Pattern Discovery & Error Analysis

### LLM-Assisted Pattern Surface Phase
Prior to conducting our deep-dive granular review, we passed our misclassified dataset blocks through an adversarial LLM pattern extraction pipeline. 
* **Thematic Hypotheses Generated by AI:** The tool hypothesized that errors were heavily clustered in short text strings under 100 characters and posts containing heavy sarcasm.
* **Human Verification & Discarded Observations:** Upon re-reading the raw records to ground these assertions, **we discarded the length and sarcasm hypotheses**. Short items were actually classified easily by structural tokens. Instead, the real common denominator was **pronoun-dominance vs. syntactic styling**. The model over-indexed on words like "I", "We", or "My" regardless of high-signal technological announcements wrapped inside those paragraphs. 

### Deep-Dive Analysis of Fine-Tuned Failures

#### Case Study 1: The Directional Boundary Mistake (True News $
ightarrow$ Predicted Opinion)
* **Post Text:** 
    * *Title:* 1 in 5 Americans believe AI systems will become more powerful than governments, new poll finds
    * *Body:* "My colleagues at Johns Hopkins and I ran a national survey on AI attitudes and some of the r..."
* **True Label:** `AI_Info/News` (1)
* **Predicted Label:** `Question/Opinion` (0) — *Confidence: 0.66*
* **Root Cause Analysis:** The title is a textbook news headline reporting statistical data from a new poll. However, the post body shifts immediately into a first-person narrative (*"My colleagues at Johns Hopkins and I..."*). The model's tokenizer flagged these personal pronouns (`My`, `I`) as indicators of subjective community discussion, causing it to misapply the spirit of the **Primary Intent Rule**. It failed to realize that the first-person context was actually verifying an academic research breakthrough rather than sharing a personal opinion.
* **Pipeline Mitigation:** This represents a training data distribution limitation where first-person research disclosures are underrepresented compared to standard media links. Fixing it requires enriching the `AI_Info/News` set with academic case-studies written in the active voice.

#### Case Study 2: High-Context Technical Tutorials vs. Personal Blog Formats
* **Post Text:** 
    * *Title:* We made an LLM pipeline survive a provider outage mid-execution. Here's the FSM pattern.
    * *Body:* "Every major LLM provider had at least one significant outage in 2025. Anthropic, OpenAI, Gemini — ..."
* **True Label:** `AI_Info/News` (1)
* **Predicted Label:** `Question/Opinion` (0) — *Confidence: 0.94*
* **Root Cause Analysis:** This represents a severe false positive for the opinion class, driven by conversational phrasing (*"We made..."*, *"Here's the..."*). Under the tightened annotation rules, high-signal open-source framework documentation, architecture designs (Finite State Machine patterns), and post-mortems belong in `AI_Info/News`. DistilBERT missed the semantic importance of technical tokens like `"FSM pattern"` and `"LLM pipeline"`, over-indexing on the chatty, conversational tone often used by developers sharing projects on Reddit.
* **Pipeline Mitigation:** Introduce a domain-specific vocabulary enhancement or vocabulary weight adjustment during fine-tuning to elevate tech architecture sequences (`FSM`, `pipeline`) above general text style.

#### Case Study 3: The Hypothetical Hype & Parody Blindspot
* **Post Text:** 
    * *Title:* Security fears lead to suspension of anthropic's claude fable 5 and mythos 5.
    * *Body:* "Anthropic has suspended access to its Claude Fable 5 and Mythos 5 AI models following security concerns. The ..."
* **True Label:** `Question/Opinion` (0)
* **Predicted Label:** `AI_Info/News` (1) — *Confidence: 0.50*
* **Root Cause Analysis:** This is an exceptionally tricky edge case where the user structured an entirely fictional, community-brewed rumor or parody as a formal press release snippet. Because the text mimics the syntactic pacing and structural delivery of a genuine breaking news alert, the model fell into the **Pure Source Rule** trap. Without active web access or world-knowledge verification, the model has no way of knowing that "Claude Fable 5" or "Mythos 5" are not real, currently deployed systems, making it easily fooled by formal-sounding disinformation.
* **Pipeline Mitigation:** A tighter labeling definition or an additional metadata column capturing upvote ratios or moderator-pinned flags would be needed to assist the network in isolating structural parodies.

---

## 8. Sample Classifications

Below is a diagnostic cross-section of posts evaluated by the finalized, fine-tuned DistilBERT engine:

| Post Text Content Snippet | Predicted Label | Confidence Score | Evaluation & Rationale |
| :--- | :---: | :---: | :--- |
| **Title:** Google and FBI file joint lawsuit... <br>**Body:** Google has filed a joint lawsuit with the FBI against Chinese cybercrime... | `AI_Info/News` | **0.98** | **Correct.** Factual, objective reporting regarding legal action, backed by specific dates and agencies without subjective speculation. |
| **Title:** Best AI to insert product into my hand... <br>**Body:** Looking to use for marketing. Played with Firefly but it altered text... | `Question/Opinion` | **0.99** | **Correct.** Explicit troubleshooting query seeking community assistance and tool recommendations. |
| **Title:** We made an LLM pipeline survive an outage... <br>**Body:** Every major LLM provider had an outage in 2025... | `Question/Opinion` | **0.94** | **Incorrect.** Model was tripped up by the phrase "We made" and misclassified a technical walkthrough as an opinion post. |

---

## 9. High-Level Model Reflection

There remains a distinct performance gap between **human structural intent** and **statistical model optimization**:
* **What the model captured:** The fine-tuned transformer successfully learned superficial semantic representations of structural styles. It recognized that objective press text formats indicate news, while personal pronoun-dense writing indicates forum discussions.
* **What the model missed/Overfit to:** The model overfit significantly to the presence of pronouns (`I`, `We`, `My`). It treated them as an absolute shortcut for the `Question/Opinion` label. Consequently, it missed the high-level semantic nuance that an engineer or professor describing their first-party work is delivering authoritative *News/Information*, not a casual opinion. The decision boundary acts as a stylistic syntax detector rather than a true comprehension map of semantic intent.

---

## 10. Spec Reflection

* **Guidance Value:** The prompt specification template was instrumental in mapping out the data loading, verification, and train-test splits. It forced the implementation of strict assertion rules that caught label mismatch anomalies early before tensor tokenization occurred.
* **Divergence Action:** The final production design diverged from standard specifications by incorporating string text concatenation step directly inside the loading sequence (`"Title: " + title + "
Body: " + body`). Standard approaches often drop the body text column entirely to handle empty cells or save compute, but keeping both proved mandatory here since the model required full dual-context volume indicators to implement the tie-breaking guidelines accurately.

---

## 11. AI Usage Appendix

* **Instance 1 (Data Synthesis Phase):** Directed Llama 3.3 via the Groq API to ingest 251 raw scraped rows and apply programmatic label assignment alongside structural explanation fields. *Override Action:* Overrode and discarded approximately 12 entries manually where the LLM skipped code formatting markers or misread technical tool distributions as casual forum banter.
* **Instance 2 (Pattern Surface Phase):** Injected evaluation error structures into an LLM interface to parse textual overlaps. *Override Action:* Discarded the AI's generated output regarding text length and sarcasm metrics after manually re-reading the records, overriding the model's conclusions with a localized pronoun-overfitting mitigation strategy.

---
