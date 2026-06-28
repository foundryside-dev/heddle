# 05 — Architecture Quality Assessment

> Scope: `src/warpline/` (30 modules, ~10.4k LOC) at HEAD `def6d43`. Assessor: architecture-critic
> (SME protocol). Evidence-based, severity-rated, no diplomatic softening. Inputs verified against
> `01-discovery-findings.md` and `02-subsystem-catalog.md` plus direct source reads.

## Verdict

**Overall Quality Score: 4 / 5 — Good.**
**Critical issues: 0. High issues: 2 (both maintainability/testability, heavily mitigated).**

Two genuine structural problems hold this below a 5: a 1863-LOC god-module (`store.py`) and a
276-LOC god-function (`reverify_worklist`), plus a cluster of Medium observability/fragility gaps
concentrated in the command-orchestration layer. None are defects shipping today; all are
future-edit hazards. They sit on top of an otherwise disciplined, contract-first codebase with an
exceptional correctness story — zero runtime dependencies, `mypy --strict`, a roughly 1:1
test-to-source ratio (~10,780 test LOC across 59 files vs 10,411 source LOC), clean layering with zero import
cycles, a rigorously-enforced honesty invariant, and a clean security posture — which is why the
structural problems read as a tax rather than a failure.

The score is anchored to the rubric: no Critical; the two High findings are the "monolith" example
the rubric names, mitigated by cohesion, zero internal fan-out, and heavy test coverage; the Mediums
are real but do not multiply into a 3. Security came back clean, which was the only input that could
have moved this below 4.

| Component | Score | Critical | High | Notes |
|-----------|-------|----------|------|-------|
| S1 Contract foundation | 5/5 | 0 | 0 | Closed vocabularies, honesty invariant; one Low I/O leak |
| S2 Store (`store.py`) | 4/5 | 0 | 1 | God-module; otherwise outstanding migration/merge discipline |
| S3 Compute | 5/5 | 0 | 0 | Pure, DI-tested core; the cleanest layer |
| S4 Commands (`commands.py`) | 3/5 | 0 | 1 | `reverify_worklist` god-function + Medium cluster concentrates here |
| S5 Resolution seams | 4/5 | 0 | 0 | Hand-rolled stdio JSON-RPC client is the untested risk |
| S6 Federation seams | 4/5 | 0 | 0 | Best-in-codebase honest degradation; inherently brittle to siblings |
| S7 Interface surfaces | 4/5 | 0 | 0 | Parity by convention; default duplication (Low) |
| S8 Lifecycle | 4/5 | 0 | 0 | `dogfood.py` re-implements S5/S7 plumbing (drift risk) |

---

## Findings by focus area

### Focus 1 — `store.py` god-module & `reverify_worklist` god-function

#### F1. `commands.reverify_worklist` is a 276-LOC orchestration god-function — **High**

- **Evidence:** `commands.py:793-1069`. Single function, fan_out **34** (highest in the system),
  orchestrating ≥8 distinct concerns inline: ref resolution (`815-821`), lazy capture (`824`), blast
  (`825-826`), per-entity verification-freshness with an inline cache and two git-reachability
  closures (`836-887`), stale-first presort (`908-914`), risk-as-verification SEI/locator capture
  (`934-945`), federation enrichment merge (`954-974`), attest content-hashing (`1002-1014`),
  impact-completeness (`986-992`), the list pipeline, and envelope assembly.
- **Impact:** High cyclomatic complexity. The function cannot be unit-tested below the integration
  level — every concern is entangled with the open store handle and the others' intermediate state.
  This is *where reliability bugs hide*: two of the Medium findings below (F4 throttle gap, F5
  positional invariant) live inside this function's orbit precisely because the concentration makes
  the invariants hard to see. The careful inline comments (`830-835`, `900-907`, `927-933`,
  `964-974`) are doing the work that extracted, individually-tested helpers should be doing.
- **Recommendation:** Extract the cohesive blocks into S3 (the pure compute layer) where they belong
  and can be unit-tested: a `VerificationResolver` (closures + cache, `863-887`), the SEI/locator
  capture (`934-945`), and keep `reverify_worklist` as thin wiring. The compute is already pure-ish;
  it is the *assembly* that is stranded in S4. Target: no tool body over ~80 LOC.

#### F2. `store.py` is a 1863-LOC god-module mixing four concerns — **High** (maintainability)

