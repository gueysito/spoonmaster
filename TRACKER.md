# Tracker

The single task authority. Status: `done`, `next`, `in progress`, `planned`, `blocked`, `cut`.
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
| T1 | Progressive hours verification | Attempt hours verification for every displayed finalist (up to three); retain source and retrieval time; distinguish confirmed/unknown/conflicting evidence; recheck the selected venue when missing, conflicting or stale. If hours remain unavailable, explain and encourage calling with a sourced tappable phone number when available. | 2 | done | D-013; `spoon_verify_hours`, 42 tests on Python 3.11/3.13 and Hermes 3.14.9, Ruff/standards, doctor/validate pass; cleanup verified. [Live three-venue probe](docs/history/data-gate.md) retains prose hours as unknown and produces a sourced selected-venue call link. Core checkpoint `2ecf786`; T4/T5 enforce the sequence in cards; Telegram taps remain V2. |
| T2 | Plugin scaffold, Ruff, mock-ctx tests | `plugin.yaml` and `__init__.py` load; unit tests pass; Ruff clean | 2 | done | `spoon_candidates`, directory-entrypoint test, 20 unit tests and Ruff pass on Python 3.13/3.14. Real-host verification is recorded in T3. |
| T3 | Throwaway profile scripts (up, down) | Profile created, plugin loads, `doctor` and `validate` pass, teardown leaves nothing (listed) | 1 | done | `scripts/check-hermes.py`: named isolated profile created, plugin enabled; doctor --ci, validate --install-deps and 20 tests pass on runtime 2bd378ed1b8d / Python 3.14.9. Profile, copied files, scratch roots, upload and aliases independently confirmed absent. |

## Phase 2: Spine (2026-11-09)

| ID | Task | Acceptance | Est | Status | Evidence |
|---|---|---|---|---|---|
| T4 | Gates and reject ledger | Every gate returns pass/fail/unknown with reason; `/why` lists eliminations | 3 | done | Core `8146381`; four tools, `/why` and two cleanup hooks. 64 tests pass on Python 3.11/3.13 and real Hermes 3.14.9; doctor/validate, Ruff/standards and cleanup pass. Tests cover cross-chat/registration isolation, expiry, midnight/DST and complete paging; [replay](docs/history/data-gate.md) evaluates 20 and explicitly leaves 833 unevaluated. Source gaps remain unknown. |
| T5 | Card renderer and pick/runner-up/wildcard | All required fields or explicit unknowns; no padded slots | 2 | done | Core `9b24839`; D-014 provisional cards, enforced finalist/selected verification, empty slots and revision-checked private selection. 84 tests pass on Python 3.11/3.13 and real Hermes 3.14.9; six tools/two hooks, doctor/validate, Ruff/standards and independent cleanup pass. Prices, ETA, dishes and personal taste remain explicit unknowns. |
| T6 | Taste store, scopes, feedback, diff | Diff accurate; unrelated prefs unchanged; view/correct/delete work | 3 | done | Core `4ceae78`; opt-in per-person SQLite tastes, exact diffs, controls, automatic private-session reconnection and supported cuisine/venue ranking. 103 tests pass locally on Python 3.11/3.13 plus the host-only identity test: all 104 pass on Hermes 3.14.9. Eight tools/three hooks; doctor/validate, Ruff/standards and cleanup pass. Deletion clears cached taste explanations even after binding eviction or another-process deletion. |
| T7 | Optional onboarding with pairwise picks | First conversation offers onboarding or immediate search; skipping never blocks search; one brief reminder after the first venue choice offers later onboarding; 5 to 8 picks seed the profile; text fallback works | 2 | done | Core `5ce47ba`; six optional choices, atomic seeding, direct later-onboarding entry, button/text fallback and one-time selected-venue reminder wired to the host. 123 local tests pass on Python 3.11/3.13 and all 124 on Hermes 3.14.9; doctor/validate, Ruff/standards and independent cleanup pass. Tests cover failed-save rollback, profile-isolated drafts and reconnection; live model/Telegram presentation remains unverified (V2). |
| T8 | Dining companions and household rules | Ages, diet, transport mode enforced as typed constraints; reusable family/coworker/friend profiles with explicit saving consent and confirmed party per outing; unrelated outings exclude companion context; unknown requirements remain provisional with warnings | 4 | done | Core `bc05b45`; D-015 expanded scope (2h reforecast to 4h). Private groups, reviewed save/use consent, selected members/rules, scoped ranking and hard-conflict gates; 151 local tests pass on Python 3.11/3.13 and all 152 on Hermes 3.14.9. Nine tools/three hooks, doctor/validate, Ruff/standards and independent cleanup pass. Actual-entrypoint and mutation checks cover isolation/deletion; live model/Telegram presentation remains unverified. |
| T9 | Tokyo ladder and locale scout | Japan ladder loads from data; scout proposes a ladder for an unknown city | 2 | done | Core `8d42640`; Japan/Thailand/Indonesia JSON ladders and two-query host scout under D-016, with direct confirmation, private city cache and unchanged access permissions. 167 local tests pass on Python 3.11/3.13 and all 168 on Hermes 3.14.9; ten tools/three hooks, doctor/validate, Ruff/standards and independent cleanup pass. Registered flow and installed search schema verified; live provider/model/Telegram orchestration remains unverified. |

