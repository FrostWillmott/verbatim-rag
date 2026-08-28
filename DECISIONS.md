# Decisions

Append-only log of non-obvious choices — not a changelog of every commit.
Newest entry at the top. See `documentation.md` in the rules-library for the
convention. Don't edit past entries; if a decision is reversed, add a new one
that supersedes it.

Scope: decisions about **this project** — its code, configuration, dependencies,
process. The working infrastructure this branch carries is deliberate and
described in `AGENTS.md`, but decisions *about* it — which rule modules apply,
how the linter preset was adapted, editor settings — belong in their commit
messages rather than here. Someone reading this repository wants to know why the
software is the way it is.

<!--
## YYYY-MM-DD — <short title>
<One or two lines: the decision and why. Link related files/PRs if useful.>
-->

## 2026-08-28 — An extraction failure stops being an answer about the documents

`extractors.py` caught every exception, logged it, and returned an empty span
list for that document. The response builder renders an empty result as "no
relevant information found in the provided documents" — so an unusable key or a
model the account cannot reach told the user their corpus had no answer, with a
`200` and a green status behind it. In a product whose claim is provenance, that
is the worst available shape for a failure: not a missing answer, a false one.

`SpanExtractionUnavailable` is raised when *every* document's extraction failed,
and only then. Partial failure keeps its old behaviour, because one chunk lost
to a rate limit should not blank an answer the rest still ground — and drawing
the line at total failure means the change can only speak where the old code was
silent, never break a case that worked. The API answers `503`, not `500`: the
request was valid and the condition is usually temporary. The provider's own
message is passed through, because it names the cause and holds no secret.

This changes the failure contract of a published package: callers who relied on
an empty answer now get an exception. Done anyway, in the fork, with the reason
recorded — the previous return value was not a weaker answer, it was a wrong
one.

## 2026-08-28 — Superseding two numbers in the 2026-08-27 scoring entry

The entry below, "The audit's own scoring model, transcribed and calibrated",
still carries two figures that later work disproved, and this log does not edit
its own past: the correction goes here.

"Reproduces every published score exactly — ten of ten" is **nine of ten**. The
cognitive-debt formula gives 58.5 against a published 59 and only reproduces
under round-half-up, which that report never states. The first pass called it ten
of ten because `7×.25 + 6×.20 + 6×.20 + 2×.10 + 6×.25` evaluates to
`5.8500000000000005` in binary floating point, which rounds the convenient way —
a right answer for a wrong reason, and the reason was a float artefact.

"Security goes 25 → 92" is **25 → 100**, since `SEC-3` was closed in `735a50a`
and no finding from that report remains open.

Both corrections are already in `AUDIT.md`; what was missing was this entry,
which the project's own rule requires — a reversed decision is closed by a new
record, not by silence in the old one.

## 2026-08-28 — The frontend gets a suite, scoped to the claim and to what people had to find twice

`TST-4` was deferred for time, and the deferral stopped being honest once three
passes — two manual, one outside evaluation — returned the same ranked list.
What is tested is that list, in its order: a citation leads to its own source,
which is the product's central claim and had nothing behind it; a new question
carries no trace of the previous selection; and keyboard activation behaves like
a click while leaving focus where the user put it.

Vitest, configured inside the existing `vite.config.js` — a second config file
would repeat the jsx loader rules and the `@` alias and drift from them. The
component is driven through the real `ApiContext` with a harness that swaps the
answer, so the submit path under test is the component's own, not a mock of it.

Two things are deliberate. The suite covers `CleanFactInterface` and nothing
else: this is the critical path plus two regressions, not coverage. And
`MANUAL-UI-CHECK.md` stays — a suite cannot judge whether a focus ring is
visible, and both manual passes are what told these tests what to assert.

Non-vacuity was measured, not claimed: against the pre-fix component exactly the
two regression tests fail, and against a mutant that always returns the first
citation five of seven do. The mutant also caught a test whose name promised
more than it checked, which is the reason to run one.

