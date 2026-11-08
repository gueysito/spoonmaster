# Adopt the standards kit

This is a template, not an instruction to reformat a repo now. Offer adoption once
after the existing identity check confirms `gueysito/*` or `Crafty-Systems-Labs/*`.
Other owners' repos use their own contribution rules. Ask if ownership is unclear.
Record a dated defer/decline in AGENTS.md; those repos are exempt until they adopt.

## Before changing anything

Fetch and review remote activity, overlap and divergence through the repo's owning
workflow. Read its AGENTS.md, package manager and existing configuration. Preserve
existing lint rules and add these rules; do not replace stricter project checks.
Inventory `.git/hooks`, `.husky`, other hook frameworks and `core.hooksPath`.
Hooks already installed remain active during adoption. Never skip hooks, suppress
failures, weaken tests or use `--no-verify`. Resolve any conflict before proceeding.

Put this kit in the repo's committed `.standards/` folder. Copy `prettierrc.json`
to `.prettierrc.json`, `prettierignore` to `.prettierignore`, `eslint.config.mjs`
and `ruff.toml` to the root, merging existing configuration and ignores. The `.mjs`
extension keeps the flat ESLint config usable in CommonJS and ESM repos.
Exclude generated, vendored, lockfile and byte-preserved archive paths explicitly;
custom exclusions must agree between the checker, Prettier, ESLint and Ruff.
The default kit uses directories `generated`, `vendor`, `archives` and `dist`.

For JS/TS/JSX/Svelte, use exact-pinned local Prettier, ESLint, Stylistic, TypeScript
parser and Svelte adapter dependencies. `test-tools/package.json` records the tested
versions; merge the dependencies into the repo's own manifest, preserving its
package manager. It is not a replacement application manifest. Keep its lockfile.
Follow JS-SUPPLY-CHAIN-SAFETY: audit before install, seven-day release-age gate,
review lifecycle scripts, block unreviewed scripts, frozen CI installs.
Use `.venv/bin/ruff` pinned to the tested version in `test-tools/requirements.txt`.
The kit fetches nothing and uses no global formatter or package runner.

Prettier width 100 is a formatting target. ESLint's maintained Stylistic rules
block lines over 120 (except URLs, strings, templates and regex), chained statements
and dense one-line JSX. Ruff explicitly selects E501 at width 100. Keep the repo's
existing language rules. Other languages need their own existing equivalent checks
before their baseline can be marked adopted; these templates cover JS/TS/Svelte/Python.

## Adoption order

1. Run the repo's formatter for one mechanical formatting commit, with an R2 body.
   Run the full project tests. Put the formatting commit hash in the committed
   `.git-blame-ignore-revs` file in the following lint-fix commit.
2. Fix lint findings in a separate commit with Why/Changed/Verified. Run the full
   tests again. Keep code, its docs and tracker changes together in each commit.
3. Install hooks last, when format and lint are clean. From the repo root, run
   `sh .standards/setup-hooks.sh`. Review its found/kept report. It keeps existing
   hook files unchanged and chains every executable hook from the formerly active
   hook directory. Other discovered hook directories remain unchanged. Existing
   `.githooks` contents cause a stop for reviewed migration, never an overwrite.
   Commit the generated `.githooks` files. `standards.previousHooksPath` is local
   Git configuration: rerun setup on each clone to preserve that clone's hooks.
   A preserved pre-commit hook that edits the index blocks the attempt; review and
   restage before retrying. Do not disable that protection to make a commit pass.
4. Add a code-style section and `Standards baseline: adopted YYYY-MM-DD` to AGENTS.md.
   It must state the actual formatter/linter and exclusions. Set the commit template
   using setup (Why/Changed/Verified; docs-only Why/Changed; optional Follow-up).
   Run `sh .standards/check-standards.sh` and the full tests, then commit this slice.

For a fresh clone with the kit's already-committed `.githooks`, setup verifies the
kit's wrappers and preserves that clone's previous active hooks before activation.
If a framework changes hook locations later, review the chain and rerun migration.

## Front door

Fill only missing pieces from GitHub Workflow §3: README, AGENTS.md reading order,
one-screen state and one tracker for ongoing work. Preserve established equivalents
and frozen history. Record larger gaps in the existing tracker for the owner.
Repos without code adopt the commit template, hooks and front door only; no
formatter configuration is required. The read-only check honors recorded
defer/decline decisions without another offer and runs outside the hooks.

## What the hooks check

Pre-commit exports the complete index into a temporary directory, then checks only
added/modified staged code. Both source and configuration come from the index.
Partly staged files are judged by what will be committed; the worktree and index
are never rewritten. Staged configuration symlinks are rejected. Local executable
configs and pinned tools remain trusted repository code, just as in normal lint.

`check-standards.sh` checks baseline items and executes checks against all tracked
index code, plus failing rule probes. `--staged` runs the same staged-content check
as pre-commit. It reports missing tooling and bad configurations as failures.
It creates only temporary files, never installs dependencies or updates the index.

Commit-msg requires nonempty sections, not merely heading names. Docs-only commits
need Why/Changed. Other commits need Why/Changed/Verified. Actual Git merge state
and Git-generated reverts qualify; copied merge/revert subjects do not.

Automation exceptions use the single reviewed `AUTOMATED-COMMITS.md` inventory.
At adoption copy it and its `AUTOMATED-COMMITS-EVIDENCE.json` into `.standards/`.
The hook requires an ancestor process holding the named reviewed script open,
a matching source hash, the exact generated message and the allowed staged paths.
On macOS it uses `lsof` script descriptor 255; on Linux `/proc` descriptor paths.
Missing process proof or changed sources fail closed; review before granting an
exception. Scripts already producing R2 bodies need no exception. This does not
authorize running sync/adoption scripts or connecting to hosts.

Expected weights: pre-commit 0.5–3s for local tool startup plus staged file volume;
commit-msg under 100ms normally for body/index checks, up to 1s for automation
process proof. Previously installed hooks add their existing cost. Other generated
hook wrappers only delegate to those previous hooks; they add Python startup.

## Test and rollback

Use the test-tools manifest/lockfile in a scratch folder only, audit, then `npm ci
--ignore-scripts`; install pinned Ruff in a scratch venv. Run `python3
test-kit.py /path/to/scratch/tools`. No production automation is executed by tests.
The suite covers each readability rule, clean files, partial staging, real merges
and reverts, message bodies, hook preservation, index mutation and named automation.

Rollback is a reviewed Git revert of the adoption commits and restoration of the
previous hooksPath recorded in local Git config. Existing hook files were retained.
Keep the formatting hash for blame history. Never bypass a failing hook to rollback;
resolve its concrete finding through the owning repo's workflow.
