# Project Planning Template: Community Classification Task

This document serves as the planning blueprint for designing, collecting, annotating, and evaluating a text classification model tailored to a specific online community. 

---

## 1. Community Selection
* **What community did you choose and why?**
  *https://www.reddit.com/r/ArtificialInteligence/ 
  I choose an artifical intelligence reddit forum. My personal reason for choosing it is because it is related to AI and I give me more of a reason to learn by researching forums on reddit about that things going on in the world and the facts and opinions of my people in real time.*
* **Why is this community a good fit for a classification task?**
  * *With AI advancing, information gets quickly filler by fact or opinion. Now in days, facts quickly become later proven false. This community is a good fit for a classification task because it helps filter out the communities opinions and just understand the true facts about AI. Or on the other coin, sometimes people just want to listen to what other people have to say about AI.*

---

## 2. Labels & Annotation Guide
* **Label Definitions:**
  * **Label 1: [Question/Opinion]** — *A questiong is a linguistic or conceptual expression used to seek information, clarification, or provoke thought; an expresion used for exploration, understanding or obtaining information. An opinion being a personal belief, viewpoint, or judgment about a topic, expressed clearly and supported with reasons or evidence sometimes with persuasive intent.*
  * **Label 2: [AI_Info/News]** — *writing designed to provide factual information about a specific topic to educate or inform the reader; writing with the purpose to infrom, explain, describe, or report factual information.*
  
  

* **Example Posts per Label:**
  * **Label 1:**
    1. *If one of the issues with DatCenters is water usage, why not incorporate desalination into the water cooling systems and build the data centers near the ocean or other major sources of salt water.
    The 'waste stream' of the data center would be water that could then be added to the municipal water system.*

    2. *As I look at the scale of the data center build out and the controversies it’s stirring up, it doesn’t seem to be factoring in how LLM workflows are changing and the possibility of local models bearing the brunt of processing on-device.

    If you look at the processors being installed on today’s Macs and iPhones, they’re very well equipped to handle a smaller LLM, maybe a 3b or even 8b.

    For companies that are charging for tokens instead of value, this represents an existential threat, since LLMs haven’t quantified their value beyond tokens. At present, it’s like the business is more about renting compute than delivering value and the models are just the way to bring in customers, which could easily be upended by more powerful processors and models installed on locally as part of the OS.*
  * **Label 2:**
    1. *Trump tells Axios he no longer views Anthropic as national security threat
    https://www.reuters.com/world/us/trump-tells-axios-he-no-longer-views-anthropic-national-security-threat-2026-06-19/*
    2. *Five Chinese AI labs cut inference token prices in a single week, with the steepest reductions reported up to 99%. It is the latest escalation in a domestic price war as labs fight for developer share.

    The second-order effect is the interesting one: when frontier-ish inference trends toward nearly free, the moat stops being the model and moves to distribution, tooling, and whatever sits on top. Cheap tokens pull a lot of applications that were marginal at current prices into being viable.

    Source : https://aiweekly.co/alerts/five-chinese-ai-labs-cut-token-prices-up-to-99*

 

---

## 3. Hard Edge Cases & Boundary Disambiguation
* **What type of post will be genuinely ambiguous between two labels?**
  * *A post will be genuinely ambiguous when it is formatted as an AI Info/News update (e.g., sharing a new product release, benchmark score, or a link to an article) but the user heavily infuses their personal speculation, subjective analysis, or a direct question into the post body. For example, a post titled "OpenAI releases new model XYZ" that spends three paragraphs discussing personal theories on why the model might fail, or a post that copies and pastes a factual news snippet but structures the entire post around asking the community "Is this true, or is this just hype?" creates a heavy overlap between raw factual reporting and subjective community opinion.*
* **How will you handle it when you encounter it during annotation?**
  * *To ensure consistency, the following deterministic tie-breaking rules will be applied:

The Primary Intent Rule: If the post starts with factual news but shifts into a personal rant, subjective critique, or prediction, classify it as Label 1 [Question/Opinion] if the subjective text takes up more than 50% of the post volume.

