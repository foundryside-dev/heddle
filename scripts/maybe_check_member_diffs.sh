#!/usr/bin/env bash
set -euo pipefail

case "${WARPLINE_CHECK_MEMBER_DIFFS:-0}" in
  1|true|TRUE|yes|YES|on|ON)
    bash scripts/check_no_member_diffs.sh
    ;;
  *)
    printf 'Skipping sibling dirty-baseline check; set WARPLINE_CHECK_MEMBER_DIFFS=1 to enable.\n' >&2
    ;;
esac
