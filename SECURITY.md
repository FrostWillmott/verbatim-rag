# Reporting a vulnerability

This repository is a fork of
[`KRLabsOrg/verbatim-rag`](https://github.com/KRLabsOrg/verbatim-rag). Where a
report should go depends on which code it is about, and the distinction is not
pedantic — sending a library vulnerability here delays the fix for everyone who
installed it from PyPI.

**In the library — `verbatim_rag/`, `packages/core/`, the published packages.**
That code is upstream's and so are its users. Report it to
`KRLabsOrg/verbatim-rag`, privately: open a draft security advisory there, or
contact the maintainers through the channels that repository lists. Please do
not open a public issue for it, here or there.

**In this fork's own changes.** The `audit-remediation` branch adds an ingest
entry point, container and CI configuration, settings, and frontend fixes. If
something there is exploitable, report it privately through this repository's
security advisories ("Report a vulnerability" on the Security tab). If that is
unavailable, open an issue saying only that you have a report and asking for a
private channel — no details in the issue text.

## What to expect

An honest answer rather than a service level: this fork is a remediation
exercise, not a maintained product. Reports are read and acknowledged when the
owner is working on it, which is not continuous. Nothing here is deployed
publicly and no release is published from this repository, so the practical
exposure of a defect in the fork's own code is limited to whoever runs the
container stack themselves.

If a report turns out to affect the library rather than the fork, it will be
redirected upstream and you will be told so rather than left waiting.

## Out of scope

- The demo stack has **no authentication anywhere** — that is upstream's design
  for a prototype, documented in `README.md`, and not a finding. Anything
  reachable because the API is unauthenticated is expected behaviour, not a
  vulnerability.
- The `.env` in a local checkout, and any key placed in it, are the operator's.
- Findings already recorded in [`AUDIT.md`](AUDIT.md), including the ones marked
  `rejected` with their reasons.