## 2026-08-28 — A refusal reversed: the product map was a compilation, not an invention

`AIR-5` was rejected on the grounds that writing a product map for someone
else's project invents intent. The report had asked for the opposite — reuse
what `README.md` and `PUBLIC_ROADMAP.md` already say, with no new commitments —
and this branch had already compiled `AGENTS.md` and `DECISIONS.md` that way.
The refusal answered the hardest available reading of the task, which is the
failure mode a refusal is most likely to hide in.

`PRODUCT-MAP.md` is therefore a compilation with its sources named per section,
and it draws the line the refusal should have drawn in the first place:
workflows, vocabulary, non-goals and success signals exist in the repository and
are compiled; personas and per-persona metrics do not exist anywhere and are
named as a gap rather than filled. A fork has no authority to invent product
intent and then cite it back as if it had been recorded.

## 2026-08-28 — Two calls from the second UI pass: reconcile instead of refocus, 404 instead of fallback

The keyboard losing focus when a citation is activated looked like a missing
`focus()` call. It was not: the citation element, the remark plugin and the
answer's `components` map were all defined inside the render body, so every
state change gave React a new element type and it remounted the whole answer.
Re-focusing by selector would have hidden that and kept the remount, which also
throws away scroll position and animation state. The identities are stable now —
module scope for the element and the plugin, `useMemo`/`useCallback` for the
rest — so React reconciles rather than rebuilds, and the focused node simply
stays.

Second: `nginx.conf` answered any missing path with `index.html`, which is right
for a client-side route and wrong for a file. A deleted image came back `200
text/html`, so it appeared in no console and in no status-code check. Paths that
name a file now `=404`, and `/api/` became an `^~` prefix so a future endpoint
ending in `.json` cannot fall into that rule. The fallback stays for everything
that is not a file, because that is what it is for.

## 2026-08-28 — The model and its endpoint become settings; the choice stays the maintainer's

CFG-4 asks which of the constants in `api/dependencies.py` are deliberate and
which are settings nobody wired. Two of them stopped being able to wait: the
pinned model `moonshotai/kimi-k2-instruct-0905` is not reachable from every Groq
account, and when it is not, every question is answered "no relevant information
found" with a `200` and a green status (BEY-12). Reaching a model that works
meant editing source.

So `LLM_MODEL` and `LLM_API_BASE` are fields on `APIConfig` — the settings
mechanism this API already had, not a new one — with the previous literals as
defaults, byte for byte. A contract test pins the defaults, and a second one
pins that the values actually reach `LLMClient`: BEY-6 was a whole set of
documented variables that reached nothing, and a new setting that is inert is
worse than no setting.

This deliberately answers nothing about *which* model or endpoint is right, and
leaves the embedding model and the collection name `"acl"` untouched — they are
the pair BEY-9 turns on, and moving where the API reads without settling that
question would orphan an existing index in silence.

## 2026-08-27 — The status endpoint reports what the index holds, not that it exists

`/api/status` computed readiness as `rag.index is not None`, which is true from
startup whether or not anything was ever indexed. The UI rendered it as a green
"Ready" while every question answered "no relevant information found". Added
`document_count`, counted through the same `vector_store.get_all_documents()`
call `/api/documents` already uses rather than a second, cheaper count — a
parallel mechanism beside a working one is the error this branch has twice
reverted for. The cost is that the number saturates at the listing's limit,
which is enough to separate empty from populated. `None` stays distinct from
`0`: a store that cannot answer is not an empty one. `resources_loaded` still
means "the stack is up", because making it false on an empty index would disable
the question input for the operator about to fill it.

## 2026-08-27 — The demo gets an ingest path that derives from the API instead of choosing

