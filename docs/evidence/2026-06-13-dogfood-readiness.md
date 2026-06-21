# Dogfood Readiness Evidence - 2026-06-13

Command:

```bash
uv run warpline dogfood-eval --real-member-repo <lacuna-root> --output /tmp/warpline-dogfood-results.json --json
```

Result:

- Schema: `warpline.dogfood_results.v1`
- Real-member lane: 1/1 Lacuna case met parity against an executed
  `git diff --name-only` plus `rg` baseline.
- Real Loomweave lane: 1/1 Lacuna case showed uplift after MCP
  `capture_snapshot`; the current run captured 522 Loomweave edges and
  produced 4 `reverify` work items.
- Seeded federation smoke lane: 10/10 cases showed enriched reverify output.
- Synthetic solo lane: 0/10 cases passed after `NO_SNAPSHOT` was removed from
  the parity predicate; this lane is smoke coverage, not readiness evidence.
- Manual escape required: 0/1 real-member readiness cases.
- Output artifact: `/tmp/warpline-dogfood-results.json`

Interpretation:

This satisfies the current product-candidate threshold: one real member repo
must pass baseline parity, real Loomweave snapshot capture, and non-empty MCP
`changed -> reverify` uplift. Seeded cases still protect the Warpline-owned graph
contract, but they no longer decide readiness by themselves.
