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
- If token/env loading is needed from `/fast/comfyui` paths, use
  `comfygo runtime-envrc` to create the machine-local runtime `.envrc`; do not
  hand-code secrets into runtime directories.

<!-- SPECKIT START -->
The feature in progress is **descriptor-model-registry**.
Read `specs/001-descriptor-model-registry/plan.md` for the implementation
plan, technical context, constitution checks, and project structure.
Also read `specs/001-descriptor-model-registry/spec.md` for user stories,
requirements, and acceptance criteria.
<!-- SPECKIT END -->
