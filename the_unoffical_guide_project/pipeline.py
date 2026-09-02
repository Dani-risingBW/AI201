"""Milestone 3 — ingestion & chunking pipeline for The Unofficial Guide.

Loads the 13 designated sources (local Reddit JSON, live web pages, a PDF,
a short-form transcript, and Rate My Professor), crawls and extracts linked PDF forms,
persists each ingested source to documents/, chunks everything with RecursiveCharacterTextSplitter,
and builds an indexed ChromaDB vector store.
"""

import os
import io
import re
import json
from urllib.parse import urljoin, urlparse
import requests
import pdfplumber
from bs4 import BeautifulSoup

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

# ==========================================
# 0. PATHS (resolve relative to this file so the pipeline runs from anywhere)
# ==========================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOCUMENTS_DIR = os.path.join(BASE_DIR, "documents")
CHROMA_DIR = os.path.join(BASE_DIR, "chroma_db")
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
    "12_rate_my_professor": "Howard University Faculty",  # Trigger for RMP API pipeline
    "13_student_documents": "https://financialservices.howard.edu/documents-forms"
}

# Sources that contain links to external downloadable PDF forms we want to recursively crawl
SOURCES_TO_CRAWL_FOR_PDFS = ["7_finaid_landing", "10_registrar_forms", "13_student_documents"]

# --- Source 12: Rate My Professor selection ---
PROFESSORS_TO_SCRAPE = ["Legand Burge"]
RMP_TOP_N = 5
RMP_POOL_SIZE = 300          # candidate professors fetched, then ranked locally
RMP_MIN_RATINGS = 5          # ignore sparsely-rated profs when picking top-N
RMP_RANK_BY = "most_rated"   # "most_rated" (numRatings) or "highest_rated" (avgRating)

# --- Source 11: TikTok short-form media ---
TIKTOK_URLS = [
    "https://www.tiktok.com/@ssanyuspeaks/video/7530062510569884942",
    "https://www.youtube.com/watch?v=6LeI1AlZGek",
    "https://www.tiktok.com/@ssanyuspeaks/video/7527812876464082189?utm_campaign=&utm_source=unknown&refer=player_v1&referrer_url=https%3A%2F%2Fwww.tiktok.com%2Fembed%2Fv3%2F7527812876464082189%3F%26autoplay%3D1&referer_video_id=7527812876464082189",
    "https://www.tiktok.com/@ssanyuspeaks/video/7511726905322900782?utm_campaign=&utm_source=unknown&refer=player_v1&referrer_url=https%3A%2F%2Fwww.tiktok.com%2Fembed%2Fv3%2F7511726905322900782%3F%26autoplay%3D1&referer_video_id=7511726905322900782",
    "https://www.tiktok.com/@ssanyuspeaks/video/7637194378301148429",
    "https://www.tiktok.com/@ssanyuspeaks/video/7635075980599627022",
    "https://www.tiktok.com/@ssanyuspeaks/video/7587096506457443639",
    "https://www.tiktok.com/@ssanyuspeaks/video/7568541420085120269",
    "https://www.tiktok.com/@ssanyuspeaks/video/7536632597468728631",
]
WHISPER_MODEL_SIZE = "base"

# ==========================================
# 2. RATE MY PROFESSOR INGESTION MODULE
# ==========================================
RMP_GRAPHQL_URL = "https://www.ratemyprofessors.com/graphql"
RMP_HEADERS = {
    "Authorization": "Basic dGVzdDp0ZXN0",
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (HowardGuideBot Educational Project)",
}
HOWARD_SCHOOL_ID = "U2Nob29sLTQyMQ=="

def _rmp_query(query: str, variables: dict) -> dict:
    resp = requests.post(
        RMP_GRAPHQL_URL, headers=RMP_HEADERS,
        json={"query": query, "variables": variables}, timeout=20
    )
    resp.raise_for_status()
    return resp.json()

_TEACHER_FIELDS = (
    "id firstName lastName department avgRating avgDifficulty numRatings wouldTakeAgainPercent"
)

def _lookup_teacher_by_name(name: str):
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

    nodes = [t for t in nodes if (t.get("numRatings") or 0) >= min_ratings]
    if rank_by == "highest_rated":
        nodes.sort(key=lambda t: (t.get("avgRating") or 0, t.get("numRatings") or 0), reverse=True)
    else:
        nodes.sort(key=lambda t: (t.get("numRatings") or 0, t.get("avgRating") or 0), reverse=True)
    return nodes[:n]

