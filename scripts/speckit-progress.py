#!/usr/bin/env python3
"""
speckit-progress: Diagnostic visualizer + progress graphs for speckit features.
Run via: uv run --no-project python scripts/speckit-progress.py [path-to-tasks.md]

Outputs:
- Quantified stats (tasks closed, phases, bloat, converge iterations)
- Phase / story completion table
- Mermaid diagrams for progress (phase status, iteration timeline, bottlenecks)
- List of high-ROI things that can be "programmed out" to resolve speckit projects faster
- Recommendations (use before/after each speckit-*, before claiming done)

This automates what was manual greps + mental tracking during 004's long resolution.
Intended to surface bloat/iteration count/claim drift early so remediation loops shrink.
"""

import re
import sys
from pathlib import Path


def parse_tasks(path: Path):
    txt = path.read_text()
    total_x = len(re.findall(r"- \[X\] T\d+", txt))
    total_open = len(re.findall(r"- \[ \] T\d+", txt))
    phases = []
    for m in re.finditer(r"^## Phase (\d+): (.*?)(?=\n## Phase |\Z)", txt, re.M | re.S):
        pnum = int(m.group(1))
        header = m.group(2).split("\n")[0].strip()[:60]
        x = len(re.findall(r"- \[X\] T", m.group(0)))
        o = len(re.findall(r"- \[ \] T", m.group(0)))
        t = x + o
        pct = int(100 * x / t) if t else 0
        phases.append(
            {"num": pnum, "title": header, "x": x, "o": o, "total": t, "pct": pct}
        )
    conv_mentions = len(re.findall(r"converge|Convergence|converged", txt, re.I))
    superseded_refs = len(re.findall(r"superseded by", txt, re.I))
    us_counts = {}
    for us in ["US1", "US2", "US3"]:
        ux = len(re.findall(rf"\[X\].*{us}", txt))
        uo = len(re.findall(rf"\[ \].*{us}", txt))
        us_counts[us] = {"x": ux, "o": uo}
    high_open = re.findall(r"- \[ \] (T0\d+ .*?)(?=\n- \[ |$)", txt, re.M)[
        :5
    ]  # sample current open
    return {
        "total_x": total_x,
        "total_open": total_open,
        "phases": phases,
        "conv_mentions": conv_mentions,
        "superseded_refs": superseded_refs,
        "us": us_counts,
        "sample_open": high_open,
        "raw": txt,
    }


def make_mermaid_phase_bars(data):
    lines = [
        "```mermaid",
        "%%{init: {'theme':'dark', 'themeVariables': {'primaryColor':'#0a0'}} }%%",
        "graph LR",
    ]
    for p in data["phases"]:
        label = f"P{p['num']} {p['title'][:30]}... [{p['x']}/{p['total']} {p['pct']}%]"
        color = (
            ":::done"
            if p["pct"] == 100
            else (":::partial" if p["pct"] > 0 else ":::open")
        )
        lines.append(f"    P{p['num']}[{label}] {color}")
    lines.append("    classDef done fill:#0a3,stroke:#0f0,color:#fff")
    lines.append("    classDef partial fill:#530,stroke:#f80,color:#fff")
    lines.append("    classDef open fill:#300,stroke:#f00,color:#fff")
    lines.append("```")
    return "\n".join(lines)


def make_mermaid_timeline(data):
    # Static summary of what the 004 history showed (derived from 27 conv mentions + 14 phases)
    return """```mermaid
gantt
    title Speckit 004 Resolution Drag (14 phases, 27 converge mentions, 2 adversarial reviews)
    dateFormat  YYYY-MM-DD
    section Core Feature Work (US1+US2+US3)
    Spec + Plan + Initial Tasks           :done, 2026-06-21, 1d
    Impl + early US1/US2/US3              :done, 2026-06-21, 1d
    section Heavy Iteration (main source of "why so long")
    Phase 7-9 Convergence remediation     :crit, 2026-06-21, 1d
    Adversarial review + clarify          :crit, 2026-06-22, 1d
    Phase 10/11 "done" claims             :done, 2026-06-22, 1d
    005 docs sidecar + broad Phase12 review (caught partials) :crit, 2026-06-22, 1d
    Phase 13/14 final impl + converge     :active, 2026-06-22, 1d
    section Overhead Multiplier (per change)
    Gate (verify-quality + pre-commit)    : 2026-06-21, 2026-06-22
    Doctor GCD (always full 16 + pytest)  : 2026-06-22, 1d
    Manual smoke / real-world test        :crit, 2026-06-22, 1d
```"""


def make_mermaid_bottleneck():
    return """```mermaid
flowchart TD
    A[Optimistic Phase X impl + "all done" handoff] --> B[Adversarial / converge catches stub/grep/limited-doctor]
    B --> C[Remediation pass: code + update 4 md files + re-audit + re-gate]
    C --> D[More converge/analyze because history bloat + stale claims linger]
    D --> A
    E[No hermetic E2E / smoke requires real Comfy checkout + tokens] --> B
    F[Manual speckit steps: 10 skills invoked separately, no orchestrator] --> D
    G[Gate cost 30s-5min + doctor always pays full GCD] --> C
    class A,B,C,D,E,F,G crit
```"""


