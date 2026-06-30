# 06 — Architect Handover

**Purpose:** transition from *analysis* to *improvement planning*. This unifies the independent
architecture-critic findings (`05-quality-assessment.md`, F1-F11) and the debt catalog
(`temp/debt-catalog.md`, D1-D12) into one de-duplicated, prioritized, sequenced backlog an architect or
maintainer can act on.

**Headline for the decision-maker:** warpline is a **4/5, healthy, contract-first system with zero
shipping defects**. The work below is *future-edit hazard reduction*, not firefighting. It is small in
absolute terms (one High, a handful of Mediums) and the two highest-value items are **cheap**
(a property test; three log lines). There is no rewrite here — the architecture is sound.

---

## 1. Verdict recap

| Axis | Finding |
| --- | --- |
| Overall quality | **4/5 — Good** (architecture-critic, SME-rated) |
| Critical / High / Med / Low | 0 Critical · 1 High (data-integrity, `D2/F6`) · ~6 Medium · ~6 Low |
| Shipping defects | **None.** Every finding is a maintainability, observability, latency, or fragility hazard for *future* edits |
| Security | **Clean** within the local-first, single-tenant model (zero deps, no shell, argv-list, parameterized SQL) |
| Best decisions | Pure S3 compute + Protocol ports; the honesty invariant; `_schema_presence_floor` migration rigor; zero supply chain |
| Worst decisions | Concentration: `store.py` (god-module) + `reverify_worklist` (god-function); manual FK integrity |

---

## 2. Finding reconciliation (critic F ↔ debt D)

The two independent passes agree strongly; the critic added four items the debt pass didn't (F4, F5,
F7, F9), and the debt pass added items the critic folded into prose (D4, D5, D7, D8, D10). Unified:

