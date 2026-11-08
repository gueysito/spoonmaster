# Repository standards

Kit files are unchanged copies from Biggie Configs
`d1e02551bf27f62859f5e8759de5ed03781f68f7`, `shared/global-reference/coding/standards-kit/`;
automation inventory and evidence come from its parent coding folder. Update from that
owner after review.

Run `sh .standards/setup-hooks.sh` once per clone. Setup preserves and chains existing
active hooks; each clone activates its own chain. `sh .standards/check-standards.sh`
validates the baseline and tracked code.

Python will use Ruff 0.15.6 format/check at width 100 with E501, added with the first
code slice. The kit excludes `.standards/`, generated/vendor/archives/dist paths and
environments. Pre-commit checks staged content without changing the index; commit-msg
requires meaningful Why/Changed and also Verified for code or tooling. No network is
used.

Hook weight estimate: pre-commit 150-300ms and commit-msg 150-200ms on a small repo,
from Python startup plus staged volume. See [ADOPTION.md](ADOPTION.md) for behavior and
rollback. Local checks do not prove recommendation quality, source rights or runtime
safety.