The configuration mismatch below stands and is still the maintainer's to
resolve. What changed is that a demo which cannot be demonstrated is a defect of
this fork's prototype surface, and there is a fix that does not require picking
a winner: `api/ingest.py` builds its index by calling `get_rag_instance`, the
same factory the API reads through. Writing the collection name and embedding
model into a third file would have been the "second mechanism beside a working
one" error in a new place, and it would drift the first time either value
changed.

It lives in `api/`, not in the published CLI, so nothing about the library's
behaviour changes. Milvus Lite's single-writer constraint means the API has to
be stopped for the run, which is documented rather than worked around.

## 2026-08-27 — The shipped indexer writes where the shipped API does not read

`verbatim_rag/cli.py` indexes into collection `verbatim_rag` with
`all-MiniLM-L6-v2`; `api/dependencies.py` reads collection `acl` with
`ibm-granite/granite-embedding-small-english-r2`. So the documented way to
populate an index cannot populate the demo's index, which is why the container
stack has nothing to demonstrate out of the box. Both failure modes are silent:
the name mismatch looks like an empty index, and because both models emit 384
dimensions, fixing only the name would load vectors from the wrong model into
the right slot and return meaningless results without raising. Milvus Lite is
additionally single-writer, so an external ingest process cannot open the file
while the API holds it.

Not repaired here, because every repair picks one of the two hardcoded
configurations as authoritative and both are the maintainer's to choose — the
same values `CFG-4` already raises. Recorded as `BEY-9`.

## 2026-08-27 — The UI was checked by a person, and that is where four defects came from

The frontend was the one surface this branch changed without running: nine
components deleted, a provider removed, six lint rules switched off pending a
judgement about an interface nobody had exercised. CI proved the bundle builds.

A written protocol with a fixed report form (`MANUAL-UI-CHECK.md`), run by
someone who had not done the work, returned four defects and settled one of the
disabled rules. Three of the four are invisible to any static check here: two are
agreements between two halves of the system that no single file is wrong about,
and one is an endpoint whose answer is true to its own code and false to its
reader. The filled report is kept unedited as `MANUAL-UI-CHECK-RESULT.md`,
including the five steps that could not run.

## 2026-08-27 — The first real CI run found the same mistake a second time

Pushing the branch and opening the pull request was the point at which anything
here was checked by GitHub rather than by a local imitation of it. Six of seven
jobs passed first time, including the ones with least local certainty — the full
ML stack, the frontend, and both container builds.

The matrix failed, on a mistake already made once on this branch and thought
fixed. A new test needs `datasets`, which belongs to the root package and not to
verbatim-core, so it was marked `requires_full_stack` — and a marker does not
help, because `-m` filters after collection and collection is what dies. The same
sentence is written in this file from the first time it happened.

The fault was not the discipline, it was the design: `conftest.py` kept a
hand-written list of which files need the root package, and that list rotted
within one commit. It is now derived from the files themselves — any test module
mentioning the marker is skipped when the root package is absent — so adding one
cannot repeat this.

Two runs also justify the push on their own terms. `rights-check` failed because
the pull request body was missing the contribution-rights checkbox the repository
requires, which no local reproduction would have caught. And the matrix failure
was invisible to a local run precisely because a developer machine has the full
stack installed.

## 2026-08-27 — An outside review found the showcase section destroyed, and a refusal that contradicted itself

An independent evaluation of this branch, run with a different model and without
access to the working transcript, returned findings worth acting on. Four
mattered.

The worst was self-inflicted and one commit old. The script that refreshed the
scoreboard substituted by report name across the whole file, and the calibration
table's rows begin with the same names — so it overwrote the section that
demonstrates the arithmetic, leaving prose that referenced numbers no longer
present. In a commit about tidying, breaking the most-read section, against a
standing rule to read the final diff before committing. Restored and corrected.

The calibration claim itself was overstated. It said ten formulas of ten
reproduce exactly; nine do. Cognitive debt sums to 5.85 and ×10 lands on 58.5
against a published 59, so it needs half-up rounding the report never states.
The first pass reported 59 only because Python's binary float makes the sum
5.8500000000000005 — the right answer for the wrong reason, which is the kind of
agreement that hides a mistake instead of catching it.

