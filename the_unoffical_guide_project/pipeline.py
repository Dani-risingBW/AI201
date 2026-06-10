"""Milestone 3 — ingestion & chunking pipeline for The Unofficial Guide.

Loads the 12 designated sources (local Reddit JSON, live web pages, a PDF,
a short-form transcript, and Rate My Professor), persists each ingested source
to documents/, then chunks everything with RecursiveCharacterTextSplitter.
"""

import os
import io
import re
import json
import requests
import pdfplumber
from bs4 import BeautifulSoup
from langchain_text_splitters import RecursiveCharacterTextSplitter

# ==========================================
# 0. PATHS (resolve relative to this file so the pipeline runs from anywhere)
# ==========================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOCUMENTS_DIR = os.path.join(BASE_DIR, "documents")
os.makedirs(DOCUMENTS_DIR, exist_ok=True)

# ==========================================
# 1. SPECIFICATION PARAMETERS (From planning.md)
# ==========================================
CHUNK_SIZE = 800
CHUNK_OVERLAP = 150

# Map out your designated 12 system sources
SOURCES = {
    "1_r_howard_university": "local_reddit_hot_posts.json",  # Downloaded JSON endpoint (lives in documents/)
    "2_hu_administration": "https://howard.edu/about/administration",
    "3_find_faculty": "https://profiles.howard.edu/node/66726",
    "4_bisonhub_pdf": "https://bisonhub.howard.edu/sites/bisonhub.howard.edu/files/2024-08/Third-Party%20Accessing%20BisonHub_Final.pdf",
    "5_queue_hub": "https://financialservices.howard.edu/financial-aid/financial-aid-basics/how-apply-federal-aid/schedule-appointment",
    "6_walk_in_policy": "https://financialservices.howard.edu/",
    "7_finaid_landing": "https://financialservices.howard.edu/financial-aid",
    "8_bisonhub_matrix": "https://bisonhub.howard.edu/contact",
    "9_distance_contacts": "https://online.howard.edu/admitted/important-contacts/",
    "10_registrar_forms": "https://howard.edu/registrar/forms",
    "11_tiktok_advice": "MOCK_TIKTOK_TRANSCRIPT_11",  # Handled via short-form speech proxy
    "12_rate_my_professor": "Howard University Faculty"  # Trigger for RMP API pipeline
}

# --- Source 12: Rate My Professor selection ---
# (a) Explicit names — looked up individually (use the exact RMP spelling).
#     Add as many names as you like; each is fetched and added to source 12.
PROFESSORS_TO_SCRAPE = ["Legand Burge"]
# (b) Automatic top-N — also pull the N highest-ranked Howard professors with no
#     names needed. Set RMP_TOP_N = 0 to disable and use only the list above.
RMP_TOP_N = 5
RMP_POOL_SIZE = 300          # candidate professors fetched, then ranked locally
RMP_MIN_RATINGS = 5          # ignore sparsely-rated profs when picking top-N
RMP_RANK_BY = "most_rated"   # "most_rated" (numRatings) or "highest_rated" (avgRating)

# ==========================================
# 2. RATE MY PROFESSOR INGESTION MODULE (direct GraphQL — the pip library is broken)
# ==========================================
# RMP exposes a public read-only GraphQL endpoint. The library `RateMyProfessorAPI`
# no longer authenticates against it, so we query it directly with the public token.
RMP_GRAPHQL_URL = "https://www.ratemyprofessors.com/graphql"
RMP_HEADERS = {
    "Authorization": "Basic dGVzdDp0ZXN0",  # RMP's public read-only basic-auth token
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (HowardGuideBot Educational Project)",
}
HOWARD_SCHOOL_ID = "U2Nob29sLTQyMQ=="  # base64 of "School-421" = Howard University

