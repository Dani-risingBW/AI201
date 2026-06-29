
# planning.md: Content Attribution & Transparency System Design

## 1. 3-Signal Detection Pipeline Design

## 1. Detection Signals Pipeline

### Signal 1: Stylometric Heuristics (Sentence Length & Vocabulary Variance)
- **What it measures:** The geometric and mechanical structure of the text. It analyzes vocabulary richness—such as the Type-Token Ratio (TTR)—and "burstiness," which calculates the standard deviation of sentence lengths. 
- **Implementation Strategy:** Computed locally via pure Python string processing, regular expressions, and basic statistical math arrays. 
- **Output Type:** Continuous score between `0.0` (highly varied lengths/vocabulary, indicating human) and `1.0` (highly uniform, rigid structures, indicating AI).
- **Blind Spots (What it cannot capture):** - **Prompt-Engineered Text:** It completely misses AI text generated using explicit stylistic instructions (e.g., *"Write a short story using highly varied sentence lengths and complex, rare vocabulary"*).
  - **Highly Structured Human Writing:** It will generate false positives for certain types of human creators, such as legal documents, technical instruction manuals, or academic papers, which naturally rely on rigid, repetitive structures and low sentence variance.

### Signal 2: LLM-Based Classification (Forensic Analysis via Groq)
- **What it measures:** High-level tone, semantic cliches, conversational pacing, and common RLHF (Reinforcement Learning from Human Feedback) styling biases. It identifies synthetic formatting tendencies that pass structural tests but sound unnatural.
- **Implementation Strategy:** Executes a real-time, zero-shot system prompt against a fast inference model (e.g., `llama-3.3-70b-versatile` via the Groq API) configured to return a rigid, validated JSON block.
- **Output Type:** Continuous probability score between `0.0` (confident human) and `1.0` (confident AI).
- **Blind Spots (What it cannot capture):**
  - **Jailbreaks and Adversarial Formatting:** If an AI text block includes obfuscated characters (e.g., swapping letters for lookalike Cyrillic symbols) or structural formatting wrappers, the LLM classifier can get distracted by the surface noise and miss the synthetic undertone.
  - **"Humanized" AI Outputs:** It struggles with text that has been passed through programmatic paraphrasing tools or lightly edited by a human editor to remove classic AI-isms and conversational crutches.

### Signal 3: Semantic Consistency & Fact-Density Heuristic
- **What it measures:** The informational entity-to-token ratio and semantic progression over time. It captures whether the text uses empty, circular phrasing (typical of auto-regressive text models) or introduces concrete, varying conceptual anchors.
- **Implementation Strategy:** Programmed via Python keyword density tracking, phrase repetition mapping, or lightweight Part-of-Speech/Entity parsing dictionaries.
- **Output Type:** Continuous score between `0.0` (dense, distinct factual objects) and `1.0` (low informational density, repeating loops).
- **Blind Spots (What it cannot capture):**
  - **AI Halitosis (Hallucinated Entity Spikes):** If a generative model is prompted to invent highly specific fictitious names, fictional history lore, or rapid, erratic topics, this heuristic will see a high density of unique nouns and assume it is human, ignoring that the text is entirely hallucinated.
  - **Minimalist Human Writing:** It penalizes valid human writing that is intentionally simple or stream-of-consciousness—such as flash fiction, emotional poetry, or stylized blog entries—where concrete nouns and entities are sparse, but repetition is an intentional artistic device.

### Combination Logic & Mathematical Formula
To synthesize these distinct vectors into a single metric, the system uses a weighted ensemble formula. This design leverages the fast contextual reading of the LLM while allowing structural and semantic anomalies to pull the system into an "Uncertain" state if they conflict.

### Mathematical Formula
$$\text{Confidence Score} = 0.25 \cdot S_{\text{stylometric}} + 0.45 \cdot S_{\text{llm\_groq}} + 0.30 \cdot S_{\text{semantic\_density}}$$

### Weighting Justification
- **Groq LLM Classifier ($45\%$):** Given the heaviest weight due to its ability to capture holistic nuances, abstract context, and conversational signatures that simple math checks overlook.
- **Semantic Density Heuristic ($30\%$):** Serves as a strong semantic baseline to evaluate whether the text actually says something substantive or is just filling space with grammatically perfect fluff.
- **Stylometric Heuristic ($25\%$):** Anchors the formula to raw mechanical syntax. It acts as an instant trap for standard, uniform AI text outputs without overriding the nuances caught by the other two layers.
---

## 2. Uncertainty Representation & Calibration

### Score Interpretation
In this system, the combined confidence score ($0.0 \le \text{Score} \le 1.0$) represents the aggregated probability that a text exhibits synthetic generation patterns. 

- **Meaning of a 0.60 Score:** A score of 0.60 does *not* mean the text is "60% AI-generated." Instead, it indicates a state of high structural or systemic conflict (e.g., the local stylometric heuristic flags the text as highly uniform, but the Groq LLM classifier detects strong human nuance and contextual depth). This triggers an **Uncertain / Mixed** classification, creating a protective buffer against definitive false accusations.