SEC-3 was refused as "a redesign of the library's public query API". It is not:
`filter` is accepted by the HTTP models, the surface the README calls a
prototype, and it can be narrowed there without touching the library at all. The
same reasoning had already closed DEAD-2 by removing `template_id` from the
schema. Applying a principle to one finding and its opposite to another is worse
than either answer alone. Now closed with a boundary validator.

And PR #46 was cited as evidence that "upstream chose 8080". It is my own pull
request and it is still open. That dressed a personal choice as external
validation — the least defensible sentence in the register, and the easiest for a
reader to check.

The pattern across all four: prose drifting away from what the tree and the
platform actually say, in a document whose whole value is that it does not.

## 2026-08-27 — The audit's own scoring model, transcribed and calibrated

Each report publishes its arithmetic. Transcribing all ten and feeding them the
reports' own inputs reproduces every published score exactly — ten of ten. That
turns the scores from something to be taken on trust into something reproducible,
and it is the only reason the effect of this branch can be stated as a number at
all.

What is recomputed is limited on purpose. Security, dead code and the coverage
term of test quality have mechanical inputs, so they are computed. Everything
resting on a criteria sum rated 0–5 or 0–10 is not: re-rating those means scoring
my own work, which is worth nothing whoever does the arithmetic. An independent
assessor can do it with the transcribed model; I should not.

Two of the movements are the instrument, not the work, and both were predicted
before the numbers were run.

Security goes 25 → 92, and most of that is a cap lifting rather than sixty-seven
points of improvement: any confirmed critical finding forces the score under 40
regardless of everything else, and closing one released it.

Dead code goes 57 → 59 although four of its six named deductions are gone and the
raw arithmetic says 91. The report's cap for "findings on several surfaces at
once" still binds, because two surfaces remain. Applying their rule rather than
routing around it is the point.

The third prediction has no number: open-source readiness scored 100 as a domain
no-op for a fork with no delta of its own. This branch is that delta, so the
report would now score its fourteen criteria for real and land lower. Better said
plainly than left for a reader to mistake the old 100 for an achievement.

## 2026-08-27 — transformers moved to 5.16.1, and predicting a side effect is not checking it

The upgrade itself was undramatic. Three packages move on Linux — transformers,
tokenizers, huggingface-hub — torch is untouched, and `pip-audit` stops reporting
transformers. What made it worth deferring until there was time was that the test
suite mocks transformers, so a green suite says nothing about whether models
still load. They were therefore loaded for real: the default extractor with
`trust_remote_code=True`, which returned a correct verbatim span, and the default
cross-encoder reranker, which ranked the relevant passage first. The API image
was rebuilt and carries 5.16.1.

The first rebuild failed, and the reason is the part worth keeping. Adding
`[tool.uv.sources]` earlier — so development resolves `verbatim-core` from
`packages/core` rather than PyPI — changed what the documented regeneration
command emits into `docker/constraints.txt`. It now writes `-e packages/core`,
and pip refuses editable entries inside a constraints file, so the image stopped
building.

That side effect had been predicted at the time and written down next to the key.
The note was correct and useless: it said the next regeneration would drop the
`verbatim-core` pin, and nobody ran the command to find out what it would do
instead. Several commits passed between introducing the breakage and discovering
it, and only building the image found it.

The regeneration command in `docker/overrides.txt` now carries
`--no-emit-package verbatim-core` and the reason it is required.

## 2026-08-27 — The agent entry point is vendor-neutral and states boundaries, not just layout

`AGENTS.md`, not a directory named after one assistant. The finding was that
there is no cross-agent entry point; answering it with a vendor-specific file
would have been answering a different question.

Most of it is navigation and a verification matrix, which is unremarkable. Two
parts are not.

