# Feature Specification: Comfygo Patched Tmux Control

**Feature Branch**: `004-comfygo-patched-tmux`

**Created**: 2026-06-21

**Status**: Draft

**Input**: User description: "Patch currently-installed ComfyUI + vendored base nodes reliably. Provide up-front settings so the tool gets comfy-cli 'setup the way I like it'. Every launch must sequentially get everything up to date, verify, then launch comfy-cli/ComfyUI inside tmux so that over SSH (single terminal) the controlling shell stays free while the app can still drive comfy-cli and ComfyUI in the tmux window. Support preferred HF git-clone full-data folders + loose files: detect on Civitai, fetch rich details, find HF version, download skeleton, move weights into HF layout + civitai side folder, emit rich comfygo-model.json descriptors so nodes can find and recognise the tools. Make patching resilient across comfy updates using versioned public (non-secret) patch documentation and name-based matching in the repo; on mismatch inform the user so they (with grok) can update the patch. Everything must work over SSH on a headless server. Keep existing speckit artifacts and do not expose private details."

## Clarifications

### Session 2026-06-21
- Q: Should the tool replace all direct use of comfy-cli or coexist? → A: The tool owns the orchestrated flow (update/verify/tmux launch) while still allowing direct comfy-cli when wanted. The goal is to stop the tiring manual work.
- Q: How are "up-front settings" stored? → A: Ignored local files (direnv .envrc.local or a small app config). Never committed. Describe desired patching, launch behavior, model policy, etc.
- Q: tmux window management details (new session vs attach, pane vs window)? → A: Practical: ensure the launch puts the comfy process in its own tmux window/pane so the current shell remains the control plane. The app must be able to send commands to that tmux target.
- Q: Scope of "re-patch after update"? → A: Focus on the vendored base (custom_nodes in this repo) + the two known patches (comfyui + comfy-cli local-nodes). Use historical node names/paths + manifests.
- Q: How much of Civitai/HF enrichment is automated vs manual review? → A: Automated where possible (API calls with direnv keys), with clear output in the JSON. User can edit the resulting JSON.
- Q: Public issues privacy? → A: High-level only. No private paths, keys, model names that reveal usage, no personal infrastructure details.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Reliable Patch of Currently Installed Base (Priority: P1)

A user (or the server) has a ComfyUI + comfy-cli setup. They want the vendored base nodes + patches from this repo applied cleanly, and re-applied correctly even after a `comfy update`.

**Why this priority**: This is the primary stated goal. Without solid patching, nothing else matters.

**Independent Test**: Run the tool's patch/sync step (via patched comfy local-nodes or scripts). Observe that the exact set of vendored custom nodes and the two patches are present and functional. Then simulate an upstream change and re-run; either it self-heals or tells the user exactly what to fix.

**Acceptance Scenarios**:

1. **Given** a fresh or partially drifted ComfyUI workspace, **When** the user runs the tool's primary patch command, **Then** the vendored base custom nodes are synced and the known patches are applied.
2. **Given** the patches were previously applied, **When** comfy-cli performs an update that overwrites files, **Then** the next launch or explicit re-patch either restores the desired state using the versioned patch docs or clearly informs the user which node/file needs a new patch.
3. **Given** the user is SSHed to the headless server, **When** they invoke the patch flow, **Then** it completes without requiring GUI or local display.

### User Story 2 - One-Command Launch That Owns the Full Sequence in Tmux (Priority: P1)

Over SSH the user only has one terminal. They want to run one command that updates, verifies, then puts comfy-cli/ComfyUI into tmux so their current shell stays responsive and the tool can still drive things.

**Why this priority**: Directly solves the "tiring" and "single terminal" pain.

**Independent Test**: SSH (or simulate), run the launch command with up-front settings present. Observe sequential logs (update → verify → tmux launch). The controlling shell remains usable while ComfyUI runs in another tmux window. The app can still interact with the tmuxed comfy process.

**Acceptance Scenarios**:

1. **Given** up-front settings that describe desired patching and launch behavior, **When** the user runs the launch command, **Then** it first gets nodes/patches/descriptors up to date, then verifies, then launches inside tmux.
2. **Given** the launch has completed, **When** the user is in the original shell, **Then** they still have a prompt and can ask the app to control the tmux-launched comfy (status, stop, etc.).
3. **Given** the same command is run over plain SSH, **Then** everything works with direnv-loaded keys and no X11.

### User Story 3 - Preferred HF Git-Clone + Civitai Enrichment Produces Usable Descriptors (Priority: P2)

User has (or downloads via git clone with full data) HF model folders and some loose files. They want the tool to enrich them with Civitai details + proper HF layout + side metadata + rich JSON so nodes can find the models without hard-coded paths.

**Why this priority**: Matches the preferred acquisition method and the "nodes will pick up whatever it needs" goal.

**Independent Test**: Point the tool at a git-cloned HF folder or a loose file (with direnv keys present). After enrichment, a proper HF layout + civitai side folder exists and a comfygo-model.json with kind + rich source info is present. Reconcile makes it visible. A node (or the registry lookup) can discover it by the declared type.

**Acceptance Scenarios**:

1. **Given** a git-cloned HF model folder (full data), **When** the enrichment step runs, **Then** Civitai match (if any) is fetched, HF skeleton is ensured, weights are in the right place inside the layout, and a civitai side folder + rich JSON are created.
2. **Given** a loose .safetensors, **When** enrichment runs, **Then** the same structured result is produced.
3. **Given** the enriched JSON, **When** the registry scans and reconciles, **Then** the model appears under the declared kind/categories for nodes to use.

### Edge Cases

