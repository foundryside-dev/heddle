# Current State - Warpline

Checkpoint: 2026-06-29 — branch `release/1.2.0` (a 1.3.0-worth of accepted, **now-committed**
capability built atop v1.2.0; the version cut + release is the open owner escalation)

## The bet right now

**Cut + release the `release/1.2.0` stack.** Spine hardening shipped as **v1.2.0** (PDR-0006).
Atop it, four accepted capabilities have landed and are now **all committed**:

- **Verification-freshness** (PDR-0005 → accepted PDR-0007) — `last_verified` trust-decay axis,
  merged + validated on a real repo against its reversal trigger.
- **Four-member federation** (PDR-0008) — all `include_federation` members are real reverify
  consumers: filigree (work), wardline (risk/attest-2), legis (governance), **plainweave
  (requirements)** — the dimension warpline had never wired.
- **Arch-analysis Phase-2 reliability hardening** (PDR-0009, this session) — U1/U2/U3/U4/U8
  (`commits 69d081c + 62f2c4c`); guardrail work, behavior-preserving, suite 572 passed.

The capability is built, accepted, and committed; what remains is the **version cut (1.3.0 vs
1.2.x) and the public-release-status change** — an owner escalation (below).

## Branch / release state

- **`main` = v1.2.0** (spine hardening; PDR-0006).
- **Working branch = `release/1.2.0`** @ `62f2c4c` — carries v1.2.0 + verification-freshness +
  attest-2 risk + legis governance + `project_status` + D1 impact_completeness + the
  **requirements consumer** + the **Phase-2 reliability wave** — all committed.
- **Identity (standing requirement):** git/gh identity is **tachyon-beep** (active); johnm-dta
  inactive. Verified before each commit this session.

## In flight

- **Phase-2 reliability hardening (PDR-0009) — DONE, committed.** U1 orphan invariant, U2
  order-drift identity echo, U3 read-path breadcrumbs, U4 throttle gap, U8 loomweave client
  hardening. Adversarially reviewed; no tracker tickets (the arch-analysis→filigree bridge was
  owner-gated and the wave was done directly; recorded in PDR-0009 + the commits).
- `warpline-17242c627b` (P3) — atomic ROLLBACK coverage + no-open-transaction precondition.
  **OPEN — clean, startable** (last ungated 1.2.0 follow-up; distinct from Phase 2).
- `warpline-9eae3eb86a` (P3) — Charter→Plainweave sibling-guard evidence refresh. **Now ungated**
  — the `plainweave` sibling repo is present locally; reconfirm before claiming.
- Observation `warpline-obs-da4909ac64` (P3): bare-`assert`-under-`-O` in `mcp.py` inputSchema
  guard (expires 2026-07-09 unless promoted).

## Open questions / blocked-on-owner (escalations)

1. **Cut + release the `release/1.2.0` stack** — version cut (1.3.0 vs 1.2.x) + the
   public-release-status change outside this repo. Owner's call (grant: "changing
   public/user-facing release status outside this repo").
2. **Ship the requirements producer so the 4th member is actually live (reinstall).** The
   producer review found the installed `plainweave` is **stale (v1.0.0, no verb)** vs source
   v1.1.0 — so warpline's probe reads the member `disabled` until `uv tool install --force`
   reships plainweave on PATH (and warpline's own MCP binary likely needs the same rebuild for
   the MCP consumer path — see [[warpline-mcp-binary-staleness]]). Sibling/install action;
   plainweave also has an uncommitted `pyproject.toml` + handoff doc.
3. **5th-producer hub handover** — outward-facing/sibling. warpline-side package done; GS-7
   oracle wiring + glossary freeze (OD-5) remain.
4. **Swarm coordination / provenance (owner awareness).** Multiple uncoordinated swarm sessions
   landed sibling-consumer work in a shared tree this period — the legis/wardline consumers
   landed in prior sessions with no PDR, and this session a concurrent session co-mingled the
   requirements consumer with the Phase-2 wave in `commands.py` (resolved by committing both
   together). Worth a coordination convention before the next multi-stream push.
5. **(deferred)** Promoting `requirements`/`verification` into the frozen closed envelope vocab —
   future contract/glossary escalation (v1 keeps both as reverify-item fields; PDR-0005/0008).

## What this checkpoint did

- **PDR-0009** — accepted the arch-analysis Phase-2 reliability hardening wave (U1/U2/U3/U4/U8),
  delivered across two adversarially-reviewed workflows and committed (`69d081c` + `62f2c4c`);
  behavior-preserving, frozen contracts intact, 572 passed. Autonomous under the grant.
- **Reconciled a stale brief.** The prior checkpoint (PDR-0008) called the requirements consumer
  *UNCOMMITTED* and framed U2/U3/U4 as a *"concurrent, not this owner's"* observability stream —
  both wrong now: the requirements consumer is committed, and that stream **was** this owner's
  Phase-2 reliability wave. Corrected. Escalation "commit strategy for the consumer" is resolved.
- **metrics.md** — 2026-06-29 reading: Phase-2 guardrails strengthened; recorded the PDR-0008
  watch as **currently degraded** (stale plainweave binary → requirements `disabled` pending
  reinstall). **roadmap.md** — Now updated (Rung-2 diagnostic tier complete; Phase-2 done;
  release cut is the active intent). No reversal trigger crossed.

## Next session starts here

Owner decision on **escalation #1 + #2** — cut/release the stack, and the **plainweave reinstall**
that actually makes the 4th federation member live (without it the requirements dimension reads
`disabled`). Failing that, the clean repo-local pickup `warpline-9eae3eb86a` (Charter→Plainweave
evidence, now ungated) or `warpline-17242c627b` (atomic ROLLBACK coverage).
