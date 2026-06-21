# Evaluation: How to Implement the 16 GCD Scenarios

## Executive Summary

**Recommendation: Implement as a standalone shell script `scripts/comfygo-gc-doctor`.**

Do NOT integrate into `comfygo doctor`, do NOT keep purely as documentation. The 16 GCD scenarios (GCD-001 through GCD-016) are shell-level integration tests — they should be automated, repeatable, and CI-friendly. A standalone script following the structural patterns of `comfygo-live-validate` is the right fit.

---

## 1. The Spec's Explicit Boundary (GC ≠ doctor)

The spec says unequivocally:

> *"GC MUST NOT run during `comfygo doctor`"* (spec.md, line 399)
> *"Default `comfygo doctor` should continue checking registry/reconcile health."* (doctor-matrix.md, line 112)

Integrating these 16 scenarios into `comfygo doctor` would **violate the spec**. The doctor command checks *runtime health of the live environment*. GC is intentionally separate — it's a maintenance command (like `reconcile`), not a health check.

However, the doctor-matrix also says:

> *"A GC doctor check may be added as a separate doctor section or explicit development check."* (line 113)

This is an allowance, not a mandate. The phrase "explicit development check" points to a separate harness — exactly a standalone script.

**Verdict**: A standalone script respects the boundary. Integration into `comfygo doctor` does not.

---

## 2. Temp-Root vs Live-Root Separation

The 16 scenarios split cleanly:

| Scenario IDs | Root Type | Mutations? | Drives |
|---|---|---|---|
| GCD-001 to GCD-008 | Temp-root | Dry-run only (no mutation) | Tests CLI output formatting, filtering, symlink warnings |
| GCD-009 to GCD-013 | Temp-root | Apply **required** (tests error gates) | Validates that every error path exits 1 with correct message |
| GCD-014 to GCD-015 | Temp-root | Apply **required** (mutates) | Quarantine + idempotency |
| GCD-016 | Temp-root | Dry-run only | Flag ordering |

**Live-root scenarios are explicitly not included.** The doctor-matrix says the live smoke is *optional* and *read-only only* (line 91-108). Every scenario in the matrix runs against a `mktemp -d /tmp/comfygo-gc-doctor.XXXXXX` temporary root.

This makes a standalone script the natural home — it creates its own temp root, runs all 16 scenarios, and destroys it. There's no dependency on a real ComfyUI model root.

**Verdict**: The temp-root-only nature of the matrix strongly favors a self-contained standalone script. Making `comfygo doctor` create a temp root just to run GC scenarios would be architecturally wrong — doctor checks the live runtime, not disposable temp directories.

---

## 3. Structural Sharing with `comfygo-live-validate`

`comfygo-live-validate` (171 lines) follows a proven pattern:

```bash
# 1. Create evidence directory
run_dir="$(mktemp -d /tmp/comfygo-live.XXXXXX)"

# 2. Fail accumulator
failed=0
record_fail() { ... }

# 3. Phases (each is a block that runs a command, checks output, 
#    logs to evidence dir, calls record_fail on mismatch)

# 4. Final result
if [ "$failed" -eq 0 ]; then echo "PASS: ..."; exit 0
else echo "FAIL: ..."; exit 1; fi
```

A GC doctor script can directly replicate this:

1. **Evidence directory**: `mktemp -d /tmp/comfygo-gc-doctor.XXXXXX`
2. **Fixture setup phase**: Create all fixture folders under `$MODELS_DIR` before any tests
3. **Scenario execution phase**: For each ID, run the command, capture exit code + stdout + stderr, check expected output fragment + expected exit code + mutation assertion
4. **Cleanup phase**: `rm -rf "$MODELS_DIR"` (or keep for inspection on failure)

The shared elements are:
- Evidence directory lifecycle
- `record_fail`/fail accumulator pattern
- Per-step logging to evidence dir
- Exit 0/1 convention

The GC-specific differences are:
- Pre-builds a richer fixture tree (marker folders, symlinks, reserved dirs, unsafe names)
- Runs 16 scenarios instead of ~5 phases
- Has more granular assertions per scenario (exit code + output text + filesystem state)
- Runs on a throwaway temp root, not a live environment

**Verdict**: The script can share the structural skeleton of `comfygo-live-validate` but is a *separate script* because the setup, assertions, and lifecycle are fundamentally different.

---

## 4. Exit Code Convention

| Exit Code | Meaning |
|---|---|
| 0 | All 16 scenarios passed their assertions |
| 1 | One or more scenarios failed (details in evidence directory) |

This matches `comfygo-live-validate`'s convention exactly. It is also the natural convention for CI pipeline use.

**Important**: A scenario that *expects* the GC command to exit 1 (e.g., GCD-009 expects `exit 1` for `--apply` without `-f`) is a **passing scenario** in the doctor harness. The harness checks that the command produces exit 1 — that's correct behavior. The harness exit code reflects whether all **harness assertions** pass, not whether individual GC commands pass.

---

## 5. Which Scenarios Should Pass vs Fail

**All 16 scenarios are passing scenarios in the doctor harness.** Each scenario asserts that the GC command produces the *expected* behavior (exit code + output + filesystem state). The harness "fails" only when actual behavior deviates from expected.