The matrix carries its caveats rather than hiding them: the frontend needs
Node >= 20.19 and will not build on an older one, mkdocs is not installed
locally, and the docs deploy job runs only on push to `main` so it cannot be
exercised from a pull request at all. A matrix that implies everything is
checkable is worse than no matrix, because the first person to trust it learns
otherwise at the wrong moment.

The boundaries section lists what looks like cleanup and is not — weakening span
verification, changing constructor signatures of published packages, deleting
compatibility modules, repointing project identity, adding a second config or
lock mechanism beside an existing one. Each carries its reason, because a
prohibition without one gets argued with by the next reader, and in this
repository several of them are the difference between a fix and a regression.

## 2026-08-27 — Retrieved text is framed as data, and deliberately not sanitised

Retrieved documents are attacker-controlled in any real deployment, and they were
interpolated into the extraction prompt with no delimiter and no statement of
what they are. In `extraction/default.txt` the rules came *before* the documents,
which is the worst order: an injected instruction gets to speak last.

The finding was narrower than it first looked, and the correction is worth
keeping. `_verify_spans` checks every span against the text of the document it
was attributed to, so a fabricated quote is dropped, and so is a quote
misattributed to another document. The verbatim guarantee holds under injection.
What does not hold is completeness: a document that persuades the model to return
an empty array for itself is indistinguishable from a document with nothing
relevant. For a product whose entire claim is provenance, silently omitting a
source is the failure that matters, and it is the one verification cannot see.

Both extraction prompts now fence the retrieved text, say plainly that it is data
rather than instruction, put the authoritative rules after the block, and state
that a document asking to be skipped must still be reported.

Sanitising the text was rejected. Neutralising injection markers rewrites the
text the model is asked to quote from, so any span containing a rewritten marker
fails verbatim verification against the original — on a corpus of ACL papers,
which includes papers about prompt injection, that trades a speculative attack
for certain, silent data loss.

Two limits, stated rather than implied: the delimiter is forgeable by a document
that contains it, and the tests assert the instruction is present, not that a
model obeys it. Proving the latter needs an evaluation set, which is a piece of
work in its own right. This is defence in depth on top of span verification, not
a replacement for it.

## 2026-08-27 — CI installs from the same pin set as everything else

The docs workflow ran `pip install mkdocs-material "mkdocstrings[python]>=0.24"`
in a job holding `contents: write`, which means a freshly published release of
any of those packages, or of anything they depend on, executed install-time code
in a job that can write to this repository. That was the audit's only critical
finding.

Closed by pointing every `pip install` in both workflows at
`dev-constraints.txt`, and by declaring the release and audit tooling — `build`,
`twine`, `pip-audit` — in the `dev` extra so one generated file covers local
work, CI and docs alike. The alternative was a second list of versions
maintained inside the workflow, which is the duplication this repository has
been removing all day.

Verified, not reviewed. The deploy job runs only on push to `main`, so it cannot
be exercised from a pull request; instead its exact install command was run
against a clean virtualenv with pip — the installer CI uses, not uv — and
resolved to the pinned `mkdocs-material 9.7.7`, `mkdocstrings 1.0.6`,
`mkdocs 1.6.1`. Worth stating plainly: version pinning prevents a fresh
compromised release from being pulled, but it is not hash verification.
`--generate-hashes` with `--require-hashes` is the next increment, not this one.

Actions are pinned to commit SHAs with the tag left as a trailing comment, on the
same reasoning: a tag is mutable and an action runs as code inside the workflow,
so it belongs in the same class as a package. `ubuntu-latest` stays floating on
purpose — it is GitHub-maintained, and pinning it buys maintenance work rather
than supply-chain safety. The `contents: write` permission also stays, because
`mkdocs gh-deploy` needs it; what changed is that it no longer sits next to
unpinned third-party install code.

## 2026-08-27 — Request cost is capped by literals, and shared state is no longer written

