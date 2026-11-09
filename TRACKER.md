# Tracker

The single task authority. Status: `done`, `next`, `planned`, `blocked`, `cut`.
Estimates are hours of build time; reforecast when a task passes twice its estimate.

**Stop rule:** if the spine (T1 to T9) does not work end to end by the night of
2026-11-09, T10 and T11 are cut and the remaining time goes to reliability.

## Phase 0: Repository

| ID | Task | Acceptance | Est | Status | Evidence |
|---|---|---|---|---|---|
| T0 | Repo, front door, spec, standards kit | Private repo exists; `check-standards.sh` passes | 1 | done | First commit |

## Phase 1: Data gate and scaffold (2026-11-08)

| ID | Task | Acceptance | Est | Status | Evidence |
|---|---|---|---|---|---|
| T1 | Progressive hours verification | Attempt hours verification for every displayed finalist (up to three); retain source and retrieval time; distinguish confirmed/unknown/conflicting evidence; recheck the selected venue when missing, conflicting or stale. If hours remain unavailable, explain and encourage calling with a sourced tappable phone number when available. | 2 | done | D-013; `spoon_verify_hours`, 42 tests on Python 3.11/3.13 and Hermes 3.14.9, Ruff/standards, doctor/validate pass; cleanup verified. [Live three-venue probe](docs/data-gate.md) retains prose hours as unknown and produces a sourced selected-venue call link. Core checkpoint `2ecf786`; T4/T5 enforce the sequence in cards; Telegram taps remain V2. |
| T2 | Plugin scaffold, Ruff, mock-ctx tests | `plugin.yaml` and `__init__.py` load; unit tests pass; Ruff clean | 2 | done | `spoon_candidates`, directory-entrypoint test, 20 unit tests and Ruff pass on Python 3.13/3.14. Real-host verification is recorded in T3. |
| T3 | Throwaway profile scripts (up, down) | Profile created, plugin loads, `doctor` and `validate` pass, teardown leaves nothing (listed) | 1 | done | `scripts/check-hermes.py`: named isolated profile created, plugin enabled; doctor --ci, validate --install-deps and 20 tests pass on runtime 2bd378ed1b8d / Python 3.14.9. Profile, copied files, scratch roots, upload and aliases independently confirmed absent. |

## Phase 2: Spine (2026-11-09)

| ID | Task | Acceptance | Est | Status | Evidence |
|---|---|---|---|---|---|
| T4 | Gates and reject ledger | Every gate returns pass/fail/unknown with reason; `/why` lists eliminations | 3 | done | Core `8146381`; four tools, `/why` and two cleanup hooks. 64 tests pass on Python 3.11/3.13 and real Hermes 3.14.9; doctor/validate, Ruff/standards and cleanup pass. Tests cover cross-chat/registration isolation, expiry, midnight/DST and complete paging; [replay](docs/data-gate.md) evaluates 20 and explicitly leaves 833 unevaluated. Source gaps remain unknown. |
| T5 | Card renderer and pick/runner-up/wildcard | All required fields or explicit unknowns; no padded slots | 2 | done | Core `9b24839`; D-014 provisional cards, enforced finalist/selected verification, empty slots and revision-checked private selection. 84 tests pass on Python 3.11/3.13 and real Hermes 3.14.9; six tools/two hooks, doctor/validate, Ruff/standards and independent cleanup pass. Prices, ETA, dishes and personal taste remain explicit unknowns. |
| T6 | Taste store, scopes, feedback, diff | Diff accurate; unrelated prefs unchanged; view/correct/delete work | 3 | done | Core `4ceae78`; opt-in per-person SQLite tastes, exact diffs, controls, automatic private-session reconnection and supported cuisine/venue ranking. 103 tests pass locally on Python 3.11/3.13 plus the host-only identity test: all 104 pass on Hermes 3.14.9. Eight tools/three hooks; doctor/validate, Ruff/standards and cleanup pass. Deletion clears cached taste explanations even after binding eviction or another-process deletion. |
| T7 | Optional onboarding with pairwise picks | First conversation offers onboarding or immediate search; skipping never blocks search; one brief reminder after the first venue choice offers later onboarding; 5 to 8 picks seed the profile; text fallback works | 2 | next | Owner specified the two-path first-use flow and later reminder on 2026-11-08; copy and entry points in PRD F8. Core flow now has six optional choices, atomic seeding, skip-without-tastes and one-time reminder claims; 14 focused tests pass. Host wiring and real-runtime verification remain next. |
| T8 | Household rules | Ages, diet, transport mode enforced as typed constraints | 2 | planned | |
| T9 | Tokyo ladder and locale scout | Japan ladder loads from data; scout proposes a ladder for an unknown city | 2 | planned | |

## Phase 3: Closer, hardening, submission (2026-11-10)

| ID | Task | Acceptance | Est | Status | Evidence |
|---|---|---|---|---|---|
| T10 | Merge profiles (spike `a2a`, else share card) | Merged pick never violates a hard veto; explains fit per person | 3 | planned | |
| T11 | Order card | Top dishes with evidence counts; local text; no safety promises | 2 | planned | |
| T12 | Fresh install, failure cases, privacy controls | PRD section 9 checks pass on a clean profile | 3 | planned | |
| T13 | README disclosures and catalog entry draft | Every host, stored item and capability listed | 1 | planned | Pilot network/privacy disclosures present. Resolve shared Overpass backend suitability before public release; [operator policy](https://dev.overpass-api.de/overpass-doc/en/preface/commons.html). |
| T14 | Security review at the public boundary | Owner chooses run, later or decline | 1 | planned | |
| T15 | Public visibility, license, catalog PR | Owner approval for each | 1 | blocked | Owner decision |
| T16 | Demo video, X post, hackathon form | Owner records, posts and submits | 2 | blocked | Owner action |

## Verification rows

| ID | Question | How | Status |
|---|---|---|---|
| V1 | Can a plugin send images in Telegram? | Throwaway bot or final check | planned |
| V2 | Do Telegram expandable quotes, `ask_choice` buttons and `tel:` links work? | Channel check; visible phone number remains the portable fallback | planned |
| V3 | SemVer value for `requires_hermes` | [v2026.9.24 package metadata](https://github.com/NousResearch/hermes-agent/blob/v2026.9.24/pyproject.toml): 0.21.5; manifest declares >=0.21.5. Installed-runtime compatibility passed T3; a pristine minimum-version matrix was not run. | done |
| V4 | Free tiers for Google Places and HotPepper | Official pricing and terms pages | planned |
| V5 | Tabelog terms on automated access | Official terms | planned |
| V6 | Host web tool names for `dispatch_tool` | Read-only listing on the test host | planned |
| V7 | `a2a` between two private installs | Spike in T10 | planned |
