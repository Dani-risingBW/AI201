
# planning.md: Content Attribution & Transparency System Design

## 1. 3-Signal Detection Pipeline Design


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

- **Who can submit an appeal:** Any content creator or platform author who owns the submitted piece of text and wishes to contest an automated "Likely AI" or "Uncertain / Mixed" classification.
- **Information provided by claimant:**
  - `submission_id`: A unique UUID string referencing the original content evaluation entry in the database.
  - `creator_reasoning`: A required text string (minimum 50 characters) where the author justifies their authorship (e.g., outlining their creative process, research drafting steps, or specialized template use).
  - `contact_email`: A validated email string to notify the creator once the human review determination is finalized or to request further operational clarification.
- **System Actions on Receipt:**
  - **Status Changes:** The database record for the targeted `submission_id` instantly changes its state from `Classified` $\rightarrow$ `Under Review`.
  - **Audit Log Actions:** An atomic, immutable JSON entry is appended to the structured system audit log using the event key `APPEAL_RECEIVED`. The log record schema explicitly captures:
    ```json
    {
      "event_type": "APPEAL_RECEIVED",
      "timestamp": "2026-06-29T16:32:00Z",
      "submission_id": "8f3b2c9d-11e5-4a7b-a25c",
      "contact_email": "creator@example.com",
      "meta": {
        "original_classification": "likely_ai",
        "original_ensemble_score": 0.842,
        "creator_reasoning_length": 245
      }
    }
    ```
- **Human Reviewer Queue Interface:**
  - *When a reviewer opens the moderation queue dashboard, they will see a structured workspace displaying:*
    1. **Contextual Metadata Panel:** The unique `submission_id`, the verified **`contact_email`** (enabling direct reviewer outreach for follow-up questions), the duration the appeal has been sitting in the queue, and the original automated classification tier.
    2. **Side-by-Side Content & Signal Analysis:** The full raw submitted text highlighting areas where the system misidentified patterns, alongside a breakdown of individual pipeline scores ($S_{\text{stylometric}}$, $S_{\text{llm}}$, $S_{\text{density}}$) to expose exactly which signal triggered the false flag.
    3. **Creator Justification & Resolution Controls:** The plain-text `creator_reasoning` statement, flanked by action controls allowing the reviewer to either **Uphold Classification** or **Overrule to Human** (which shifts the database status to `Verified Human` and updates the platform badge).

---

## 5. Anticipated Edge Cases
*Identify specific content types where the heuristic pipeline will struggle.*

- **Edge Case 1 (False Positive AI - Human Work Misclassified as AI):**
  - **Scenario Description:** A highly structured traditional poem (e.g., a villanelle or a pantoum) written by a human creator that relies on strict, rigid meter, a repetitive rhyme scheme, and simple, foundational vocabulary.
  - **Why signals fail:** - **Signal 1 (Stylometric Heuristic)** will output a maximum AI score (~1.0) because the sentence length variance is non-existent and the vocabulary diversity (Type-Token Ratio) is incredibly low due to the intentional poetic repetition. 
    - **Signal 3 (Semantic Density)** will also misfire and output a high AI score (~0.90) because the circular phrasing and repetitive artistic loops look exactly like an auto-regressive model stuck in a generation loop. 
    - Because two out of three signals aggressively align at the extreme top end, they overrule the LLM classifier, dragging the final ensemble score past the $0.75$ threshold and erroneously displaying the "High-Confidence AI" transparency label on original art.

- **Edge Case 2 (False Negative Human - AI Work Misclassified as Human):**
  - **Scenario Description:** An AI-generated technical programming blog post or highly optimized software documentation guide created using an explicit engineering prompt (e.g., *"Write a detailed technical guide with extreme structural variation, code snippets, and conversational industry anecdotes"*).
  - **Why signals fail:** - **Signal 3 (Semantic Density)** will fail completely and return a low, human-like score (~0.15) because a technical documentation prompt naturally forces the inclusion of an exceptionally high density of unique nouns, proper programmatic methods, and distinct factual code entities. 
    - **Signal 1 (Stylometric Heuristic)** will also be tricked into a human classification (~0.20) because the inclusion of raw code snippets alternating with prose artificially spikes the sentence length standard deviation (burstiness). 
    - Despite the text being completely synthetic, these structural and factual distortions mathematically drag the final calibrated ensemble score below $0.35$, causing the system to mistakenly grant it a "Verified Human" transparency certificate.

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

---

## 7. AI Tool Plan
*Scaffolding parameters for generating implementation code using large language models.*

### Milestone 3: Submission Endpoint & First Signal
- **Spec Sections Provided:** `Section 1 (Signal 1 Spec: Stylometric Heuristics)`, `Section 6 (Architecture Block: Workflow Diagram & Narrative)`
- **Prompt Deliverables:** Ask the AI tool to generate a Python Flask application skeleton including the boilerplate error handling, SQLite/in-memory database initialization, `POST /api/submit` routing with structural JSON payload validation, and the standalone Python function executing `Signal 1` (calculating Type-Token Ratio and sentence length standard deviation locally).
- **Verification Plan:** Verify by passing 3 distinct raw text blocks (a short story excerpt, a repetitive block, and a structured prose sample) directly into the standalone stylometric signal function via a local execution script before hooking it up to the API route, confirming that the output outputs a clean mathematical metric.