def _rmp_query(query: str, variables: dict) -> dict:
    """Posts a GraphQL query to RMP and returns the parsed JSON."""
    resp = requests.post(
        RMP_GRAPHQL_URL, headers=RMP_HEADERS,
        json={"query": query, "variables": variables}, timeout=20
    )
    resp.raise_for_status()
    return resp.json()

# Field set shared by name-lookup and top-N pool queries.
_TEACHER_FIELDS = (
    "id firstName lastName department avgRating avgDifficulty numRatings wouldTakeAgainPercent"
)

def _lookup_teacher_by_name(name: str):
    """Finds a single Howard professor node by name (first match), or None."""
    q = (
        "query T($q: TeacherSearchQuery!){ newSearch{ teachers(query: $q){ edges{ node{ "
        + _TEACHER_FIELDS + " } } } } }"
    )
    try:
        data = _rmp_query(q, {"q": {"text": name, "schoolID": HOWARD_SCHOOL_ID}})
        edges = data.get("data", {}).get("newSearch", {}).get("teachers", {}).get("edges", [])
    except Exception as e:
        print(f"  RMP request failed for {name}: {e}")
        return None
    if not edges:
        print(f"  Could not retrieve profile data for {name}.")
        return None
    return edges[0]["node"]

def _fetch_top_teachers(n: int, pool_size: int, min_ratings: int, rank_by: str):
    """Fetches a pool of Howard professors and returns the top-n ranked nodes."""
    q = (
        "query P($q: TeacherSearchQuery!, $n: Int!){ newSearch{ teachers(query: $q, first: $n){ "
        "edges{ node{ " + _TEACHER_FIELDS + " } } } } }"
    )
    try:
        data = _rmp_query(q, {"q": {"text": "", "schoolID": HOWARD_SCHOOL_ID}, "n": pool_size})
        nodes = [e["node"] for e in
                 data.get("data", {}).get("newSearch", {}).get("teachers", {}).get("edges", [])]
    except Exception as e:
        print(f"  RMP top-N pool request failed: {e}")
        return []

    # Only rank professors with enough reviews to be meaningful.
    nodes = [t for t in nodes if (t.get("numRatings") or 0) >= min_ratings]
    if rank_by == "highest_rated":
        nodes.sort(key=lambda t: (t.get("avgRating") or 0, t.get("numRatings") or 0), reverse=True)
    else:  # "most_rated"
        nodes.sort(key=lambda t: (t.get("numRatings") or 0, t.get("avgRating") or 0), reverse=True)
    return nodes[:n]

def _format_professor_dossier(node: dict) -> str:
    """Builds the dossier text (metrics + student comments) for one professor."""
    ratings_query = (
        "query R($id: ID!){ node(id: $id){ ... on Teacher{ ratings(first: 20){ edges{ node{ "
        "class comment clarityRating difficultyRating wouldTakeAgain date "
        "} } } } } }"
    )
    full_name = f"{node['firstName']} {node['lastName']}"
    text = f"\n\n[RATE MY PROFESSOR DOSSIER: {full_name}]\n"
    text += f"Department: {node['department']} | Overall Rating: {node['avgRating']}/5\n"
    text += f"Difficulty Index: {node['avgDifficulty']}/5\n"
    text += f"Total Student Ratings: {node['numRatings']}\n"
    wta = node.get("wouldTakeAgainPercent")
    if wta is not None and wta >= 0:
        text += f"Would Take Again: {round(wta, 1)}%\n"

    # Append individual textual evaluations
    text += "Student Comments & Evaluations:\n"
    try:
        rdata = _rmp_query(ratings_query, {"id": node["id"]})
        rating_edges = rdata.get("data", {}).get("node", {}).get("ratings", {}).get("edges", [])
        for r in rating_edges:
            rn = r["node"]
            comment = (rn.get("comment") or "").strip().replace("\n", " ")
            text += (
                f"- (Course: {rn.get('class', 'N/A')}) Rating: {rn.get('clarityRating', '?')}/5. "
                f"Difficulty: {rn.get('difficultyRating', '?')}/5. Comment: {comment}\n"
            )
    except Exception as e:
        print(f"  Could not fetch individual ratings for {full_name}: {e}")
    return text