The Call-to-Action / Question Dominance Rule: If a post contains factual news but concludes with a direct question prompting community discussion (e.g., "What do you all think this means for the future?"), it must be classified as Label 1 [Question/Opinion], as the core purpose of the post is to invite opinion rather than simply inform.

The "Pure Source" Exception: If the post simply links to a news source or copies a headline/press release verbatim with negligible commentary (less than 1-2 sentences of personal thoughts), it will automatically be classified as Label 2 [AI_Info/News].*

---

## 4. Data Collection Plan
* **Where will you collect examples?**
  * *I could use a scraping tool called Apify that should pull data into a csv file.*
* **Target Sample Size:**
  * *Target sample size: 200*
* **Contingency Strategy for Underrepresented Labels:**
  * **What will you do if a specific label is heavily underrepresented after reviewing 200 total raw examples?**
    * *If a standard sequential scrape leaves one label heavily underrepresented, I will use a multi-tiered targeted collection strategy to balance the dataset:

    Targeted Subreddit Flairs: The r/ArtificialInteligence community uses mandatory flairs. If Label 2 [AI Info/News] is underrepresented, I will configure Apify or run a custom search to specifically scrape posts tagged with the News, Research, or New Model/Tool flairs. Conversely, if Label 1 [Question/Opinion] is lagging, I will pull directly from the Question, Analysis/Opinion, or Discussion flairs.

    Algorithmic Search Filtering (Keyword Seeding): I will execute search-based scraping using strict linguistic anchors. For Label 1, I will query terms that trigger debate or inquiry (e.g., "should we", "does anyone else", "in my opinion", "what are your thoughts"). For Label 2, I will search for objective source indicators (e.g., "source:", "breakthrough", "announced", "v2", or URL strings like "arxiv.org" or "reuters.com").

    Sorting Parameter Pivots: If a standard "New" stream yields a massive imbalance of low-effort opinion posts, I will shift my collection parameters to "Top (Past Month)" or "Hot". Factual news, research breakthroughs, and major industry announcements heavily dominate the top-voted slots, making it a highly efficient way to instantly surface missing Label 2 instances.*

### 4.5 Baseline Evaluation Reflection (Zero-Shot vs. Prompt Constraints)

* **Performance Metrics:** 
  * Baseline Accuracy: 80.3% (76/76 parseable responses)
  * Class 0 (Question/Opinion) F1-Score: 0.85 (Recall: 0.78, Precision: 0.93)
  * Class 1 (AI_Info/News) F1-Score: 0.71 (Recall: 0.86, Precision: 0.60)

* **Error Analysis & Insights:**
  The baseline model achieved high recall for `AI_Info/News` (0.86), meaning it successfully caught almost all factual updates. However, it suffered from a severe precision bottleneck (0.60), resulting in a 40% false positive rate for news items. This directly stems from the underlying class imbalance in the community dataset (~71% conversational posts). The zero-shot model routinely got "blinded" by early factual references or linked articles, completely overlooking the user's trailing commentary or open-ended questions. 

* **Tightening the Guardrails:**
  To mitigate this precision trap, the system prompt was upgraded to a few-shot framework. By embedding explicit negative examples that demonstrate the *Primary Intent (50% Volume Rule)* and *Call-to-Action Rule* in action, the model is forced to evaluate text volume and conversational syntax before aggressively guessing the news label. This step isolates true high-signal information updates from highly subjective community chatter, creating a robust target column for subsequent DistilBERT fine-tuning.
---

## 5. Evaluation Metrics
* **Selected Metrics & Justification:**
  * *Macro F1-Score: I will use the Macro F1-Score as my primary success metric. This calculates the harmonic mean of precision and recall for both classes independently and then averages them equally. It forces the model to perform well on both labels rather than letting a high performance on a dominant class mask a failing grade on a rarer class.

  Classification Accuracy: I will track overall accuracy as my baseline trend metric. It represents the simple percentage of total posts correctly categorized out of the entire sample, allowing me to easily track stability and baseline progress during the training epochs in Google Colab.

  Per-Class Precision & Recall: I will calculate precision and recall specifically for each individual label to track behavioral vulnerabilities. Precision reveals how many predicted flags are actually correct, while recall measures how many true instances the model managed to capture out of everything available.*