def _format_professor_dossier(node: dict) -> str:
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
    print("Connecting to RateMyProfessors GraphQL API...")
    selected = []
    seen_ids = set()

    for prof_name in target_professors:
        print(f"Looking up named professor: {prof_name}...")
        node = _lookup_teacher_by_name(prof_name)
        if node and node["id"] not in seen_ids:
            selected.append(node)
            seen_ids.add(node["id"])

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
# 3. LOADER & RECURSIVE PDF MODULES
# ==========================================
def parse_local_reddit_json(file_path: str) -> str:
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
    """Downloads a PDF and extracts text using pdfplumber."""
    headers = {"User-Agent": "HowardGuideBot/1.0 (Educational Project context)"}
    try:
        response = requests.get(url, headers=headers, timeout=20)
        if response.status_code != 200:
            return f"Placeholder content for inaccessible PDF: {url}"

        pages = []
        with pdfplumber.open(io.BytesIO(response.content)) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text and text.strip():
                    pages.append(text)

        return re.sub(r'\s+', ' ', "\n".join(pages)).strip()
    except Exception as e:
        print(f"Failed parsing PDF {url}: {e}")
        return ""

def crawl_linked_pdfs_from_page(source_id: str, page_url: str) -> list[Document]:
    """Finds all PDF links on a page, downloads and parses them with metadata."""
    headers = {"User-Agent": "HowardGuideBot/1.0 (Educational Project context)"}
    extracted_docs = []

    try:
        response = requests.get(page_url, headers=headers, timeout=15)
        if response.status_code != 200:
            return []
        soup = BeautifulSoup(response.text, "html.parser")
    except Exception as e:
        print(f"Failed fetching links from {page_url}: {e}")
        return []

    seen_urls = set()
    for a_tag in soup.find_all("a", href=True):
        full_url = urljoin(page_url, a_tag["href"].strip())
        parsed = urlparse(full_url)

        if parsed.path.lower().endswith(".pdf") and full_url not in seen_urls:
            seen_urls.add(full_url)
            link_title = a_tag.get_text(strip=True) or os.path.basename(parsed.path)
            print(f"  -> Found linked PDF: {link_title} ({full_url})")

            pdf_text = scrape_pdf(full_url)
            if pdf_text:
                # Save each discovered PDF to documents/
                safe_slug = re.sub(r'[^a-zA-Z0-9_-]', '_', link_title)[:50]
                pdf_filename = f"{source_id}_form_{safe_slug}.txt"
                with open(os.path.join(DOCUMENTS_DIR, pdf_filename), "w", encoding="utf-8") as f:
                    f.write(pdf_text)

                extracted_docs.append(
                    Document(
                        page_content=pdf_text,
                        metadata={
                            "source_origin": source_id,
                            "parent_page": page_url,
                            "pdf_url": full_url,
                            "title": link_title,
                            "type": "linked_pdf_form"
                        }
                    )
                )

    return extracted_docs

def transcribe_tiktoks(urls) -> str:
    urls = [u for u in (urls or []) if u]
    if not urls:
        return ""

    import tempfile
    import glob as _glob
    import yt_dlp
    from yt_dlp.networking.impersonate import ImpersonateTarget
    from faster_whisper import WhisperModel

    print(f"  Loading faster-whisper ({WHISPER_MODEL_SIZE})...")
    model = WhisperModel(WHISPER_MODEL_SIZE, device="cpu", compute_type="int8")

    compiled = ""
    for url in urls:
        tmpdir = tempfile.mkdtemp(prefix="tiktok_")
        ydl_opts = {
            "format": "download/bestaudio/best",
            "outtmpl": os.path.join(tmpdir, "audio.%(ext)s"),
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "impersonate": ImpersonateTarget("chrome"),
        }
        try:
            print(f"  Downloading TikTok audio: {url}")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            files = _glob.glob(os.path.join(tmpdir, "audio.*"))
            if not files:
                continue

            print("  Transcribing...")
            segments, _info = model.transcribe(files[0])
            text = " ".join(seg.text.strip() for seg in segments).strip()
            if text:
                compiled += f"\n\n[Student Video Transcript - {url}]: {text}"
        except Exception as e:
            print(f"  TikTok transcription failed for {url}: {e}")
            continue

    return compiled.strip()

