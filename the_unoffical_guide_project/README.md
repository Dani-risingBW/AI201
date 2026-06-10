# The Unofficial Guide — Project 1

A retrieval-augmented (RAG) assistant that answers Howard University administrative
questions — financial aid, registration, campus offices, and professors — grounded
**only** in a corpus of real Howard sources. Built as: ingest → chunk → embed →
ChromaDB → retrieve → grounded Groq generation → Gradio UI.

Run it:

```bash
python pipeline.py        # ingest 12 sources -> documents/
python vector_store.py    # embed + build the ChromaDB index
python app.py             # launch the Gradio interface
```

---

## Domain

This guide covers **Howard University administration**, with a focus on financial
aid and the offices students must navigate to resolve holds, aid, and registration
issues. The motivating idea is the "Howard Runaround" — the lived experience of
being bounced between offices for answers that are technically available but hard
to find. The knowledge is valuable and hard to find through official channels
because the real answers are scattered across official pages, buried in PDFs, and
crowdsourced informally on Reddit and TikTok (e.g., the 2025 financial-aid crisis
discussion). This system gathers those scattered, mixed-formality sources into one
place a student can actually ask.

---

## Document Sources

12 sources spanning official pages, an official PDF, a downloaded Reddit feed,
student short-form video, and Rate My Professor.

| # | Source | Type | URL or file path |
|---|--------|------|-----------------|
| 1 | r/HowardUniversity (hot posts) | Reddit JSON (local) | `documents/local_reddit_hot_posts.json` |
| 2 | Howard Administration Directory | Web page | https://howard.edu/about/administration |
| 3 | Find Faculty & Staff | Web page | https://profiles.howard.edu/node/66726 |
| 4 | BisonHub Third-Party Access | PDF | https://bisonhub.howard.edu/.../Third-Party%20Accessing%20BisonHub_Final.pdf |
| 5 | Schedule a Financial Aid Appointment | Web page | https://financialservices.howard.edu/financial-aid/financial-aid-basics/how-apply-federal-aid/schedule-appointment |
| 6 | Student Financial Services (home / walk-in) | Web page | https://financialservices.howard.edu/ |
| 7 | Financial Aid landing page | Web page | https://financialservices.howard.edu/financial-aid |
| 8 | BisonHub contact matrix | Web page | https://bisonhub.howard.edu/contact |
| 9 | Online/Graduate important contacts | Web page | https://online.howard.edu/admitted/important-contacts/ |
| 10 | Registrar forms | Web page | https://howard.edu/registrar/forms |
| 11 | Student TikTok / YouTube advice | Video transcripts (yt-dlp + Whisper) | 9 videos incl. @ssanyuspeaks; see `pipeline.py` `TIKTOK_URLS` |
| 12 | Rate My Professor (Howard, School-421) | GraphQL API | https://www.ratemyprofessors.com |

---

## Chunking Strategy

**Chunk size:** 800 characters.

**Overlap:** 150 characters.

**Why these choices fit your documents:** the corpus is heterogeneous — long FAQ-
style web pages, a procedural PDF, conversational Reddit posts, and spoken-video
transcripts. 800 characters is large enough to keep a complete instruction, contact
block, or piece of advice together, but small enough to isolate a single topic so
retrieval stays focused. The 150-character overlap (~19%) preserves context across
boundaries so a sentence split mid-thought is still recoverable in the neighboring
chunk (verified: consecutive chunks repeat the trailing/leading text). Preprocessing
before chunking: HTML stripped with BeautifulSoup (script/style/nav/footer removed),
PDF text extracted with `pdfplumber`, video audio transcribed with faster-whisper,
and Reddit JSON flattened to title + body. Splitting uses
`RecursiveCharacterTextSplitter` with separators `["\n\n", "\n", " ", ""]`.

**Final chunk count:** 228 chunks across all 12 sources.

---

## Embedding Model