- **Evidence:** `store.py` holds (a) the frozen `SCHEMA` DDL (`35-107`), (b) the migration runner +
  schema-presence floor (`123-630`), (c) the read-only `read_store_binding` probe (`306-402`), and
  (d) the 40-method `WarplineStore` data-access class (`633-1863`). fan_in 38, fan_out 0 internal.
- **Impact:** This is a genuine problem, not "acceptable cohesion" — but the cost is bounded and the
  module is *defensibly* cohesive (it is all persistence; the zero internal fan-out is the evidence
  it is a true foundation, and the 40 methods do share the `self.conn` invariant). The cost is a
  navigation/merge-conflict tax and a single-file blast radius for any persistence edit. It does
  **not** block growth today and carries strong compensating controls (see Strengths). Rate it High
  on the maintainability axis, not as a reliability defect.
- **Recommendation:** Split along the four seams already visible in the file: `store_schema.py`
  (`SCHEMA` + `MIGRATIONS` + `_run_migrations` + `_schema_presence_floor`), `store_binding.py`
  (`read_store_binding` + `StoreBinding`), and `store.py` (`WarplineStore`). The merge family
  (`reresolve_entity_key_sei` → `_merge_into_twin` → `_repoint_*`, `770-1054`, ~270 LOC) is a natural
  fourth unit (`store_identity_merge.py`) given its high-stakes, self-contained nature.

### Focus 2 — Fail-soft `except Exception`: robustness vs silent-failure debuggability

The fail-soft pattern is **not monolithic** — it splits into two tiers with very different
observability, and the split is the finding.

**Honest tier (a genuine strength — see S2 below):** the federation seams catch broad `Exception`
but capture the exception text *in-band* into the response's `weft_reason.cause`:
`federation.py:248` (`filigree consult raised: {exc!r}`), `:279` (wardline), `:315` (legis). The
degraded result is honest **and** traceable — the opposite of a silent failure. `git.py`'s
fail-soft helpers (`is_ancestor`, `commits_between`, `resolve_commit`) likewise distinguish
"could not compute" (None) from a real answer.

**Silent tier (the finding):**

#### F3. Read-path swallows discard the exception with no trace anywhere — **Medium** (observability)

- **Evidence:** `commands.py:674` (`_lazy_capture_if_missing`) and `:707` (`_attest_content_hashes`)
  both `except Exception: return` with **no** `health_log` write, **no** `logger` call, and **no**
  in-band capture of `exc`. `session_context` (`:77`) does the same. Contrast: `health_log` is
  written from the *hook* paths (`cli.py:456,474`) and the store-internal paths
  (`store.py:421-427,1452,1510,1670`), but never from these read-path swallows.