# ==========================================
# 3b. PERSISTENCE MODULE
# ==========================================
def persist_scraped_documents(loaded_documents: dict) -> None:
    print("\n=== Persisting ingested base sources to documents/ ===")
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
    extra_pdf_documents = []

    print("\n=== Phase 1: Ingesting Raw Source Material ===")

    for source_id, location in SOURCES.items():
        if source_id == "12_rate_my_professor":
            rmp_text = scrape_ratemyprofessor_data(PROFESSORS_TO_SCRAPE)
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
            transcript = transcribe_tiktoks(TIKTOK_URLS)
            if not transcript:
                cache_path = os.path.join(DOCUMENTS_DIR, f"{source_id}.txt")
                if os.path.exists(cache_path):
                    print("TikTok live transcription unavailable — using cached snapshot.")
                    with open(cache_path, "r", encoding="utf-8") as f:
                        transcript = f.read()
            if transcript:
                loaded_documents[source_id] = transcript

        elif location.lower().endswith(".pdf"):
            print(f"Extracting direct PDF source: {source_id}...")
            text_content = scrape_pdf(location)
            if text_content:
                loaded_documents[source_id] = text_content

        elif location.startswith("http"):
            print(f"Scraping structural website: {source_id} ({location})...")
            text_content = scrape_and_clean_web(location)
            if text_content:
                loaded_documents[source_id] = text_content

            # Check if this website contains linked documents to crawl
            if source_id in SOURCES_TO_CRAWL_FOR_PDFS:
                print(f"Crawling linked PDF forms on {source_id}...")
                discovered_pdfs = crawl_linked_pdfs_from_page(source_id, location)
                extra_pdf_documents.extend(discovered_pdfs)

    print(f"\nSuccessfully collected {len(loaded_documents)} base sources and {len(extra_pdf_documents)} linked PDF forms.")

    # Save root sources to disk
    persist_scraped_documents(loaded_documents)

    print(f"\n=== Phase 2: Chunking (Size: {CHUNK_SIZE}, Overlap: {CHUNK_OVERLAP}) ===")

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
        separators=["\n\n", "\n", " ", ""]
    )

    all_chunks = []

    # 1. Chunk base documents
    for doc_id, text in loaded_documents.items():
        doc_chunks = text_splitter.create_documents(
            texts=[text],
            metadatas=[{"source_origin": doc_id, "url": SOURCES.get(doc_id, "")}]
        )
        all_chunks.extend(doc_chunks)
        print(f"-> Source '{doc_id}' split cleanly into {len(doc_chunks)} chunks.")

    # 2. Chunk discovered PDF forms
    if extra_pdf_documents:
        pdf_chunks = text_splitter.split_documents(extra_pdf_documents)
        all_chunks.extend(pdf_chunks)
        print(f"-> Discovered PDF forms split cleanly into {len(pdf_chunks)} chunks.")

    print(f"\nPipeline processing complete. Total searchable database chunks: {len(all_chunks)}")

    # ==========================================
    # Phase 3: ChromaDB Vector Store Indexing
    # ==========================================
    print("\n=== Phase 3: Persisting Chunks to ChromaDB ===")
    print("Embedding chunks using all-MiniLM-L6-v2...")
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

    vectorstore = Chroma.from_documents(
        documents=all_chunks,
        embedding=embeddings,
        persist_directory=CHROMA_DIR
    )
    print(f"ChromaDB successfully built and stored at '{CHROMA_DIR}'.")

    # Sanity verification block checking the Rate My Professor chunk quality
    print("\n=== Phase 4: Auditing Rate My Professor Chunk Integrity ===")
    rmp_chunks = [c for c in all_chunks if c.metadata.get("source_origin") == "12_rate_my_professor"]

    if rmp_chunks:
        sample = rmp_chunks[0]
        print(f"\n[SAMPLE RETRIEVED CHUNK FROM RMP DATASET]")
        print("-" * 60)
        print(sample.page_content)
        print("-" * 60)
        print(f"Character Length: {len(sample.page_content)}")
    else:
        print("No specific RMP chunks generated. Ensure the professor has active evaluations on the platform.")

    return vectorstore

if __name__ == "__main__":
    run_full_guide_pipeline()
