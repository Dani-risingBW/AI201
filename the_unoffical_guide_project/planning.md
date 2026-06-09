# Project 1 Planning: The Unofficial Guide

> Write this document before you write any pipeline code.
> Your spec and architecture diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Update the Retrieval Approach and Chunking Strategy sections if you change your approach during implementation.
> Update this file before starting any stretch features.

---

## Domain

<!-- What domain did you choose? Why is this knowledge valuable and hard to find through official channels? -->
I chose to create an unofficial guide through Howard University administration. This all started because of the term "the Howard Runaround", which states that the only way around financial aid or any type of administrative help leds to the student having to run around the university to find that answer. Often caused by administration themselves due to understaff, lack of knowledge, or overall lack of care of the students. I wanted to create a domain that helps answers questions that we all may need faster than you can say "Howard Run around" because trust me -- all questions have been answered, just the hard way. So let us make it easy. 

---

## Documents

<!-- List your specific sources: URLs, subreddit names, forum threads, or file descriptions.
     Aim for at least 10 sources that together cover different subtopics or perspectives within your domain. -->

| # | Source | Description | URL or location |
|---|--------|-------------|-----------------|
| 1 |r/HowardUniversity Subreddit (Hot Posts) |The unofficial student forum where current and prospective Bison crowdsource real-time advice on housing, financial aid delays, professors, and campus life — capturing candid perspectives the official channels rarely publish. |https://www.reddit.com/r/HowardUniversity/hot/ |
| 2 |Howard University Administration Directory |The official roster of senior university leadership and administrative offices, useful for identifying who is responsible for which division when routing questions or escalations. |https://howard.edu/about/administration |
| 3 |Find Faculty and Staff at Howard |The searchable university profiles directory for locating faculty and staff by name, school, department, or area of expertise, including contact details and research focus. |https://profiles.howard.edu/node/66726?search=&school=All&department=&type=All&expertise=All |
| 4 |The BisonHub/Workday Third-Party Job Aid (PDF) |The official university training document detailing exactly how the new BisonHub portal processes third-party or "proxy" authorization for parents/guardians to view student finances and pay bills. |https://bisonhub.howard.edu/sites/bisonhub.howard.edu/files/2024-08/Third-Party%20Accessing%20BisonHub_Final.pdf |
| 5 |Virtual Chat & In-Person Counselors Queue Hub |The scheduling page for booking financial aid appointments and accessing virtual chat or in-person counselor queues, outlining how students reach an advisor for federal aid questions. |https://financialservices.howard.edu/financial-aid/financial-aid-basics/how-apply-federal-aid/schedule-appointment |
| 6 |Office Hours & Walk-In Sign-In Policy Guide |The main Office of Financial Services hub describing office hours, walk-in sign-in procedures, and the policies governing how students access in-person support. |https://financialservices.howard.edu/ |
| 7 |The Official Financial Aid Office Landing Page |The authoritative starting point for financial aid information — eligibility, application steps, disbursement, and deadlines — serving as the canonical reference for aid-related answers. |https://financialservices.howard.edu/financial-aid |
| 8 |Campus Operations Central Contact Matrix |The BisonHub contact directory mapping common student-services issues to the correct office, phone number, and email, so questions can be routed to the right department. |https://bisonhub.howard.edu/contact |
| 9 |Graduate & Distance Learning Key Contacts Directory |The contacts list for admitted online and graduate students, identifying the advisors and support offices specific to distance-learning programs. |https://online.howard.edu/admitted/important-contacts/ |
| 10 |Howard Forms |The Office of the Registrar's repository of official forms (enrollment, registration, records changes, verification) detailing which document each academic process requires. |https://howard.edu/registrar/forms |
| 11 |Howard TikTok Advice |The #howarduniversity TikTok feed, an unofficial source of short-form student-generated tips, campus culture, and lived-experience advice not found in official documentation. |https://www.tiktok.com/tag/howarduniversity |
| 12 |Rate my professor |Get student feedback on the course, rigor, and character of professors |https://www.ratemyprofessors.com/|
---

