# Current state

Discovery and progressive hours verification run locally; recommendations and taste
learning do not exist yet. T1's revised acceptance passes. Updated 2026-11-08.

## Works

- Product spec, architecture, source ladders, demo spine, decisions, idea register.
- Standards kit adopted; commit-message and pre-commit hooks active.
- `spoon_candidates` and `spoon_verify_hours`: finalist checks, selected refresh, sourced call links.
- 42 tests pass on Python 3.11/3.13 and real Hermes Python 3.14.9; Ruff format/lint pass.
- [Live probe](docs/data-gate.md): three venue attempts, two prose-hours extracts, selected recheck.
- Real Hermes doctor/validate pass with two tools; profile, upload and temporary root removed.

## Known from the test host (2026-11-08)

- Hermes 2026.9.24 stable, git install; `plugins validate`, `plugins doctor`,
  `profile create` and `profile delete` available.
- Enabled toolsets: web, browser, vision, tts. Disabled: stt.
- Bundled `a2a` agent-to-agent plugin present but not enabled.
- Catalog search shows no dining or restaurant-recommendation plugin.
- Runtime 2bd378ed1b8d, Python 3.14.9; isolated test registered two tools and zero hooks.

## Unverified (see TRACKER V-rows)

- Telegram: telephone-link taps, plugin images, expandable quotes, `ask_choice` buttons.
- Free tiers for Google Places and HotPepper Gourmet; Tabelog terms.
- Pristine minimum-version compatibility and Telegram delivery of the new tool.

## Next action

T4: gates and reject ledger. Live prose hours remain unconfirmed; T4/T5 must enforce
verification in the recommendation/card pipeline. No release or catalog submission.

## Deadline

Submission 2026-11-11 17:00 EST. The catalog PR should be open by the evening of
2026-11-10.
