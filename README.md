# The Unofficial Guide: Columbia CS Professor Reviews

This project is a RAG system for asking questions about Columbia Computer Science professor reviews from CULPA. It retrieves relevant student review chunks and uses Groq to generate answers grounded only in those retrieved chunks.

## Domain

The domain is Columbia CS professor reviews from CULPA. This knowledge is useful because Columbia's official course descriptions list topics and requirements, but they do not show what students actually experienced: workload, grading, exams, teaching style, organization, and whether students recommend a professor. CULPA is unofficial, so it captures student perspectives that are spread across many professor pages and are hard to search manually.

## Document Sources

Each document is one professor's collected CULPA reviews. The source manifest is saved at `documents/culpa_sources_manifest.json`; raw API responses are saved in `documents/raw_json/`.

| # | Source | Type | URL or file path |
|---|--------|------|-----------------|
| 1 | Adam Cannon reviews | CULPA API + local text | `https://culpa.info/api/review/professor/515?page=1`; `documents/adam_cannon_reviews.txt` |
| 2 | Paul Blaer reviews | CULPA API + local text | `https://culpa.info/api/review/professor/3409?page=1`; `documents/paul_blaer_reviews.txt` |
| 3 | Tony Dear reviews | CULPA API + local text | `https://culpa.info/api/review/professor/13639?page=1`; `documents/tony_dear_reviews.txt` |
| 4 | Ansaf Salleb-Aouissi reviews | CULPA API + local text | `https://culpa.info/api/review/professor/13076?page=1`; `documents/ansaf_salleb_aouissi_reviews.txt` |
| 5 | Jason Nieh reviews | CULPA API + local text | `https://culpa.info/api/review/professor/45?page=1`; `documents/jason_nieh_reviews.txt` |
| 6 | Clifford Stein reviews | CULPA API + local text | `https://culpa.info/api/review/professor/1342?page=1`; `documents/clifford_stein_reviews.txt` |
| 7 | Luis Gravano reviews | CULPA API + local text | `https://culpa.info/api/review/professor/375?page=1`; `documents/luis_gravano_reviews.txt` |
| 8 | Simha Sethumadhavan reviews | CULPA API + local text | `https://culpa.info/api/review/professor/3429?page=1`; `documents/simha_sethumadhavan_reviews.txt` |
| 9 | Tal Malkin reviews | CULPA API + local text | `https://culpa.info/api/review/professor/1621?page=1`; `documents/tal_malkin_reviews.txt` |
| 10 | Rocco Servedio reviews | CULPA API + local text | `https://culpa.info/api/review/professor/1724?page=1`; `documents/rocco_servedio_reviews.txt` |

The collection script is `scripts/collect_culpa_reviews.py`. It collected 376 reviews across the 10 professor documents. One data limitation: CULPA reported 94 Adam Cannon reviews, but pagination returned 93.

## Chunking Strategy

**Chunk size:** One CULPA review per chunk. If a review is unusually long, the code splits it by paragraph while preserving the same metadata.

**Overlap:** Normal review chunks use zero overlap because each review is an independent student opinion. Paragraph-split long reviews use one paragraph of overlap.

**Why these choices fit your documents:** CULPA reviews are short-to-medium opinion documents. One review usually contains the course, rating, workload, and student opinion together, so it is a natural semantic unit. Fixed 500-character chunks could separate workload from opinion or cut a sentence in half.

**Final chunk count:** 394 chunks, saved in `chunks.jsonl`.

**Sample chunks:**

1. `adam_cannon_reviews.txt`, review `88398`: Computing in Context review mentioning three projects in the first half, three projects in the Econ section, labs, and a final harder than the midterm.
2. `adam_cannon_reviews.txt`, review `2029`: Object-Oriented Programming review saying CS has a lot of work, but Cannon is willing to help.
3. `paul_blaer_reviews.txt`, review `22624`: Object-Oriented Programming review warning that biweekly assignments can be time-consuming.
4. `tony_dear_reviews.txt`, review `81549`: Artificial Intelligence review discussing uneven workload distribution and grading concerns.
5. `ansaf_salleb_aouissi_reviews.txt`, review `79991`: Artificial Intelligence review listing five homeworks, a midterm, and a final.

## Embedding Model

**Model used:** `all-MiniLM-L6-v2` from `sentence-transformers`.

**Production tradeoff reflection:** I chose this model because it is free, local, fast, and good enough for a small class project. For production, I would compare models based on retrieval accuracy, context length, cost, latency, multilingual support, privacy, and how well they handle student slang and course-specific wording. A stronger API embedding model might improve accuracy, but a local model reduces cost and avoids sending student review text to an external embedding service.

## Retrieval Tests

I used ChromaDB with semantic similarity search and `top-k = 5`.

| Query | Top returned chunks | Relevance |
|---|---|---|
| What do students say about Adam Cannon's workload in intro CS courses? | `adam_cannon_reviews.txt` reviews `2902`, `82081`, `87247`, `972`, `78264` | Relevant. The chunks are all Adam Cannon reviews and include workload details like projects, psets, ZyBook/HW percentages, assignments, midterms, and finals. |
| What do students say about Paul Blaer's exams and homework? | `paul_blaer_reviews.txt` reviews `89350`, `86750`, `87572`, `89446`, `87778` | Relevant. The chunks mention written/coding homework, exam expectations, fair exams, tough grading, and ZyBooks/Codio assignments. |
| What do students say about Jason Nieh's Operating Systems course? | `jason_nieh_reviews.txt` reviews `79709`, `6898`, `81766`, `84904`, `5752` | Mostly relevant. Four chunks are Operating Systems I reviews; one chunk is Operating Systems II, which is related but less directly relevant. |

