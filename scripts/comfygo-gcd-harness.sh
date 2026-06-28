#!/usr/bin/env bash
# Run the 16 GCD scenarios from specs/002-model-gc/doctor-matrix.md in an isolated temp root.
#
# Usage:
#   scripts/comfygo-gcd-harness.sh
#   COMFYGO_GCD_EVIDENCE_DIR=/tmp/evidence scripts/comfygo-gcd-harness.sh
#
# Exit codes:
#   0 — all 16 scenarios passed (prints "PASS: all 16 GCD scenarios passed")
#   1 — one or more scenarios failed

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WRAPPER="$SCRIPT_DIR/comfygo-models.sh"
EVIDENCE_DIR="${COMFYGO_GCD_EVIDENCE_DIR:-${TMPDIR:-/tmp}/comfygo-gcd-harness.$$}"

gc_ok=true
MODELS_DIR=""
RUN_RC=0
RUN_OUT=""
gc_today="$(date +%F)"
gc_log="$EVIDENCE_DIR/gc-doctor.log"

mkdir -p "$EVIDENCE_DIR"

write_gc_result() {
  local gcd_id="$1"
  local result="$2"
  local detail="$3"
  echo "  $result: $gcd_id — $detail" | tee -a "$gc_log"
  if [[ "$result" != "PASS" ]]; then
    gc_ok=false
  fi
}

cleanup_models_dir() {
  if [[ -n "${MODELS_DIR:-}" && -d "$MODELS_DIR" ]]; then
    rm -rf "$MODELS_DIR"
  fi
}

reset_models_dir() {
  rm -rf "$MODELS_DIR"
  mkdir -p "$MODELS_DIR"
}

run_gcd_cmd() {
  local gcd_id="$1"
  shift
  RUN_OUT="$EVIDENCE_DIR/${gcd_id}.out"
  "$@" >"$RUN_OUT" 2>&1
  RUN_RC=$?
}

output_has() {
  grep -Fq -- "$1" "$RUN_OUT"
}

output_lacks() {
  ! grep -Fq -- "$1" "$RUN_OUT"
}

output_exact() {
  local expected="$1"
  local expected_file="$EVIDENCE_DIR/expected-output.txt"
  printf '%s\n' "$expected" >"$expected_file"
  cmp -s "$RUN_OUT" "$expected_file"
}

output_summary() {
  tr '\n' '|' <"$RUN_OUT" | sed 's/|$//'
}

trash_absent() {
  [[ ! -e "$MODELS_DIR/.comfygo_trash" ]]
}

if [[ ! -x "$WRAPPER" ]]; then
  echo "FAIL: scripts/comfygo-models.sh not found or not executable" >&2
  exit 1
fi

MODELS_DIR="$(mktemp -d /tmp/comfygo-gc-doctor.XXXXXX)"
trap cleanup_models_dir EXIT
trap 'cleanup_models_dir; exit 1' INT TERM

# GCD-001: Empty root
reset_models_dir
run_gcd_cmd "GCD-001" "$WRAPPER" --models-dir "$MODELS_DIR" gc
if [[ "$RUN_RC" -eq 0 ]] && output_exact "Nothing to report." && trash_absent; then
  write_gc_result "GCD-001" "PASS" "empty root -> exit 0, exact empty report, no trash"
else
  write_gc_result "GCD-001" "FAIL" "exit=$RUN_RC output=$(output_summary)"
fi

# GCD-002: Managed downloader
mkdir -p "$MODELS_DIR/ManagedDownloader"
printf '{"schema":"comfygo.download.v1","repo":"example/m"}\n' \
  >"$MODELS_DIR/ManagedDownloader/.comfygo-download.json"
run_gcd_cmd "GCD-002" "$WRAPPER" --models-dir "$MODELS_DIR" gc
if [[ "$RUN_RC" -eq 0 ]] && output_has "marker: downloader" && trash_absent; then
  write_gc_result "GCD-002" "PASS" "managed downloader detected, no trash"
else
  write_gc_result "GCD-002" "FAIL" "exit=$RUN_RC output=$(output_summary)"
fi

# GCD-003: Managed descriptor
mkdir -p "$MODELS_DIR/ManagedDescriptor"
printf '{"schema":"comfygo.model.v1","name":"x","kind":"diffusers"}\n' \
  >"$MODELS_DIR/ManagedDescriptor/comfygo-model.json"
run_gcd_cmd "GCD-003" "$WRAPPER" --models-dir "$MODELS_DIR" gc
if [[ "$RUN_RC" -eq 0 ]] && output_has "marker: descriptor" && trash_absent; then
  write_gc_result "GCD-003" "PASS" "managed descriptor detected, no trash"
else
  write_gc_result "GCD-003" "FAIL" "exit=$RUN_RC output=$(output_summary)"
fi

