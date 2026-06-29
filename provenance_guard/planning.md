# planning.md

## 1. Core Detection & Governance Strategy

### Detection Signals
The system uses a two-signal ensemble pipeline to analyze text.
* **Signal 1: Burstiness (Structural Variance)**
    * *What it measures:* The variance in sentence length and structure. Human writing features high variance (short punchy sentences mixed with long clauses), whereas LLM outputs tend to be uniform and highly structured.
    * *Output:* A float score between `0.0` (perfectly uniform/likely AI) and `1.0` (highly varied/likely human).
* **Signal 2: Perplexity (Vocabulary Distribution)**
    * *What it measures:* The predictability of word choices using an N-gram frequency lookup or local language model heuristics. AI text relies heavily on highly probable tokens.
    * *Output:* A float score between `0.0` (highly predictable/likely AI) and `1.0` (unexpected vocabulary choices/likely human).
* **Combination Logic:**
    The final confidence score ($C$) represents the system's certainty that the text is **AI-generated**. It is calculated via a weighted average, inverted so that values closer to 1.0 signify AI:
    $$C = 1.0 - (0.4 	imes 	ext{Burstiness} + 0.6 	imes 	ext{Perplexity})$$

### Uncertainty Representation
The final confidence score ($C$) ranges from `0.0` (absolute certainty of human origin) to `1.0` (absolute certainty of AI origin).
* **Score Interpretation (0.6):** A score of `0.6` indicates mild leaning toward AI generation, but falls strictly into the "Uncertain" gray zone due to conflicting or weak signal metrics.
* **Calibration Thresholds:**
    * `0.00 <= C < 0.35`: **Likely Human**
    * `0.35 <= C <= 0.65`: **Uncertain / Mixed**
    * `0.65 < C <= 1.00`: **Likely AI**

### Transparency Label Design
* **High-Confidence AI ($C > 0.65$):** > 🤖 **Automated Content Label:** This text closely matches structural patterns typical of AI generation. (Confidence: [Score]%)
* **High-Confidence Human ($C < 0.35$):** > ✍️ **Verified Human Writing:** This content exhibits a high degree of structural and vocabulary variance consistent with natural human authorship.
* **Uncertain Result ($0.35 \le C \le 0.65$):** > ⚖️ **Ambiguous Authorship:** This text contains a mix of stylistic indicators. Origin could not be definitively determined.

### Appeals Workflow
* **Who can appeal:** The original content creator/uploader.
* **Information provided:** The original Content ID, the creator's email, and a required text explanation justification (minimum 15 words) countering the system's assessment.
* **System Action on Receipt:**
    1. Updates the database status code for the record from `Completed` to `Under Review`.
    2. Appends an un-redacted action entry to the structured audit log.
* **Human Reviewer Queue View:** A dashboard showing a table with: `Appeal ID`, `Content ID`, `Original AI Confidence Score`, `Submission Timestamp`, `Creator Justification Text`, and two action buttons: `[Approve Appeal - Force Human Label]` and `[Deny Appeal - Maintain Label]`.

### Anticipated Edge Cases
* **Edge Case 1: Repetitive Structural Poetry.** A highly structured human-written poem using precise repetition and simple vocabulary (e.g., a villanelle or pantoum) will trigger low burstiness and low perplexity, causing an erroneous high-confidence AI classification.
* **Edge Case 2: Highly Edited / Co-Piloted Text.** Text drafted by a human but run through a heavy grammar checker or stylistic regularizer (like Grammarly) will see its natural burstiness smoothed out, pushing it directly into the "Uncertain" or "Likely AI" classification.

---

## 2. Architecture

```
[ Client / Creator ] 
     │       ▲
     │ (1)   │ (4) JSON Response
     ▼       │
┌────────────────────────────────────────────────────────┐
│ Flask API Gateway                                      │
│  ├── Rate Limiter (Flask-Limiter)                      │
│  └── Routes: /analyze , /appeal , /log                 │
└────┬───────────────────────────────────────────────────┘
     │                                     ▲
     │ (2) Process                         │ (3) Log & Return
     ▼                                     │
┌───────────────────────┐            ┌─────┴─────────────┐
│ Pipeline Engine       │            │ SQLite Database   │
│  ├── Signal 1 (Burst) │───────────►│  ├── Audit Logs   │
│  └── Signal 2 (Perpl) │            │  └── Appeal Queue │
└───────────────────────┘            └───────────────────┘
```

