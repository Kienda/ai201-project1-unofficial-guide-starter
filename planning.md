# Project 1 Planning: The Unofficial Guide

> Write this document before you write any pipeline code.
> Update this file before starting any stretch features.

---

## Domain

My domain is Columbia Computer Science professor reviews from CULPA. This knowledge is valuable because official Columbia course descriptions explain topics and requirements, but they usually do not show what students actually experienced in the class. CULPA is unofficial and separate from Columbia's official catalog, so students can describe workload, grading, teaching style, course organization, and whether they recommend a professor more freely.

This knowledge is hard to find manually because it is spread across many professor pages and many individual reviews. The system should help users ask plain-language questions about CS professors and get answers grounded in the collected student reviews.

---

## Documents

Each document is one professor's collected CULPA reviews. I chose one professor per document because it keeps retrieval and citation focused. If a user asks about Adam Cannon, the system can retrieve review chunks from `adam_cannon_reviews.txt` instead of searching one giant file containing every professor.

| # | Source | Description | URL or location |
|---|--------|-------------|-----------------|
| 1 | CULPA API, Adam Cannon | Columbia CS professor reviews; 93 reviews collected | `https://culpa.info/api/review/professor/515?page=1`; local file: `documents/adam_cannon_reviews.txt` |
| 2 | CULPA API, Paul Blaer | Columbia CS professor reviews; 84 reviews collected | `https://culpa.info/api/review/professor/3409?page=1`; local file: `documents/paul_blaer_reviews.txt` |
| 3 | CULPA API, Tony Dear | Columbia CS professor reviews; 45 reviews collected | `https://culpa.info/api/review/professor/13639?page=1`; local file: `documents/tony_dear_reviews.txt` |
| 4 | CULPA API, Ansaf Salleb-Aouissi | Columbia CS professor reviews; 31 reviews collected | `https://culpa.info/api/review/professor/13076?page=1`; local file: `documents/ansaf_salleb_aouissi_reviews.txt` |
| 5 | CULPA API, Jason Nieh | Columbia CS professor reviews; 29 reviews collected | `https://culpa.info/api/review/professor/45?page=1`; local file: `documents/jason_nieh_reviews.txt` |
| 6 | CULPA API, Clifford Stein | Columbia CS professor reviews; 29 reviews collected | `https://culpa.info/api/review/professor/1342?page=1`; local file: `documents/clifford_stein_reviews.txt` |
| 7 | CULPA API, Luis Gravano | Columbia CS professor reviews; 18 reviews collected | `https://culpa.info/api/review/professor/375?page=1`; local file: `documents/luis_gravano_reviews.txt` |
| 8 | CULPA API, Simha Sethumadhavan | Columbia CS professor reviews; 16 reviews collected | `https://culpa.info/api/review/professor/3429?page=1`; local file: `documents/simha_sethumadhavan_reviews.txt` |
| 9 | CULPA API, Tal Malkin | Columbia CS professor reviews; 16 reviews collected | `https://culpa.info/api/review/professor/1621?page=1`; local file: `documents/tal_malkin_reviews.txt` |
| 10 | CULPA API, Rocco Servedio | Columbia CS professor reviews; 15 reviews collected | `https://culpa.info/api/review/professor/1724?page=1`; local file: `documents/rocco_servedio_reviews.txt` |

The collection script also saves `documents/culpa_sources_manifest.json`, which records professor IDs, API URLs, local file names, and review counts. Raw API responses are saved in `documents/raw_json/` so the source data is traceable.

---

## Chunking Strategy

**Chunk size:**
One CULPA review per chunk. Most chunks will contain the professor name, course, rating, workload text, and review content. If a review is unusually long, I will split it by paragraph into smaller chunks while keeping the same professor, course, rating, review ID, and source metadata.

**Overlap:**
Zero overlap between normal review chunks because separate reviews are independent student opinions. For unusually long reviews that must be split by paragraph, I will use one paragraph of overlap so a detail at a paragraph boundary is not lost.

**Reasoning:**
These documents are review-heavy, not long official guides. One review is already a complete unit of meaning: it usually includes a student's opinion, workload description, course context, and rating. This is better than splitting every fixed number of characters because a fixed split could separate the workload from the opinion or cut a sentence in half. If chunks are too small, retrieval may return fragments that do not answer the question. If chunks are too large, a chunk may mix too many topics and make semantic search less precise.

---

## Retrieval Approach

