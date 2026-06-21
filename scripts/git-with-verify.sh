#!/usr/bin/env bash
# scripts/git-with-verify.sh
#
# Optional shell wrapper for extra safety.
# Source this (or copy the function) in your ~/.bashrc or ~/.zshrc on the development machine.
#
# It wraps "git commit" and "git push" so the quality gates are run
# *even if* an AI agent (Grok, Codex, Hermes, Agy, Claude, Cursor, etc.)
# simply tells you to run "git commit".
#
# This is the ultimate agent-agnostic hook.

git() {
  if [[ "$1" == "commit" || "$1" == "push" ]]; then
    echo "🔒 [git-with-verify] Running local quality gates before 'git $*' ..."
    if ! ./scripts/verify-quality.sh; then
      echo "❌ Quality gates failed. Do not $1 until this passes."
      return 1
    fi
    echo "✅ Gates passed. Proceeding with 'git $*'."
  fi
  command git "$@"
}

# To use:
#   source /path/to/this/script
# Then normal "git commit" and "git push" will automatically verify first.
