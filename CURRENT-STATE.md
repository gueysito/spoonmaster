# Current state

Evidence-only discovery runs locally; recommendations and taste learning do not exist
yet. The OSM-only data gate failed hours coverage. Updated 2026-11-08.

## Works

- Product spec, architecture, source ladders, demo spine, decisions, idea register.
- Standards kit adopted; commit-message and pre-commit hooks active.
- `spoon_candidates` scaffold, bounded OSM discovery, conservative weekly-hours parser.
- 20 unit tests, including directory-package registration; Ruff 0.15.6 format/lint.
- [Shibuya live probe](docs/data-gate.md): 853 candidates, 174 parsed hours, two venue-page checks.
- Real Hermes doctor/validate and 20 tests pass in a throwaway profile; teardown verified.

## Known from the test host (2026-11-08)

- Hermes 2026.9.24 stable, git install; `plugins validate`, `plugins doctor`,
  `profile create` and `profile delete` available.
- Enabled toolsets: web, browser, vision, tts. Disabled: stt.
- Bundled `a2a` agent-to-agent plugin present but not enabled.
- Catalog search shows no dining or restaurant-recommendation plugin.
- Runtime 2bd378ed1b8d, Python 3.14.9; isolated test registered one tool and zero hooks.

## Unverified (see TRACKER V-rows)

- Telegram: plugin image sending, expandable quotes, `ask_choice` buttons in use.
- Free tiers for Google Places and HotPepper Gourmet; Tabelog terms.
- Pristine minimum-version compatibility and Telegram delivery of the new tool.

## Next action

T1: discuss source enrichment or an explicitly approved acceptance change; only 20.4%
of candidates have parsed weekly hours. T2 and T3 pass. No release or catalog submission.

## Deadline

Submission 2026-11-11 17:00 EST. The catalog PR should be open by the evening of
2026-11-10.