`num_docs` and `k` are bounded to 1–50, the transform context to 100 items of
100 000 characters. The numbers are literals in `api/app.py`, deliberately not
new environment settings: the previous change removed options that were declared
and did nothing, and an unwired `MAX_NUM_DOCS` would have recreated exactly that.
When someone needs to tune these, they become settings and get wired in the same
change.

The cost was measured rather than assumed. A request carrying 10 000 context
items kept the endpoint working for 41 seconds; with the cap it is refused in
0.03 seconds.

`StreamingRAG` no longer writes to `self.rag.k` at all. It had been saving the
value, overwriting it with the caller's `num_docs`, and restoring it at five
different exit points — one of which, the outer `except`, did not restore, so a
failed stream left the retrieval default rewritten for every later request in
the process. Repairing that path would have left the other problem standing:
`self.rag` is a singleton, so two concurrent streams corrupted each other even
when both succeeded. `self.rag.k` turned out to be read in exactly one place, so
a local variable replaces the whole mechanism.

The LLM key is now reported instead of guessed at. The old check asked whether
`OPENAI_API_KEY` was present in the environment, not whether it held anything,
while `.env.example` ships it empty — so the most likely broken setup was also
the one that produced no warning. Blank now counts as missing, the message goes
through the logger rather than `print` at import time, and `/api/status` carries
`llm_configured` so the state is visible before the first query instead of after
it. It is still not a startup failure: `.env.example` documents on purpose that a
missing key does not stop the stack. The defect was the silence, not the
tolerance.

## 2026-08-27 — Three identical-looking settings got three different answers

`MAX_QUESTION_LENGTH`, `TEMPLATES_PATH` and `template_id` were all reported as
"declared but detached". They are not the same problem.

The first two had a consumer to connect to, so they were connected.
`MAX_QUESTION_LENGTH` now reaches `APIService`, which previously hardcoded
`1000` and did not receive the config at all. `TEMPLATES_PATH` now loads into the
template manager that actually renders answers, instead of only the separate one
behind `/api/templates`.

`template_id` had no consumer anywhere: neither `VerbatimRAG.query` nor
`query_async` accepts such a parameter, so honouring it would mean changing the
public API of the upstream library — not a fork owner's call. It is removed from
the schema instead, and `QueryRequestModel` now forbids extra fields, so a client
that sends it gets a 422 rather than a 200 with an answer that ignored it.
Silence was the defect; rejecting is the fix.

The obvious way to wire `TEMPLATES_PATH` would have been to hand the API's
existing `TemplateManager` to `VerbatimRAG`, which accepts one. That would have
been a regression: the API builds it with no `llm_client`, and a manager without
one has `strategies["contextual"] is None`, so the mode falls back to `static`
and the framing of every answer changes silently. There is a test pinning that
behaviour, because it is the reason for the shape of the code.

`API_HOST` and `API_PORT` stay direct-run-only. The container's entrypoint gives
uvicorn its host and port; making the Dockerfile read these would move deployment
configuration into the image for no gain. That is a decision, not an oversight,
so it is written down rather than left looking like the same bug.

## 2026-08-27 — Secret files are blocked by an enforced rule, not a declared one

Reads of `.env`, `*.local` env files, `*.pem` and `*.key` are denied in
`.claude/settings.json`. Verified rather than assumed: after the change the
refusal comes back through both the file tool and Bash, which were the two routes
that had in fact been reading `.env` earlier the same day.

The repository previously carried a `.aiignore` listing the same paths, and it
was deleted. Nothing here consumed it, so it enforced nothing while looking like
a guarantee — and two mechanisms for one job is the failure this repository's own
rules forbid. `.env.example` stays readable: it is a tracked template the README
points at and holds no secret.

## 2026-08-27 — The first API test was written before the fix it proves