def scrape_ratemyprofessor_data(target_professors, top_n: int = RMP_TOP_N) -> str:
    """
    Queries Rate My Professors' GraphQL API for Howard University (School-421).
    Combines (a) any explicitly named professors with (b) the automatic top-N
    ranked Howard professors, de-duplicates them, and compiles metrics +
    student comments for chunk injection.
    """
    print("Connecting to RateMyProfessors GraphQL API...")

    selected = []        # ordered list of teacher nodes
    seen_ids = set()

    # (a) Explicit names first (exact RMP spelling)
    for prof_name in target_professors:
        print(f"Looking up named professor: {prof_name}...")
        node = _lookup_teacher_by_name(prof_name)
        if node and node["id"] not in seen_ids:
            selected.append(node)
            seen_ids.add(node["id"])

    # (b) Automatic top-N Howard professors
    if top_n and top_n > 0:
        print(f"Fetching top {top_n} Howard professors (ranked by {RMP_RANK_BY})...")
        for node in _fetch_top_teachers(top_n, RMP_POOL_SIZE, RMP_MIN_RATINGS, RMP_RANK_BY):
            if node["id"] not in seen_ids:
                selected.append(node)
                seen_ids.add(node["id"])

    compiled_rmp_data = ""
    for node in selected:
        print(f"  Compiling dossier: {node['firstName']} {node['lastName']} "
              f"({node['numRatings']} ratings, {node['avgRating']}/5)")
        compiled_rmp_data += _format_professor_dossier(node)

    return compiled_rmp_data

# ==========================================
# 3. OTHER LOADER MODULES (Reddit, Web, Media)
# ==========================================
def parse_local_reddit_json(file_path: str) -> str:
    """Reads a local downloaded Reddit .json file and extracts text."""
    if not os.path.exists(file_path):
        return "Mock Reddit Content: Current financial aid holds require walk-ins at the administration building before 3:15 PM."

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    compiled_text = ""
    posts = data.get("data", {}).get("children", [])
    for post in posts:
        post_data = post.get("data", {})
        compiled_text += f"\n\nReddit Post Title: {post_data.get('title', '')}\n"
        compiled_text += f"Content: {post_data.get('selftext', '')}"
    return compiled_text

def scrape_and_clean_web(url: str) -> str:
    """Fetches web HTML, strips template noise, and returns plain text."""
    headers = {"User-Agent": "HowardGuideBot/1.0 (Educational Project context)"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return f"Placeholder content for inaccessible page: {url}"

        soup = BeautifulSoup(response.text, "html.parser")
        for element in soup(["script", "style", "nav", "footer", "header"]):
            element.decompose()

        return re.sub(r'\s+', ' ', soup.get_text(separator=" ")).strip()
    except Exception as e:
        print(f"Failed parsing {url}: {e}")
        return ""

def scrape_pdf(url: str) -> str:
    """Downloads a PDF and extracts real text with pdfplumber (BeautifulSoup
    can't read PDFs — it would return raw binary stream data)."""
    headers = {"User-Agent": "HowardGuideBot/1.0 (Educational Project context)"}
    try:
        response = requests.get(url, headers=headers, timeout=20)
        if response.status_code != 200:
            return f"Placeholder content for inaccessible PDF: {url}"

        pages = []
        with pdfplumber.open(io.BytesIO(response.content)) as pdf:
            for page in pdf.pages:
                pages.append(page.extract_text() or "")

        return re.sub(r'\s+', ' ', "\n".join(pages)).strip()
    except Exception as e:
        print(f"Failed parsing PDF {url}: {e}")
        return ""

# ==========================================
# 3b. PERSISTENCE — write every ingested source into the documents/ folder
# ==========================================
def persist_scraped_documents(loaded_documents: dict) -> None:
    """Saves each ingested source's text to documents/<source_id>.txt so the
    scraped corpus is captured on disk (alongside the raw Reddit JSON)."""
    print("\n=== Persisting ingested sources to documents/ ===")
    for source_id, text in loaded_documents.items():
        out_path = os.path.join(DOCUMENTS_DIR, f"{source_id}.txt")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"-> Saved {len(text)} chars to documents/{source_id}.txt")