---

### Calibration Strategy
Raw heuristic outputs and LLM probabilities often suffer from "overconfidence" near the extreme bounds ($0.0$ or $1.0$). To smooth out these spikes and ensure scores are meaningful, the system implements a two-step calibration pipeline before running the final ensemble weighting:

1. **Sigmoid Scaling for Heuristics:** Raw statistical metrics (such as sentence length standard deviation) are mapped to a logistic sigmoid function:
   $$S_{\text{calibrated}} = \frac{1}{1 + e^{-k(x - x_0)}}$$
   *This compresses extreme outliers and expands the middle range, ensuring marginal structural anomalies do not wildly swing the score.*
2. **Conflict-Based Penalty Dampening:** If the distance between your strongest signals is structurally massive (e.g., $|S_{\text{llm}} - S_{\text{stylometric}}| > 0.6$), the system applies a dampening function that mathematically pulls the final aggregated score toward the $0.50$ baseline. This explicitly forces system disagreement into the "Uncertain" buffer zone rather than letting a single aggressive signal trigger an incorrect high-confidence label.

---

### Threshold Classifications & False Positive Mitigation
To protect human creators, the thresholds are intentionally asymmetrical. The burden of proof for labeling content as "Likely AI" is set exceptionally high to prevent false positives.

| Score Range | Classification | System Meaning / Core Balance |
| :--- | :--- | :--- |
| **$0.00 \le \text{Score} < 0.35$** | **Likely Human** | The text exhibits natural structural burstiness, rich entity-to-token distribution, and passes the LLM contextual scan. Safe for automated publishing. |
| **$0.35 \le \text{Score} \le 0.75$** | **Uncertain / Mixed** | **The Safety Buffer:** Signals are in conflict, or the text exhibits borderline traits (e.g., highly technical human documentation or an LLM heavily edited by a human). The system refuses to make a definitive judgment. |
| **$0.75 < \text{Score} \le 1.00$** | **Likely AI** | All three pipeline components heavily agree. The text shows structural monotony, low unique entity density, and clear RLHF conversational signatures. |

#### The Balancing Act (Risk Minimization)
- **Protecting Humans from False Positives:** By setting the AI threshold floor all the way up at **$0.76$**, you ensure that highly structured human writing (like technical prose, essays with a formal voice, or repetitive poetry) is pushed down into the **Uncertain** category instead of being mislabeled as machine-made. 
- **Managing False Negatives (AI slipping through):** A sophisticated AI prompt that successfully mimics human sentence length variance might trick the stylometric signal ($S_1 = 0.20$). However, because the Groq LLM classifier ($S_2$) and semantic density ($S_3$) carry a combined weight of $75\%$, a high AI reading from them will still drag the final score safely into the $0.50 - 0.65$ **Uncertain** bracket. It won't get a clean "Likely Human" pass, forcing transparency.
---

### 3. Transparency Label Design
*Write out the exact text variants that will be returned by the API and displayed to non-technical users.*

### Variant A: High-Confidence AI Result
- **Trigger Condition:** Combined Ensemble Confidence Score $> 0.75$ ($0.76 \le \text{Score} \le 1.00$)
- **Exact Label Text:** > "Attribution: Automated Content. Our system has identified highly predictable structural arrangements, repetitive sentence geometries, and linguistic patterns characteristic of AI-generated text."
- **Context/Explanation provided to reader:** This label explicitly communicates an artificial origin without being confrontational. It provides non-technical readers with an objective explanation of *why* it was flagged (predictable structures and uniform sentence shapes) so they understand the determination is based on measurable stylistic mechanics, not an arbitrary guess.

### Variant B: High-Confidence Human Result
- **Trigger Condition:** Combined Ensemble Confidence Score $< 0.35$ ($0.00 \le \text{Score} < 0.35$)
- **Exact Label Text:** > "Attribution: Verified Human Content. This text exhibits natural language variance, expressive structural burstiness, and contextual transitions characteristic of original human authorship."
- **Context/Explanation provided to reader:** This label provides positive validation for authentic human writing. It explains that the text displays "structural burstiness" and natural pacing variations in plain language, reassuring readers that the writing carries the stylistic fingerprints of genuine human thought and composition.

### Variant C: Uncertain / Mixed Result
- **Trigger Condition:** Combined Ensemble Confidence Score between $0.35$ and $0.75$ ($0.35 \le \text{Score} \le 0.75$)
- **Exact Label Text:** > "Attribution: Indeterminate / Mixed Content. Our system detected conflicting structural signals. This text may contain a mixture of human editing and AI assistance, or it may follow a rigid technical layout that prevents a definitive classification."
- **Context/Explanation provided to reader:** This label serves as our crucial safety buffer. Instead of forcing a false classification on borderline text, it transparently admits the ambiguity to the reader. It explains that highly structured human templates (like coding blogs or formal essays) or heavily edited AI texts can confuse the system, reassuring creators that the platform prefers transparency over inaccurate accusations.

---

