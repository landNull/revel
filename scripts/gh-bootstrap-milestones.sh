#!/usr/bin/env bash
# Generic GitHub milestone bootstrap. Project data lives in a JSON source file.
# GitHub has no bulk-create milestone endpoint; this issues one POST per row.
#
# Usage:
#   ./scripts/gh-bootstrap-milestones.sh
#   ./scripts/gh-bootstrap-milestones.sh path/to/roadmap.json
#   SOURCE=planning/roadmap.json REPO=owner/name DRY_RUN=1 ./scripts/gh-bootstrap-milestones.sh
#
# Source schema (see planning/roadmap.json):
#   {
#     "repository": "https://github.com/owner/name" | "owner/name",
#     "milestones": [
#       {
#         "title": "M0",
#         "due_on": "2026-10-12T23:59:59Z",
#         "description": "optional",
#         "state": "open",
#         "issue_numbers": [1, 2]
#       }
#     ]
#   }

set -euo pipefail

SOURCE="${1:-${SOURCE:-planning/roadmap.json}}"
DRY_RUN="${DRY_RUN:-0}"

if ! command -v jq >/dev/null 2>&1; then
  echo "error: jq is required" >&2
  exit 1
fi
if ! command -v gh >/dev/null 2>&1; then
  echo "error: gh is required" >&2
  exit 1
fi
if [[ ! -f "$SOURCE" ]]; then
  echo "error: source file not found: $SOURCE" >&2
  exit 1
fi

repo_from_source() {
  local raw
  raw="$(jq -r '.repository // .repo // empty' "$SOURCE")"
  if [[ -z "$raw" ]]; then
    return 1
  fi
  raw="${raw#https://github.com/}"
  raw="${raw#http://github.com/}"
  raw="${raw%.git}"
  raw="${raw%/}"
  printf '%s\n' "$raw"
}

if [[ -n "${REPO:-}" ]]; then
  :
elif REPO="$(repo_from_source)"; then
  :
elif REPO="$(gh repo view --json nameWithOwner --jq .nameWithOwner 2>/dev/null)"; then
  :
else
  echo "error: set REPO=owner/name or put repository in $SOURCE" >&2
  exit 1
fi

jq empty "$SOURCE"
if ! jq -e '.milestones | type=="array"' "$SOURCE" >/dev/null; then
  echo "error: $SOURCE must contain a milestones array" >&2
  exit 1
fi

printf 'source: %s\n' "$SOURCE"
printf 'repo:   %s\n' "$REPO"

create_milestone() {
  local title="$1" due="$2" description="$3" state="$4"
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
  local -a flags=(-f title="$title" -f state="$state")
  if [[ -n "$description" ]]; then
    flags+=(-f description="$description")
  fi
  if [[ -n "$due" ]]; then
    flags+=(-f due_on="$due")
  fi
  gh api --method POST "repos/${REPO}/milestones" \
    "${flags[@]}" \
    --jq '.number,.title,.html_url'
}

milestone_number() {
  local title="$1"
  gh api "repos/${REPO}/milestones?state=all&per_page=100" \
    --jq ".[] | select(.title==\"${title}\") | .number"
}

assign_issues() {
  local title="$1"
  shift
  if [[ "$#" -eq 0 ]]; then
    return 0
  fi
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

while IFS=$'\t' read -r title due description state; do
  create_milestone "$title" "$due" "$description" "$state"
done < <(
  jq -r '
    .milestones[]
    | [
        .title,
        (.due_on // ""),
        ((.description // "") | gsub("\t"; " ") | gsub("\n"; " ")),
        (.state // "open")
      ]
    | @tsv
  ' "$SOURCE"
)

if [[ "$DRY_RUN" == "1" ]]; then
  echo "skip attach in DRY_RUN"
  exit 0
fi

while IFS=$'\t' read -r title numbers; do
  # numbers is space-separated issue ids
  # shellcheck disable=SC2086
  assign_issues "$title" $numbers
done < <(
  jq -r '
    .milestones[]
    | select((.issue_numbers // []) | length > 0)
    | [.title, ((.issue_numbers | map(tostring) | join(" ")))]
    | @tsv
  ' "$SOURCE"
)

echo "done"
echo "list: gh api repos/${REPO}/milestones --jq .[].title"