## Approved expansion (2026-11-09)

Owner approved NYC/SF plus shared review influence before hands-on testing and GitHub publication.
Local-pilot exposure; estimate 6 hours total, reforecast before exceeding 12 hours.

| ID | Task | Acceptance | Est | Status | Evidence |
|---|---|---|---|---|---|
| T9a | NYC/SF city ladders and U.S. basics | City aliases select distinct sources; other U.S. cities remain scouted; sourced U.S. phone links and both time zones work | 1 | done | City/phone/time-zone regressions plus existing locale/discovery checks pass. No new website access or account. |
| T9b | Shared attributed review influence | Branch-matched permitted evidence affects otherwise comparable picks across bundled and confirmed future-city ladders; taste/vetoes win; cards/ledger retain attribution and honest gaps; isolated host verification passes | 5 | done | D-017; 190 tests run locally (one host-only skip), all 190 pass on Hermes 3.14.9. Ruff/standards, doctor/validate and scanner pass; isolated root/profile/upload/alias cleanup independently verified. Changed-code/security/bounded-work review passed; mutation checks prove pick influence and publisher deduplication regressions detect removal. Live NYC discovery returned 111 venues (66 street addresses); Live SF discovery returned 116 venues (95 street addresses) after two upstream HTTP/availability failures and operator-guidance review. Live host-provider/model/Telegram quality remains T12. |

## Phase 3: Closer, hardening, submission (2026-11-10)