### Flow Narrative
When a user submits text to `/analyze`, the Flask API checks the rate limit, routes the text through the `Pipeline Engine` to execute both detection signals concurrently, calculates the final confidence score, and writes a structured entry to the `SQLite Database` audit log before returning the transparency label text. If a creator submits a POST request to `/appeal`, the API validates the submission, modifies the matching entry's status in the database to `Under Review`, and places it into the reviewer queue log without altering the baseline raw signal mathematical data.

---

## 3. AI Tool Plan

### M3: Submission Endpoint & First Signal
* **Spec Sections Provided:** *Detection Signals (Signal 1 focus)* + *Architecture Diagram*.
* **Prompt Request:** "Generate a Flask app skeleton containing a rate-limited POST `/analyze` endpoint accepting a `content` string. Implement the first signal function (`calculate_burstiness`) using basic string variance calculations, returning a score between 0.0 and 1.0."
* **Verification Strategy:** Run a standalone python script passing a flat corporate memo (low variance) and a chaotic stream-of-consciousness paragraph (high variance) directly to the function to confirm the score scales correctly before exposing it via the route.

### M4: Second Signal & Confidence Scoring
* **Spec Sections Provided:** *Detection Signals (Full)* + *Uncertainty Representation* + *Architecture Diagram*.
* **Prompt Request:** "Implement the second signal function (`calculate_perplexity`) using token uniqueness checks. Write the core aggregation function that combines both signals into the final weighted $C$ value according to the mathematical formula, returning calibrated classification categories."
* **Verification Strategy:** Test the pipeline using 3 deterministic mock inputs representing clear human writing, clear AI boilerplate text, and borderline short-form phrases to guarantee that output scores span across all three threshold bins (`Likely Human`, `Uncertain`, `Likely AI`).

### M5: Production Layer
* **Spec Sections Provided:** *Transparency Label Design* + *Appeals Workflow* + *Architecture Diagram*.
* **Prompt Request:** "Write the formatting module map that translates confidence scores directly to the exact text labels defined in the spec. Build the POST `/appeal` and GET `/log` endpoints, wiring them to an SQLite database schema that logs states and transitions tracking the status changes to 'Under Review'."
* **Verification Strategy:** Programmatically submit an analysis request, grab its generated ID, post a payload to `/appeal` using that ID, and run a query against `/log` to verify that the entry state updates cleanly to `Under Review` with the user justification visible.




# planning.md: Content Attribution & Transparency System Design

## 1. 3-Signal Detection Pipeline Design

## 1. Detection Signals Pipeline

### Signal 1: Stylometric Heuristics (Sentence Length & Vocabulary Variance)
- **What it measures:** The geometric and mechanical structure of the text. It analyzes vocabulary richness—such as the Type-Token Ratio (TTR)—and "burstiness," which calculates the standard deviation of sentence lengths. 
- **Implementation Strategy:** Computed locally via pure Python string processing, regular expressions, and basic statistical math arrays. 
- **Output Type:** Continuous score between `0.0` (highly varied lengths/vocabulary, indicating human) and `1.0` (highly uniform, rigid structures, indicating AI).

### Signal 2: LLM-Based Classification (Forensic Analysis via Groq)
- **What it measures:** High-level tone, semantic cliches, conversational pacing, and common RLHF (Reinforcement Learning from Human Feedback) styling biases. It identifies synthetic formatting tendencies that pass structural tests but sound unnatural.
- **Implementation Strategy:** Executes a real-time, zero-shot system prompt against a fast inference model (e.g., `llama-3.3-70b-versatile` via the Groq API) configured to return a rigid, validated JSON block.
- **Output Type:** Continuous probability score between `0.0` (confident human) and `1.0` (confident AI).

