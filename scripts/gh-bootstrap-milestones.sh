#!/usr/bin/env bash
# Bulk-create Revel GitHub milestones and attach existing issues.
# GitHub has no bulk-create milestone endpoint. This is one script, many POSTs.
#
# Usage (from a clone of landNull/revel, after: gh auth login):
#   chmod +x scripts/gh-bootstrap-milestones.sh
#   ./scripts/gh-bootstrap-milestones.sh
#
# Optional:
#   REPO=landNull/revel ./scripts/gh-bootstrap-milestones.sh
#   DRY_RUN=1 ./scripts/gh-bootstrap-milestones.sh

set -euo pipefail

REPO="${REPO:-landNull/revel}"
DRY_RUN="${DRY_RUN:-0}"

JQ_MILESTONE_SUMMARY='.number,.title,.html_url'

api() {
  if [[ "$DRY_RUN" == "1" ]]; then
    printf 'DRY_RUN: gh api %s\n' "$*"
    return 0
  fi
  gh api "$@"
}

create_milestone() {
  local title="$1" due="$2" description="$3"
  printf 'milestone: %s\n' "$title"
  if [[ "$DRY_RUN" == "1" ]]; then
    return 0
  fi
  local existing
  existing="$(
    gh api "repos/${REPO}/milestones?state=all&per_page=100" \
      --jq ".[] | select(.title==\"${title}\") | .number" || true
  )"
  if [[ -n "${existing}" ]]; then
    printf 'exists: %s (#%s)\n' "$title" "$existing"
    return 0
  fi
  gh api --method POST "repos/${REPO}/milestones" \
    -f title="$title" \
    -f state="open" \
    -f due_on="$due" \
    -f description="$description" \
    --jq "${JQ_MILESTONE_SUMMARY}"
}

milestone_number() {
  local title="$1"
  gh api "repos/${REPO}/milestones?state=all&per_page=100" \
    --jq ".[] | select(.title==\"${title}\") | .number"
}

assign_issues() {
  local title="$1"
  shift
  local number
  number="$(milestone_number "$title")"
  if [[ -z "$number" ]]; then
    printf 'error: milestone not found: %s\n' "$title" >&2
    return 1
  fi
  local issue
  for issue in "$@"; do
    printf 'attach #%s -> %s (#%s)\n' "$issue" "$title" "$number"
    if [[ "$DRY_RUN" == "1" ]]; then
      continue
    fi
    gh issue edit "$issue" --repo "$REPO" --milestone "$title" >/dev/null
  done
}

create_milestone "M0 Foundation" "2026-10-12T23:59:59Z" \
  "Lock N001-N004, Python 3.11 package skeleton, agent contract."
create_milestone "M1 Graph" "2026-11-02T23:59:59Z" \
  "All 17 node types plus generic directed links."
create_milestone "M2 Store" "2026-11-16T23:59:59Z" \
  "SQLite default adapter. Scale path documented only."
create_milestone "M3 Control plane" "2026-12-07T23:59:59Z" \
  "revelctl create/link/query/mutate."
create_milestone "M4 Kanban projection" "2026-12-21T23:59:59Z" \
  "Primary projection plus calendar/gantt/list."
create_milestone "M5 TUI" "2027-01-18T23:59:59Z" \
  "Textual surface."
create_milestone "M6 Web" "2027-02-15T23:59:59Z" \
  "Python web backend; JS widgets are views only."
create_milestone "M7 Adapters" "2027-03-15T23:59:59Z" \
  "fs, IMAP/SMTP; OS users/groups optional."
create_milestone "M8 Package" "2027-03-31T23:59:59Z" \
  "wheel, pipx, container. No distro policy."

if [[ "$DRY_RUN" == "1" ]]; then
  echo "skip attach in DRY_RUN"
  exit 0
fi

assign_issues "M0 Foundation" 2 3 4 5 6 7
assign_issues "M1 Graph" 8 9 10 11 12 13 14
assign_issues "M2 Store" 15
assign_issues "M3 Control plane" 16
assign_issues "M4 Kanban projection" 17 18
assign_issues "M5 TUI" 19
assign_issues "M6 Web" 20
assign_issues "M7 Adapters" 21 22 23
assign_issues "M8 Package" 24

echo "done"
echo "list: gh api repos/${REPO}/milestones --jq .[].title"