### Milestone 4: Second & Third Signals + Confidence Scoring
- **Spec Sections Provided:** `Section 1 (Full 3-Signals Spec & Weights)`, `Section 2 (Uncertainty Representation & Calibration Logic)`, `Section 6 (Architecture Workflow Diagram)`
- **Prompt Deliverables:** Ask the AI tool to write the standalone Python function for `Signal 2` (connecting securely to the Groq API using a fast model like `llama-3.3-70b-versatile` to capture synthetic tone) and `Signal 3` (evaluating keyword/entity structural density loops). Instruct it to implement the mathematical scoring formula, the sigmoid calibration function, and the conflict-based dampening checks that funnel severe signal disagreement safely toward the $0.50$ baseline.
- **Verification Plan:** Submit an identical, highly creative original human text block and an over-stylized, repetitive machine-generated paragraph to the pipeline. Verify that the final calculated ensemble scores vary meaningfully across the threshold boundaries, ensuring clear AI-generated data logs a score $>0.75$ and distinct human text scores safely below $0.35$.

### Milestone 5: Production Layer (Labels, Appeals, & Logs)
- **Spec Sections Provided:** `Section 3 (Transparency Label Design)`, `Section 4 (Appeals Workflow)`, `Section 6 (Architecture Workflow Diagram)`
- **Prompt Deliverables:** Ask the AI tool to build the helper functions returning the exact string literals for all three transparency label variants based on the classification ranges. Instruct it to implement the `POST /api/appeal` endpoint to accept a `submission_id`, a `creator_reasoning` string, and a `contact_email`, update the database status row atomically to `"under review"`, and construct an atomic append mechanism that captures the complete event payload (including creator email) in the structured JSON audit log file.
- **Verification Plan:** Verify by manually adjusting system evaluation scores to confirm that all three distinct plain-language label variants are correctly generated and reachable via the response schema. Execute an appeal request against an existing database entry to verify that its row status updates flawlessly, and assert that the structured audit log records a fully populated `APPEAL_RECEIVED` object containing the creator's contact information.

## 8. Stretch Features Specification

### Feature 1: Ensemble Detection Pipeline (Core Component Upgrade)
* **Status:** **Fully Integrated**
* **Implementation Strategy:** Upgraded the minimum pipeline requirements from 2 signals to an advanced 3-signal setup by incorporating a localized Semantic Consistency & Fact-Density Heuristic ($S_3$). This utilizes a formal weighted aggregation formula ($25\%$ Stylometric, $45\%$ Groq LLM, $30\%$ Semantic Density) alongside a conflict-dampening calibration layer to protect creators against aggressive false flags.

### Feature 2: Provenance Certificate ("Verified Human" Credential)
* **What it is:** A secure, platform-backed verification status appended to a creator's submission payload once they successfully verify their baseline human authorship. This bypasses automated ambiguity for that specific piece of work and rewards creators with a trusted credential badge visible to platform readers.
* **Earned By:** Creators can earn this certificate under two conditions: (1) Passing a successful manual human review via the appeals workflow queue, or (2) Authenticating their drafting sequence via session telemetry hooks during text composition.
* **UI Representation & Response Schema:** When earned, the system appends a `"provenance_certificate"` object into the transparency label meta layout.
  ```json
  "provenance_certificate": {
    "is_verified_human": true,
    "certificate_id": "cert_uuid_99b1a8c2",
    "verification_method": "human_appeal_overrule",
    "display_badge_text": "✓ Verified Original Human Content"
  }

### Feature 3: Live System Analytics Dashboard

## 1. Feature Architecture Overview
The Live System Analytics Dashboard is an isolated administrative endpoint (`GET /api/analytics`) that aggregates operational records out of the SQLite/Memory database to track system execution patterns, appeal trajectories, and model alignment characteristics. This endpoint operates as an executive monitoring system to verify that the asymmetrical threshold calibration is effectively minimizing false positives over time.

## 2. Core Metrics Computed & Business Logic
The analytics engine queries database records to dynamically compile three operational metrics:

1. **Distribution Patterns:** - *Logic:* Computes the rolling percentages of total processed documents classified into each of the three threshold zones (*Likely Human*, *Uncertain/Mixed*, or *Likely AI*). 
   - *Purpose:* Monitors whether the system's classifications align with expected platform usage trends or if systemic drift is shifting classifications abnormally toward an extreme.

2. **Contestation Rate (Appeal Rate):** - *Logic:* Calculates the exact percentage of high-risk designations (*Likely AI* and *Uncertain/Mixed*) that are actively contested by creators using the `POST /api/appeal` endpoint. 
   - *Formula:* `(Total Appeal Submissions) / (Total Likely AI + Total Uncertain Content) * 100`

3. **Signal Variance Rate (System Conflict Flag):** - *Logic:* Tracks the frequency and percentage of submissions where the local mechanical math heuristics and the Groq LLM API responses fiercely contradict one another (defined as an absolute mathematical distance $|S_{\text{llm}} - S_{\text{stylometric}}| > 0.6$).
   - *Purpose:* Measures how frequently the conflict-based calibration engine successfully steps in to pull a borderline record out of a false-positive state into the protective "Uncertain" buffer zone.

## 3. Production JSON Response Schema
When requested by an authorized client or internal administration portal, the `GET /api/analytics` surface area returns a clean, fully compiled structural object:

```json
{
  "total_processed_submissions": 1420,
  "distribution_patterns": {
    "likely_human_percentage": 62.4,
    "uncertain_mixed_percentage": 24.1,
    "likely_ai_percentage": 13.5
  },
  "appeals_telemetry": {
    "total_appeals_submitted": 54,
    "active_contestation_rate": "10.15%"
  },
  "system_health": {
    "signal_variance_dampening_triggers": 42,
    "heuristic_llm_conflict_rate": "2.95%"
  }
}
```