def print_report(data, tasks_path: Path):
    print("=" * 70)
    print("SPECKIT PROGRESS REPORT (automated root-cause + graphs for slow resolution)")
    print(f"Source: {tasks_path}")
    print("=" * 70)
    print(
        f"Tasks: {data['total_x'] + data['total_open']} total  |  [X]: {data['total_x']}  |  [ ]: {data['total_open']}"
    )
    print(f"Convergence/iteration mentions: {data['conv_mentions']}")
    print(f"Superseded/historical refs (bloat): {data['superseded_refs']}")
    print(f"Phases: {len(data['phases'])} (see table + graphs below)")
    print()
    print("Per US (from task labels):")
    for us, c in data["us"].items():
        tot = c["x"] + c["o"]
        print(f"  {us}: {c['x']}/{tot} [X]  ({int(100 * c['x'] / tot) if tot else 0}%)")
    print()
    print("--- PHASE TABLE (approx completion from [X]/[ ] counts) ---")
    print("P# | Title (truncated)                          | done/open | %")
    for p in data["phases"]:
        print(
            f"{p['num']:>2} | {p['title']:<42} | {p['x']:>2}/{p['total']:<2}     | {p['pct']:>3}%"
        )
    print()
    print(
        "--- SAMPLE OPEN (historical or low-prio in current file; many are archival) ---"
    )
    for s in data["sample_open"]:
        print(f"  - {s[:80]}...")
    print()
    print("--- MERMAID: PHASE STATUS (color: green=100%, orange=partial, red=open) ---")
    print(make_mermaid_phase_bars(data))
    print()
    print("--- MERMAID: ITERATION / TIMELINE (what caused the 'long' feel) ---")
    print(make_mermaid_timeline(data))
    print()
    print(
        "--- MERMAID: BOTTLENECK LOOP (the anti-pattern that lengthens resolution) ---"
    )
    print(make_mermaid_bottleneck())
    print()
    print(
        "=== THINGS THAT CAN BE PROGRAMMED OUT (to make speckit projects resolve faster) ==="
    )
    print(
        "1. Manual converge/analyze/clarify/adversarial loops: add `speckit-finish` orchestrator skill/script that chains the required ones, auto-runs text-audit + claim-reality check, updates tasks handoff, stops on new gaps."
    )
    print(
        "2. Stale 'implemented' claims + optimistic handoffs: add validator (grep Txxx + 'implemented'/'integrated'/'structured' in code+plan+tasks, diff against [X] status + test results). Would have flagged Phase 10/11 before review."
    )
    print(
        "3. Historical bloat (26 open + 33 superseded refs + Phase 8/9 full lists): make converge always collapse superseded into a single 'see appendix' or prune after 2 passes; T076 was low-prio so lingered."
    )
    print(
        "4. Progress tracking / graphs: this script (or integrated in converge). Run after every tasks update or impl to see % , bottlenecks, iteration count at a glance. Auto-emit to a PROGRESS.md or append to tasks."
    )
    print(
        "5. Non-hermetic verification (smoke skips without real Comfy+cli+direnv+tokens; manual SSH sim): bootstrap hermetic harness that `git clone --depth 1` pinned comfyui/comfy-cli into /tmp, mocks tokens, runs `comfygo` under fake envrc, asserts exact contract messages, descriptors, no-disrupt tmux logic, GCD PASS. Make `comfygo doctor --smoke-repatch` call it."
    )
    print(
        "6. Doctor perf (always spawns full verify + 16 GCD + registry pytest even for quick protection/paths check): default to --fast internally for summary; --full-gcd or explicit to force full 16 + evidence. Add timing to doctor output."
    )
    print(
        "7. Gate cost on every micro change (ruff+bandit+pytest+pre-commit+verify on scripts/): cache uvx, make verify --quick for doc-only or known-safe, or integrate lightweight claim checker that doesn't need full pytest."
    )
    print(
        "8. 10+ separate speckit skill invocations + manual AGENTS.md + .specify/feature.json sync: single meta entrypoint `comfygo speckit ...` (or dedicated) that knows the DAG (specify->plan->tasks->impl->analyze->converge->review->gate) and required artifacts."
    )
    print(
        "9. Real-world test left as 'recommend after commit': make smoke + enrich + launch + doctor --full-gcd part of the 'done' contract that can run in CI with setup scripts (comfy-install-with-local-nodes in temp dir)."
    )
    print()
    print("=== HOW TO USE THIS TO GO FASTER ===")
    print(
        f"  uv run --no-project python {tasks_path.parent.parent / 'scripts' / 'speckit-progress.py'} specs/NNN-foo/tasks.md"
    )
    print(
        "  Re-run after any speckit-*, after code changes that affect Txxx, before claiming 'Phase N complete' or pushing."
    )
    print(
        "  If open count or conv_mentions high or sample_open shows active HIGH tasks: do not declare victory; run converge + validator first."
    )
    print()
    print("Current health for this tasks.md:")
    if data["superseded_refs"] > 20 or data["conv_mentions"] > 15:
        print(
            "  ⚠️  HIGH iteration/bloat detected — run the cleaner (T076 intent) + this script in loop until numbers drop."
        )
    else:
        print("  OK range for complex feature.")
    print()
    print(
        "Root cause hypothesis confirmed by numbers + code: process ceremony + missing automation for tracking/claims/verification + external dep on real runtime for acceptance = many days of cycles for what is fundamentally settings + ~150 lines of bash glue + one py helper integration."
    )
    print("=" * 70)


if __name__ == "__main__":
    p = (
        Path(sys.argv[1])
        if len(sys.argv) > 1
        else Path("specs/004-comfygo-patched-tmux/tasks.md")
    )
    if not p.exists():
        print(
            "Usage: uv run --no-project python scripts/speckit-progress.py [tasks.md]"
        )
        sys.exit(2)
    data = parse_tasks(p)
    print_report(data, p)