# GCD-004: Ambiguous folder
mkdir -p "$MODELS_DIR/AmbiguousOnly"
run_gcd_cmd "GCD-004" "$WRAPPER" --models-dir "$MODELS_DIR" gc
if [[ "$RUN_RC" -eq 0 ]] && output_has "Ambiguous" && [[ -d "$MODELS_DIR/AmbiguousOnly" ]]; then
  write_gc_result "GCD-004" "PASS" "ambiguous folder listed, source unchanged"
else
  write_gc_result "GCD-004" "FAIL" "exit=$RUN_RC output=$(output_summary)"
fi

# GCD-005: Reserved and hidden folders only
reset_models_dir
mkdir -p "$MODELS_DIR/diffusion_models" "$MODELS_DIR/.hidden_folder"
run_gcd_cmd "GCD-005" "$WRAPPER" --models-dir "$MODELS_DIR" gc
if [[ "$RUN_RC" -eq 0 ]] && output_exact "Nothing to report." && trash_absent; then
  write_gc_result "GCD-005" "PASS" "reserved/hidden skipped, exact empty report, no trash"
else
  write_gc_result "GCD-005" "FAIL" "exit=$RUN_RC output=$(output_summary)"
fi

# GCD-006: Source symlink dry-run
reset_models_dir
mkdir -p "$MODELS_DIR/real"
ln -s real "$MODELS_DIR/LinkedModel"
run_gcd_cmd "GCD-006" "$WRAPPER" --models-dir "$MODELS_DIR" gc
if [[ "$RUN_RC" -eq 0 ]] && output_has "symlink" && [[ -L "$MODELS_DIR/LinkedModel" ]] && trash_absent; then
  write_gc_result "GCD-006" "PASS" "source symlink warning, symlink unchanged, no trash"
else
  write_gc_result "GCD-006" "FAIL" "exit=$RUN_RC output=$(output_summary)"
fi

# GCD-007: Source symlink with -f
run_gcd_cmd "GCD-007" "$WRAPPER" --models-dir "$MODELS_DIR" gc -f LinkedModel
if [[ "$RUN_RC" -eq 1 ]] && output_has "symlink" && [[ -L "$MODELS_DIR/LinkedModel" ]] && trash_absent; then
  write_gc_result "GCD-007" "PASS" "symlink -f filtered -> exit 1, no trash"
else
  write_gc_result "GCD-007" "FAIL" "exit=$RUN_RC output=$(output_summary)"
fi

# GCD-008: Source symlink with -f --apply
run_gcd_cmd "GCD-008" "$WRAPPER" --models-dir "$MODELS_DIR" gc -f LinkedModel --apply
if [[ "$RUN_RC" -eq 1 ]] && output_has "symlink" && [[ -L "$MODELS_DIR/LinkedModel" ]] && trash_absent; then
  write_gc_result "GCD-008" "PASS" "symlink --apply rejected, no trash"
else
  write_gc_result "GCD-008" "FAIL" "exit=$RUN_RC output=$(output_summary)"
fi

# GCD-009: --apply without -f
reset_models_dir
mkdir -p "$MODELS_DIR/ManagedDownloader"
printf '{}' >"$MODELS_DIR/ManagedDownloader/.comfygo-download.json"
run_gcd_cmd "GCD-009" "$WRAPPER" --models-dir "$MODELS_DIR" gc --apply
if [[ "$RUN_RC" -eq 1 ]] && output_has "requires -f NAME" && [[ -d "$MODELS_DIR/ManagedDownloader" ]] && trash_absent; then
  write_gc_result "GCD-009" "PASS" "--apply without -f rejected, no trash"
else
  write_gc_result "GCD-009" "FAIL" "exit=$RUN_RC output=$(output_summary)"
fi

# GCD-010: Missing target
run_gcd_cmd "GCD-010" "$WRAPPER" --models-dir "$MODELS_DIR" gc -f Missing --apply
if [[ "$RUN_RC" -eq 1 ]] && output_has "No managed folder" && [[ -d "$MODELS_DIR/ManagedDownloader" ]] && trash_absent; then
  write_gc_result "GCD-010" "PASS" "missing target rejected, no trash"
else
  write_gc_result "GCD-010" "FAIL" "exit=$RUN_RC output=$(output_summary)"
fi

# GCD-011: Ambiguous-only --apply
mkdir -p "$MODELS_DIR/AmbiguousOnly"
run_gcd_cmd "GCD-011" "$WRAPPER" --models-dir "$MODELS_DIR" gc -f AmbiguousOnly --apply
if [[ "$RUN_RC" -eq 1 ]] && output_has "not managed" && [[ -d "$MODELS_DIR/AmbiguousOnly" ]] && trash_absent; then
  write_gc_result "GCD-011" "PASS" "ambiguous --apply rejected, no trash"
else
  write_gc_result "GCD-011" "FAIL" "exit=$RUN_RC output=$(output_summary)"
fi