* **Why are these the right metrics for this specific task?**
  * *Accuracy alone is entirely insufficient for this task because Reddit data is naturally unpredictable and highly prone to class imbalance. If 80% of the posts pulled from r/ArtificialInteligence are community opinions, a broken model that lazily predicts [Question/Opinion] for every single post will achieve a misleadingly high accuracy of 80% while being completely useless at extracting actual news.

  Furthermore, false positives and false negatives carry distinct consequences for the downstream utility of this classifier:

  A False Positive for News (predicting News when it is actually an Opinion) pollutes the factual data stream with subjective speculation, defeatist rants, or unverified community hype—defeating the core purpose of filtering out the noise.

  A False Negative for News (predicting Opinion when it is actually News) means a user completely misses out on a real-time factual breakthrough, research paper, or industry update because it was mistakenly filtered away into the discussion bucket.

  Tracking the balance between Precision and Recall ensures the classifier remains both highly accurate and highly reliable for the community.*

---

## 6. Definition of Success
* **Operational Usefulness:**
  * *This classifier becomes genuinely useful by acting as an automated, objective, real-time content filter for the community. Rather than relying on unreliable user-selected flairs or manual moderator review, the model instantly scans incoming text to separate raw data from personal commentary. The tool ensures that any post routed into the factual stream is pristine and noise-free. This allows researchers and enthusiasts to read a pure digest of verified advancements, while simultaneously isolating community rants, questions, and speculations into a dedicated discussion hub.*
* **Deployment Threshold ("Good Enough"):**
  * *To deploy this model into production, it must meet the following precise quantitative benchmarks on the validation dataset:Primary Metric: A Macro F1-Score of $\ge$ 0.82, ensuring strong mathematical performance across both classes regardless of any underlying data imbalance.Class-Specific Error Constraint: A Precision score of $\ge$ 0.85 on Label 2 [AI Info/News]. This strictly mandates that no more than 15% of the posts labeled as news can be false positives (opinions leaking into the news feed). To enforce this behavior, the model's prediction probability threshold for Label 2 will be raised from the default $0.50$ to $0.70$.Baseline Benchmark: The model must outscore a simple zero-intelligence majority-class guessing baseline by at least 35% on Macro F1.*
* **Evaluation Plan Review:**
  * *Yes, these success criteria are highly specific, completely quantifiable, and entirely objective. A independent third party could seamlessly take the final predictions, run them through scikit-learn's classification report, and look at three explicit numbers: the Macro F1-score, the precision rate for Label 2, and the final classification matrix. There is zero room for subjective bias—the model either hits the 0.82 Macro F1 and 0.85 News Precision baselines, or it fails.*

---

## 7. AI Tool Plan

### A. Label Stress-Testing
* **Prompting Strategy:**
  * *
  You are a cold, deterministic data labeling pipeline for r/ArtificialInteligence text classification. Analyze the following Reddit post text and map it to exactly one of these two categories:
  - `0` for [Question/Opinion]
  - `1` for [AI_Info/News]

  ### Core Annotation Rules:
  1. **Primary Intent (50% Volume Rule):** If a post blends news and personal critique, calculate the visual/text volume. If subjective speculation or critique takes up 50% or more of the text block, label it `0`. 
  2. **Call-to-Action Rule:** If a post presents a news event but actively concludes by prompting community engagement, opinions, or open-ended questions (e.g., "Thoughts?"), label it `0`.
  3. **Pure Source Rule:** Verbatim headlines, links, change-logs, or news snippets with minimal commentary (under 2 sentences) must be labeled `1`.

  ### Hard Edge-Case Rules:
  - Hypothetical industry speculation masquerading as news (e.g., "Rumor: Model X drops tomorrow, here is why it will fail") = Label `0`.
  - Corporate press-releases formatted natively without explicit outbound links = Label `1`.

  ### Output Format:
  Return ONLY a valid, minified JSON object matching this schema. Do not include markdown formatting, pleasantries, or text before/after the JSON.
  {"label": <0 or 1>, "confidence": <float between 0.0 and 1.0>, "applied_rule": "<Brief sentence stating which rule or edge case broke the tie>"}

  ### Post Text to Process:
  """
  [
  {
    "post_title": "Do you believe AI will leave humans extinct?",
    "post_body": "So many people believe AI will leave people unemployed or have society fall in love with chatbots, but there needs to be more mainstream dialogue around the idea that this could literally cause human life to be extinct... How likely do you believe that within our lifetimes (so the next 50-75 years), AI will leave the human race either extinct or cause close to a mass extinction?"
  },
  {
    "post_title": "Australian MP Andrew Hastie compares AI race to Cold-War nuclear arms race",
    "post_body": "Australian Liberal MP Andrew Hastie has compared the global AI competition to the Cold War nuclear arms race. He warned that Australia risks its sovereignty and strategic independence being constrained by AI superpowers... Source: https://www.theguardian.com/australia-news/2026/jun/15/andrew-hastie-ai-artificial-intelligence-power-cold-war-nuclear-arms-race-comparison-australia"
  }
]
  """*
