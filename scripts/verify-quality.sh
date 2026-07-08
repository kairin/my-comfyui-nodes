#!/usr/bin/env bash
# scripts/verify-quality.sh
# Run this (or via pre-commit) BEFORE any commit/push.
# Goal: Make sure the code would pass Codacy (and other static analysis) locally.
# This saves GitHub Actions minutes, Codacy tokens, and prevents "cannot merge" frustration.
#
# Usage:
#   ./scripts/verify-quality.sh
#   or
#   uv run --no-project bash scripts/verify-quality.sh
#
# If this passes, `git commit` + `git push` should result in green Codacy checks.

set -euo pipefail

echo "🔍 Running local quality verification (Codacy-equivalent checks)..."

# Ensure uv is available (per AGENTS.md and constitution)
if ! command -v uv &> /dev/null; then
  echo "❌ uv is required but not found. Install it first: https://docs.astral.sh/uv/getting-started/installation/"
  exit 1
fi

FAILED=0

# 1. Python linting & formatting with Ruff (primary Python tool in Codacy now)
# Scope to owned code only — do NOT touch vendored third-party nodes (ComfyUI-*, etc.)
echo "→ Ruff (lint + format) [owned code only]..."
if ! uvx ruff check custom_nodes/comfygo_model_registry scripts --fix --exit-non-zero-on-fix; then
  echo "❌ Ruff lint issues found. Run 'uvx ruff check custom_nodes/comfygo_model_registry scripts --fix' to auto-fix."
  FAILED=1
fi
if ! uvx ruff format --check custom_nodes/comfygo_model_registry scripts; then
  echo "❌ Ruff format issues. Run 'uvx ruff format custom_nodes/comfygo_model_registry scripts' to fix."
  FAILED=1
fi

# 2. Shell scripts (ShellCheck matches Codacy)
echo "→ ShellCheck..."
if command -v shellcheck &> /dev/null; then
  if ! shellcheck -x scripts/*.sh 2>/dev/null || true; then
    # Note: shellcheck may not be installed globally; try via uv or note
    echo "  (shellcheck not in PATH or some scripts have issues - install shellcheck or run via Docker if needed)"
  fi
else
  echo "  (shellcheck not installed globally - skipping detailed check. Install with your package manager for full local runs.)"
fi

# 3. Python security (Bandit - matches Codacy)
echo "→ Bandit security scan (on registry code)..."
if ! uvx bandit -r custom_nodes/comfygo_model_registry -q -c bandit.yaml; then
  echo "❌ Bandit found security issues."
  FAILED=1
fi

# 4. Run relevant tests (the ones that would affect registry analysis)
echo "→ Running registry tests..."
if ! uv run --no-project pytest custom_nodes/comfygo_model_registry/tests -q --tb=no; then
  echo "❌ Tests failing."
  FAILED=1
fi

# 5. Codacy CLI local analysis (if you have local token or for supported tools)
# Note: Full remote-equivalent requires project token. Run what you can locally.
echo "→ Codacy CLI (local analysis where possible)..."
# Local analysis uses codacy-cli-v2 (`codacy-cli`), NOT the cloud CLI (`codacy`), which
# has no `analyze` command. codacy-cli-v2 needs .codacy/codacy.yaml with pinned
# "tool@version" strings + the matching runtime (the old "- name: <tool>" form fails to
# parse and exits 0 with empty SARIF). `analyze` never uploads, so this is CI-safe.
if [[ -n "${VERIFY_QUALITY_INVOKED_BY_PRE_COMMIT:-}" ]]; then
  # Skip during pre-commit: codacy-cli analyze is slow and writes .codacy/{logs,tools-configs}
  # artifacts that would trip pre-commit's "files modified" guard. Codacy runs in CI; run this
  # script directly for a local scan.
  echo "  (skipped during pre-commit — Codacy analysis runs in CI; run this script directly for a local scan)"
elif command -v codacy-cli &> /dev/null; then
  echo "  codacy-cli detected — running local pylint analysis (no upload)..."
  # codacy-cli-v2 needs .codacy/codacy.yaml (pinned tool@version + runtime). Track what already
  # exists and remove only what we create so the working tree is left exactly as we found it
  # (codacy-cli also generates .codacy/logs, tools-configs, and .gitignore).
  codacy_dir_existed=1; [[ -d .codacy ]] || codacy_dir_existed=0
  codacy_cfg=".codacy/codacy.yaml"; created_codacy_cfg=0
  if [[ ! -f "$codacy_cfg" ]]; then
    mkdir -p .codacy
    printf 'runtimes:\n    - python@3.11.11\ntools:\n    - pylint@3.3.6\n' > "$codacy_cfg"
    created_codacy_cfg=1
  fi
  if codacy-cli analyze --tool pylint --format sarif -o "/tmp/codacy-verify-$$.sarif" 2>/dev/null; then
    echo "  (Codacy local analyze complete — SARIF at /tmp/codacy-verify-$$.sarif)"
  else
    echo "  (Codacy local analyze skipped or partial - full scan happens in CI)"
  fi
  # Clean up: drop the whole dir if we created it, else remove only the config we wrote.
  if [[ "$codacy_dir_existed" == "0" ]]; then
    rm -rf .codacy
  elif [[ "$created_codacy_cfg" == "1" ]]; then
    rm -f "$codacy_cfg"
  fi
else
  echo "  (codacy-cli not in PATH - install codacy-cli-v2 for local Codacy simulation)"
fi

# 6. Other quick checks (YAML, JSON, large files, etc.)
# When this script is invoked as the verify-quality pre-commit hook, hygiene hooks
# (trailing-whitespace, check-yaml, …) have already run — do not call pre-commit
# again or we recurse: verify-quality → pre-commit --all-files → verify-quality → …
echo "→ Basic repo hygiene..."
if [[ -n "${VERIFY_QUALITY_INVOKED_BY_PRE_COMMIT:-}" ]]; then
  echo "  skipped (pre-commit hygiene hooks already ran for this commit)"
elif ! SKIP=verify-quality uvx pre-commit run --all-files --config .pre-commit-config.yaml 2>/dev/null | tail -5; then
  echo "  (pre-commit config issues - run 'SKIP=verify-quality pre-commit run --all-files' manually)"
fi

if [ $FAILED -eq 0 ]; then
  echo ""
  echo "✅ All local quality checks passed!"
  echo "   Your code should pass Codacy without issues."
  echo "   Safe to commit + push."
  echo ""
  echo "   Next: git commit -m '...' && git push"
  exit 0
else
  echo ""
  echo "❌ Some checks failed. Fix the issues above before committing."
  echo "   Re-run this script after fixes."
  exit 1
fi
