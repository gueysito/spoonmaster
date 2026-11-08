# Current state

Discovery, progressive hours checks and the reject ledger run locally; recommendation
cards and taste learning remain planned. T4 passes. Updated 2026-11-08.

## Works

- Product spec, architecture, source ladders, demo spine, decisions, idea register.
- Standards kit adopted; commit-message and pre-commit hooks active.
- `spoon_candidates` and `spoon_verify_hours`: finalist checks, selected refresh, sourced call links.
- `spoon_evaluate`, `spoon_ledger` and `/why`: all ten gates, explicit failures/unknowns, full paging.
- 64 tests pass on Python 3.11/3.13 and real Hermes Python 3.14.9; Ruff format/lint pass.
- [Live probe](docs/data-gate.md): three venue attempts, two prose-hours extracts, selected recheck.
- Real Hermes doctor/validate pass with four tools/two hooks; profiles, upload and roots removed.
- Private search/ledger memory is registration- and conversation-scoped, bounded and expiring.

## Known from the test host (2026-11-08)

- Hermes 2026.9.24 stable, git install; `plugins validate`, `plugins doctor`,
  `profile create` and `profile delete` available.
- Enabled toolsets: web, browser, vision, tts. Disabled: stt.
- Bundled `a2a` agent-to-agent plugin present but not enabled.
- Catalog search shows no dining or restaurant-recommendation plugin.
- Runtime 2bd378ed1b8d, Python 3.14.9; isolated test registered four tools and two hooks.

## Unverified (see TRACKER V-rows)

- Telegram: `/why` delivery, telephone-link taps, images, expandable quotes, `ask_choice` buttons.
- Free tiers for Google Places and HotPepper Gourmet; Tabelog terms.
- Pristine minimum-version compatibility and Telegram delivery of the new tool.

## Next action

T5: recommendation cards and pick/runner-up/wildcard. Source gaps, including date-specific
availability, remain unknown. No release or catalog submission.

## Deadline

Submission 2026-11-11 17:00 EST. The catalog PR should be open by the evening of
2026-11-10.
