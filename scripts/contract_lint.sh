#!/usr/bin/env bash
# contract_lint.sh — sprint-harness v3.1 contract hygiene linter.
# Lints docs/sprint/sprints/<sprint-id>.md: length budget, QA-Notes/
# Completed entry-length caps, Dev-Complete move-integrity, ISO-8601
# not-future timestamps, Context Dump budget, status/total_items rule.
# Usage: contract_lint.sh <sprint-id> | contract_lint.sh -f <path>
# Exit: 0 all PASS; 1 a check FAILed; 2 usage/file error.
# Make executable: chmod +x contract_lint.sh
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: contract_lint.sh <sprint-id>
       contract_lint.sh -f <path>

Lints a sprint contract file for sprint-harness v3.1 hygiene rules:
  1. contract length <= 400 lines
  2. each QA Notes entry <= 8 lines
  3. each Completed entry <= 3 lines
  4. Dev-Complete move-integrity when completed_items == total_items
  5. locked_at / last_updated / lint timestamps are ISO-8601 (Z or
     +NN:NN offset) and not in the future
  6. Context Dump section <= 10 lines
  7. status: planned requires total_items > 0; total_items: 0 is legal
     only with status: planning

<sprint-id> resolves docs/sprint/sprints/<sprint-id>.md relative to the
repo root (via `git rev-parse --show-toplevel`, falling back to the
current directory). Use -f <path> to lint an arbitrary file directly.

Prints one PASS/FAIL line per check, then a final one-line summary for
the contract's `lint:` frontmatter field, e.g. "PASS 396 2026-07-10T11:02:07Z"
(result, line count, current `date -u` timestamp).

Exit codes: 0 all PASS; 1 one or more FAIL; 2 usage/file error.
EOF
}

# --- Argument parsing ---
FILE=""
SPRINT_ID=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    -f)
      shift
      if [[ $# -eq 0 ]]; then
        echo "error: -f requires a path argument" >&2
        exit 2
      fi
      FILE="$1"
      shift
      ;;
    -*)
      echo "error: unknown option '$1'" >&2
      usage >&2
      exit 2
      ;;
    *)
      if [[ -n "$SPRINT_ID" || -n "$FILE" ]]; then
        echo "error: unexpected extra argument '$1'" >&2
        exit 2
      fi
      SPRINT_ID="$1"
      shift
      ;;
  esac
done

if [[ -z "$FILE" && -z "$SPRINT_ID" ]]; then
  echo "error: sprint-id or -f <path> is required" >&2
  usage >&2
  exit 2
fi

if [[ -z "$FILE" ]]; then
  REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
  FILE="${REPO_ROOT}/docs/sprint/sprints/${SPRINT_ID}.md"
fi

if [[ ! -f "$FILE" ]]; then
  echo "error: contract file not found: $FILE" >&2
  exit 2
fi

# --- Frontmatter + section helpers -----------------------------------------