* **Refinement Loop:**
  * *During bulk data processing, the 71% class imbalance revealed a critical semantic overlap: many users post objective, high-signal project releases or step-by-step tutorials, but frame them using personal pronouns (e.g., "I built an open-source tool, what do you think?"). To keep the factual data pool clean without completely starving the dataset of technical contributions, the text volume rule was tightened: explicit tool deployment documentation, code repositories, or step-by-step technical guides are categorized under Label 1 (AI_Info/News) even if they include brief conversational filler, provided an outbound project destination URL or reproducible framework code block is present.*

### B. Annotation Assistance
* **Pre-Labeling Framework:**
  * *I will use a programmatic zero-shot LLM framework to automate the baseline labeling pass across the dataset. The specific foundation architecture used is Llama 3.3 70B accessed via the Groq API (llama-3.3-70b-versatile). This model was selected due to its highly optimized inference speeds, massive context parsing window, and native JSON mode configuration, which allows for clean bulk dataset handling at zero cost under the platform's free tier.*
* **Traceability & Disclosure:**
  * *To maintain strict transparency, accountability, and traceability throughout the engineering pipeline, the dataset's structural schema handles tracking dynamically. The document contains an explicit, dedicated notes column mapped directly alongside the label targets. Whenever an entry is evaluated by the Groq API, the script forces the LLM to record a structural string log detailing the exact decision heuristic or rule exception applied (e.g., "Call-to-Action Rule applied"). Any manual overrides, hard-coded adjustments, or human verifications will have their notes cell explicitly modified to read "Human Verified," ensuring an auditor can seamlessly separate human ground-truth labels from synthetic classifications in the final AI usage appendix.*

### C. Failure Analysis
* **Error Pattern Extraction:**
  * *I Plan to give my list wrong  predictions to an AI tool and feed them into an AI tool to isolate thematic or structural patterns in the errors.*
* **Human Verification Plan:**
  * *To ensure the AI-synthesized error patterns are grounded in reality rather than hallucinated trends, I will execute a rigorous three-step human validation check before compiling the final evaluation report:

  Random Ground-Truth Spot Checks: From each distinct error category the AI claims to identify (e.g., if the AI claims "The model consistently misclassifies news posts containing exclamation marks"), I will randomly pull 3–5 raw text examples from that specific subset in the dataset. I will manually read them to verify if that structural pattern actually exists or if the AI is over-generalizing a fluke.

  Confusion Matrix Mapping: I will match the AI’s qualitative feedback against a quantitative confusion matrix generated in Google Colab. If the AI asserts that the model is struggling with "short news snippets with links," I must see a corresponding mathematical dip in the Precision score of Label 2 [AI Info/News]. If the metrics do not back up the AI's structural claims, the pattern will be rejected.

  Rule Set Stress Test: I will take the top two most prevalent failure modes identified by the AI and cross-reference them directly against my Part 3 Boundary Disambiguation rules. This check will determine if the failure happened because the DistilBERT model lacked capacity, or if my original instructions in the annotation guide were too weak or mathematically contradictory, allowing me to definitively assign the root cause of the error.*


  