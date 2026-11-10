# Current state

Owner-reported dining/onboarding repairs are implemented and verified for another
CLI test. Live map discovery now completes (D-019): the client deadline matches the
measured endpoint, same-area repeats are served from a 10-minute cache and cooldowns
no longer drop cards. Telegram taps remain unverified. T9a/T9b pass. Updated 2026-11-10.

## Works

- Product spec, architecture, source ladders, demo spine, decisions, idea register.
- Standards kit adopted; commit-message and pre-commit hooks active.
- `spoon_candidates` and `spoon_verify_hours`: finalist checks, selected refresh, sourced call links.
- `spoon_evaluate`, `spoon_ledger` and `/why`: all ten gates, explicit failures/unknowns, full paging.
- 229 local tests pass plus one host-only skip; Ruff passes. 225 passed on Hermes 3.14.9
  before the D-019 changes; the host rerun is pending.
- Live Shibuya discovery returns 853 venues in about 38 s; a second cuisine in the same
  area answers from cache with no new map query (T12b).
- [Live probe](docs/data-gate.md): three venue attempts, two prose-hours extracts, selected recheck.
- Real Hermes doctor/validate pass with twelve tools/three hooks; profiles, upload and roots removed.
- `spoon_recommend` / `spoon_select`: provisional cards, call guidance, empty slots and stale-choice guards.
- Private outing memory expires; opted-in tastes persist with view/correct/delete controls.
- Private-session identity reconnects saved tastes; shared contexts are denied.
- Selectable six-choice onboarding completes in the real CLI; explicit food requests skip the welcome.
- Saved family/coworker/friend groups require confirmed attendance per search; sensitive-save consent.
- Typed age/diet/outing rules, hard vetoes and explicit provisional warnings.
- Japan/Thailand/Indonesia and NYC/SF ladders; reviewed future-city sources use the same review path.
- Branch-matched editorial and comparable crowd evidence can break taste ties; cards retain sources.
- Live NYC/SF discovery passes; SF needed a later attempt after upstream failures.

## Known from the test host (2026-11-08)

- Hermes 2026.9.24 stable, git install; `plugins validate`, `plugins doctor`,
  `profile create` and `profile delete` available.
- Enabled toolsets: web, browser, vision, tts. Disabled: stt.
- Bundled `a2a` agent-to-agent plugin present but not enabled.
- Catalog search shows no dining or restaurant-recommendation plugin.
- Runtime 2bd378ed1b8d, Python 3.14.9; isolated test registered twelve tools and three hooks.

## Unverified (see TRACKER V-rows)

- Telegram: `/why` delivery, telephone-link taps, images, expandable quotes, `ask_choice` buttons.
- Free tiers for Google Places and HotPepper Gourmet; Tabelog terms.
- Pristine minimum-version compatibility and Telegram delivery of the new tool.
- Sustained recommendation quality and complete venue coverage during upstream outages.

## Next action

T12: owner retest of the repaired CLI flow with the D-019 discovery changes, after a
Hermes host test rerun; Telegram channel verification remains V2.
No release or catalog submission.

## Deadline

Submission 2026-11-11 17:00 EST. The catalog PR should be open by the evening of
2026-11-10.