### Signal 3: Named Entity & Concept Density Heuristic
- **What it measures:** The factual density and semantic progression of the text. It tracks the ratio of concrete programmatic concepts, numbers, and proper nouns relative to overall functional filler words.
- **Implementation Strategy:** Use Python string processing or local regex-based Part-of-Speech/Keyword dictionaries to measure the semantic entity-to-token ratio.
- **Output Type:** Continuous score between 0.0 (High informational unique density / Human) and 1.0 (Low density, repetitive circular concepts / AI).

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
*Define how raw confidence scores map to meaningful certainty thresholds.*

- **Score Interpretation (e.g., 0.60):** [Explain what a score of 0.60 means to your system. Does it mean weak AI indicators? Borderline human? High variance between signals?]
- **Calibration Strategy:** [How will raw signal scores be normalized or scaled into a standard 0.0 to 1.0 scale?]
- **Threshold Classifications:**
  - **Likely AI Range:** `[Lower Bound] - [Upper Bound]` (e.g., $0.70 \le \text{score} \le 1.00$)
  - **Uncertain / Mixed Range:** `[Lower Bound] - [Upper Bound]` (e.g., $0.40 < \text{score} < 0.70$)
  - **Likely Human Range:** `[Lower Bound] - [Upper Bound]` (e.g., $0.00 \le \text{score} \le 0.40$)

---

## 3. Transparency Label Design
*Write out the exact text variants that will be returned by the API and displayed to non-technical users.*

### Variant A: High-Confidence AI Result
- **Trigger Condition:** [Specify score threshold condition]
- **Exact Label Text:** > "[Insert exact plain-language text here]"
- **Context/Explanation provided to reader:** [How does it communicate the AI origin transparently?]

### Variant B: High-Confidence Human Result
- **Trigger Condition:** [Specify score threshold condition]
- **Exact Label Text:** > "[Insert exact plain-language text here]"
- **Context/Explanation provided to reader:** [How does it communicate human origin transparently?]

### Variant C: Uncertain / Mixed Result
- **Trigger Condition:** [Specify score threshold condition]
- **Exact Label Text:** > "[Insert exact plain-language text here]"
- **Context/Explanation provided to reader:** [How does it explain the ambiguity to a non-technical reader?]

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
  [ Creator Content Submission ]
                 │
                 ▼
     ┌───────────────────────┐
     │  POST /api/submit     │ <─── Rate Limiter (Flask-Limiter)
     └───────────┬───────────┘
                 │
                 ▼
     ┌───────────────────────┐
     │  Detection Pipeline   │ ───► Run Signal 1 Heuristics
     │  & Scoring Engine     │ ───► Run Signal 2 Heuristics
     └───────────┬───────────┘
                 │
                 ▼
     ┌───────────────────────┐
     │ Transparency Label    │ ───► Append Label JSON Meta
     │   & Schema Builder    │
     └───────────┬───────────┘
                 │
                 ├──────────────────────────────┐
                 ▼                              ▼
     ┌───────────────────────┐      ┌───────────────────────┐
     │ SQLite / Memory DB    │      │  Structured Audit Log │
     │  (Store Classification)│      │  (Append Event Log)   │
     └───────────▲───────────┘      └───────────────────────┘
                 │
         [ Creator Appeal ]
                 │
                 ▼
     ┌───────────────────────┐
     │  POST /api/appeal     │ ───► Update Status: "Under Review"
     └───────────────────────┘ ───► Write Appeal Log Entry
```

### Flow Narrative
The content submission flow begins when a user submits text to the `POST /api/submit` endpoint, passing through a rate-limiting layer. The pipeline executes independent heuristic signal functions, aggregates their outputs mathematically into a 0.0–1.0 score, constructs a plain-language transparency label, saves the result to the local database, and commits a record to the structured audit log. The appeals flow is triggered via `POST /api/appeal`, where a creator submits their reason for contesting a decision; the system logs the context, updates the record's status to `"under review"`, and surfaces the transaction to the human evaluation queue.