# Recovery foundation — ticket #41 (staging handoff)

Small delivery: preserve failed candidates and verify recovery before
continuing. It does not reimplement the full #40 orchestrator, does not add
`/agent-fix-cycle`, does not change form #38, limits, models or secrets, and
does not claim a prior PR resolved before gates.

## Provenance

- Ticket: #41 — Bootstrap: conservar candidatos fallidos y verificar
  recuperación antes de continuar. Parent #40 paused; #38 blocked by #40.
- Accepted bootstrap #42 merged in
  `4528057d497268a0e08d52b3e364702ab24657e0`: committed candidate plus final
  per-axis reports are already preserved before gates. This delivery does not
  rebuild that bootstrap and does not recover the lost pre-#42 candidates
  from logs (artifacts contained only `result.json`).
- Entry base: `feat/callflow-generic-profile`
  (`90798e5749c06136d6b6e34991c2a40382dde668`, docs/bootstrap planning only
  over v0.2.8). `reference/` holds exact copies of the accepted controls and
  public CLI tests; the legacy `test_agent_flow` with internal mocks is not
  imitated here.
- New code lives only in `docs/bootstrap/recovery-foundation/` with public
  CLI tests in `tests/test_recovery_foundation.py`. No live controls, payload
  AGENTS, `.opencode` in the workspace, secrets, or real provider calls are
  touched. Mock/laboratory data only. PHP5.4/Python3.6 compatibility is kept.

## What is new after #42

- Safe capture of **uncommitted** changes only after confirmed worker
  termination, with the same finite limits/exclusions/checksums as committed
  sources. Unconfirmed termination records `unavailable` without reading a
  snapshot in writing. `check-failed` is never conflated with `timeout`.
- Integral `restore` verification in a clean worktree at the registered base:
  provenance, checksums, completeness, modes, no truncation, no symlinks, no
  outside paths, no secrets. Transcripts/logs are never a restore source.
- Executable pre-merge review/CI path for the final published handoff PR
  (the #42 branch review is specific to that branch and is not an automatic
  gate for another PR). Standards/Spec run from the approved declarative
  configs in isolated temp dirs without `GH_TOKEN` in model envs, publish
  separate HEAD-stamped reports, and any missing/`FAIL`/`timeout`/
  `NEEDS-DECISION`/`action_required`/foreign-SHA never approves. Reviews never
  mutate the candidate.
- Deterministic `checksum.py` generates/verifies `handoff.json`. The model
  never invents hashes; the operator runs the tool and verifies on publish.

## Files (origins -> live destinations)

- `preserve.py` -> `tools/recovery_preserve.py`
- `restore.py` -> `tools/recovery_restore.py`
- `review.py` -> `tools/recovery_review.py`
- `checksum.py` -> `tools/recovery_checksum.py`
- `recovery-review.yml` -> `.github/workflows/recovery-review.yml`
- `README.md` stays as staging documentation.
- `handoff.json` is **generated** by `checksum.py`, never hand-edited.

Limits (shared with the accepted evidence helper): 200 files,
256 KiB/file, 2 MiB total sources, 4 MiB patch. Excluded: absolute/`..`/
backslash/control paths, protected roots (`tools/agent_*`,
`tests/automation`, `docs/agents`, `.github`, `.opencode`, ...),
sensitive suffixes/parts/names (keys, logs, sqlite, secrets, `.env`,
`auth.json`, `profiles.conf`), symlinks and non-regular modes.

## Exact commands

Staging (isolated worktree, no live edits):

```bash
git fetch origin feat/callflow-generic-profile
git worktree add --detach /tmp/cfh-41 feat/callflow-generic-profile
```

Preserve after a non-successful controller exit (confirmed termination):

```bash
python3 docs/bootstrap/recovery-foundation/preserve.py preserve \
  --workspace /tmp/cfh-41-work --base <base40> --head <head40> \
  --result /tmp/evidence/result.json --output /tmp/bundle \
  --worker-terminated --ticket 41 --run <run-id>
# stdout: manifest JSON; return 0 only when status complete.
# Unconfirmed termination: omit --worker-terminated -> status unavailable,
# reason termination-unconfirmed, no worktree snapshot is read.
```

Checksum / handoff generation and verification (no invented hashes):

```bash
python3 docs/bootstrap/recovery-foundation/checksum.py \
  --root docs/bootstrap/recovery-foundation \
  --output docs/bootstrap/recovery-foundation/handoff.json
python3 docs/bootstrap/recovery-foundation/checksum.py \
  --root docs/bootstrap/recovery-foundation \
  --verify docs/bootstrap/recovery-foundation/handoff.json
```

Restore into a clean worktree at the registered base:

```bash
git worktree add --detach /tmp/cfh-41-restore <base40>
python3 docs/bootstrap/recovery-foundation/restore.py restore \
  --bundle /tmp/bundle --worktree /tmp/cfh-41-restore
# return 0 only when status restored; incomplete/truncated/tampered,
# symlinks, outside paths and secrets are refused.
```

Reliable publication (operator only, trusted harness):

1. Verify `handoff.json` with `checksum.py --verify`.
2. Copy exactly the verified bytes to their live destinations.
3. Open a **draft** PR against `main` from
   `bootstrap/recovery-foundation-*` with marker
   `<!-- callflow-recovery-handoff:41 -->` in the body. Do not complete code.

Review/CI of the final HEAD **before** first merge:

```bash
# CI: existing addon gates on the exact HEAD (unchanged, plus new tests).
python3 -m unittest discover -s tests -p 'test_recovery_foundation.py' -v
python3 tools/agent_gates.py "$HEAD_WORKSPACE"   # when live controls exist
# Reviews: one job per axis via recovery-review.yml, or manually:
python3 tools/recovery_review.py --pr <n> --axis spec --head <sha> \
  --base <base> --workspace <candidate> \
  --profiles docs/bootstrap/payload/opencode/agents --evidence /tmp/rev-spec
python3 tools/recovery_review.py --pr <n> --axis standards --head <sha> \
  --base <base> --workspace <candidate> \
  --profiles docs/bootstrap/payload/opencode/agents --evidence /tmp/rev-std
```

Accept only with both axis reports `PASS` for the exact HEAD, published in
the PR, plus successful CI of the same HEAD. Any new commit invalidates both
reviews and CI. A staging/legacy review never substitutes these gates.

## Limits

- Laboratory/mocks only; no installed-production acceptance is claimed from
  unit tests. Publication/resumption of the usual pre-gate PR continues for
  #40; scope is not broadened to #38 and the full orchestrator is not
  rewritten here.
- Models stay pinned (implement/spec
  `opencode/muse-spark-1.3-contributor-free`, standards
  `opencode/mimo-v2.6-flash-free`, CLI `1.18.30`); no paid fallback, no
  merge/deploy permissions, no secrets or workflow-write for models.
