# Current state

The catalog-review browser fix is published and re-pinned for maintainer review. Native execution
stays in Hermes's approval pipeline; Spoonmaster passively retains matching evidence.
The repository is public under MIT. Long-chat limitations remain documented.

## Current verification

- 124 local tests, two host-only skips; Ruff, standards and diff checks pass.
- All 124 native tests, doctor/validate and scanner pass; eight tools and six hooks.
- Native synthetic hook-to-citation flow passes; test profile/upload cleanup verified.
- Browser provider execution, image results and minimum-version behavior are unverified.
- Final source-URL repair: all 13 locale tests pass on Hermes.
- Seven replay requests completed with five or six retained comparisons each.
- Chinese discovery found China Town, but no final comparison was delivered.
- End-to-end latency improvement is not established; compaction still occurred.
- Measurements and limits: [TRACKER](TRACKER.md#owner-approved-research-quality-and-context-efficiency-d-022).

## Next action

Await maintainer re-review of [catalog PR #153203](https://github.com/NousResearch/hermes-agent/pull/153203),
pinned to `4ef303a`. The owner confirmed demo/form submission. The recorded provider
rejection is not a release gate.

## Boundaries

Model judgment interprets sources and ranks; code retains evidence and enforces
consent, bounded work and conversation isolation. Reusable city source lists remain.
T14 remains separate. No live-agent or retained owner-profile upgrade is included.
Voice ingestion, Telegram display and external host-memory writes are not live-verified.
