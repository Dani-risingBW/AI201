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

# List of example professors to scrape from Howard for Source 12
PROFESSORS_TO_SCRAPE = ["Legand Burge"]

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

def scrape_ratemyprofessor_data(target_professors) -> str:
    """
    Queries Rate My Professors' GraphQL API to locate Howard University (School-421)
    faculty reviews, compiling metrics and student comments for chunk injection.
    """
    print("Connecting to RateMyProfessors GraphQL API...")

    teacher_query = (
        "query T($q: TeacherSearchQuery!){ newSearch{ teachers(query: $q){ edges{ node{ "
        "id firstName lastName department avgRating avgDifficulty numRatings wouldTakeAgainPercent "
        "} } } } }"
    )
    ratings_query = (
        "query R($id: ID!){ node(id: $id){ ... on Teacher{ ratings(first: 20){ edges{ node{ "
        "class comment clarityRating difficultyRating wouldTakeAgain date "
        "} } } } } }"
    )

    compiled_rmp_data = ""

    for prof_name in target_professors:
        print(f"Scraping RMP metrics for: {prof_name}...")
        try:
            data = _rmp_query(teacher_query, {"q": {"text": prof_name, "schoolID": HOWARD_SCHOOL_ID}})
            edges = data.get("data", {}).get("newSearch", {}).get("teachers", {}).get("edges", [])
        except Exception as e:
            print(f"  RMP request failed for {prof_name}: {e}")
            continue

        if not edges:
            print(f"Could not retrieve profile data for {prof_name}.")
            continue

        node = edges[0]["node"]
        full_name = f"{node['firstName']} {node['lastName']}"
        prof_text = f"\n\n[RATE MY PROFESSOR DOSSIER: {full_name}]\n"
        prof_text += f"Department: {node['department']} | Overall Rating: {node['avgRating']}/5\n"
        prof_text += f"Difficulty Index: {node['avgDifficulty']}/5\n"
        prof_text += f"Total Student Ratings: {node['numRatings']}\n"
        wta = node.get("wouldTakeAgainPercent")
        if wta is not None and wta >= 0:
            prof_text += f"Would Take Again: {round(wta, 1)}%\n"

        # Append individual textual evaluations
        prof_text += "Student Comments & Evaluations:\n"
        try:
            rdata = _rmp_query(ratings_query, {"id": node["id"]})
            rating_edges = rdata.get("data", {}).get("node", {}).get("ratings", {}).get("edges", [])
            for r in rating_edges:
                rn = r["node"]
                comment = (rn.get("comment") or "").strip().replace("\n", " ")
                prof_text += (
                    f"- (Course: {rn.get('class', 'N/A')}) Rating: {rn.get('clarityRating', '?')}/5. "
                    f"Difficulty: {rn.get('difficultyRating', '?')}/5. Comment: {comment}\n"
                )
        except Exception as e:
            print(f"  Could not fetch individual ratings for {full_name}: {e}")

        compiled_rmp_data += prof_text

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
