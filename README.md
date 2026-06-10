# CodeSheriff

CodeSheriff — Ask plain-English questions about a GitHub repository. A
multi-agent system that retrieves, reasons, critiques, and synthesises
answers with confidence scores and cited source files.

When you join a new codebase (or come back to your own after six months),
the slowest part isn't reading code — it's figuring out *which* code to
read and how much to trust your own first guess about why it's structured
that way. CodeSheriff retrieves the relevant chunks, reasons about the
design intent, has a second model adversarially check that reasoning for
gaps, and gives you a final answer with a confidence score and the exact
files it's based on.

## Architecture

CodeSheriff runs every question through a fixed four-agent pipeline,
coordinated by a plain Python orchestrator (no agent decides the pipeline
order — see "Design decisions" below).

| Agent | Model | Job | Why separate |
|---|---|---|---|
| Navigator | `llama-3.1-8b-instant` (small, optional LLM step) | Semantic search over ChromaDB for relevant code chunks, plus `git log` for related commits | Retrieval is a search problem, not a reasoning problem — keeping it separate means the reasoning agents work from a fixed, inspectable set of evidence instead of re-retrieving mid-thought |
| Analyst | `llama-3.1-8b-instant` | Reasons about the *design intent* behind the retrieved code — why it's structured this way, not just what it does — and self-rates a `confidence_hint` | A single model that both proposes and grades its own answer tends to be overconfident; separating proposal from review is the whole point |
| Critic | `llama-3.1-8b-instant` | Adversarially reviews the Analyst's hypothesis: missing files, unsupported assumptions, incomplete retrieval, contradicting evidence | Receives only file/chunk *names* from the Navigator, not their content — it can't just re-agree with the Analyst's reading of the code, it has to reason about coverage gaps (see "Design decisions") |
| Synthesiser | `llama-3.3-70b-versatile` | Reconciles the Analyst's reasoning with the Critic's challenges into the final answer, citing only evidence the Analyst already referenced | This is the one output the user sees, and it has to resolve two potentially conflicting upstream views — worth the larger model |

## Eval results

| Metric | Score |
|---|---|
| Retrieval recall | 0.80 |
| Confidence calibration | 0.90 |
| Avg confidence | 0.51 |

- **Retrieval recall (0.80)** — across the eval question set, 80% of the
  files a correct answer should cite were actually retrieved and cited.
- **Confidence calibration (0.90)** — 90% of answers met the minimum
  confidence threshold defined for that question, meaning the system's
  self-reported confidence roughly tracks how complete its evidence
  actually was.
- **Avg confidence (0.51)** — on average, the pipeline reports "medium"
  confidence, which matches the Analyst's own guidance that most honest
  answers from partial retrieval should land in the 0.5–0.75 range rather
  than near-certain.

## Stack

| Backend | Frontend |
|---|---|
| FastAPI | React (Vite) |
| Groq API (`llama-3.1-8b-instant`, `llama-3.3-70b-versatile`) | Plain CSS |
| ChromaDB (local persistent vector store) | `fetch` against the FastAPI backend |
| `sentence-transformers` (`all-MiniLM-L6-v2`) | |
| `tree-sitter` / `tree-sitter-python` (chunking) | |
| PostgreSQL + SQLAlchemy (async, trace logging) | |
| Pydantic (agent I/O contracts) | |

## Getting started

```bash
# a. Clone and create a virtual environment
git clone <your-fork-url> codesheriff
cd codesheriff
python3.11 -m venv .venv

# b. Install dependencies
.venv/bin/pip install -r requirements.txt

# c. Set up environment variables
cp .env.example .env
# then edit .env and fill in GROQ_API_KEY (and CODESHERIFF_DB_URL if not using the default)

# d. Start PostgreSQL (skip if you already have a local Postgres running)
docker run --name codesheriff-db -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=codesheriff -p 5432:5432 -d postgres

# e. Index a repo (defaults to indexing CodeSheriff itself)
.venv/bin/python scripts/index_repo.py --repo_path . --repo_name codesheriff

# f. Start the backend
.venv/bin/uvicorn backend.main:app --reload

# g. Start the frontend (in a separate terminal)
cd frontend
npm install
npm run dev
```

Then open `http://localhost:5173`.

## Project structure

```
codesheriff/
  backend/
    agents/        # Navigator, Analyst, Critic, Synthesiser agent implementations
    db/             # ChromaDB and PostgreSQL clients + trace logging
    indexer/        # Repo walking, tree-sitter chunking, embedding pipeline
    models/         # Pydantic schemas shared between agents and the API
    orchestrator/   # Pure Python coordination of the agent pipeline
    utils/          # Git log parsing for commit-based retrieval
    main.py         # FastAPI app: /api/index, /api/query, /api/trace/{id}
  evals/
    ground_truth.json  # Eval question set with expected files/keywords/confidence
    eval_runner.py      # Runs the eval set against a live backend, scores results
    eval_results/        # Timestamped eval run reports (gitignored)
  frontend/
    src/            # React app: ask form, answer view, trace viewer
  scripts/          # CLI entry points and integration tests
  out/              # Generated ChromaDB persistence (gitignored)
```

## Design decisions

- **The Critic receives chunk names but not chunk content.** If the Critic
  saw the same code the Analyst saw, it would tend to read it the same way
  and largely agree — that's not adversarial review, it's a second opinion
  on the same evidence. By giving it only the *coverage* (which files and
  chunks were retrieved, not their contents), the Critic is structurally
  forced to reason about what's missing or unverified rather than
  re-deriving the Analyst's conclusion.

- **Confidence is computed in Python, not asked of the model.** The final
  confidence score is `clamp(analyst.confidence_hint + critic.confidence_adjustment, 0, 1)`
  — a deterministic function of two model outputs, not a third number the
  model is asked to produce. Asking an LLM to "rate your overall confidence
  given everything above" tends to produce a number anchored on tone rather
  than on the specific gaps the Critic just identified; computing it from
  the two structured signals keeps the final score traceable to *why* it is
  what it is.

- **The Orchestrator is pure Python coordination, not an LLM agent.** The
  pipeline order (Navigator → Analyst → Critic → Synthesiser) is fixed and
  known in advance — there's no decision here for a model to make, and
  using an LLM to "decide what to do next" would add latency, cost, and a
  failure mode (a misrouted step) for zero benefit. Agents are reserved for
  steps that genuinely require judgment.

## Known limitations

- The current setup has limited git history, which limits how much the
  Navigator's commit-based retrieval can contribute to "why was this
  written this way" questions — most of that reasoning currently comes
  from code structure alone.
- Retrieval is a flat ChromaDB similarity search over all chunks in a
  repo. This works well at the scale tested here but degrades as a
  codebase grows — there's no module-level pre-filtering, so accuracy
  drops as the chunk count grows into the tens of thousands.
- Confidence scores have roughly ±0.05 run-to-run variance for the same
  question, since the Analyst and Critic run at temperature 0.2 — the
  same question can land just above or below a given threshold on
  different runs.

---

Built as part of a structured AI engineering learning roadmap.
