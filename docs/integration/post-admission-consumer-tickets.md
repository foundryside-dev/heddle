# Warpline Post-Admission Consumer Tickets

Status: draft ticket package. Use only after `spike/REPORT.md` recommends `go`
and owner admission is explicit.

Do not patch sibling repos from Warpline delivery work.

## Loomweave

- Goal: consume Warpline temporal history to implement or redirect `entity_high_churn_list` and `entity_recent_change_list`.
- Boundary: Loomweave owns current structure and SEI. Warpline supplies temporal history only.
- Acceptance: Loomweave still answers current graph queries from Loomweave storage; Warpline absence disables only churn/recency enrichment.

## Charter

- Goal: consume Warpline reverify/affected-set facts when Charter impact analysis lands.
- Boundary: Charter owns obligations, baselines, verification evidence, and requirement impact. Warpline supplies structural/temporal affected entities.
- Acceptance: Charter impact reports still run from local trace links when Warpline is absent.

## Legis

- Goal: optionally include Warpline affected-set facts in governance/preflight context.
- Boundary: Legis owns governance, sign-offs, CI/check context, and attestations. Warpline does not allow/block changes.
- Acceptance: Legis can surface Warpline context as advisory facts without changing policy decisions when Warpline is absent.

## Wardline

- Goal: optionally scope rescans to Warpline's affected set.
- Boundary: Wardline owns trust policy, findings, baselines, waivers, judge labels, and attestations.
- Acceptance: Wardline full scan remains available and authoritative; scoped scan output says when scope came from Warpline and what completeness/staleness applied.

## Filigree

- Goal: optionally file or link Warpline reverify worklists as work items after explicit user/tool action.
- Boundary: Filigree owns work state, issue lifecycle, claims, and close gates.
- Acceptance: Warpline never auto-files by default; generated work carries `scan_source`/producer identity and affected entity keys.