## 4. Appeals Workflow
*Define the exact data structures and process flow when a creator contests an attribution.*

- **Who can submit an appeal:** [e.g., Authenticated authors, content creators, or any submission owner]
- **Information provided by claimant:**
  - `[Field 1]:` [e.g., original_submission_id]
  - `[Field 2]:` [e.g., creator_reasoning (text justification)]
  - `[Field 3]:` [e.g., proof_of_authorship (optional link/text)]
- **System Actions on Receipt:**
  - **Status Changes:** [What state does the record transition to? e.g., `Classified` $\rightarrow$ `Under Review`]
  - **Audit Log Actions:** [What specific event keys and fields get appended to the structured JSON audit log?]
- **Human Reviewer Queue Interface:**
  - *When a reviewer opens the queue, they will see:*
    1. [Item 1]
    2. [Item 2]
    3. [Item 3]

---

## 5. Anticipated Edge Cases
*Identify specific content types where the heuristic pipeline will struggle.*

- **Edge Case 1 (False Positive AI):**
  - **Scenario Description:** [e.g., A poem with high structural repetition, rigid meter, and basic vocabulary.]
  - **Why signals fail:** [Explain how specific signals misinterpret this text as machine-generated.]
- **Edge Case 2 (False Negative Human):**
  - **Scenario Description:** [e.g., Technical programming blogs or heavily edited professional text with extreme structural variation.]
  - **Why signals fail:** [Explain why the pipeline will incorrectly classify or mark this as uncertain.]

---

## 6. Architecture
*System reference block for code generation and cross-milestone alignment.*

### Workflow Diagram (ASCII)

```text
========================================================================================
(1) SUBMISSION FLOW
========================================================================================

  [ Creator Content ] 
           │
           │ (JSON Payload: raw text)
           ▼
   ┌───────────────┐
   │  POST/submit  │ <─── [ Rate Limiter (Flask-Limiter) ]
   └───────┬───────┘
           │
           │ (Cleaned Raw Text)
           ▼
   ┌────────────────────────────────────────────────────────┐
   │                  Detection Pipeline                    │
   │                                                        │
   │  ┌───────────┐      ┌───────────┐      ┌───────────┐   │
   │  │ Signal 1  │      │ Signal 2  │      │ Signal 3  │   │
   │  │ (Stylom.) │      │  (Groq)   │      │ (Density) │   │
   │  └─────┬─────┘      └─────┬─────┘      └─────┬─────┘   │
   └────────│──────────────────│──────────────────│─────────┘
            │                  │                  │
            └──────────┬───────┴──────────┬───────┘
                       │                  │
                       │ (Signal Scores: S1, S2, S3)
                       ▼
   ┌──────────────────────────────────────────────┐
   │      Scoring Engine & Calibration            │
   │  - Applies Sigmoid & Dampening Formula       │
   └───────────────────┬──────────────────────────┘
                       │
                       │ (Combined Score: 0.0 - 1.0)
                       ▼
   ┌──────────────────────────────────────────────┐
   │     Transparency Label & Schema Builder      │
   │  - Generates UI text based on score range    │
   └───────────────────┬──────────────────────────┘
                       │
                       │ (Combined Score + Generated Label Text)
                       ├────────────────────────────────────────┐
                       ▼                                        ▼
   ┌──────────────────────────────────────┐          ┌──────────────────────┐
   │         SQLite / Memory DB           │          │ Structured Audit Log │
   │  - Stores Text, Score, & Label Text  │          │ - Appends Event Log  │
   └──────────────────────────────────────┘          └──────────────────────┘
                       │
                       │ (JSON Response: Score, Label Text, Classification)
                       ▼
               [ Client API Response ]


========================================================================================
(2) APPEAL FLOW
========================================================================================

  [ Creator Contest Request ]
           │
           │ (JSON Payload: submission_id, reasoning)
           ▼
   ┌───────────────┐
   │  POST/appeal  │
   └───────┬───────┘
           │
           │ (Validated ID & Reason)
           ▼
   ┌──────────────────────────────────────┐
   │          SQLite / Memory DB          │ ───► Updates Status to: "Under Review"
   └───────────────────┬──────────────────┘
                       │
                       │ (Logged State Metas)
                       ▼
   ┌──────────────────────────────────────┐
   │        Structured Audit Log          │ ───► Appends Review Queue Flag
   └───────────────────┬──────────────────┘
                       │
                       │ (JSON Response: status: "under review", logged: true)
                       ▼
               [ Client API Response ]
```

### Flow Narrative
The content submission flow begins when a user submits text to the `POST /api/submit` endpoint protected by a rate-limiting layer, triggering the parallel execution of the structural, LLM-based, and semantic density signals to compute a calibrated ensemble confidence score. Once the pipeline builds the calibrated transparency label schema, it simultaneously commits the evaluation data to a local database and registers a structured entry in the system audit log. Creators can contest any classification via the `POST /api/appeal` endpoint, which writes an appeal event to the log, updates the internal database entry status to `"under review"`, and instantly flags the record for priority human moderation in the evaluation queue.