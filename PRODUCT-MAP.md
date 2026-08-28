# Product map

One page for the question "what is this project, in its own words, and what do
its words mean" — the shared vocabulary, the workflows that actually exist, and
the boundaries the project draws around itself.

**This page adds nothing.** Every line is compiled from `README.md`,
`PUBLIC_ROADMAP.md`, `docs/index.md` and `CONTRIBUTING.md`, and each section
says where it came from so a disagreement can be settled against the source
rather than against this file. Where the material does not exist, this page says
so instead of filling the gap — see [What is deliberately not
here](#what-is-deliberately-not-here).

## The guarantee, and its edge

*Source: `README.md` "Concept" and "What \"verbatim\" means"; `PUBLIC_ROADMAP.md`
"Vision".*

Verbatim RAG is a **provenance-first answer layer**: given a question and source
context, it returns source excerpts with structured citations instead of freely
generated factual text.

The guarantee is about **evidence provenance, not truth**. The system can show
that a cited excerpt came from the supplied source. It cannot guarantee that the
source is correct, that retrieval was complete, or that the extracted passage is
the best available answer. In the default contextual template mode it may also
generate presentation text *around* the cited excerpts; `template_mode="static"`
keeps that framing fixed and deterministic.

Reading the guarantee narrowly is the point: it is the difference between "this
sentence is in your document" and "this sentence is true".

## Vocabulary

*Source: `README.md`, `docs/index.md`, `docs/guide/verbatim-core.md`.*

| Term | Means | Easily confused with |
|---|---|---|
| **span** / excerpt | A stretch of text taken verbatim from a source document | A generated paraphrase — which is what this project exists to avoid |
| **citation** | A numbered reference in the answer text pointing at one span | The span itself; the answer carries `[n]`, the citation record carries the text |
| **highlight** | The span's offsets inside the source document, used to mark it in the UI | The citation; a highlight is a position, a citation is a reference |
| **document** | One ingested source, with a title and an origin | A **chunk**: retrieval and citation operate on chunks, and one document yields many |
| **template mode** | `contextual` generates framing around the excerpts; `static` keeps framing fixed | The extractor: the mode shapes presentation, the extractor decides what is quoted |
| **extractor** | The component that selects spans — LLM-based, fine-tuned ModernBERT, or semantic highlighting | The LLM client, which is one extractor's dependency, not the mechanism |
| **`verbatim-core`** | The lean, reusable question + context → evidence transform | **`verbatim-rag`**, the full pipeline: ingestion, indexing, retrieval, orchestration |

## The three workflows that exist

*Source: `README.md` "Repository map", "Quick Start", "API and web prototype",
"Local development stack".*

1. **Evidence transform, no infrastructure.** `pip install verbatim-core`, hand
   it a question and the context you already retrieved, get back verified spans
   and citations. This is the path for an existing RAG stack that only wants the
   evidence step. Entry point: `docs/guide/verbatim-core.md`.
2. **Full pipeline.** `pip install verbatim-rag`, process documents, build an
   index with an embedding provider and a vector store, query it, receive a
   cited answer. Entry point: `README.md` "Quick Start"; the moving parts are
   listed under "Architecture".
3. **Demo stack.** `docker compose up`, an API and a web UI on one port, meant
   for seeing the product rather than for running it. Entry point: `README.md`
   "Local development stack (Docker Compose)", including how documents get into
   the index — the stack starts empty and says so.

Everything else in the repository serves one of those three.

## Non-goals

*Source: `PUBLIC_ROADMAP.md` — these are the project's own words, not an
inference from them.*

- The current milestone is about extraction correctness and provenance. It
  **does not commit** a framework integration, an ingestion product, or a
  supported self-hosting surface.
- The roadmap carries **no delivery dates**, deliberately.
- Items under "Exploring" are open design questions, not promised features. They
  move into a milestone only after a bounded contract and evidence from an
  actual workflow.
- Truth, retrieval recall, and answer completeness are outside the guarantee,
  as above.

## What counts as progress

*Source: `PUBLIC_ROADMAP.md` "Next", "How this roadmap changes";
`CONTRIBUTING.md`.*

- **Correctness work** may go straight into the current milestone.
- **Validation work** must state its dataset, metric, split, and failure cases.
  The named target is making the published span metric reproducible on another
  corpus, with negative examples and per-example output.
- **Product-surface work** needs a scoped design and a user workflow before it
  counts as implementation-ready.
- User-facing changes land with tests, documentation, and a changelog entry.
- Negative results and narrower designs are useful outcomes, explicitly.

## What a good answer looks like

*Source: `README.md` "How It Works"; the API's own responses.*

- **Answered.** The response text carries `[1]`, `[2]` …; each number resolves to
  a citation whose text occurs verbatim in the document it points at, and the UI
  can highlight it there.
- **Nothing relevant.** "No relevant information found in the provided
  documents." This is a claim about the corpus, and it is only made when the
  corpus was actually consulted.
- **Could not consult.** If the extraction model cannot be reached at all, the
  API answers `503` naming the provider's error — deliberately *not* the
  sentence above. See `BEY-12` in `AUDIT.md`.
- **Empty index.** `/api/status` reports `document_count`, and the UI says "No
  documents indexed" rather than showing a green "Ready". See `BEY-8`.

## What is deliberately not here

The audit item this page answers (`AIR-5`) also asked for **personas/roles** and
per-persona **success metrics**. Those are not in the repository in any form,
and this is a fork with no product authority over the upstream project: writing
them would be inventing intent and then citing it back as if it had been
recorded. They are named here as a gap rather than filled — which is also what
`PUBLIC_ROADMAP.md` does with its own open questions.

The rest of the item — workflows, terminology, non-goals, success signals,
examples of expected behaviour — is compiled above from material that already
existed.