| Unified ID | Item | Critic | Debt | Severity (reconciled) |
| --- | --- | --- | --- | --- |
| **U1** | FK-less derived tables — manual referential integrity | F6 | **D2** | **High** (only data-integrity item) |
| **U2** | Positional invariant `_blast`↔`commands` (silent mis-attribution) | **F5** | — | Medium (highest *residual* risk — silent-correctness) |
| **U3** | Silent read-path `except Exception` swallows (no breadcrumb) | F3 | D6 | Medium (best effort/value ratio) |
| **U4** | Lazy-capture throttle misses capture-time failures | **F4** | — | Medium (latency + observability) |
| **U5** | `reverify_worklist` god-function (276 LOC, fan_out 34) | F1 | D3 | Medium-High |
| **U6** | `store.py` god-module (1863 LOC, 4 concerns) | F2 | D1 | Medium |
| **U7** | Orchestration glue stranded in S4 (feeds U5) | (Focus 5) | D4 | Medium |
| **U8** | `loomweave` stdio client test-gap / timeout fragility | F11 | D12 | Medium |
| **U9** | Attest N+1 loomweave round-trips (per-SEI) | — | D5 | Medium (perf, attest path only) |
| **U10** | Per-surface input default / arg-coercion duplication | F8 | D9 | Low |
| **U11** | `_repoint_snapshot_edges` self-edge: docstring ≠ code | **F7** | — | Low |
| **U12** | `dogfood.py` re-implements S5/S7 plumbing | — | D7 | Low |
| **U13** | Hardcoded `/tmp` + `spike/REPORT.md` default paths | — | D8 | Low |
| **U14** | git verbs lack `--` options terminator | **F9** | — | Low (hardening) |
| **U15** | `listing.py` FS overflow-spill in pure S1 layer | F10 | D11 | Low |
| **U16** | Unraised `WarplineError` subclasses (frozen-vocab) | — | D10 | Low (likely intentional — *document, don't delete*) |

Plus a **housekeeping** item outside `src/` scope:

| **U17** | 3 `test_attest.py` HighEntropyHex loomweave findings are **false positives** (content-addressing hashes + a synthetic `bbbb…` fixture + a commit SHA used as test data, not credentials — verified). `.env` is git-ignored (OK). | Waive in the loomweave/wardline baseline. |

---

## 3. Recommended sequence

Ordered by **(value × inverse effort)**, then by risk class. Each is behavior-preserving and gated by
the existing (~1:1, 59-file) test suite.

### Wave 1 — cheap, high-leverage (do first; ~1-2 days total)

1. **U3 + U4 — read-path observability (S, Medium).** Route the three silent swallows
   (`commands.py:77,674,707`) through `store.log_health(repo, "<CODE>", repr(exc))`, and move the
   throttle-marker stamp into the outer `except` of `_lazy_capture_if_missing`. *Removes a whole class
   of invisible field degradation.* Note: the `# noqa: BLE001` annotations are currently **inert** (BLE
   is not in ruff's `select`) — either add `BLE` to the select set or drop the misleading comments.
2. **U1 — FK-integrity invariant (M, High).** Do **not** rewrite the schema (SEI-orthogonality is
   deliberate, `store.py:177`). Add a `_assert_no_orphans` debug/CI invariant + a property test that
   runs the full `_merge_into_twin` family against a fixture and asserts every `*_entity_key_id`
   resolves. Converts a silent-corruption risk into a loud test failure.
3. **U2 — eliminate the positional invariant (S-M, Medium, highest residual risk).** Carry
   `entity_key_id` in a private (non-frozen) field on the enriched rows so verification state aligns
   *by key*, not by index (`commands.py:836-843`); or assert `len`+per-row id echo. This is the only
   finding that can fail *silently incorrect* — fix it before it can be tripped.
4. **U11 + U14 + U16 — one-line hygiene.** Add the `new_source == new_target` guard (or fix the
   docstring) in `_repoint_snapshot_edges`; insert `"--"` before git refs in the read-only verbs;
   annotate the three reserved error subclasses as frozen-vocab (don't delete).
5. **U17 — waive the 3 test_attest false-positive secrets** in the loomweave/wardline baseline.

### Wave 2 — structural (the refactors; sequence matters)

6. **U6 — split `store.py`** along its four visible seams: `store_schema.py` (DDL + migrations +
   presence-floor), `store_binding.py` (`read_store_binding`/`StoreBinding`), `store_identity_merge.py`
   (the `_merge_into_twin`/`_repoint_*` family — naturally pairs with the U1 invariant), and `store.py`
   (the `WarplineStore` read/write methods). Mechanical, behavior-preserving.
7. **U5 + U7 — extract `reverify_worklist` assembly into S3.** Move the verification resolver (cache +
   `_covers`/`_between` closures), the SEI/locator capture, and the stranded glue
   (`_lazy_capture_if_missing`, `_attest_content_hashes`, `_merge_federation_enrichment`) down into the
   pure compute layer / a `reverify_assembly` seam. Leaves `reverify_worklist` as thin wiring (target
   ≤ ~80 LOC) and unlocks unit tests for each concern. Do *after* U6 so the store seams are stable.
8. **U8 — harden + test the loomweave client.** Add a read deadline and focused tests for partial
   reads, EOF/broken-pipe, oversized frames, and timeout (a hang here degrades every graph-enriched
   tool).

### Wave 3 — opportunistic (low priority; do when touching the area)

9. **U9** batch the attest loomweave resolve (add a batch call to `LoomweaveMcpClient`).
10. **U10** centralize per-surface defaults/coercion in one shared table. **U12** reuse S5/S7 from
    `dogfood`. **U13** derive temp paths from `tempfile.gettempdir()`. **U15** inject the `listing`
    overflow-spill sink.

---

## 4. What NOT to do

- **Do not add naive FK/CASCADE to the derived tables.** It would fire mid-merge and break the
  intentional SEI-orthogonal repoint. U1's fix is a *test invariant*, not a schema change.
- **Do not delete the three unraised error subclasses (U16).** They pin entries of the frozen
  `warpline.error.v1` vocabulary; removing them is a contract change.
- **Do not "fix" the federation broad-`except` swallows.** They already capture `{exc!r}` in-band into
  `weft_reason.cause` — that is the *correct* pattern (and the model U3 should copy), not debt.
- **Do not refactor for its own sake.** This is a 4/5 system; Wave 1 captures most of the value.

---

## 5. Decision points for the owner

1. **Adopt FKs or keep manual?** (U1) Recommended: keep manual + add the invariant test. Confirm.
2. **Refactor budget.** Wave 1 is ~1-2 days and high-value; Waves 2-3 are optional structural
   investment. Decide whether the god-unit splits (U5/U6) are worth the churn now or deferred until the
   next feature touches them.
3. **Bridge to the tracker.** This repo uses **filigree**. Recommended: promote U1-U8 to filigree
   issues (U1/U2/U3 as P1; U5/U6/U8 as P2), labelled `arch-analysis-2026-06-28`. The codebase also has
   **warpline itself** (`reverify`) and **wardline** (`scan`) gates — run them before/after each
   refactor wave.

## 6. Next-step tooling

- **Prioritization deep-dive:** `axiom-system-architect:prioritize-improvements` (this handover is its
  input).
- **Per-refactor planning:** `axiom-planning:implementation-planning` for U5/U6 (the structural moves).
- **Validation evidence** for this analysis: `temp/validation-catalog.md` (catalog gate, PASS-WITH-FIXES,
  all fixes applied), `temp/debt-catalog.md` (full debt inventory), and `05-quality-assessment.md` (the
  SME critique with confidence/risk/gaps).

---

*Analysis package complete: `00`-`06` + `temp/`. Confidence: High. Scope: `src/warpline/` at HEAD
`def6d43`. The two structural Highs (U5/U6) and the silent-correctness Medium (U2) are the items most
worth an architect's attention; everything else is hygiene.*