| ID | Expected CLI Exit | Harness Assertion | Harness Verdict |
|---|---|---|---|
| **GCD-001** | 0 | stdout == "Nothing to report."; no `.comfygo_trash/` | PASS |
| **GCD-002** | 0 | stdout has "Managed folders:" + "marker: downloader"; no trash | PASS |
| **GCD-003** | 0 | stdout has "Managed folders:" + "marker: descriptor"; no trash | PASS |
| **GCD-004** | 0 | stdout has "Ambiguous:" + "no marker file found"; source unchanged | PASS |
| **GCD-005** | 0 | stdout == "Nothing to report."; skipped folders unchanged | PASS |
| **GCD-006** | 0 | stdout has symlink refusal warning; symlink unchanged, no trash | PASS |
| **GCD-007** | 1 | stdout has symlink refusal warning; symlink unchanged, no trash | PASS |
| **GCD-008** | 1 | stdout has symlink refusal warning; symlink unchanged, no trash | PASS |
| **GCD-009** | 1 | stdout has "error: --apply requires -f NAME"; source unchanged, no trash | PASS |
| **GCD-010** | 1 | stdout has "error: No managed folder matching 'Missing'"; no trash | PASS |
| **GCD-011** | 1 | stdout has "error: Folder 'AmbiguousOnly' is not managed"; no trash | PASS |
| **GCD-012** | 1 | stdout has "matched multiple managed folders" + both paths; no trash | PASS |
| **GCD-013** | 1 | stdout has "Unsafe path segment" and no "Traceback"; source unchanged | PASS |
| **GCD-014** | 0 | stdout has "Quarantined:"; source gone; trash dir created | PASS |
| **GCD-015** | 1 | stdout has "No managed folder matching 'ManagedDownloader'"; trash unchanged | PASS |
| **GCD-016** | 0 | Same as GCD-002; flag after subcommand still works | PASS |

Harness exit 0 when all 16 PASS. Harness exit 1 if any test deviates.

---

## 6. Architecture: Proposed Script Shape

```
scripts/comfygo-gc-doctor
```

```bash
#!/usr/bin/env bash
# comfygo-gc-doctor — automated GC scenario harness (GCD-001..GCD-016).
# All scenarios run against a throwaway temp model root. Apply scenarios
# use the temp root — never the live model root.
# Exit: 0 (all passed), 1 (any assertion failed)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
WRAPPER="$REPO_DIR/scripts/comfygo-models.sh"

# Evidence directory
run_dir="$(mktemp -d /tmp/comfygo-gc-doctor.XXXXXX)"
echo "Evidence: $run_dir"

# Fail accumulator
failed=0
record_fail() { echo "  FAIL: $1"; failed=1; }

# Phase 1: Build fixture tree under $MODELS_DIR (all 16 fixtures)
MODELS_DIR="$(mktemp -d /tmp/comfygo-gc-doctor.XXXXXX)"
# ... create ManagedDownloader, ManagedDescriptor, AmbiguousOnly,
#     ModelOne, ModelTwo, LinkedModel, ~UnsafeModel, reserved dirs, etc.

# Phase 2: Run each scenario (GCD-001..GCD-016)
# Each scenario: run command, log to evidence, assert exit+output+fs state
# e.g.:
echo "=== GCD-001: Empty root dry-run ==="
out=$(comand...); rc=$?
echo "$out" > "$run_dir/gcd-001.log"
if [ "$rc" -ne 0 ]; then record_fail "GCD-001: expected exit 0, got $rc"; fi
if [ "$out" != "Nothing to report." ]; then record_fail "GCD-001: unexpected output"; fi
if [ -d "$MODELS_DIR/.comfygo_trash" ]; then record_fail "GCD-001: trash created"; fi
# ... (remaining 15 scenarios) ...

# Phase 3: Cleanup
rm -rf "$MODELS_DIR"

# Result
if [ "$failed" -eq 0 ]; then
    echo "PASS: all 16 GC scenarios passed"
    echo "Evidence: $run_dir"; exit 0
else
    echo "FAIL: one or more GC scenarios failed (see evidence)"
    echo "Evidence: $run_dir"; exit 1
fi
```

### Scenario execution order dependency

GCD-015 (idempotency) depends on GCD-014 (quarantine) having already run. The script MUST run GCD-014 before GCD-015. All other scenarios are independent and could theoretically run in any order.

**Proposed order**: GCD-001 through GCD-016 sequentially, because:
- GCD-001..GCD-008: dry-run only, no side effects
- GCD-009..GCD-013: error gates, no mutation on failure
- GCD-014: successful quarantine (creates trash)
- GCD-015: depends on GCD-014's trash
- GCD-016: independent dry-run, run last as a final sanity check

### What the existing Python tests (test_gc.py) already cover

The existing `test_gc.py` already covers the *Python-level* assertions for the same behaviors. The shell script covers *integration-level* assertions — does the user-facing CLI wrapper (`comfygo-models.sh`) produce the correct exit code and output when invoked from a real shell? These are orthogonal concerns:

- Python tests: fast, unit-level, mock-capable
- Shell doctor script: slower, end-to-end, validates the full CLI command pipeline

Both are valuable. The doctor script is the CI gate that catches issues like wrapper forwarding bugs, environment variable leakage, or script path resolution errors that Python tests can't catch.

---

## 7. Record of What Was Evaluated

| File | Role |
|---|---|
| `specs/002-model-gc/doctor-matrix.md` | Canonical 16-scenario matrix |
| `specs/002-model-gc/spec.md` | Spec: GC boundary, FR-001 through FR-015 |
| `specs/002-model-gc/contracts/README.md` | Exact exit codes and error messages |
| `specs/002-model-gc/quickstart.md` | Validation scenarios 1-8 (maps to GCD-001..GCD-016 subset) |
| `scripts/comfygo-live-validate` | Structural template for bash doctor script |
| `scripts/comfygo-models.sh` | CLI wrapper that the scenarios invoke |
| `custom_nodes/comfygo_model_registry/tests/test_gc.py` | Existing Python-level GC tests |
| `custom_nodes/comfygo_model_registry/tests/test_cli.py` | CLI dispatch tests |
| `custom_nodes/comfygo_model_registry/tests/test_wrapper.py` | Wrapper integration tests |