The in-scope distances were generally around `0.53` to `0.70`, while an out-of-scope dining hall query returned much weaker distances around `1.53` to `1.63`.

## Grounded Generation

**System prompt grounding instruction:**

```text
You answer questions about Columbia CS professor reviews using only the provided CULPA review excerpts. If the excerpts do not contain enough information, say: "I don't have enough information from the provided reviews to answer that." Do not use outside knowledge. Cite sources in the answer using the source numbers provided, such as [Source 1].
```

**How source attribution is surfaced in the response:** The prompt asks the model to cite `[Source N]` inside the answer. The app also programmatically prints the retrieved source list below the answer, including source document, review ID, course code, and distance.

**Example response 1:** For Adam Cannon workload, the system cited `adam_cannon_reviews.txt` reviews and summarized psets, projects, midterms, finals, ZyBook/HW percentages, and office-hours advice.

**Example response 2:** For Paul Blaer exams and homework, the system cited `paul_blaer_reviews.txt` reviews and summarized written/coding homework, clear exam expectations, fair exams, and difficult coding homework.

**Out-of-scope refusal:** For "What is the best dining hall at Columbia?" the system answered: "I don't have enough information from the provided reviews to answer that. The review excerpts provided are about Columbia CS professors and courses, but they do not mention dining halls."

## Query Interface

The interface is a Gradio web app in `app.py`.

**Input field:** A free-text question about the collected CULPA CS professor reviews.

**Output fields:** A grounded answer and a retrieved-source list.

Run:

```powershell
python build_index.py
python app.py
```

Then open `http://127.0.0.1:7860`.

**Sample interaction transcript:**

Question: `What do students say about Paul Blaer's exams and homework?`

Answer summary: Students say Blaer tells them what to expect on exams, exams are often fair or straightforward, written homework can be manageable, and coding homework can be difficult. The answer cites multiple `paul_blaer_reviews.txt` review sources.

## Evaluation Report

| # | Question | Expected answer | System response (summarized) | Retrieval quality | Response accuracy |
|---|----------|-----------------|------------------------------|-------------------|-------------------|
| 1 | What do students say about Adam Cannon's workload in intro CS courses? | Workload is often high for beginners, with coding/ZyBook work, projects or assignments, midterms, and a final; several reviews say it is fair or doable with office hours and steady work. | Summarized psets, projects, midterms, finals, ZyBook/HW percentages, grace time, and proactive help-seeking. | Relevant | Accurate |
| 2 | What do students say about Paul Blaer's exams and homework? | Reviews mention written/coding homework, clear exam expectations, fair or straightforward exams, and sometimes difficult coding homework. | Said Blaer tells students what to expect on exams, exams are fair/straightforward, written homework is easier, and coding homework can be brutal. | Relevant | Accurate |
| 3 | What do students say about Tony Dear's course difficulty? | Reviews describe him as organized and strong, but many say courses, homework, and exams are difficult; some mention a generous curve. | Gave a balanced answer: some students find him reasonable, others say exams/finals are very difficult, and homework can be time-consuming. | Relevant | Accurate |
| 4 | What do students say about Ansaf Salleb-Aouissi's workload and grading? | Reviews often describe workload as manageable, assignments as fair/straightforward, and grading as lenient or curved. | Said workload is generally light, assignments vary but difficult ones may be curved, and grading can include partial credit and regrade discussions. | Partially relevant | Partially accurate |
| 5 | What do students say about Jason Nieh's Operating Systems course? | Reviews describe OS as extremely hard and high-workload, with heavy assignments and exams; positive reviews praise learning value and Nieh's teaching. | Summarized mixed views: strong lecturer and high learning value, but heavy Linux-kernel workload, difficult assignments, and some negative experiences. | Mostly relevant | Accurate |

## Failure Case Analysis

**Question that failed:** What do students say about Ansaf Salleb-Aouissi's workload and grading?

**What the system returned:** The answer was mostly correct, but one retrieved chunk came from Ansaf's Artificial Intelligence reviews and discussed a buggy grading script. That was less relevant to the Discrete Mathematics workload/grading pattern that most retrieved chunks discussed.

**Root cause:** Retrieval used semantic similarity only and did not filter by course. Because the query asked about a professor broadly, ChromaDB returned chunks from multiple courses taught by the same professor.

**What I would change to fix it:** Add metadata filtering by course code or course name when the user asks about a specific course, or ask a clarification question when the professor has reviews across multiple courses.

## Spec Reflection

**One way the spec helped during implementation:** The spec made the pipeline decisions concrete before coding. Choosing one professor per document and one review per chunk made the implementation easier because the metadata and source citation strategy were already defined.

**One way the implementation diverged from the spec, and why:** The plan said most chunks would be one review, with long reviews split by paragraph if needed. The implementation followed that, but the final chunk count became 394 even though there were 376 collected reviews because some long reviews were split into multiple chunks.

## AI Usage

**Instance 1**

- *What I gave the AI:* I described the CULPA source, the 10 selected CS professors, and the requirement to save local documents from the API.
- *What it produced:* A Python collection script that downloads CULPA JSON, saves raw API responses, and writes readable professor review files.
- *What I changed or overrode:* I verified the generated documents manually, noticed the Adam Cannon API count mismatch, and added a warning so the data limitation is visible.

**Instance 2**

- *What I gave the AI:* I provided the chunking and retrieval plan from `planning.md`: one review per chunk, `all-MiniLM-L6-v2`, ChromaDB, and top-k 5.
- *What it produced:* The RAG pipeline code for chunk creation, embeddings, ChromaDB indexing, retrieval, and Groq generation.
- *What I changed or overrode:* I tested retrieval before generation, kept source attribution programmatic, and documented a failure case where semantic search returned the right professor but a less relevant course.
