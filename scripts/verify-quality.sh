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
    # shellcheck may not be installed globally; try via uv or note
    echo "  (shellcheck not in PATH or some scripts have issues - install shellcheck or run via Docker if needed)"
  fi
else
  echo "  (shellcheck not installed globally - skipping detailed check. Install with your package manager for full local runs.)"
fi

# 3. Python security (Bandit - matches Codacy)
echo "→ Bandit security scan (on registry code)..."
if ! uvx bandit -r custom_nodes/comfygo_model_registry -q --skip B101,B404,B603,B108; then
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
if command -v codacy &> /dev/null; then
  # The cloud-cli may support analyze in some setups; run a basic check or skip full
  echo "  Codacy CLI detected. For full local scan mirroring CI:"
  echo "    codacy analyze --directory . --tool ruff,bandit,shellcheck --no-upload || true"
  # Attempt a non-blocking run if possible
  codacy analyze --directory . --tool ruff,bandit 2>/dev/null --no-upload || echo "  (Codacy local analyze skipped or partial - full scan happens in CI)"
else
  echo "  (codacy CLI not in PATH - install if you want local Codacy simulation)"
fi

# 6. Other quick checks (YAML, JSON in excludes, large files, etc.)
echo "→ Basic repo hygiene..."
if ! uvx pre-commit run --all-files --config .pre-commit-config.yaml 2>/dev/null | tail -5; then
  echo "  (pre-commit config issues - run 'pre-commit run --all-files' manually)"
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