# GCD-012: Multi-match --apply
reset_models_dir
mkdir -p "$MODELS_DIR/ModelOne" "$MODELS_DIR/ModelTwo"
printf '{}' >"$MODELS_DIR/ModelOne/.comfygo-download.json"
printf '{}' >"$MODELS_DIR/ModelTwo/.comfygo-download.json"
run_gcd_cmd "GCD-012" "$WRAPPER" --models-dir "$MODELS_DIR" gc -f Model --apply
if [[ "$RUN_RC" -eq 1 ]] && output_has "multiple" && [[ -d "$MODELS_DIR/ModelOne" ]] && [[ -d "$MODELS_DIR/ModelTwo" ]] && trash_absent; then
  write_gc_result "GCD-012" "PASS" "multi-match rejected, both sources unchanged, no trash"
else
  write_gc_result "GCD-012" "FAIL" "exit=$RUN_RC output=$(output_summary)"
fi

# GCD-013: Unsafe path segment
reset_models_dir
mkdir -p "$MODELS_DIR/~UnsafeModel"
printf '{}' >"$MODELS_DIR/~UnsafeModel/.comfygo-download.json"
run_gcd_cmd "GCD-013" "$WRAPPER" --models-dir "$MODELS_DIR" gc -f '~UnsafeModel' --apply
if [[ "$RUN_RC" -eq 1 ]] && output_has "Unsafe path segment" && output_lacks "Traceback" && [[ -d "$MODELS_DIR/~UnsafeModel" ]] && trash_absent; then
  write_gc_result "GCD-013" "PASS" "unsafe path rejected without traceback or trash"
else
  write_gc_result "GCD-013" "FAIL" "exit=$RUN_RC output=$(output_summary)"
fi

# GCD-014: Successful quarantine
reset_models_dir
mkdir -p "$MODELS_DIR/ManagedDownloader"
printf '{}' >"$MODELS_DIR/ManagedDownloader/.comfygo-download.json"
run_gcd_cmd "GCD-014" "$WRAPPER" --models-dir "$MODELS_DIR" gc -f ManagedDownloader --apply
trash_date_dir="$MODELS_DIR/.comfygo_trash/$gc_today"
trash_dest="$trash_date_dir/ManagedDownloader"
trash_count=0
if [[ -d "$trash_date_dir" ]]; then
  trash_count=$(find "$trash_date_dir" -mindepth 1 -maxdepth 1 -type d | wc -l | tr -d ' ')
fi
if [[ "$RUN_RC" -eq 0 ]] && output_has "Quarantined" && [[ ! -e "$MODELS_DIR/ManagedDownloader" ]] && [[ -d "$trash_dest" ]] && [[ "$trash_count" -eq 1 ]]; then
  write_gc_result "GCD-014" "PASS" "quarantine succeeded at .comfygo_trash/$gc_today/ManagedDownloader"
else
  write_gc_result "GCD-014" "FAIL" "exit=$RUN_RC output=$(output_summary)"
fi
trash_snapshot_before="$EVIDENCE_DIR/GCD-015-trash-before.txt"
if [[ -d "$MODELS_DIR/.comfygo_trash" ]]; then
  find "$MODELS_DIR/.comfygo_trash" -mindepth 1 -maxdepth 4 -print | sort >"$trash_snapshot_before"
else
  : >"$trash_snapshot_before"
fi

# GCD-015: Idempotency
run_gcd_cmd "GCD-015" "$WRAPPER" --models-dir "$MODELS_DIR" gc -f ManagedDownloader --apply
trash_snapshot_after="$EVIDENCE_DIR/GCD-015-trash-after.txt"
if [[ -d "$MODELS_DIR/.comfygo_trash" ]]; then
  find "$MODELS_DIR/.comfygo_trash" -mindepth 1 -maxdepth 4 -print | sort >"$trash_snapshot_after"
else
  : >"$trash_snapshot_after"
fi
if [[ "$RUN_RC" -eq 1 ]] && output_has "No managed folder" && cmp -s "$trash_snapshot_before" "$trash_snapshot_after"; then
  write_gc_result "GCD-015" "PASS" "idempotent re-apply rejected, trash unchanged"
else
  write_gc_result "GCD-015" "FAIL" "exit=$RUN_RC output=$(output_summary)"
fi

# GCD-016: Flag ordering
reset_models_dir
mkdir -p "$MODELS_DIR/ManagedDownloader"
printf '{}' >"$MODELS_DIR/ManagedDownloader/.comfygo-download.json"
run_gcd_cmd "GCD-016" "$WRAPPER" gc --models-dir "$MODELS_DIR"
if [[ "$RUN_RC" -eq 0 ]] && output_has "ManagedDownloader" && trash_absent; then
  write_gc_result "GCD-016" "PASS" "flag ordering works, no trash"
else
  write_gc_result "GCD-016" "FAIL" "exit=$RUN_RC output=$(output_summary)"
fi

if "$gc_ok"; then
  echo "PASS: all 16 GCD scenarios passed"
  exit 0
fi

echo "--- GC doctor summary ---" >&2
cat "$gc_log" >&2
exit 1
