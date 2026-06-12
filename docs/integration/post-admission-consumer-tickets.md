# Heddle Post-Admission Consumer Tickets

Status: draft ticket package. Use only after `spike/REPORT.md` recommends `go`
and owner admission is explicit.

Do not patch sibling repos from Heddle delivery work.

## Loomweave

- Goal: consume Heddle temporal history to implement or redirect `entity_high_churn_list` and `entity_recent_change_list`.
- Boundary: Loomweave owns current structure and SEI. Heddle supplies temporal history only.
- Acceptance: Loomweave still answers current graph queries from Loomweave storage; Heddle absence disables only churn/recency enrichment.

## Charter

- Goal: consume Heddle reverify/affected-set facts when Charter impact analysis lands.
- Boundary: Charter owns obligations, baselines, verification evidence, and requirement impact. Heddle supplies structural/temporal affected entities.
- Acceptance: Charter impact reports still run from local trace links when Heddle is absent.

## Legis

- Goal: optionally include Heddle affected-set facts in governance/preflight context.
- Boundary: Legis owns governance, sign-offs, CI/check context, and attestations. Heddle does not allow/block changes.
- Acceptance: Legis can surface Heddle context as advisory facts without changing policy decisions when Heddle is absent.

## Wardline

- Goal: optionally scope rescans to Heddle's affected set.
- Boundary: Wardline owns trust policy, findings, baselines, waivers, judge labels, and attestations.
- Acceptance: Wardline full scan remains available and authoritative; scoped scan output says when scope came from Heddle and what completeness/staleness applied.

## Filigree

- Goal: optionally file or link Heddle reverify worklists as work items after explicit user/tool action.
- Boundary: Filigree owns work state, issue lifecycle, claims, and close gates.
- Acceptance: Heddle never auto-files by default; generated work carries `scan_source`/producer identity and affected entity keys.
