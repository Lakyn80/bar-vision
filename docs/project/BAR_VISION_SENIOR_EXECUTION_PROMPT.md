# BAR VISION — SENIOR AUTONOMOUS EXECUTION PROMPT

This document is the Bar Vision project-specific executive overlay for coding agents.

Mandatory companions (read fully before code changes):

```text
docs/project/UNIVERSAL_EXECUTION_PROTOCOL.md
docs/project/BAR_VISION_EXECUTION_MAP_EN.md
```

Priority:

```text
1. Current explicit user instruction
2. Security constraints
3. BAR_VISION_EXECUTION_MAP project-specific rules
4. This senior execution prompt (including Git authorization below)
5. Project architecture
6. UNIVERSAL_EXECUTION_PROTOCOL
7. Existing repository conventions
```

Docker is authoritative. Host application port: `18100` only unless a verified requirement exists.

Physical bottle data, calibration milliliters, and vision benchmark accuracy must never be fabricated.

Implementation does NOT authorize production deployment.

---

# GIT COMMIT AND PUSH AUTHORIZATION

After all required implementation, regression tests, runtime verification, and performance checks pass:

1. Inspect the complete Git diff.
2. Verify that no unrelated user work, secrets, `.env` files, generated artifacts, caches, logs, datasets, or temporary files are staged.
3. Split the completed work into logical atomic commits where appropriate.
4. Use clear Conventional Commit-style commit messages.
5. Do not commit any known broken or unverified state.
6. Push the completed commits to the CURRENT Git branch.
7. Do not create, switch, merge, rebase, or delete branches unless technically required by the existing repository workflow.
8. Do not force-push.
9. Do not deploy anything.

Before committing, run:

```bash
git status --short
git diff --stat
git diff
```

After committing, run:

```bash
git log --oneline -5
git status --short
```

Then push:

```bash
git push
```

If the current branch has no upstream, inspect the repository configuration and establish the appropriate upstream only if unambiguous and safe.

If push fails:

* report the exact failure,
* do not hide it,
* do not force-push,
* leave the local commits intact.

Final report must include:

```text
Branch:
Commits created:
Commit hashes:
Push result:
Remaining uncommitted files:
```

Git commit and push are authorized ONLY after all relevant regression tests and verification gates pass.

Authorized workflow:

```text
úprava
↓
regresní testy
↓
benchmark (when applicable / real data exists)
↓
Docker/runtime ověření
↓
kontrola diffu
↓
atomické commity
↓
push
```

**Push ano, deployment ne.**