## Chunking Strategy

<!-- How will you split documents into chunks?
     State your chunk size (in tokens or characters), overlap size, and explain why those
     numbers fit the structure of your documents.
     A review-heavy corpus warrants different chunking than a long FAQ. -->

**Chunk size:**
 Chunk size: 500 to 800 characters. 

**Overlap:**
100 to 150 characters. 

**Reasoning:**
I will start with medium-sized chunks so that it is long enough to hold email templates or solutions but small enough to isolate topics. Solutions do not need to long of an answer. The overlap size is to ensure the context is not lost.

---

## Retrieval Approach

<!-- Which embedding model are you using (e.g., all-MiniLM-L6-v2 via sentence-transformers)?
     How many chunks will you retrieve per query (top-k)?
     If you were deploying this for real users and cost wasn't a constraint, what tradeoffs
     would you weigh in choosing a different embedding model — context length, multilingual
     support, accuracy on domain-specific text, latency? -->

**Embedding model:**
sentence-transformers (all-MiniLM-L6-v2)

**Top-k:**
K = 4 or 5

**Production tradeoff reflection:**
For my Howard University administrative Guide, I want accuracy to be my highest priority so I would want a slightly higher K score. I understand that this will take the model a little longer to compute which is find becuase we want it more accurate than fast. 

---

## Evaluation Plan

<!-- List your 5 test questions with their expected correct answers.
     Questions should be specific enough that you can judge whether the system's response
     is right or wrong. "What are good dining halls?" is too vague.
     "What do students say about wait times at [dining hall name] during lunch?" is testable. -->

| # | Question | Expected answer |
|---|----------|-----------------|
| 1 |What is the best way to contact financial aid as a first-year student? |It is best to leave an email for documentation but calling for an immediate response. |
| 2 |Who should I contact that is high enough for a response but not the President of Howard University for financial aid? |John Gordon |
| 3 |Tell me more about the problem with work study |Howard university current revoked many students work study due to new regulations and limited finances |
| 4 |Advice for a graduate student finding resources for financial support| A list of resources such as grants that students can apply to or financial aid links for further assistance|
| 5 |How to clear financial hold on workday |Links and steps to contacting someone or an already written guide from many sources on how to remove a financial hold |

---

## Anticipated Challenges

<!-- What could go wrong? Name at least two specific risks with reasoning.
     Consider: noisy or inconsistent documents, missing source attribution, off-topic
     retrieval, chunks that split key information across boundaries. -->

1. It may also cause a run around because most of the resources are from Howard Univeristy. The accuracy may be high but I not too sure on if the question is actually answered. 

2. The model may be too slow at retrieval and processing because it has a lot to read or it may not know how to read the different materials. My documents vary from short form videos to pdfs with images. 

---

## Architecture

<!-- Draw a diagram of your pipeline showing the five stages:
     Document Ingestion → Chunking → Embedding + Vector Store → Retrieval → Generation
     Label each stage with the tool or library you're using.
     You can use ASCII art, a Mermaid diagram, or embed a sketch as an image.
     You'll use this diagram as context when prompting AI tools to implement each stage. -->

---

## AI Tool Plan

<!-- For each part of the pipeline below, describe:
     - Which AI tool you plan to use (Claude, Copilot, ChatGPT, etc.)
     - What you'll give it as input (which sections of this planning.md, which requirements)
     - What you expect it to produce
     - How you'll verify the output matches your spec

     "I'll use AI to help me code" is not a plan.
     "I'll give Claude my Chunking Strategy section and ask it to implement chunk_text()
     with my specified chunk size and overlap" is a plan. -->

**Milestone 3 — Ingestion and chunking:**

**Milestone 4 — Embedding and retrieval:**

**Milestone 5 — Generation and interface:**