| ID | Task | Acceptance | Est | Status | Evidence |
|---|---|---|---|---|---|
| T10 | Merge profiles (spike `a2a`, else share card) | Merged pick never violates a hard veto; explains fit per person | 3 | planned | After hands-on spine testing. |
| T11 | Order card | Top dishes with evidence counts; local text; no safety promises | 2 | planned | |
| T12 | Fresh install, failure cases, privacy controls | PRD section 9 checks pass on a clean profile | 8 | in progress | Reforecast for owner-approved D-018 repairs. Dining transaction, bounded web/map recovery, meal relevance, distinct brands, saved explanations, selectable onboarding, ride links and canonical delivery implemented. 219 tests run locally (one host-only skip). Live native six-choice onboarding completes and saves; same-session `/why` returns the real ledger even on source failure. Tokyo returns three distinct options. Follow-up fixes cover footprint bounds, cross-city crowd baseline, immediate duplicate-call reuse and safe geocoder limits. Code `49d02ed`: all 219 tests pass on Hermes 3.14.9; doctor/validate/scanner pass with 12 tools and 3 hooks. Bali outage recovery returns a Korean BBQ option with Maps/Grab/Gojek links. Both test profiles and roots are independently verified absent. Owner-reported repairs are complete for CLI retest; Telegram V2 and remaining release checks stay separate. |
| T12b | Discovery latency and repeat-request consistency | Live same-area search returns map candidates; a second cuisine seconds later still gets cards; no cooldown error paths; timeouts classified | 2 | done | D-019. Client/server deadlines 45/30 s from measured 33 to 38 s responses; 10-minute recentered area cache; waiting cooldowns and locks; map query beside the web pass; parallel finalist page reads; 504/socket timeouts report `source_timeout`. 230 local tests pass (one host-only skip), Ruff/standards/diff-check pass. Live Shibuya: first discovery 37.8 s with 853 venues (failed at 15 s before), second cuisine 0.0 s from cache. Hermes host rerun pending. |
| T13 | README disclosures and catalog entry draft | Disclose host delegation, storage and capabilities; match the catalog entry to the release commit | 1 | done | README disclosures and catalog entry prepared against the public release. The source-led runtime has no direct Overpass backend. |
| T14 | Security review at the public boundary | Owner chooses run, later or decline | 1 | planned | |
| T15 | Public visibility, license, catalog PR | Owner approval for each | 1 | done | Public MIT release; [catalog PR #153203](https://github.com/NousResearch/hermes-agent/pull/153203) opened. Maintainer admission awaits T13b. |
| T16 | Demo video, X post, submission form | Owner records, posts and submits | 2 | done | Owner confirmed demo and form submission on 2026-11-11. |
| T13b | Catalog browser permission fix | No browser proxy; native guarded execution with request-bound post-tool evidence; regression/native checks; corrected disclosures and catalog pin | 2 | done | D-023; published `4ef303a`, catalog commit `77f897f`, [reviewer reply](https://github.com/NousResearch/hermes-agent/pull/153203#issuecomment-6812561666). 124 local tests (two host-only skips), all 124 native tests, doctor/validate/scanner, Ruff/standards/diff and catalog validation pass; synthetic native hook-to-citation/blocked-result checks and cleanup verified. Maintainer admission remains pending. |

T13b live verification (2026-11-11): the published runtime passed a one-page native
agent test against `https://www.ichiranusa.com/`: one real browser call (7.9s), exact
output captured as `e1`, quoted branch/ramen evidence accepted by `spoon_present`, and
a provisional ICHIRAN Brooklyn recommendation delivered with source/Maps links.
No search/extraction fallback or terminal call; unknown hours/prices/independent quality
remained explicit. With browser/terminal disabled, neither tool was exposed, the native
bridge refused browser execution, single/mixed-batch proxies were rejected, and collection
returned no evidence with all 12 operations remaining. Test profile and upload cleanup
verified. Runtime unchanged from `4ef303a`; image/other-backend testing remains separate.

## Verification rows

T12 owner retest correction (2026-11-10): raw `/spoon profile` output now has a human
summary while export/tool data remain unchanged. City-only origins are rejected;
Photon English-name selection fixes reproduced Japanese-name mapping failures, and
map waits are reduced. Code `e6a28a8`: 222 tests pass on isolated Hermes with doctor/validate; local suite
has one host-only skip. Installed in the retained owner test profile with identical
taste-database checksum; readable profile and immediate city clarification verified
in the native terminal. A subsequent replay exposed unmapped web-only discoveries;
bounded map-led recovery now targets the existing second web query without accepting
map-name-only evidence. Local suite: 224 tests with one host-only skip. Final meal
replay recovered one independently mapped and source-backed Shibuya tonkatsu option
despite the primary map-service error (22.6-second dining call); hours remained
unconfirmed and empty slots stayed explicit. Exact-name matches now survive model
omission/failure. Code `d33a18d`: all 225 tests pass on Hermes 3.14.9, doctor/validate
and scanner pass, isolated root cleanup verified. Installed in the retained test
profile; saved tastes unchanged. Local suite has one host-only skip.

| ID | Question | How | Status |
|---|---|---|---|
| V1 | Can a plugin send images in Telegram? | Throwaway bot or final check | planned |
| V2 | Do Telegram expandable quotes, `ask_choice` buttons and `tel:` links work? | Channel check; visible phone number remains the portable fallback | planned |
| V3 | SemVer value for `requires_hermes` | [v2026.9.24 package metadata](https://github.com/NousResearch/hermes-agent/blob/v2026.9.24/pyproject.toml): 0.21.5; manifest declares >=0.21.5. Installed-runtime compatibility passed T3; a pristine minimum-version matrix was not run. | done |
| V4 | Free tiers for Google Places and HotPepper | Official pricing and terms pages | planned |
| V5 | Tabelog terms on automated access | Official terms | planned |
| V6 | Host web tool names for `dispatch_tool` | `web_search` with `query` and `limit` verified from the installed schema; public dispatcher/response contract inspected at 2bd378ed1b8d. Live provider call remains unverified. | done |
| V7 | `a2a` between two private installs | Spike in T10 | planned |


## Owner-approved experience replacement (D-020)

| ID | Task | Acceptance | Est | Status | Evidence |
|---|---|---|---|---|---|
| T12c | Source-led research and readable dining experience | Web-supported restaurants survive map failure; native host research tools; retained source comparison; meaningful progress and replacement requests; area locations; readable controls; relevant free-form tastes and host-transcribed input; independent live-city checks before owner handoff | 6 | done | 249 tests run locally with one host-only skip; all 249 pass on Hermes 3.14.9. Ruff/standards/diff checks, doctor/validate pass with 14 tools and four hooks. Live Tokyo/Canggu/SF/NYC/El Paso comparisons produce distinct alternatives without map admission. Native terminal verifies readable profile/enable, source-backed alternatives, restored Maps links, same-session /why and child/mild-food steering during research. Retained test profile adopted with exact code hashes and unchanged taste DB checksum; connection returns TEST_READY. Disposable profile/root cleanup independently verified. |

T12c verification detail (2026-11-10): Tokyo excludes a documented closed venue;
SF distinguishes Chubby Noodle's current address from older branch reviews; NYC
connects bright/tangy preferences to actual dishes and flags atmosphere tradeoffs.
El Paso retains four compared places, shows three distinct businesses and incorporates
a child/mild-food update received during research. `/why` preserves that update.
Observed final runs take roughly two to three minutes including model synthesis.
CLI delivery queued timed notices until the answer ended, so the timer worker was
removed; real model updates between research calls remain. The obsolete worker
test was replaced by a regression for repeated URLs in `/why`. A scoped final-output
hook restores omitted Maps links without holding streaming or changing other turns.

Changed-boundary review: session isolation, expiry/reset/replacement, profile changes,
bounded arguments/evidence/calls, source-text handling and host-tool allowlisting
checked. Existing consent and local taste ownership remain; no new credentials,
providers, dependencies, payments, public ingress or core patches. Quote matching
does not certify source meaning; live reviews cover that separate model responsibility.
This is local-pilot verification, not the broad public-boundary audit at T14.
Native audio ingestion and Telegram display still need their respective surfaces;
the owner does not need terminal audio setup. Browser delegation is implemented
but this isolated CLI exposed web search/extract, so browser execution is not claimed
as live-verified. The native launcher completed dependency bookkeeping on first use;
the verified Hermes source revision remained `2bd378ed1b8d`.

## Owner-approved source-led consolidation (D-021)

| ID | Task | Acceptance | Est | Status | Evidence |
|---|---|---|---|---|---|
| T12d | Research fan-out and one source-led path | Three-entry context-preserving batches; narrow cancellation; full citation indexing; confirmed companions and reusable source lists; eight tools/four hooks; obsolete pipeline removed; native checks and matched five-city comparison | 6 | done | Runtime through `28bf417`; 108 tests locally (one host-only skip), all 108 on Hermes; Ruff, standards, doctor/validate and diff checks pass. Native steering, cancellation and selected-companion replacement pass; measurements below. Publication/adoption verified separately at handoff. |

Five-city comparison: baseline `5d9d31c`, candidate `7e40d80`, corrected SF replay
`97d745c`, same Hermes `2bd378ed1b8d` and configured gpt-6.1-sol. Times include CLI
startup and final answer; one matched sample each, not a statistical guarantee.

| City/request | Seconds before → after | Research calls before → after | Distinct businesses compared before → after | Pick source spot-check |
|---|---|---|---|---|
| Shibuya tonkatsu | 218.8 → 154.2 | 11 → 4 | 5 → 6 | Nagi → Genkatsu: food review plus menu/hours; dated review pricing identified |
| Canggu family lunch | 89.3 → 149.2 | 5 → 3 | 5 → 5 | Milk & Madu Berawa: independent food/family coverage and official branch facts |
| SF Marina noodles | 114.0 → 104.7 | 8 → 3 | 5 → 3 | Chubby → Hinodeya: current branch facts; older/other-branch praise distinguished; Chubby retained at Silver Cloud |
| Greenwich Village vegetarian | 150.6 → 132.4 | 11 → 4 | 5 → 6 | Ananda: vegetarian/tangy dishes supported; older quiet-lunch review does not guarantee quiet dinner |
| El Paso tacos near Redd/Westwind | 184.6 → 134.8 | 8 → 4 | 5 → 5 | El Beso → Elemi West Side: independent food coverage plus current branch menu/location |

Median 150.6 → 134.8 seconds (10.5% lower); Canggu became slower. Research round
trips fell 43 → 18, while actual research operations rose 43 → 51. Every final run
showed three distinct picks. Spot-checks compared material claims with retained
host source excerpts, not calls to venues. The first SF candidate took 129.5 seconds
and wrongly excluded Chubby using an old closed address. General current-operation
instructions fixed that replay; restaurant judgment still requires live evaluation.

Native acceptance: three-search batches returned separate evidence IDs; partial/error
and context isolation also pass threaded tests. Mid-research “ok” preserved work;
city and peanut-allergy updates replaced the request and reached final text and /why.
Terminal redirection bypasses the input hook, so the existing dine tool now accepts
request-scoped cancellation; the live “stop please” replay cleared /why. A synthetic
saved child's subset reached research only after confirmation; replacement returned
no confirmed party. Full-response indexing covers the reproduced 131-URL case.

Changed-boundary review (`5d9d31c` → `28bf417`, 2026-11-10/11): checked owner/session
isolation, consent, expiry/deletion/replacement, stale concurrent results, bounded
calls/inputs, tool allowlisting, untrusted source handling and sanitized errors.
Found and fixed party-expiry reuse, URL cutoff, redirect cancellation and obsolete
companion instructions. No unresolved findings in this scope; no new dependencies,
public endpoints, credentials, payments or uploads. The broad public audit remains T14.
Browser ordering is thread-tested, not live-provider verified; voice ingestion and
Telegram rendering need those surfaces. The owner need not set up terminal audio.
Earlier checkpoint detail remains in the incremental commits. Native validation
profiles were deleted with independent absence checks; owner testing uses its retained
profile and does not change live agents.

## Owner-approved research quality and context efficiency (D-022)

| ID | Task | Acceptance | Est | Status | Evidence |
|---|---|---|---|---|---|
| T12e | Source discovery, durable opt-in and lean evidence | Credible unfamiliar-city sources; broader alternatives; meaningful delay updates; relevant source guidance and nonduplicated previews; concise comparison; private opt-in city memory with advisory host-memory offer; focused checks and one long mixed-city replay | 4 | done | Runtime through `084d030`; 116 local tests (one host-only skip), native 115 plus final 13 locale tests, Ruff/standards/doctor/validate pass. Seven replay requests completed; eighth failed after compaction with provider HTTP 400. Owner accepted the recorded limitations and authorized publication/adoption; installation readiness is checked separately. |

One resumed CLI conversation completed seven requests: Tokyo sushi 154s (CLI-reported),
Tokyo tonkatsu 117.6s, Mexico City 120.9s, Canggu 169.0s, Rome 142.1s,
Paris 234.8s and El Paso tacos 162.3s (wall time including startup). Each retained
five comparisons, Paris six. Sources were saved after opt-in; the initial Tokyo
query-bearing URL rejection prompted the separately verified repair in `084d030`.
Replay runtime was `d91da3d`; no mid-replay plugin replacement or restaurant seeding.

The eighth request, El Paso Chinese, compacted context, independently discovered
China Town, then ended with provider HTTP 400 / Bad Request before presenting.
Its last four research responses were valid JSON without top-level plugin errors;
this does not prove the cause of the provider rejection. No successful final Chinese
comparison or PF Chang's coverage is claimed. The recorder's initial session-source
filter was corrected from local to oneshot without repeating the first request.

The first seven turns returned about 1.065M tool-response characters. Narrower source
guidance and deduplicated previews pass focused checks, but broader detailed research
still accumulates substantial context. The earlier owner chat is not a controlled
matched benchmark; these measurements do not establish a speedup. Closure, branch,
menu-price and hours uncertainty were explained during research. Host compaction and
provider latency remain unresolved. No automatic short-circuit was added to hide them.

Changed-boundary checks cover local consent, owner isolation, opt-out/deletion,
transaction rechecks, retained stale leads, source bounds and citation validation.
No new dependencies, endpoints, credentials or external memory writes. Native local
source opt-in worked; external memory destination/sharing remains advisory and needs
separate consent. T14's broad public audit and channel-specific tests remain separate.

Disposable validation/replay profiles, staging and upload were removed with independent
absence checks. The retained owner test profile was preserved and not upgraded.

Owner clarified acceptance: no repeated long replay or consistent-speed gate. The
recorded HTTP 400 remains unresolved, not an established plugin defect. Publish the
verified implementation and adopt it with bounded native installation/startup checks.