- **Impact:** Debuggability, not correctness. The honesty invariant holds downstream — a swallowed
  lazy-capture degrades to `NO_SNAPSHOT`, a swallowed attest-hash to `attestation_incomplete` — so
  output is never wrong. But the **cause** is lost. An operator whose loomweave is subtly broken
  (malformed neighborhood, handshake regression) sees a permanently degraded result with no recorded
  reason and no way to distinguish "loomweave absent" from "loomweave present but erroring." The
  codebase already has the right pattern two layers over (federation's `{exc!r}` capture); these
  three sites simply do not use it.
- **Recommendation:** Route these swallows through `store.log_health(repo, "LAZY_CAPTURE_FAILED",
  repr(exc))` / `"ATTEST_HASH_FAILED"`. The store handle is already open in scope. This makes the
  read-path swallows as observable as the hook-path ones already are.

#### F4. Lazy-capture throttle does not cover post-probe capture failures — **Medium** (latency + observability)

- **Evidence:** `_lazy_capture_if_missing` (`commands.py:615-675`) records the throttle marker
  (`_record_lazy_capture_attempt`, `:649`) **only** on the `probe.status != "available"` branch. If
  the probe reports available but `capture_edge_snapshot` (`:661`) raises, control falls to the outer
  `except Exception: return` (`:674`) which records **nothing** and clears **nothing**. The module
  docstring (`:551-560`) claims "a failed/unavailable probe records a lightweight throttle marker" —
  but a capture-time failure is neither failed-probe nor recorded.
- **Impact:** On a repo where loomweave is reachable but capture consistently fails (a DB-write error,
  or a structural error in the loomweave response that escapes the per-entity guard), every
  subsequent read re-pays the full `LoomweaveProbe` spin-up (~1-5s, per the module's own latency
  note) **plus** the failing capture, forever, silently. The window is narrow — per-entity
  `neighborhood()` failures are caught and converted to `DELTA` failures inside
  `snapshot.py:144`, which still writes a snapshot and clears the marker (a real strength) — so the
  triggers are DB-level write failures and structural response errors, not ordinary loomweave
  flakiness. But within that window the cost is unbounded and invisible.
- **Recommendation:** Move `_record_lazy_capture_attempt(store)` to the outer `except` (or wrap the
  capture so any failure stamps the marker), so the throttle covers *all* failure modes its docstring
  claims to. Combine with F3's `log_health`.

### Focus 3 — Manual referential integrity on FK-less derived tables

#### F6. The `_merge_into_twin` family maintains integrity by hand on FK-less tables — **Medium** (fragility), implementation **sound**

- **Evidence:** `co_change_pairs` (`store.py:182-194`) and `snapshot_edges` (`store.py:91-99`) key on
  `entity_key_id` integers with **no** `FOREIGN KEY`. Integrity across a SEI re-resolution merge is
  maintained entirely in Python: `_merge_into_twin` (`831-901`), `_repoint_co_change_pairs`
  (`903-990`), `_repoint_snapshot_edges` (`992-1054`), all inside one `BEGIN IMMEDIATE` txn.
- **Adjudication — the implementation is correct, and that deserves credit:** globally-unique
  `AUTOINCREMENT` `entity_keys.id` makes the cross-table repoint sound (no id reuse to alias an edge
  onto the wrong entity); collision handling is canonical (co-change counts are *summed*, recency
  kept via `_later_marker`'s "non-null beats null" rule `430-448`, self-pairs dropped `:946-948`);
  `change_events` collisions delete the null-keyed duplicate (M5) with **documented, intentional**
  data loss of divergent `hunk_summary`/`actor` (`:868-873`, Q7) — acceptable on a convergent
  self-heal path, not a defect. The repoint runs *before* the null-key DELETE (`:896-900`), so no
  dangling reference window exists.
- **Impact:** The risk is not today's correctness — it is that ~270 LOC of high-stakes surgery
  replaces what a DB-level `FOREIGN KEY ... ON ... ` or a generated-column constraint would enforce
  for free. A future contributor adding a third `entity_key_id`-referencing table, or altering the
  canonical-ordering rule, must manually replicate all three collision modes (self, re-canonicalize,
  collide) or silently corrupt the graph. SQLite FKs are off by default and the project chose not to
  enable them; that choice is now load-bearing on reviewer vigilance.
- **Recommendation:** Either (a) enable `PRAGMA foreign_keys=ON` and add real FKs with
  `ON DELETE`/repoint semantics where SQLite supports them, accepting the merge still needs manual
  re-canonicalization; or (b) keep manual but add a `_assert_no_orphans` debug invariant run in tests
  after every merge, so a future edit that breaks integrity fails a test rather than ships.

#### F7. `_repoint_snapshot_edges` docstring claims self-edge collapse the code does not do — **Low**

- **Evidence:** `store.py:999` docstring: "collapse a source==target self-edge. `INSERT OR IGNORE` …"
  But `INSERT OR IGNORE` (`:1040-1054`) only collapses **duplicate PK** rows, not a self-edge: when
  an edge `(source=null_key, target=twin)` is repointed it becomes `(source=twin, target=twin)` and
  is inserted as a self-edge. The sibling `_repoint_co_change_pairs` *does* explicitly drop self-pairs
  (`:946-948`); `snapshot_edges` has no equivalent `new_source == new_target` guard.
- **Impact:** Benign **today**: `blast_radius`'s BFS dedups on a `seen` set (`propagation.py:81-83`),
  so a `twin→twin` self-edge is skipped (twin is always already seen) and never produces a spurious
  affected entry. But the spurious row persists in `snapshot_edges` and would surface to any consumer
  that reads edges directly, and the doc/code mismatch is exactly the maintenance trap F6 warns about
  — the asymmetry between the two repoint paths reads as intentional when it is not.
- **Recommendation:** Add the `if new_source == new_target: continue` guard to match
  `_repoint_co_change_pairs`, or correct the docstring. One line either way.

### Focus 4 — Dual-surface (CLI/MCP) over one `commands.py`

**Strength:** "two surfaces, one core" is real and well-executed. Both `cli.py` and `mcp.py` delegate
to the same `commands.py` functions, so business-logic parity is *structural*, not tested-into-place.
Tool metadata is declarative (`mcp.py:_build_tools`), endorsed-name + shim return identical
schema+data, and golden contract vectors pin the envelope (`tests/contracts/test_golden_vectors.py`,
`test_reverify_worklist_schema.py`).

#### F8. Input defaults are independently re-specified per surface — **Low** (duplication)

- **Evidence:** The numeric defaults exist in **three** places that must stay in sync by convention:
  the `commands.py` signature defaults (`depth=2`, `limit=50/100`), the MCP coercers
  (`mcp.py:351-391` `_depth_arg` defaults 2, `_limit_arg(args, 50)` / `(args, 100)`), and the
  `cli.py` argparse types. They match today.
- **Impact:** The "identical schema+data" guarantee covers the *core path* but **not** the per-surface
  input coercion/defaults, which are re-encoded. A future change to a default in one surface drifts
  silently from the others. I did **not** find a test asserting numeric-default equality across CLI
  and MCP (the golden vectors pin envelope *shape*, not cross-surface default parity) — though I did
  not exhaustively read all 59 test files, so state this as "not confirmed present," not "absent."
- **Recommendation:** Source defaults from one module-level constant table imported by both surfaces,
  or add a parity test that drives the same args through both and asserts equal envelopes.

### Focus 5 — Coupling / cohesion / separation of concerns / testability

- **Layering is clean and the module-import graph is acyclic** (`module_circular_import_list` = 0).
  *Reconciliation note (post-validation):* `02-subsystem-catalog.md` was corrected after this
  assessment to record one **subsystem-level S2↔S3 back-edge** — `store` (S2) lazily imports
  `coupling` (S3) at `store.py:1468-1469,1554` (and `cli.py:136`), while `propagation`/`_blast` (S3)
  import `store` (S2). It stays *module*-acyclic only because `coupling` is a pure leaf and the import
  is deferred — an explicit workaround. This is a minor coupling smell, not a cycle that breaks the
  build; it does not change the F1/F2 severities but it is the kind of layer-bleed the F4/F2 split work
  should tidy. The other upward reaches (S8→S7 dogfood drives `mcp.dispatch`; S3→S6 `reverify` imports
  seam *ports*) are intentional and acyclic.
- **The pure compute layer (S3) is the architecture's best decision** — DI via callbacks/Protocols
  (`verification.compose_verification_freshness` takes `covers`/`between`; `reverify` takes a
  `WorkClient`) keeps it unit-testable with no DB or git. This is why S3 scores 5/5.
- **But the orchestration glue that *feeds* S3 is stranded in S4** (`_lazy_capture_if_missing`,
  `_attest_content_hashes`, `_merge_federation_enrichment`, `_member_scalar`, the `verification_for`
  cache). These reusable-looking helpers live in the command module, not the compute layer, which is
  the structural root of F1. The compute is clean; its assembly is concentrated.

#### F5. Unenforced positional invariant across the `_blast`/`commands` boundary — **Medium** (correctness-fragility)

- **Evidence:** `commands.py:836-843` builds `changed_key_ids`/`affected_key_ids` from
  `result["changed"]`/`result["affected"]` by **position**, then aligns them positionally to the
  frozen `changed`/`affected` entity views (which deliberately drop `entity_key_id` for
  SEI-orthogonality). Correctness depends on `enrich_blast` (`_blast.py:142-159`) iterating the same
  source lists in the same order with no filter — enforced **only** by code comments
  (`commands.py:830-835` "verified _blast.py:142-157"; `_blast.py:142-143`).
- **Impact:** The verification-freshness block is attached to entities by index. A future edit that
  filters one side but not the other (e.g., `enrich_blast` skips a row with a null `entity_key_id`
  while the key-id extraction does not) silently misattaches the *wrong verification state to the
  wrong entity* — a correctness bug with no exception, caught only by a test that happens to exercise
  a filtered case. The frozen view dropping `entity_key_id` is the right call (SEI-orthogonality); the
  *parallel-list* compensation is the fragile part.
- **Recommendation:** Carry `entity_key_id` in a private (non-frozen) field on the enriched rows so
  the alignment is by-key, not by-index, eliminating the positional dependency; or add an assertion
  (`len(changed) == len(changed_key_ids)` plus a per-row id echo) so a future divergence fails loudly.

### Focus 6 — Other genuinely notable items

#### F9. Read-only git verbs lack a `--` options terminator before refs/paths — **Low** (security hardening)

- **Evidence:** `resolve_commit` (`git.py:95`), `commits_between` (`:130`), `_commits` (`:39-43`),
  `is_ancestor` (`:109-114`) interpolate caller-supplied refs into argv without a `--`
  end-of-options separator.
- **Impact:** No shell injection exists anywhere (verified: zero `shell=True`/`os.system`/`os.popen`;
  argv-list throughout; SEI/qualname/path passed as discrete argv elements `federation.py:77,176`,
  `loomweave.py:52,155`; SQL fully parameterized with the only interpolation being int-coerced
  `PRAGMA user_version = {int}`). The residual is *argument*-injection: a ref/path beginning with `-`
  consumed as a git flag. Bounded to read-only verbs (`rev-parse`/`rev-list`/`merge-base`/`log`/
  `show`) with no code-execution primitive, and the "attacker" must already be the local CLI/MCP
  caller — outside warpline's local-first, single-tenant threat model. This is a hardening nit, not a
  vulnerability, and does **not** move the score.
- **Recommendation:** Insert `"--"` before ref/path arguments (`["rev-parse", "--verify", "--quiet",
  "--", f"{ref}^{{commit}}"]` where the verb supports it), as defense-in-depth.

#### F10. `listing.py` mixes pure predicates with filesystem overflow-spill — **Low** (carried from catalog)

- **Evidence:** `02-subsystem-catalog.md:54` (S1 Concerns) — `apply_overflow` writes a file inside an otherwise
  side-effect-free contract module (S1). Assessed via catalog, not line-by-line (see Information Gaps).
- **Impact:** A small I/O leak into the layer that is otherwise the purest in the system; complicates
  unit-testing the list pipeline in isolation.
- **Recommendation:** Inject the spill sink (a writer callback) so the predicate pipeline stays pure.

#### F11. `loomweave.py`'s hand-rolled `selectors`-based stdio JSON-RPC client is the untested risk — **Low-Medium**

- **Evidence:** `LoomweaveMcpClient` (`loomweave.py:91-229`, ~170 LOC of `subprocess.Popen` +
  `selectors` non-blocking I/O + deadline handling). A deadlock/timeout bug here degrades every
  graph-enriched tool. `02-subsystem-catalog.md:228` (S5 Concerns) flags it; `test_loomweave_probe.py` exists
  but I did not confirm it exercises the concurrency/timeout paths.
- **Recommendation:** Targeted tests for the deadline, partial-read, and process-death paths.

---

## Strengths (genuine, evidence-cited — not token positivity)

1. **Clean security posture.** Zero runtime dependencies (`pyproject.toml:24`), no `shell=True` /
   `os.system` / `os.popen` anywhere, argv-list subprocess invocation throughout, fully parameterized
   SQL (only interpolation is int-coerced `PRAGMA user_version`). For a tool that shells out to git +
   three sibling CLIs, this is the right posture and it is held consistently.
2. **The honesty invariant is real and rigorously enforced end-to-end**, including in degradation:
   closed `ENRICHMENT_VOCAB`/reason/error vocabularies (`envelope.py:12-20`, `errors.py`,
   `listing.py:14-33`), and the federation seams capture the failing exception *in-band*
   (`federation.py:248,279,315`) so degradation is honest **and** debuggable. `absent` is never
   conflated with `unavailable`.
3. **Migration discipline is sophisticated.** Forward-only, `BEGIN IMMEDIATE` per-step atomicity,
   concurrent-open safety via re-read under the RESERVED lock (`store.py:611-630`), and the
   standout `_schema_presence_floor` (`:469-509`) that refuses to trust a `meta.schema_version`
   marker the on-disk objects do not back up — defending against a lying marker is a level of rigor
   most projects never reach.
4. **The identity-merge surgery is correct** (F6): globally-unique key ids, canonical collision
   handling, recency-preserving, no dangling-reference window, with intentional+documented data loss.
5. **`read_store_binding`** (`store.py:306-402`) is a correctly-designed strictly-read-only probe
   (`mode=ro`, creates nothing, fails closed on out-of-vocab status at `commands.py:1446-1449`),
   properly distinct from the lazily-creating `open()` — the right tool for stale-binary detection.
6. **The pure S3 compute core + Protocol ports** make the analytical heart unit-testable without
   infrastructure.
7. **Test investment is exceptional**: ~1:1 test-to-source ratio (~10.8k test LOC), 59 files, including contract
   golden vectors, an honesty-invariant suite, migration tests, and reresolve/merge tests.

---

## Confidence Assessment

**Overall confidence: High.** I read in full: `commands.py` (1486 LOC), `store.py:1-632` and
`:770-1054` (schema, migration runner, presence floor, the entire merge family), `read_store_binding`,
`propagation.py`, `_blast.enrich_blast`, `snapshot.py:110-169`, `federation.py:230-318`,
`siblings.py:40-79`, `git.py:1-135`, and the MCP handler defaults. Findings F1-F9 are grounded in
directly-read file:line evidence and verified control flow (F4 and F5 were traced, not inferred). F7
was confirmed by reading both repoint functions and the BFS consumer. Security claims were verified by
exhaustive grep (`shell=True`/`os.system`/`os.popen` → none) plus reading every subprocess argv site.

**Lower confidence (Medium):** F10 (`listing.py` I/O leak — taken from the catalog, not read
line-by-line) and F11 (`loomweave` client test coverage — existence of `test_loomweave_probe.py`
confirmed, contents not read). The F8 negative ("no cross-surface default-parity test") is stated as
*not confirmed present* rather than *absent* because I did not read all 59 test files.

## Risk Assessment

- **Highest residual risk: F5 (positional invariant).** It is the only finding that can produce a
  *silent correctness* failure (wrong verification state on the wrong entity) rather than a degraded-
  but-honest one. Likelihood is low (requires a specific future edit) but detection is poor.
- **Operational risk: F4 (throttle gap).** Narrow trigger window, but within it the cost is unbounded
  and invisible — the kind of issue that surfaces as "warpline got slow" with no diagnostic trail.
- **Maintenance risk: F1 + F2 + F6.** The two god-units plus the manual FK integrity concentrate
  future-edit hazard. They do not threaten today's correctness; they threaten the *next* contributor's
  ability to change persistence or the reverify flow without regression.
- **No security risk identified** within the local-first, single-tenant threat model. F9 is hardening.
- **Inherent (accepted) risk:** S6's three-transport sibling fan-out (filigree HTTP, legis CLI,
  wardline CLI) is brittle to sibling interface changes by design; mitigated by mirrored schemas +
  consumer-rejection tests. Not a warpline-side defect.

## Information Gaps

- `store.py:1056-1863` (co-change update path, churn aggregation, snapshot read methods) was assessed
  via signatures, docstrings, and the catalog's method inventory — **not** line-by-line. Findings do
  not depend on its internals, but I cannot certify that region at the same confidence as `:1-1054`.
- `listing.py`, `cop.py`, `cli.py`, and the S8 modules were assessed via catalog + call sites, not
  full reads. F10 inherits the catalog's confidence.
- I did not run the test suite or measure actual coverage; the ~1:1 ratio is a LOC count, not a
  branch-coverage figure, and I did not verify that F4/F5/F7's specific paths are tested.
- The `loomweave` JSON-RPC client's concurrency/timeout behavior (F11) was not exercised or read.

## Caveats

- Severities are rated against the rubric's objective definitions, deliberately resisting the
  symmetric temptation to inflate Mediums to Highs to "look rigorous." F3/F4 are Medium and *heavily
  mitigated by the honesty invariant* (downstream output stays correct); they are observability and
  latency issues, not correctness. F7 and F9 are correctly Low (neutralized by the BFS `seen`-set and
  the argv-list posture respectively). I have stated each mitigation so the severities read as earned.
- The two High findings are maintainability/testability concentrations, **not** defects. Nothing here
  ships broken. The 4/5 reflects a system that is correct and disciplined today but carries two
  structural decisions (the god-units) and one fragile invariant (F5) that will tax or trip future
  edits.
- This assessment critiques architecture quality only. Cataloguing the debt items as tracked tickets,
  and sequencing the recommended refactors, are out of scope (route to debt-cataloger /
  prioritize-improvements).
