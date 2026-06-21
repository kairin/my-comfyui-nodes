# Research: Model Garbage Collection (comfygo models gc)

**Phase 0 output** — Technical research and design decisions.

## Key Decisions

### Ownership Proof Model

**Decision**: GC requires an explicit `-f NAME --apply` to quarantine any
folder. Dry-run (`comfygo models gc`) reports all managed folders but
never moves anything. This avoids the "marker means garbage" trap —
having `.comfygo-download.json` or `comfygo-model.json` means "comfygo
knows this folder," not "this folder is disposable."

**Rationale**: A user-created `comfygo-model.json` does not indicate
the model is no longer needed. Only the user can decide that. The
`-f NAME` flag forces explicit targeting.

**Alternatives considered**:
- `--all-owned --apply` — rejected for v1: too easy to accidentally
  quarantine active models.
- Marker-age-based GC — rejected for v1: requires defining "old."
- Check active views before GC — rejected: would require reconcile
  state that may not exist.

### Quarantine vs Delete

**Decision**: Quarantine uses `os.rename()` (same-filesystem move).
No copy+delete fallback. If the trash is on a different filesystem,
GC reports the error and does not move the folder.

**Rationale**: Model folders can be large (tens of GB). Copy+delete
would be slow, risk partial copies on failure, and the copy phase
would be a destructive side effect of a read-only operation (the user
asked to move, not duplicate). A cross-filesystem error is safer.

**Destination collisions**: If `.comfygo_trash/<date>/<name>/` already
exists, append a suffix (`-1`, `-2`, etc.) and warn. Never overwrite.
Treat symlinks at the destination as collisions.

### .comfygo_trash Symlink Safety

**Decision**: Apply explicit safety checks:
- Refuse to create .comfygo_trash if it is a symlink
- Refuse if date or name subdirectories under trash are symlinks
- Treat destination symlink as collision
- Refuse to quarantine source folder if it is a symlink

**Rationale**: Consistent with the existing registry safety contract
(FR-005, FR-013 from feature 001), but specified explicitly rather
than "reuse pattern."

### Unique-Match Apply Rule

**Decision**: `-f NAME --apply` must resolve to exactly one managed
folder. Zero matches, ambiguous-only matches, or multiple managed
matches all produce errors with no mutation.

**Rationale**: Without a unique match, GC cannot know which folder
the user intended to quarantine. Choosing the first match silently
would be dangerous.

### Top-Level-Only Scan Scope (v1)

**Decision**: GC v1 scans only top-level directories under the model
root. It does not scan legacy category children through `extra_roots`.
This protects legacy payloads from being moved by a cleanup feature.

**Rationale**: Legacy category folders like `diffusers/` and
`library/` contain user model data that GC should not touch. A
future version may add explicit support, but v1 is conservative.

### CLI Integration

**Decision**: Add `gc` as a subcommand under the existing
`comfygo models` parser. No new entry point. The `-f` flag filters
which managed folders GC considers; without it, GC reports everything
but takes no action.

```text
comfygo models gc                     # dry-run: report all managed
comfygo models gc -f Qwen             # filtered dry-run
comfygo models gc --apply             # error (no -f)
comfygo models gc -f Qwen --apply     # quarantine specific folder
```

### Unsafe Folder Names and Normalization Boundary

**Decision**: GC validates quarantine destination path segments and treats a
managed source folder name that fails validation as a controlled error. It
does not rename, normalize, or reinstall the folder into the model root under
short aliases such as `<kind>-NNN`.

**Rationale**: GC's safety model is explicit quarantine only. Renaming a
downloaded model folder into a canonical short root name changes install
identity and discovery behavior, so it belongs to a separate
normalization/install feature. The marker or descriptor JSON can preserve
model identity for that later behavior, while GC remains a fail-closed cleanup
command.

**Alternatives considered**:
- Normalize unsafe names during GC apply — rejected: it changes GC from
  quarantine into install repair and creates a second mutation target.
- Quarantine unsafe names under generated aliases — rejected for v1:
  restoration paths would no longer match the original folder name.
- Leave validation exceptions uncaught — rejected: users need a controlled
  error with no traceback and no filesystem mutation.

## Post-Remediation Audit (2026-06-20)

After the adversarial review and the subsequent Hermes remediation pass (which updated all 8 sections and grew tasks.md to 39 tasks with T036–T039), a compliance audit was performed.

**Key result**: The remediation follows the adversarial review **very well**. All major P0 safety items have been addressed:

- FR-007 redefined (MUST NOT prune `.comfygo_trash`).
- Unique-match rule for `-f NAME --apply` (FR-013).
- Source symlink refusal (FR-014).
- v1 top-level-only scope (FR-015).
- Data model fixes, explicit safety checks (no vague "pattern"), no `shutil`, pinned contracts, and targeted tests for invalid markers, multi-match apply, source symlinks, and `gc --apply` without `-f`.

Full audit details + updated handoff briefing are in:

**`specs/002-model-gc/adversarial-review.md`** (see the new "Post-Remediation Compliance Audit Summary" section).

The documents are now aligned with the conservative safety principles. Recommended path forward: run `/speckit-implement` starting with US2 (dry-run) per the current plan.

See `adversarial-review.md` for the complete list of proposals and "what to avoid".

This review was incorporated before any `gc.py` or `test_gc.py` work.