# get_field KEY — prints the scalar value of a top-level frontmatter key
# (between the first two `---` fences), quote-stripped. Empty if absent.
# Tolerant of block scalars / list values elsewhere in the frontmatter —
# only lines matching literally "^KEY:" at column 0 are considered.
get_field() {
  local key="$1" raw
  raw=$(awk -v key="$key" '
    BEGIN { fences = 0; infm = 0 }
    /^---[[:space:]]*$/ {
      fences++
      if (fences == 1) { infm = 1; next }
      else { exit }
    }
    infm && $0 ~ "^" key ":" {
      line = $0
      sub("^" key ":[ \t]*", "", line)
      print line
      exit
    }
  ' "$FILE" 2>/dev/null || true)
  raw="${raw%\"}"; raw="${raw#\"}"
  raw="${raw%\'}"; raw="${raw#\'}"
  printf '%s' "$raw"
}

# get_section_bounds NAME — prints "START END" line numbers (1-based) for
# the body of a "^## NAME" section, END being the line before the next
# "^## " header or EOF. Prints "0 0" if the section is not found.
get_section_bounds() {
  local name="$1"
  awk -v name="$name" '
    { total = NR; lines[NR] = $0 }
    END {
      start = 0
      for (i = 1; i <= total; i++) {
        if (lines[i] ~ ("^## " name "([[:space:]]|$)")) { start = i; break }
      }
      if (start == 0) { print "0 0"; exit }
      end = total
      for (i = start + 1; i <= total; i++) {
        if (lines[i] ~ /^## /) { end = i - 1; break }
      }
      print start, end
    }
  ' "$FILE"
}

# --- Check 1 — overall contract length ---
TOTAL_LINES=$(wc -l < "$FILE" | tr -d ' ')

check_line_count() {
  if (( TOTAL_LINES <= 400 )); then
    echo "PASS: contract length (${TOTAL_LINES} lines <= 400)"
    return 0
  fi
  echo "FAIL: contract length (${TOTAL_LINES} lines > 400) — compress: move per-item Completed verification essays, QA Notes essays, and retained planner-era Context Dump to the sprint's {id}-log.md"
  return 1
}

# --- Checks 2 & 3 — per-entry length caps (QA Notes, Completed) ---
# check_entry_lengths SECTION START_RE BOUNDARY_RE LIMIT LABEL
# Entries begin at any line matching START_RE; an entry closes at the next
# line matching BOUNDARY_RE (a new entry start, or a higher-level heading).
# Length is counted in NON-BLANK content lines (the start/header line
# included) so a spacer blank line before the next entry never inflates
# the count.
check_entry_lengths() {
  local section="$1" start_re="$2" boundary_re="$3" limit="$4" label="$5"
  local sstart send
  read -r sstart send < <(get_section_bounds "$section")
  if [[ "$sstart" -eq 0 ]]; then
    echo "PASS: ${label} (no ## ${section} section found)"
    return 0
  fi
  local violations
  violations=$(awk -v s="$sstart" -v e="$send" -v sre="$start_re" -v bre="$boundary_re" -v lim="$limit" '
    NR >= s && NR <= e { lines[NR] = $0 }
    END {
      entry_start = 0
      content = 0
      for (i = s; i <= e; i++) {
        line = lines[i]
        is_start = (line ~ sre)
        is_boundary = (line ~ bre)
        if (is_boundary && entry_start > 0 && i > entry_start) {
          if (content > lim) print entry_start ":" content
          entry_start = 0
          content = 0
        }
        if (is_start) { entry_start = i; content = 0 }
        if (entry_start > 0 && line !~ /^[ \t]*$/) { content++ }
      }
      if (entry_start > 0 && content > lim) print entry_start ":" content
    }
  ' "$FILE")
  if [[ -z "$violations" ]]; then
    echo "PASS: ${label} (all entries <= ${limit} lines)"
    return 0
  fi
  local rendered
  rendered=$(printf '%s' "$violations" | awk -F: '{printf "line %s (%s lines); ", $1, $2}')
  echo "FAIL: ${label} — entries exceeding ${limit} lines: ${rendered}"
  return 1
}

check_qa_notes_lengths() {
  # Entries are top-level "- " bullets or "#### " headers. Scoped to the
  # QA Notes section body, so [QA-FAIL: ...] bounce annotations living
  # under ## Next Steps are naturally excluded from this count.
  check_entry_lengths "QA Notes" '^- |^#### ' '^- |^#### |^## ' 8 "QA Notes entry"
}

check_completed_lengths() {
  # Entries are "#### A1 ..." item headers or "- **A1** ..." bullets.
  # "### Track ..." group headers close an open entry but are not
  # themselves entries.
  check_entry_lengths "Completed" '^#### |^- \*\*[A-Za-z0-9]' '^#### |^### |^## |^- \*\*[A-Za-z0-9]' 3 "Completed entry"
}

# --- Check 4 — Dev-Complete move-integrity invariant ---
check_move_integrity() {
  local completed_items total_items dev_complete_items
  completed_items=$(get_field "completed_items")
  total_items=$(get_field "total_items")
  dev_complete_items=$(get_field "dev_complete_items")

  if [[ -z "$total_items" || -z "$completed_items" ]]; then
    echo "PASS: move-integrity (completed_items/total_items not present, skipping)"
    return 0
  fi
  if [[ "$completed_items" != "$total_items" ]]; then
    echo "PASS: move-integrity (completed_items=${completed_items} != total_items=${total_items}, invariant not applicable)"
    return 0
  fi

  local sstart send has_content="no"
  read -r sstart send < <(get_section_bounds "Dev Complete")
  # send == sstart means the section is empty (get_section_bounds returns the
  # last body line, so no body lines when send is the header itself). Only
  # inspect the body when there is at least one body line, else the sed range
  # inverts to sstart+1,sstart and BSD sed prints the next section's header.
  if [[ "$sstart" -gt 0 && "$send" -ge "$((sstart + 1))" ]]; then
    local stripped
    stripped=$(sed -n "$((sstart + 1)),${send}p" "$FILE" | tr -d '[:space:]_.*' | tr '[:upper:]' '[:lower:]')
    if [[ -n "$stripped" && "$stripped" != "none" ]]; then
      has_content="yes"
    fi
  fi

  local dci_ok="yes"
  if [[ -n "$dev_complete_items" && "$dev_complete_items" != "0" ]]; then
    dci_ok="no"
  fi

  if [[ "$has_content" == "no" && "$dci_ok" == "yes" ]]; then
    echo "PASS: move-integrity (completed_items == total_items == ${total_items}; Dev Complete empty, dev_complete_items=0)"
    return 0
  fi
  echo "FAIL: move-integrity — completed_items == total_items == ${total_items} but Dev Complete section has entries (${has_content}) and/or dev_complete_items='${dev_complete_items}' != 0"
  return 1
}

# --- Check 5 — timestamps: ISO-8601, not future ---
ISO_RE='^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(Z|[+-][0-9]{2}:[0-9]{2})$'

# to_epoch TIMESTAMP — prints UTC epoch seconds for an ISO-8601 timestamp
# with a Z or +NN:NN/-NN:NN offset. Returns 1 if it cannot be parsed.
# Portable across BSD (macOS) and GNU date: parses the naive wall-clock
# value as if it were UTC, then manually applies the offset in seconds,
# rather than relying on %z support in `date -f`.
to_epoch() {
  local ts="$1"
  if [[ ! "$ts" =~ ^([0-9]{4})-([0-9]{2})-([0-9]{2})T([0-9]{2}):([0-9]{2}):([0-9]{2})(Z|([+-])([0-9]{2}):([0-9]{2}))$ ]]; then
    return 1
  fi
  local y=${BASH_REMATCH[1]} mo=${BASH_REMATCH[2]} d=${BASH_REMATCH[3]}
  local h=${BASH_REMATCH[4]} mi=${BASH_REMATCH[5]} s=${BASH_REMATCH[6]}
  local off=${BASH_REMATCH[7]} sign=${BASH_REMATCH[8]:-} oh=${BASH_REMATCH[9]:-} om=${BASH_REMATCH[10]:-}
  local naive="${y}-${mo}-${d}T${h}:${mi}:${s}"
  local epoch
  if ! epoch=$(date -u -j -f "%Y-%m-%dT%H:%M:%S" "$naive" +%s 2>/dev/null); then
    if ! epoch=$(date -u -d "$naive" +%s 2>/dev/null); then
      return 1
    fi
  fi
  if [[ "$off" != "Z" ]]; then
    local offset_sec=$((10#$oh * 3600 + 10#$om * 60))
    if [[ "$sign" == "-" ]]; then
      epoch=$((epoch + offset_sec))
    else
      epoch=$((epoch - offset_sec))
    fi
  fi
  printf '%s' "$epoch"
}

check_timestamps() {
  local now_epoch fail=0 msgs="" field val
  now_epoch=$(date -u +%s)

  for field in locked_at last_updated; do
    val=$(get_field "$field")
    if [[ -z "$val" || "$val" == "null" ]]; then
      continue
    fi
    if [[ ! "$val" =~ $ISO_RE ]]; then
      fail=1
      msgs="${msgs}${field}='${val}' not ISO-8601 (Z or +NN:NN offset); "
      continue
    fi
    local epoch
    if epoch=$(to_epoch "$val"); then
      if (( epoch > now_epoch )); then
        fail=1
        msgs="${msgs}${field}='${val}' is in the future; "
      fi
    else
      fail=1
      msgs="${msgs}${field}='${val}' failed to parse; "
    fi
  done

  val=$(get_field "lint")
  if [[ -n "$val" && "$val" != "null" ]]; then
    local ts
    ts=$(printf '%s' "$val" | grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(Z|[+-][0-9]{2}:[0-9]{2})' | head -1 || true)
    if [[ -n "$ts" ]]; then
      local epoch
      if epoch=$(to_epoch "$ts"); then
        if (( epoch > now_epoch )); then
          fail=1
          msgs="${msgs}lint timestamp '${ts}' is in the future; "
        fi
      else
        fail=1
        msgs="${msgs}lint timestamp '${ts}' failed to parse; "
      fi
    fi
  fi

  if [[ "$fail" -eq 0 ]]; then
    echo "PASS: timestamps (locked_at/last_updated/lint valid ISO-8601, not future)"
    return 0
  fi
  echo "FAIL: timestamps — ${msgs%; }"
  return 1
}

# --- Check 6 — Context Dump budget ---
check_context_dump() {
  local sstart send
  read -r sstart send < <(get_section_bounds "Context Dump")
  if [[ "$sstart" -eq 0 ]]; then
    echo "PASS: Context Dump (no ## Context Dump section found)"
    return 0
  fi
  local n=$(( send - sstart ))
  if (( n <= 10 )); then
    echo "PASS: Context Dump (${n} lines <= 10)"
    return 0
  fi
  echo "FAIL: Context Dump (${n} lines > 10) — replace (not append), keep only what the successor needs"
  return 1
}

# --- Check 7 — status / total_items state machine ---
check_status_totalitems() {
  local status total_items
  status=$(get_field "status")
  total_items=$(get_field "total_items")

  if [[ "$status" == "planned" ]]; then
    if [[ -z "$total_items" || ! "$total_items" =~ ^[0-9]+$ || "$total_items" -le 0 ]]; then
      echo "FAIL: status/total_items — status=planned requires total_items > 0 (got total_items='${total_items}')"
      return 1
    fi
  fi
  if [[ -n "$total_items" && "$total_items" =~ ^[0-9]+$ && "$total_items" -eq 0 && "$status" != "planning" ]]; then
    echo "FAIL: status/total_items — total_items: 0 is legal only with status: planning (got status='${status}')"
    return 1
  fi
  echo "PASS: status/total_items (status='${status}', total_items='${total_items}')"
  return 0
}

# --- Run all checks ---
OVERALL=0
run_check() {
  if ! "$@"; then
    OVERALL=1
  fi
}

run_check check_line_count
run_check check_qa_notes_lengths
run_check check_completed_lengths
run_check check_move_integrity
run_check check_timestamps
run_check check_context_dump
run_check check_status_totalitems

NOW_TS=$(date -u +%FT%TZ)
if [[ "$OVERALL" -eq 0 ]]; then
  echo "PASS ${TOTAL_LINES} ${NOW_TS}"
else
  echo "FAIL ${TOTAL_LINES} ${NOW_TS}"
fi

exit "$OVERALL"