`/api/query_async` answered 500 to every request: the route passed `filter` and
`search_params` to a service method whose signature accepted neither, and a broad
`except Exception` turned the `TypeError` into a generic server error. The two
contract tests that pin the correct behaviour were written first and committed
together with the fix, so `make check` stays green at every commit while the
evidence survives: check out the parent commit's `api/` and both fail with
`assert 500 == 200`.

The fix is the signature, not the routing. Seven of the eight routes already
bypass `APIService` and call `rag.*` directly, so the tempting change was to make
the eighth match them — but that swaps which layer serves a request for no
user-visible gain, and the service layer's fate is a design question for the
maintainer, not a side effect of a bug fix.

The test fixtures build `APIConfig(_env_file=None)` on purpose. A suite whose
result depends on the developer's own `.env` is not a suite.

## 2026-08-27 — The documented local setup could not start the API at all

Trying to write the first API test surfaced two defects nobody had gone looking
for, neither of them in any of the ten reports.

`APIConfig` inherited pydantic-settings' default `extra="forbid"`, and
`create_app()` calls `get_config()` at import time rather than through dependency
injection. So a `.env` containing `OPENAI_API_KEY` — the file the README
instructs you to create — made `import api.app` raise outright, before any
request. Docker never showed it: `.dockerignore` drops `.env`, so the values
arrive as environment variables, which pydantic-settings does not police the same
way.

Separately, every `Field(..., env="API_HOST")` was a Pydantic v1 idiom that v2
keeps only as schema metadata. Measured before the change: `API_HOST=1.2.3.4`
left `host` at `0.0.0.0`, while the undocumented `HOST=5.6.7.8` worked. The
`API_*` names were inert; the ones that happened to work did so only because the
field name matched.

Both were fixed by honouring the documented contract — `extra="ignore"` because
`.env` is shared with the rest of the stack by the README's own instructions, and
`validation_alias` because it is v2's equivalent of what the author meant. The
alternative, renaming fields to match the accidental names, would have made the
code true by quietly changing the contract instead of keeping it.

This deepens CFG-1 rather than closing it: the finding said the settings do not
reach the run path, and it turns out their names did nothing either.

## 2026-08-27 — Fork status recorded in the repository, not only in correspondence

The premise of this work — that the audited findings describe upstream code — was
explained by mail to the recruiter, which is the wrong place for it to live: the
person who reviews the code is not the person who received the message. It now
sits in the `Premise` section of `AUDIT.md` and will be repeated in the pull
request description, which is what a reviewer opens first.

No separate file for it. A fourth document beside `AUDIT.md`, `DECISIONS.md` and
the rules directory would split one piece of context three ways.

The section is kept to verifiable facts — the audited commit, the fork chain, the
platform counters — rather than to argument. As repository context it lets a
reader reach the conclusion themselves; written as a defence it would invite
scepticism about the rest of the register.

This closes CD-003, which asks for a repository-side note naming the authoritative
source and where local divergence is recorded.

## 2026-08-27 — Dependency pinning follows the repository's existing lock idiom

The root manifests had no pinned set, so local and CI installs resolved afresh
on every run — the dependency audit raises this as its third improvement step.
Closed with `dev-constraints.txt`, generated by `make lock` and consumed by
`make install` as `pip install -c`.

The mechanism matches what the repository already does rather than what I would
reach for by default. `docker/overrides.txt` documents
`uv pip compile … -o docker/constraints.txt`, and the Dockerfile installs with
`pip install -c docker/constraints.txt`: the project already treats uv as the
resolver and pip as the installer. `dev-constraints.txt` is that same pattern
applied to the development set.

A first attempt used `uv.lock` with `uv sync`, and was reverted before leaving
the branch. Two things were wrong with it. Pip cannot parse `uv.lock` and CI
installs with pip, so the lock would have pinned my machine and nothing that is
actually built — the determinism the audit asks for would have been decorative.
And `uv sync` takes ownership of `.venv`, pruning whatever the lock omits;
adopting it moved about forty packages in an environment that was working.