- Up-front settings file is missing or incomplete → tool uses safe defaults and clearly tells the user what to configure.
- Civitai or HF API calls fail (no token, rate limit, no match) → graceful degradation; still produce a basic usable descriptor from what is known locally.
- tmux not installed on the server → fail early with a clear message and installation hint (or fall back to documented alternative if user configured it).
- A vendored node author changed structure so badly that name/path matching fails → inform the user with the historical name and the exact file that needs a new patch; do not silently break.
- Re-patch during an active tmux session → the tool must not disrupt a running ComfyUI unless explicitly told (or do it safely).
- Private data (keys, specific model names that reveal usage) must never appear in committed patch docs, issues, or specs.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The primary entry point (the "app"/comfygo tool) must support up-front declarative settings (local only) that tell it how the user wants comfy-cli and the base nodes/patches/models configured.
- **FR-002**: A single launch command must execute the sequence: (1) bring the installed base up to date using the vendored sources and patches, (2) run verification steps, (3) launch the comfy process inside a tmux window/pane while leaving the invoking shell interactive.
- **FR-003**: The tool must be able to send control commands to the tmux-launched comfy-cli/ComfyUI from the controlling shell (status, restart, etc.).
- **FR-004**: After a comfy update, the tool must attempt to re-apply the known patches using versioned patch documentation stored in the repo and simple historical name/path matching.
- **FR-005**: When automatic re-patching cannot determine the correct action for a node/file, the tool must emit a clear, actionable message to the user (including the historical node name/path) and must not corrupt state.
- **FR-006**: The user (with assistance) can update a patch for a particular node and the corresponding versioned documentation; the system must then be able to use the new patch on subsequent runs.
- **FR-007**: Model acquisition helpers must support both full git-clone HF folders (preferred) and loose files.
- **FR-008**: For a candidate model (loose or cloned), the tool must be able to query Civitai (using direnv token), fetch rich details when a match is found, locate a corresponding HF version when it exists, ensure HF skeleton layout, place weights appropriately, create a civitai side folder, and write a rich comfygo-model.json.
- **FR-009**: The emitted JSON must be usable by the existing descriptor/registry machinery so that nodes can discover models by declared kind/type without hard-coded subdirectories.
- **FR-010**: All flows (patching, enrichment, launch, re-patch, verification) must succeed over plain SSH to a headless server using only direnv-loaded environment; no X11 or local GUI required.
- **FR-011**: Versioned patch documentation committed to the repo must contain no secrets, keys, tokens, private paths that reveal personal usage, or personal prompts/logs.
- **FR-012**: The vendored custom nodes in this repo (the "base") plus the known patches must be sufficient to recreate the desired patched state from a fresh ComfyUI + comfy-cli checkout.
- **FR-013**: The existing speckit artifacts, GC harnesses, doctor, verify, descriptor scanner/reconciler, and `.comfygo_views` mechanism must remain functional and are not to be removed.

### Repository Policy Requirements

- All new or modified scripts and Python must continue to be uv-first.
- No tokens, keys, or private details may be committed.
- Patch documentation and public issues must be written at a technical level that does not expose private usage.

### Key Entities

- **Up-front Settings**: Local declarative configuration (e.g. `.comfygo-settings` as simple key=value or sourced env, git-ignored). Keys include: COMFYGO_LAUNCH_TMUX_NAME, COMFYGO_PATCH_POLICY (strict/lenient), COMFYGO_ENRICH_CIVITAI, COMFYGO_PROTECTION_REMIND. Loaded via direnv or explicit file; never committed.
- **Patch Manifest / Versioned Documentation**: Committed, non-secret records (per ComfyUI/comfy-cli version) in `comfyui-patches/<version>/manifest.md` (and equivalent for comfy-cli). Format: simple structured text/JSON listing touched paths + historical names for matching + rationale. Driver compares current state to desired using name/path heuristics.
- **Enriched Model Package**: A git-clone HF layout or structured folder containing weights + civitai side folder + rich comfygo-model.json (with HF + Civitai source info).
- **Tmux Target**: The managed tmux window/pane (named via COMFYGO_LAUNCH_TMUX_NAME, default "comfyui") in which comfy-cli/ComfyUI runs (via `tmux new-window -n $name`) so the control shell stays free. Includes helpers to record target and send commands (e.g. status/stop).
- **Re-patch Driver**: Logic that, given current version and patch manifests, attempts to restore the desired patched state or informs the user.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user over SSH can run one command and obtain a fully patched, verified, tmux-launched ComfyUI while retaining an interactive controlling shell (no manual comfy-cli steps required after initial settings).
- **SC-002**: After a comfy update that would normally break patches, running the tool either restores the desired state using the committed manifests or tells the user exactly which historical node needs a new patch.
- **SC-003**: For both a git-cloned HF full folder and a loose model file, the enrichment flow produces a layout + civitai side folder + JSON that the registry can reconcile and that nodes can discover by the declared kind.
- **SC-004**: All primary flows complete successfully when invoked over plain SSH with direnv (single terminal).
- **SC-005**: No private keys, paths, or usage-revealing details appear in committed patch docs, specs, or example issues.
- **SC-006**: The vendored base + patches in the repo remain the canonical way to recreate the desired state on a fresh start.
- **SC-007**: Existing speckit test harnesses (GCD scenarios, doctor, verify) and the descriptor registry continue to function.

## Assumptions

- The user will maintain direnv files locally for tokens (already the case).
- tmux is (or can be made) available on the target server.
- The user is comfortable occasionally editing a .patch file + the versioned manifest when upstream breaks a node (with grok help).
- The existing comfygo_model_registry descriptor format is sufficient or can be lightly extended for the extra Civitai/HF metadata.
- "Base nodes" means the custom nodes vendored in this repo plus the two known patches.

## Open Questions (max 3)

None at time of writing — all major decisions have been clarified in the input. Any remaining details will be recorded in the generated speckit artifacts.