**Model used:** `all-MiniLM-L6-v2` via `sentence-transformers`, stored in a
persistent **ChromaDB** collection configured for **cosine** similarity
(`hnsw:space: cosine`). Retrieval returns the top **K = 4** chunks. The same model
embeds both the indexed chunks and the incoming query.

**Production tradeoff reflection:** MiniLM is small, fast on CPU, and free to run
locally — ideal for a student project. If deploying for real users with no cost
constraint, I would weigh: (1) a larger/more accurate model (e.g., `bge-large` or
an API embedding like OpenAI `text-embedding-3-large`) for better semantic recall
on domain-specific phrasing — our observed top similarities were modest (~0.3–0.77),
and a stronger model would likely separate relevant from irrelevant chunks more
cleanly; (2) longer context length, since some web pages exceed MiniLM's 256-token
window and get truncated before embedding; (3) latency and privacy — local MiniLM
keeps student data on-device, whereas an API embedding adds network latency and
sends queries to a third party. For this domain I would prioritize accuracy/recall,
accepting slightly higher latency.

---

## Grounded Generation

**System prompt grounding instruction:** the model (Groq `llama-3.3-70b-versatile`)
is given only the numbered, source-tagged context segments and instructed:

1. Answer **only** using the provided context segments; no outside or prior knowledge.
2. If the segments contain relevant information, use it (summarizing across segments,
   even informal transcripts).
3. **Only** if no segment is relevant, reply with exactly:
   *"I'm sorry, but I cannot find that information in the provided source documents."*
4. Be concise and practical; surface contacts, steps, links, templates.
5. Never invent names, offices, phone numbers, or policies not in the context.

**How source attribution is surfaced in the response:** attribution is computed
**programmatically**, not parsed from the model's text. `app.py` dedupes the
`source_origin` metadata of the chunks actually retrieved (`_dedup_sources`) and
returns them with their best similarity score. Because the list is derived from the
retrieval step rather than the LLM output, **sources cannot be hallucinated**. On a
refusal, the source list is forced to empty.

---

## Evaluation Report

Run against the live system (`app.answer_question`) on the final 228-chunk index.

| # | Question | Expected answer | System response (summarized) | Retrieval quality | Response accuracy |
|---|----------|-----------------|------------------------------|-------------------|-------------------|
| 1 | Best way to contact financial aid (first-year) | Email for a record, call for a fast response | Walk-in hours (last sign-in 3:15 PM), phone 800-822-6363, office hours, virtual chat, address | Relevant | Partially accurate |
| 2 | Who to escalate to (not the President) | "John Gordon" | Financial Aid Office phone/email + walk-in (no named individual) | Partially relevant | Inaccurate* |
| 3 | Problem with work study | Howard cut work-study amid new rules / limited funds | Refusal — no relevant content retrieved | Off-target | Inaccurate (correct refusal, but no answer given) |
| 4 | Grad student financial support resources | List of grants/aid links | Types of aid (grants, scholarships, loans), how-to-apply-for-federal-aid guide, FA website | Relevant | Partially accurate |
| 5 | Clear a financial hold on Workday | Links/steps to remove a hold | Refusal — no step-by-step content in corpus | Off-target | Inaccurate (correct refusal, but no answer given) |

\* **Q2 note:** the expected answer "John Gordon" came from an early *mock* TikTok
transcript that was later replaced with 9 real videos (Milestone 3 upgrade). The
real corpus no longer contains that name, so the system correctly declined to invent
it and returned the genuine office contacts instead. The expected answer is outdated,
not the system.

**Overall:** strong on broadly-documented financial-aid info (Q1, Q4); correctly
refuses rather than hallucinates when the corpus lacks the answer (Q3, Q5) — the
grounding guardrail working as intended.

---

## Failure Case Analysis

**Question that failed:** "Tell me more about the problem with work study" (Q3) —
and, during development, "Tell me more about the Howard University financial aid
crisis" produced a **false refusal** before a prompt fix.

**What the system returned:** Q3 returns the refusal sentence. The crisis question
*originally* returned a refusal even though the relevant transcript existed.

