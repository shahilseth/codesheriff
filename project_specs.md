# CodeSheriff — Project Spec

## What this app does
CodeSheriff is a multi-agent system that lets someone ask plain-English questions
about a GitHub repository ("where is the login logic?", "what does this function
do?") and get useful answers back.

To answer questions, the system first needs to "read" and understand a codebase.
That's what Phase 1 builds: a pipeline that reads a local code repo, breaks it
into meaningful pieces (functions/classes), turns each piece into a numeric
"fingerprint" (an embedding), and stores those fingerprints in a searchable
database. Later phases will let an AI agent search this database to answer
questions.

## Who uses it
- **You (developer)**, for now — running scripts from the command line to index
  a repo and test that search works.
- Eventually: anyone who wants to ask questions about a codebase via a chat-like
  interface.

## Phase 1 scope (this task)
Build the **indexing pipeline** only. No web app, no chat, no LLM calls yet.

Pipeline steps:
1. Walk a local repo folder and find Python files.
2. Split each file into chunks at function/class boundaries (using tree-sitter,
   not arbitrary text splitting — this keeps each chunk meaningful).
3. Turn each chunk into a vector embedding using a local model
   (`sentence-transformers/all-MiniLM-L6-v2` — runs on your Mac, no API key
   needed, no cost).
4. Store the vectors + metadata in ChromaDB (a local vector database — basically
   a search engine for "meaning" instead of exact text).
5. Provide a test script that indexes a repo and runs a few sample questions to
   prove search returns relevant code chunks.

## Tech stack (Phase 1)
- **Language:** Python 3.11
- **Chunking:** `tree-sitter` + `tree-sitter-python` (parses code into a tree so
  we can pull out function/class boundaries precisely)
- **Embeddings:** `sentence-transformers` (HuggingFace), model
  `all-MiniLM-L6-v2` — local, free, ~80MB download
- **Vector DB:** `chromadb`, local persistent storage (a folder on disk, no
  server to run)
- **No external APIs / no Claude / no Groq calls in this phase**

## Data model — what's stored per chunk
| Field | Meaning |
|---|---|
| `file_path` | path to the file the chunk came from, relative to repo root |
| `chunk_type` | `function`, `class`, or `module` (fallback for code outside any function/class) |
| `name` | the function/class name (or filename for module-level chunks) |
| `start_line` / `end_line` | where the chunk lives in the file |
| `repo_name` | name of the repo folder being indexed |
| `language` | `python` (only language supported in Phase 1) |
| `commit_hash` | current git HEAD commit of the repo being indexed (via `git rev-parse HEAD`) |

The chunk's **text content** + this metadata + its embedding vector all get
stored together in ChromaDB, in a collection named after the repo.

## Re-indexing behavior
If you run the indexer again on the same repo, the old collection is deleted
and rebuilt from scratch. (Smarter incremental updates come in a later phase.)

## Folder structure
```
codesheriff/
  backend/
    indexer/
      __init__.py
      chunker.py       # splits code into function/class/module chunks
      embedder.py       # wraps all-MiniLM-L6-v2, returns numpy vectors
      index_repo.py      # main pipeline: walk -> chunk -> embed -> store
    db/
      __init__.py
      chroma.py         # ChromaDB client + collection helpers
  scripts/
    index_repo.py        # CLI: python scripts/index_repo.py --repo_path ./some_repo
    test_query.py         # indexes codesheriff itself, runs 3 sample questions
  requirements.txt
```

## What "done" looks like for Phase 1
- `python scripts/index_repo.py --repo_path <some_repo>` runs without errors and
  reports how many chunks were indexed.
- `python scripts/test_query.py` indexes the codesheriff repo itself and prints
  the top-3 most relevant code chunks for 3 hardcoded questions, with their
  metadata (file, function name, lines).
- Chunks correspond to real functions/classes, not random line ranges.

## A heads-up before we start
Your Mac currently has **Python 3.9.6** as the default `python3`, but this spec
calls for **Python 3.11** (needed for current tree-sitter/chromadb packages). To
keep things from breaking, I'll set up a **virtual environment using Python
3.11**. That requires Python 3.11 to be installed first.

**Quickest fix:** install Homebrew (if you don't have it) and then Python 3.11:
```
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
brew install python@3.11
```
I won't run these for you since installing Homebrew changes your whole system —
let me know once it's done, or tell me to proceed with Python 3.9 instead (it
may still work, just less future-proof).

---

# Phase 6 — Frontend + Evals

Phases 1-5 built the whole backend pipeline (indexing, Navigator, Analyst,
Critic, Synthesiser, FastAPI, Postgres trace logging). Phase 6 makes the
system *usable* and *measurable*: a small web UI to ask questions and see how
the agents arrived at the answer, plus a script that runs a batch of
questions and reports how the system performs across all of them.

## What this adds

### 1. New backend endpoint
- `GET /api/trace/{trace_id}` — returns the full stored trace JSON (Navigator
  chunks/commits, Analyst reasoning + evidence, Critic challenges, Synthesiser
  output, latencies). Powers the TraceViewer.

### 2. Frontend (`/frontend`, React + Vite, plain JS)
- **Single page**, talks to `http://localhost:8000`.
- **Ask form**: repo path, repo name, question, "Ask" button (calls
  `/api/query`).
- **Answer view**: shows the answer text, confidence badge (high/medium/low),
  cited files, known gaps.
- **TraceViewer**: expandable sections showing, for the trace just returned
  (or fetched via `/api/trace/{trace_id}`):
  - Navigator: retrieved chunks (file, lines, similarity score) and commits
  - Analyst: hypothesis, full reasoning, evidence list, uncertainty,
    confidence_hint
  - Critic: challenges (type/severity/description), missing files,
    confidence_adjustment, critique summary
  - Synthesiser: final answer, cited files, known gaps
  - Latency breakdown per agent
- Run with `npm install && npm run dev` (Vite dev server, default port 5173 —
  already allowed by backend CORS).

### 3. Evals (`scripts/run_evals.py` + `scripts/eval_questions.json`)
- A fixed list of ~8-10 questions about the codesheriff repo itself, covering
  different question types (architecture, "where is X", "how does Y work",
  edge cases unlikely to be answerable).
- Script hits `/api/query` for each question against the already-indexed
  `codesheriff` repo and writes a report (`out/eval_report.json` +
  printed summary table) with: question, confidence, confidence_label,
  number of cited files, number of known gaps, critic confidence_adjustment,
  total latency.
- Goal: see at a glance which question types the system handles well vs.
  poorly, *before* demoing live.

## What "done" looks like for Phase 6
- `GET /api/trace/{trace_id}` returns the full trace for a real trace_id.
- `npm run dev` in `/frontend` serves a page where you can ask a question
  against the running backend, see the answer + confidence + cited files, and
  expand the TraceViewer to see each agent's contribution.
- `python scripts/run_evals.py` runs against the running backend + indexed
  `codesheriff` repo, completes without errors, and prints/saves a summary
  table for all eval questions.