Tool versions are declared once, in the `dev` extra of `pyproject.toml`, and
resolved once, in `dev-constraints.txt`. The ruff pre-commit hooks call
`.venv/bin/ruff` rather than a `rev:`-pinned mirror, so the hook and `make lint`
cannot end up enforcing different rule sets.

`[tool.uv.sources]` points `verbatim-core` at `packages/core/`. Without it the
compile pins the published 0.2.8, which then fights the editable install that
CI, the Dockerfile and `make install` all depend on. It has a side effect worth
knowing about: `docker/constraints.txt` currently pins `verbatim-core==0.2.8`
because it predates this key, so the next regeneration of that file will drop
the pin. Noted in `pyproject.toml` next to the key.

Known gap: CI still installs its tools unpinned and reads neither constraints
file. Wiring it up closes the rest of this finding and part of the critical
supply-chain one; it belongs to that work, not to this change.

## 2026-08-27 — `make check` has no type-checking step (TODO)

The verification gate is lint + format + tests. Type checking is deliberately
absent: mypy is declared in no manifest, there is no `[tool.mypy]` section, and
the inherited code has never been type-checked, so the step would be red from the
first commit and stay red. A gate that can never pass trains everyone to ignore
it. `make typecheck` prints a pointer to this entry rather than lying about what
it ran.

On a project I owned this would be a tracked task, not a deferral. Doing it
properly means: add mypy to the dev extra, start from a non-strict
`[tool.mypy]`, exclude the modules that depend on untyped third-party packages
(`torch`, `transformers`, `pymilvus`), and tighten per-package from there. That
is a work item of its own, not a side effect of installing a harness.

## 2026-08-27 — The lint gate stays where the project already had it

A stricter preset was measured against this tree before being considered: 11 rule
groups, line-length 88, target py312 produced **838 errors and 52 of 73 files
under reformatting, against an upstream baseline of zero**. The bulk is
pyupgrade (~235), bugbear (28) and ruff-specific (14) — a mass rewrite of code
this fork did not write, which would bury every real change in the diff.

So the configuration stays as the project had it and stays in `pyproject.toml`.
A standalone `ruff.toml` is not added: ruff discovers it first and then ignores
`[tool.ruff]` entirely rather than merging, so it would create a silent conflict
where none existed. There is now a note next to the block saying so.

Two additions only. `ASYNC`, which reports nothing today and guards a codebase
that genuinely mixes sync and async paths. And `known-first-party`, because
`verbatim_core` lives under `packages/core/`, is invisible to ruff's `src`
inference and was being sorted as a third-party package; the 11 `I001`
violations that surfaced are closed with the autofixer.

Those 11 files are the one place inherited code was touched, and the line is
deliberate: import ordering has a provably correct fixer, unlike the semantic
rewrites the wider rule set would have produced. For the same reason the commit
hooks run against the staged set only — repo-wide they would rewrite 68
inherited files on whitespace alone, plus 3 more that ruff reformats in
`examples/` and `scripts/`.

`target-version` stays at `py310`: both manifests declare `requires-python
>=3.10` and CI runs a 3.10/3.11/3.12 matrix, so a newer target would let
pyupgrade emit syntax that breaks the oldest leg.

## 2026-08-27 — Audit remediation lives on a branch that is never merged

Work on the external code audit happens on `audit-remediation`, branched from
`main` at `88f510a` — the exact commit the audits were taken against, so every
finding is reproducible from the branch point. `main` stays byte-identical to
`upstream/main` so that future contributions to `KRLabsOrg/verbatim-rag` can
still branch cleanly from it. A draft pull request into `main` is planned for CI
only — both workflows filter on `branches: [main]`, so without an open PR against
`main` nothing on this branch is ever checked. The branch is pushed and the pull
request is open; all three workflows are green, across nine jobs. Claims about CI
here rested on rebuilding its environment locally until that happened, and the
first real run repaid the difference by failing on two things no local
reproduction could have caught.
