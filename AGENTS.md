## Repository Rules

- This repo is uv-first. Use `uv run` for Python/comfy-cli command execution,
  `uv pip --python <workspace-python>` for workspace dependency installs, and
  `uv run --python <workspace-python> --no-project python ...` for diagnostic
  Python that must target a workspace interpreter.
- Do not add direct `pip`, `python -m pip`, or unwrapped `python` workflow
  commands. If `uv` is missing, stop and ask for `uv` to be installed first.
- Keep machine-local configuration in ignored files such as `.envrc.local` or
  `.env.local`; do not commit tokens, model weights, local prompts, logs, or
  runtime histories.
- If token/env loading is needed from runtime ComfyUI paths, use
  `comfygo runtime-envrc` to create the machine-local runtime `.envrc`; do not
  hand-code secrets into runtime directories.

## Quality Gates (Before ANY Commit or Push)

**This rule applies to ANY coding agent you are using** (Grok, Claude, Cursor, Aider, Codex, Hermes, Agy, or future ones). The agent does not matter — the process does.

**Critical rule**: All code must pass local verification *before* you run `git commit` or `git push`.
Codacy (and branch protection) runs *after* push — failures waste Actions minutes and tokens. Once code is pushed, it is too late.

### Universal Enforcement (Works Regardless of Agent)
The real cross-agent hook is at the git level:

1. Pre-commit framework (`.pre-commit-config.yaml`) + the custom verifier.
2. You (or any agent) must run the following before committing:

```bash
# One-time setup (do this on the machine)
uv tool install pre-commit
pre-commit install

# Before every commit
./scripts/verify-quality.sh
```

The `pre-commit` hook runs automatically on `git commit`. The `verify-quality.sh` script replicates the checks that would make Codacy fail (Ruff, Bandit, ShellCheck, relevant tests, hygiene, etc.).

**Never use `git commit --no-verify` or `git push --no-verify`** except in genuine emergencies (and document the reason).

### Instructions for Any AI Coding Agent
When you are talking to *any* coding agent about changes in this repo, the following must happen:

- The agent must instruct you (or directly run via tools) `./scripts/verify-quality.sh` **before** suggesting or executing a commit/push.
- If the script fails, the agent must help fix the issues and re-run the script until it passes with a ✅ message.
- Only then may the agent output a `git commit` or `git push` command.

This is the expected behaviour no matter which agent you have active at the moment.

See also:
- `.pre-commit-config.yaml`
- `scripts/verify-quality.sh`
- `docs/workflow.md` (Local Quality Gates section)
- Root `README.md` (Codacy section)
- The `local-quality-gates` skill (for agents that support formal skills like Grok)

### For Agents That Support Skills (Grok, etc.)
There is a dedicated `local-quality-gates` skill installed on this machine. When active, the agent should automatically run the verify script on any commit-related intent.

### Why This Design
- Git hooks + verify script = works **regardless** of which AI you are using right now.
- AGENTS.md (this file) = the canonical instructions you can paste or that smart agents read.
- Per-agent skills = nice-to-have automation on top for agents that have a skill system.

The combination ensures the correct behaviour is triggered *beforehand*, before any code reaches the remote.

### Even Stronger Universal Hook (Recommended for Heavy AI Use)
If you frequently let different AIs output raw `git commit` / `git push` commands, source this wrapper in your shell on the dev machine:

```bash
source scripts/git-with-verify.sh
```

After sourcing, every `git commit` and `git push` (no matter which agent suggested it) will automatically run the quality gates first.

You can add the `source` line to your `~/.bashrc`, `~/.zshrc`, or direnv setup for the project.

<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan
at specs/003-gc-doctor/plan.md
<!-- SPECKIT END -->
