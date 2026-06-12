#!/usr/bin/env bash
set -euo pipefail

baseline="docs/evidence/member-dirty-baseline.txt"
current="$(mktemp)"
trap 'rm -f "$current"' EXIT

for repo in /home/john/filigree /home/john/wardline /home/john/legis /home/john/loomweave /home/john/charter; do
  printf '## %s\n' "$repo" >>"$current"
  if [ -d "$repo/.git" ]; then
    git -C "$repo" status --short >>"$current"
  fi
done

if ! diff -u "$baseline" "$current"; then
  printf 'Member repo dirty state differs from recorded baseline. Stop and record or resolve the difference explicitly.\n' >&2
  exit 1
fi
