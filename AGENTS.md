# Work efficiently and preserve release evidence

The user wants short edit/test cycles. Read the current private checkpoint first;
do not repeat completed work or rerun unchanged validation merely for reassurance.
Keep changes together until ready for review and push once after local checks.

- Documentation changes: check links and claims; no app rebuild.
- UI changes: JavaScript syntax, existing relevant Node tests and focused rendered
  checks of the affected controls/layout. Run preference tests if persistence changes.
- Backend changes: relevant unit tests first; broaden if failures or dependencies
  justify it. Changes to analysis must preserve the sole canonical scanner/rules.
- A release/runtime/native bridge change: one complete application suite and
  source/frozen checks on the affected platforms, then package and verify those
  exact bytes. Retain pause/stop/shutdown, integrity and input-preservation checks.

Cache dependencies, cancel superseded CI runs, and assemble large source materials
only for release candidates. Retain successful evidence by commit/tree and archive
hash; do not reuse it after a relevant code/runtime change. Retry failed jobs only
after reviewing their logs. A green unchanged rerun does not prove an intermittent
issue is fixed. Keep diagnostic work bounded and record unresolved limits honestly.

Use bounded, compact tool output; avoid printing full source, licenses or logs when
a targeted section or summary will suffice. Checkpoint meaningful progress under
the active project's ignored .work directory. Never publish tokens/private music.
Publishing a requested release is authorized; account purchases/signing credentials
remain owner decisions. Do not add features or extra platforms during a release.
