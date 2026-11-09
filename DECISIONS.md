# Decisions

Owner decisions only, newest last. Each records the choice, why, the alternatives and
when to revisit. Agent recommendations are noted as such.

## D-001: Build a Hermes plugin (2026-11-08)

- Decision: a native Hermes plugin used through the owner's existing Hermes channels.
- Why: persistent taste state, deterministic gates, hooks, slash commands and typed
  model calls are things a prompt or skill cannot do; the catalog makes it installable.
- Alternatives: a skill (no state or enforcement), a separate Telegram bot (hosting,
  identity, abuse and cost duties), a standalone app (accounts, frontend, deployment), a
  new agent harness (Hermes already is one), the earlier video-editing plugin idea.
- Revisit: when a non-Hermes interface has demonstrated demand.

## D-002: Name: Spoonmaster (2026-11-08)

- Decision: Spoonmaster; slug `spoonmaster`.
- Why: no product, catalog entry or meaningful GitHub project found under the name.
- Alternatives: Forkmate (owner's first choice; collides with forkmate.ai, a live AI food
  tracker that also ships as an MCP server), Forkcast (several food-AI products), Palate
  Atlas (clean runner-up), Tablemate (unchecked), "Dining Companion" (working title).
- Limits: web, GitHub and catalog search only; no trademark search.

## D-003: One repository, private until submission, then public (2026-11-08)

- Decision: `gueysito/spoonmaster` holds spec, plan and code; it goes public at submission.
- Why: the catalog requires a public repository; one home avoids drift.
- Alternatives: a private ideation repo plus a public plugin repo.
- Consequence: everything committed must be safe to publish, including history.

## D-004: Recommendation shape: pick, runner-up, wildcard (2026-11-08)

- Decision: one decisive pick, a runner-up and a wildcard; price on every card;
  price-tier mode on request; empty slots stay empty.
- Why: leads with judgment; avoids forcing a weak or out-of-radius tier.
- Alternatives: cheap/mid/high-end tiers as the default (original brief).

## D-005: Free data only (2026-11-08)

- Decision: keyless baseline (OpenStreetMap, Open-Meteo, venue sites). Google Places and
  HotPepper Gourmet only if usable on a free tier.
- Why: anyone can install and run it; no surprise costs.
- Alternatives: paid APIs; scraping review platforms.

## D-006: Restricted sites through legitimate tiers only (2026-11-08)

- Decision: Tabelog-class sources via user-shared content, free licensed APIs, search
  snippets, or one disclosed page through the host's browser tool, off by default until
  terms are checked. Never bypass protection.
- Why: judges install on clean hosts; catalog review rejects undisclosed or abusive access.
- Alternatives: bundled scraping through a third-party crawler.

## D-007: Demo in Tokyo (2026-11-08)

- Why: the Japan ladder is the most field-tested; good OpenStreetMap coverage.

## D-008: Testing setup (2026-11-08)

- Decision: unit tests against a mock context on the development machine; integration in
  a throwaway profile on an existing Hermes host, files copied in, teardown verified.
- Why: least effort for the owner, no change to the live agent profile, no repo access
  needed on the host.
- Alternatives: install Hermes on the development machine; test in the live profile.
- Limits: the throwaway profile has no messaging bot, so Telegram-only behavior is
  checked separately or replaced by fallbacks.

## D-009: Voice is opt-in on existing setups only (2026-11-08)

- Decision: voice input works only when the agent already has speech-to-text; voice
  replies are roadmap. The plugin never configures voice services.

## D-010: Ideas live in an idea register (2026-11-08)

- Decision: [docs/idea-register.md](docs/idea-register.md) records every idea with status and
  reason; design detail lives in the spec. No conversation journals.
- Why: the owner's workflow standard; complete without being chatty.

## D-011: Standards kit adopted (2026-11-08)

- Decision: commit-message and pre-commit hooks now; Ruff format and lint with the first
  Python slice.

## D-012: Telegram-only features must reduce friction (2026-11-08)

- Decision: build a Telegram-specific behavior only when it lowers effort, always with a
  portable fallback. When unsure, present the owner's options.

## D-013: Progressive verification and call fallback (2026-11-08)

- Decision: attempt hours verification for every displayed finalist, up to three.
  Preserve source and retrieval time and distinguish confirmed, unknown and conflicting
  evidence. Refresh the selected venue when evidence is missing, conflicting or stale.
- Why: the owner approved focusing verification effort on actionable options after
  the OSM-only probe showed sparse hours coverage.
- If selected-venue hours remain unavailable, state that clearly and encourage calling.
  Provide a sourced phone number as a `tel:` hyperlink, with the visible number as a
  portable fallback. Never invent a number or place the call automatically.
- Alternatives: hours for most discovered venues (superseded T1 acceptance); checking
  hours only after selection (too late to help choose among the finalists).
- Limits: published hours do not guarantee availability or dietary safety. Arrival-time
  math remains T4. If a phone number is missing, unsafe or ambiguous, say so explicitly.
- Revisit: real source coverage, latency and channel link behavior provide new evidence.

## D-014: Provisional picks when hours are unknown (2026-11-08)

- Decision: show provisional picks with explicit uncertainty and call advice.
- Why: the owner chose this over leaving every slot empty until hours are confirmed.
- Limits: attempt verification before each displayed finalist, refresh the selected
  venue under D-013, retain unknown gate results, and never pad missing slots.
- Alternative: require confirmed hours before filling recommendation slots.
- Revisit: when better venue evidence changes practical coverage.

## D-015: Reusable companions with outing-specific application (2026-11-08)

- Decision: remember explicitly saved family, coworker and friend needs separately
  from the owner's tastes; confirm who is joining and which needs apply when referenced.
  Do not apply those records to every outing. Sensitive dietary saving requires consent.
- Why: the owner distinguished remembering companions from including them tonight.
- Decision: unverified household requirements may remain provisional with clear
  warnings; known hard conflicts exclude. Soft preferences do not become hard vetoes.
- Alternative: outing-only household data, which loses useful context between sessions.
- Limits: private local groups only; cross-agent sharing and merging remain T10.