**Root cause (tied to a specific pipeline stage):** two distinct causes at two
stages.
1. **Generation stage (false refusal, since fixed):** the financial-aid-crisis
   transcript was retrieved at **rank 1, similarity 0.77** — retrieval succeeded.
   But the first grounding prompt was too strict and rejected the informal,
   conversational transcript as "not the answer," emitting the refusal. This was a
   *generation* failure, not retrieval.
2. **Retrieval/coverage stage (Q3, Q5):** "work study" embeds near the literal words
   "work" and "study," so MiniLM pulled the faculty directory and professor reviews
   instead of aid-policy text; combined with the fact that the corpus has little to
   no document actually describing the work-study cut or Workday hold-clearing steps,
   the top-K context was genuinely irrelevant and the system refused.

**What you would change to fix it:** (1) For the false refusal — loosen the grounding
instruction to "use relevant context even if informal; refuse only if nothing is
relevant" (done; the crisis question now answers correctly while the off-topic pizza
test still refuses). (2) For the coverage gaps — add targeted documents (a work-study
FAQ, a "clear a financial hold" guide), raise K to 6–8 so short high-value chunks
survive, and/or add a small similarity floor with a stronger embedding model to cut
lexical drift on terms like "work study."

---

## Spec Reflection

**One way the spec helped you during implementation:** the `planning.md` architecture
diagram (ingest → chunk → embed → ChromaDB → retrieve → Groq) and its concrete
parameters (chunk 800/overlap 150, `all-MiniLM-L6-v2`, K=4, cosine,
`llama-3.3-70b-versatile`) acted as a precise build spec. Each module was implemented
directly against it, and the chunk settings were *imported* from the ingestion code
into the embedding code so the spec stayed the single source of truth and the two
stages could never drift.

**One way your implementation diverged from the spec, and why:** several sources
needed handling the spec under-specified. The Rate My Professor school id in the plan
(407) was wrong — Howard is actually `School-421`, and the `RateMyProfessorAPI`
library was broken, so I queried RMP's GraphQL endpoint directly. The TikTok stage
was a hardcoded mock in early development; it was upgraded to real `yt-dlp` +
`faster-whisper` transcription (requiring `curl_cffi` impersonation and the
`download` format, because TikTok's default stream is video-only). The PDF source,
originally parsed as HTML (producing binary garbage), was switched to `pdfplumber`.
These diverged from the literal plan because the real sources behaved differently
than assumed, but each change served the spec's intent — a clean, multi-format corpus.

---

## AI Usage

**Instance 1 — Ingestion + Rate My Professor**

- *What I gave the AI:* my draft `pipeline.py` and the planning.md sources/chunking
  sections, and asked it to make the pipeline run and persist scraped data to
  `documents/`.
- *What it produced:* fixes for a crash bug and the Reddit path, a `pdfplumber`-based
  PDF extractor (replacing HTML parsing that yielded binary garbage), and a direct
  GraphQL Rate My Professor fetcher after diagnosing that the library was broken and
  the school id was wrong (407 → 421).
- *What I changed or overrode:* I directed the RMP feature to support both an explicit
  professor name list **and** an automatic top-N, and chose `most_rated` ranking;
  I set the professor list (e.g., Legand Burge) and the top-N parameters.

**Instance 2 — Grounded generation + interface**

- *What I gave the AI:* my grounding/guardrail requirements (answer only from context,
  exact refusal sentence, programmatic source attribution) and a Gradio skeleton.
- *What it produced:* `app.py` with the Groq `llama-3.3-70b-versatile` call, a context
  assembler, programmatic deduplicated source attribution, and the Gradio Blocks UI.
- *What I changed or overrode:* after testing showed a **false refusal** on a question
  whose answer was retrieved at rank 1, I had the grounding prompt loosened so it uses
  relevant-but-informal context while still refusing genuinely off-topic questions —
  verified against the 5 evaluation questions and an out-of-domain control.