**Embedding model:**
`all-MiniLM-L6-v2` from `sentence-transformers`.

**Vector store:**
ChromaDB.

**Top-k:**
5 chunks per query.

**Production tradeoff reflection:**
I chose `all-MiniLM-L6-v2` because it runs locally, is free, and is fast enough for a small class project. For a production system, I would compare embedding models based on retrieval accuracy, context length, latency, cost, multilingual support, and whether the model handles student slang or course-specific language well. I would also consider whether to use a local model for privacy and cost control or an API embedding model for better accuracy and maintenance.

I chose top-k = 5 because professor reviews are subjective. Retrieving five chunks gives the model several student perspectives to summarize while keeping the context small enough to avoid adding too much unrelated text. If retrieval misses key evidence, I may increase top-k; if answers become noisy, I may lower it.

---

## Evaluation Plan

| # | Question | Expected answer |
|---|----------|-----------------|
| 1 | What do students say about Adam Cannon's workload in intro CS courses? | Reviews say the workload is often high for beginners, with weekly coding/ZyBook work, projects or assignments, midterms, and a final. Several reviews also say the work is fair or doable if students use office hours and keep up. |
| 2 | What do students say about Paul Blaer's exams and homework? | Reviews commonly mention weekly or paired homework assignments, often split between written and coding work. Several reviews say Blaer makes exam expectations clear or tells students what to study, while coding homework can be time-consuming or difficult. |
| 3 | What do students say about Tony Dear's course difficulty? | Reviews describe Tony Dear as organized, kind, and a strong lecturer, but many say his courses, homework, and exams are difficult. Several reviews mention a generous curve or that grades may work out despite hard exams. |
| 4 | What do students say about Ansaf Salleb-Aouissi's workload and grading? | Reviews often describe her workload as manageable, with written assignments, coding assignments, and exams. Several reviews say assignments are fair or straightforward, grading is lenient or curved, and the class can be easier than other CS options. |
| 5 | What do students say about Jason Nieh's Operating Systems course? | Reviews describe Operating Systems with Jason Nieh as extremely hard and high-workload, especially the six homework assignments and exams. Positive reviews say students learn a lot and praise Nieh's teaching, but warn to start early, attend office hours, and have strong C/systems preparation. |

---

## Anticipated Challenges

1. CULPA API data may be incomplete or inconsistent. For example, the Adam Cannon API response reports 94 reviews, but pagination returned 93 reviews. This means the system may miss some source material even when the API appears to provide a complete count.

2. Reviews may be old or inconsistent. Some professors have reviews from many different years and courses, so the system may mix outdated comments with recent ones unless the response explains that it is summarizing retrieved reviews rather than giving a current official judgment.

---

## Architecture

```text
CULPA API
  |
  v
Document Ingestion
  - Python urllib/json
  - save raw JSON in documents/raw_json/
  - save readable professor files in documents/
  |
  v
Cleaning + Chunking
  - keep professor, course, rating, workload, review text, review ID
  - one review per chunk
  |
  v
Embedding + Vector Store
  - sentence-transformers: all-MiniLM-L6-v2
  - ChromaDB with source metadata
  |
  v
Retrieval
  - semantic similarity search
  - top-k = 5 chunks
  |
  v
Generation
  - Groq llama-3.3-70b-versatile
  - answer only from retrieved chunks
  - include source attribution
  |
  v
Query Interface
  - Gradio web UI
  - input: user question
  - outputs: grounded answer and retrieved sources
```

---

## AI Tool Plan

**Milestone 3 - Ingestion and chunking:**
I will use AI to help implement the CULPA API ingestion script and the chunking function. I will give the AI my Documents section, my chunking strategy, and the requirement that each professor should become one local document. I will verify the output by checking that 10 files are created, reading sample documents, and confirming that chunks are readable and self-contained.

**Milestone 4 - Embedding and retrieval:**
I will use AI to help implement the ChromaDB embedding and retrieval code. I will give the AI my Retrieval Approach section, including the `all-MiniLM-L6-v2` embedding model and top-k value of 5. I will verify the output by running at least 3 evaluation queries and checking whether the returned chunks are relevant.

**Milestone 5 - Generation and interface:**
I may use AI to help with the Groq prompt and a simple Gradio interface, but I will review the generated prompt to make sure grounding and source attribution are enforced. I will test the system with both in-scope questions and an out-of-scope question to confirm that it refuses to answer when the documents do not provide enough information.
