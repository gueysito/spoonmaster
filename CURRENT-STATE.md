# Current state

Discovery, provisional recommendation cards, selected-venue rechecks and the reject
ledger run locally, with onboarding, persistent tastes and confirmed dining companions. T8 passes. Updated 2026-11-08.

## Works

- Product spec, architecture, source ladders, demo spine, decisions, idea register.
- Standards kit adopted; commit-message and pre-commit hooks active.
- `spoon_candidates` and `spoon_verify_hours`: finalist checks, selected refresh, sourced call links.
- `spoon_evaluate`, `spoon_ledger` and `/why`: all ten gates, explicit failures/unknowns, full paging.
- 151 local tests pass on Python 3.11/3.13; all 152 pass on Hermes 3.14.9; Ruff passes.
- [Live probe](docs/data-gate.md): three venue attempts, two prose-hours extracts, selected recheck.
- Real Hermes doctor/validate pass with nine tools/three hooks; profiles, upload and roots removed.
- `spoon_recommend` / `spoon_select`: provisional cards, call guidance, empty slots and stale-choice guards.
- Private outing memory expires; opted-in tastes persist with view/correct/delete controls.
- Private-session identity reconnects saved tastes; shared contexts are denied.
- First-use onboarding or immediate search; six optional picks and one later reminder.
- Saved family/coworker/friend groups require confirmed attendance per search; sensitive-save consent.
- Typed age/diet/outing rules, hard vetoes and explicit provisional warnings.

## Known from the test host (2026-11-08)

- Hermes 2026.9.24 stable, git install; `plugins validate`, `plugins doctor`,
  `profile create` and `profile delete` available.
- Enabled toolsets: web, browser, vision, tts. Disabled: stt.
- Bundled `a2a` agent-to-agent plugin present but not enabled.
- Catalog search shows no dining or restaurant-recommendation plugin.
- Runtime 2bd378ed1b8d, Python 3.14.9; isolated test registered nine tools and three hooks.

## Unverified (see TRACKER V-rows)

- Telegram: `/why` delivery, telephone-link taps, images, expandable quotes, `ask_choice` buttons.
- Free tiers for Google Places and HotPepper Gourmet; Tabelog terms.
- Pristine minimum-version compatibility and Telegram delivery of the new tool.

## Next action

T9: Tokyo source ladder as data and a locale scout for unknown cities.
No release or catalog submission.

## Deadline

Submission 2026-11-11 17:00 EST. The catalog PR should be open by the evening of
2026-11-10.
