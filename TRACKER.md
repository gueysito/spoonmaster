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
| T1 | Data gate spike | For a Shibuya pin: real OSM candidates in radius, parsed hours for most, website evidence for some, honest unknowns | 2 | blocked | [Live probe](docs/data-gate.md): 853 candidates, 174 parsed weekly hours (20.4%); two venue pages add evidence. Majority-hours criterion remains unmet; source strategy/acceptance decision required. |
| T2 | Plugin scaffold, Ruff, mock-ctx tests | `plugin.yaml` and `__init__.py` load; unit tests pass; Ruff clean | 2 | done | `spoon_candidates`, directory-entrypoint mock test, 20 unit tests and Ruff pass. Real Hermes doctor/validate remain T3, not claimed by the mock test. |
| T3 | Throwaway profile scripts (up, down) | Profile created, plugin loads, `doctor` and `validate` pass, teardown leaves nothing (listed) | 1 | planned | |

## Phase 2: Spine (2026-11-09)

| ID | Task | Acceptance | Est | Status | Evidence |
|---|---|---|---|---|---|
| T4 | Gates and reject ledger | Every gate returns pass/fail/unknown with reason; `/why` lists eliminations | 3 | planned | |
| T5 | Card renderer and pick/runner-up/wildcard | All required fields or explicit unknowns; no padded slots | 2 | planned | |
| T6 | Taste store, scopes, feedback, diff | Diff accurate; unrelated prefs unchanged; view/correct/delete work | 3 | planned | |
| T7 | Onboarding with pairwise picks | 5 to 8 picks seed the profile; text fallback works | 2 | planned | |
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
| V2 | Do Telegram expandable quotes and `ask_choice` buttons render? | Same | planned |
| V3 | SemVer value for `requires_hermes` | [v2026.9.24 package metadata](https://github.com/NousResearch/hermes-agent/blob/v2026.9.24/pyproject.toml): 0.21.5; manifest declares >=0.21.5. Real-host compatibility remains T3. | done |
| V4 | Free tiers for Google Places and HotPepper | Official pricing and terms pages | planned |
| V5 | Tabelog terms on automated access | Official terms | planned |
| V6 | Host web tool names for `dispatch_tool` | Read-only listing on the test host | planned |
| V7 | `a2a` between two private installs | Spike in T10 | planned |
