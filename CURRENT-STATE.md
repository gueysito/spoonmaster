# Current state

Nothing is installable yet: the repo holds the spec, architecture, source ladders and
plan, and no plugin code exists. Updated 2026-11-08.

## Works

- Product spec, architecture, source ladders, demo spine, decisions, idea register.
- Standards kit adopted; commit-message and pre-commit hooks active.

## Known from the test host (read-only check, 2026-11-08)

- Hermes 2026.9.24 stable, git install; `plugins validate`, `plugins doctor`,
  `profile create` and `profile delete` available.
- Enabled toolsets: web, browser, vision, tts. Disabled: stt.
- Bundled `a2a` agent-to-agent plugin present but not enabled.
- Catalog search shows no dining or restaurant-recommendation plugin.

## Unverified (see TRACKER V-rows)

- Telegram: plugin image sending, expandable quotes, `ask_choice` buttons in use.
- The SemVer release to declare in `requires_hermes`.
- Free tiers for Google Places and HotPepper Gourmet; Tabelog terms.

## Next action

T1 data gate: real OpenStreetMap candidates, hours and website evidence around a
Shibuya pin, plus the T2 plugin scaffold loading in a throwaway profile.

## Deadline

Submission 2026-11-11 17:00 EST. The catalog PR should be open by the evening of
2026-11-10.
