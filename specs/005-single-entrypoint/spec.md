# Feature Specification: Single Entrypoint CLI

**Feature Branch**: `005-single-entrypoint`

**Created**: 2026-06-22

**Status**: Draft

**Input**: User description: "need to ensure that user only need to remember 1 simple entry point. hence in the documentations need to highlight this. likewise if documentation shows this, constitution should also reflect something similar."

## Clarifications

### Session 2026-06-22
- The single entry point is the `comfygo` command (as already referenced in constitution as "the normal daily command").
- Subcommands under it are acceptable (e.g. `comfygo models enrich`); the key is users remember `comfygo` as the starting point.
- "Documentation" includes README, workflow.md, model-library.md, quickstarts, and any usage examples.
- Constitution update should reinforce under "Safe Daily Operation" or a new note.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - One Command to Rule Them All (Priority: P1)

A user (solo maintainer accessing server over SSH) wants to perform all daily ComfyUI setup, launch, patching, enrichment, and diagnostics without having to remember or discover multiple scripts, wrappers, or entry points.

**Why this priority**: This is the primary user pain point described. Cognitive load is high with scattered scripts (comfy-local, hf_select, update scripts, etc.). Aligns with existing constitution emphasis on `comfygo` as the daily command. Without this, even perfect features are hard to use.

**Independent Test**: A new user follows only the "use `comfygo`" mention in docs/README and can complete a full workflow (e.g. launch with settings, enrich a model, check doctor status) without consulting other files.

**Acceptance Scenarios**:

1. **Given** a user has the repo and basic direnv setup, **When** they type `comfygo` (or `comfygo --help`), **Then** they see the main entry point and all key sub-operations (launch, models, doctor, etc.) documented under it.
2. **Given** documentation is read, **When** the user searches for how to launch or enrich, **Then** the primary instruction always starts with `comfygo ...` (no direct script paths in top-level docs).
3. **Given** the constitution is consulted for "how to operate daily", **When** the user looks for the recommended command, **Then** it explicitly names the single entry point `comfygo`.

### User Story 2 - Consistent Highlighting Prevents Confusion (Priority: P2)

A user following examples or quickstarts in docs must not be led to use internal scripts directly; all paths must funnel through the single entry point so muscle memory is built around `comfygo`.

**Why this priority**: Supports P1 by ensuring docs don't undermine the "remember one thing" goal. Inconsistent docs are a common source of "which command do I run?" confusion.

**Independent Test**: Scan all docs/examples; every top-level usage example starts with `comfygo` (or clearly delegates to it).

**Acceptance Scenarios**:

1. **Given** an example in workflow.md or README for patching or enrichment, **When** the example is followed, **Then** it invokes via `comfygo` (or `comfygo models ...`).
2. **Given** a new user reads the constitution for daily use, **When** they look for the command, **Then** it points to `comfygo` as the single remembered entry point.

### Edge Cases

- Existing internal scripts (comfy-local, etc.) may still exist for development/debugging but must not be promoted in user-facing docs or constitution.
- Backward compatibility: old direct script invocations should continue to work for now but be deprecated in docs with pointer to `comfygo`.
- Subcommand discoverability: `comfygo --help` and `comfygo <sub> --help` must surface the full surface without requiring knowledge of separate scripts.
- If `comfygo` wrapper is not in PATH, docs must show the one-time setup (e.g. alias or install) but still position `comfygo` as the conceptual single entry point.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: There MUST be a single top-level command (named `comfygo`) that serves as the primary user entry point for all normal daily operations (launch, patching, enrichment, doctor, status, etc.).
- **FR-002**: All user-facing functionality for the tool MUST be reachable via subcommands/flags under the single `comfygo` entry point (or clearly delegated from it in docs).
- **FR-003**: User-facing documentation (README, workflow.md, model-library.md, quickstarts, examples, issue templates) MUST prominently and consistently highlight `comfygo` (or `comfygo <subcommand>`) as the command the user needs to remember and use.
- **FR-004**: The project constitution MUST contain (or be updated to contain) explicit language reinforcing the single daily command / entry point principle (e.g., under Safe Daily Operation or a new dedicated note), so that governance aligns with the UX goal.
- **FR-005**: Internal implementation scripts (comfy-local, etc.) MAY remain but MUST NOT be the promoted interface in docs or constitution; any references must redirect to the single entry point.

### Repository Policy Requirements

- All new or modified scripts and Python must continue to be uv-first.
- No tokens, keys, or private details may be committed.
- Documentation and public artifacts must consistently present the single entry point without leaking internal paths that would encourage users to remember multiple commands.

### Key Entities

- **Single Entry Point Command**: The canonical top-level executable (`comfygo`) that users invoke. It dispatches to underlying logic (settings, launch sequence, enrichment, doctor, etc.) while hiding complexity.
- **Documentation References**: All mentions of usage in docs, examples, and constitution that must point to the single entry point as the memorable interface.
- **Internal Wrappers**: Supporting scripts (e.g. comfy-local) that implement behavior but are not the user-facing remembered name.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A new user can identify and use the primary workflow (e.g. launch with settings or enrich a model) after seeing only the single `comfygo` command mentioned once in top-level docs or constitution.
- **SC-002**: 100% of user-facing examples and quickstarts in docs start with `comfygo` (or `comfygo <sub>`) as the first command shown (no bare script paths in primary flows).
- **SC-003**: The constitution explicitly names the single entry point as the recommended daily command (verifiable by grep or reading the Safe Daily Operation section).
- **SC-004**: Users report (or tests show) reduced confusion about "which command to run" (qualitative: no questions in issues/docs about multiple entry points after reading the highlighted docs).

## Assumptions

- The single entry point name is `comfygo` (already established in the existing constitution as "the normal daily command").
- Subcommands under `comfygo` are the mechanism for exposing functionality (e.g. `comfygo models enrich`, `comfygo doctor`).
- Existing internal scripts remain for power users/devs but are de-emphasized for normal users.
- "Documentation" scope includes README, docs/*.md, quickstarts, examples in code comments, and issue templates.
- This is primarily a documentation + governance alignment feature (no new code behavior required beyond ensuring the wrapper dispatches everything).
- The change can be rolled out without breaking existing direct script invocations for now (deprecation path via docs).

## Open Questions (max 3)

None — the description is clear on the goal (one memorable entry point), and reasonable defaults exist for name (`comfygo`), mechanism (subcommands + docs emphasis), and scope (docs + constitution).