# ==========================================
# 4. ENGINE COORDINATOR EXECUTION
# ==========================================
def run_full_guide_pipeline():
    loaded_documents = {}

    print("\n=== Phase 1: Ingesting Raw Source Material ===")

    for source_id, location in SOURCES.items():
        if source_id == "12_rate_my_professor":
            # Direct to specialized RMP module
            rmp_text = scrape_ratemyprofessor_data(PROFESSORS_TO_SCRAPE)
            # Option E (reproducibility): if the live API is unreachable, fall back
            # to the committed snapshot in documents/ so the corpus stays stable.
            if not rmp_text:
                cache_path = os.path.join(DOCUMENTS_DIR, f"{source_id}.txt")
                if os.path.exists(cache_path):
                    print("RMP live fetch empty — loading cached snapshot from documents/")
                    with open(cache_path, "r", encoding="utf-8") as f:
                        rmp_text = f.read()
            if rmp_text:
                loaded_documents[source_id] = rmp_text

        elif source_id == "1_r_howard_university":
            reddit_path = os.path.join(DOCUMENTS_DIR, location)
            loaded_documents[source_id] = parse_local_reddit_json(reddit_path)

        elif source_id == "11_tiktok_advice":
            # Simulate transcription extraction layer output
            loaded_documents[source_id] = (
                "[Student Video Transcript]: The 'Howard Runaround' is real. If you have a block on BisonHub, "
                "do not email general inboxes. Escalate directly to supervisors like John Gordon using clear subject headings."
            )
        elif location.lower().endswith(".pdf"):
            print(f"Extracting PDF source: {source_id}...")
            text_content = scrape_pdf(location)
            if text_content:
                loaded_documents[source_id] = text_content

        elif location.startswith("http"):
            print(f"Scraping structural website: {source_id}...")
            text_content = scrape_and_clean_web(location)
            if text_content:
                loaded_documents[source_id] = text_content

    print(f"\nSuccessfully collected {len(loaded_documents)} structured text documents.")

    # Capture the ingested corpus on disk before chunking
    persist_scraped_documents(loaded_documents)

    print(f"\n=== Phase 2: Chunking (Size: {CHUNK_SIZE}, Overlap: {CHUNK_OVERLAP}) ===")

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
        separators=["\n\n", "\n", " ", ""]
    )

    all_chunks = []
    for doc_id, text in loaded_documents.items():
        doc_chunks = text_splitter.create_documents(texts=[text], metadatas=[{"source_origin": doc_id}])
        all_chunks.extend(doc_chunks)
        print(f"-> Source '{doc_id}' split cleanly into {len(doc_chunks)} chunks.")

    print(f"\nPipeline processing complete. Total searchable database chunks: {len(all_chunks)}")

    # Sanity verification block checking the Rate My Professor chunk quality
    print("\n=== Phase 3: Auditing Rate My Professor Chunk Integrity ===")
    rmp_chunks = [c for c in all_chunks if c.metadata["source_origin"] == "12_rate_my_professor"]

    if rmp_chunks:
        sample = rmp_chunks[0]
        print(f"\n[SAMPLE RETRIEVED CHUNK FROM RMP DATASET]")
        print("-" * 60)
        print(sample.page_content)
        print("-" * 60)
        print(f"Character Length: {len(sample.page_content)}")
    else:
        print("No specific RMP chunks generated. Ensure the professor has active evaluations on the platform.")

    return all_chunks

if __name__ == "__main__":
    run_full_guide_pipeline()
