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

## D-016: Bounded locale scout through existing host search (2026-11-08)

- Decision: use the already-configured Hermes search for at most two searches per
  locale scout request, including its existing provider allowance if applicable.
- Why: T9 needs attributed local-source discovery without adding an account or provider.
- Alternative: manual proposals using only user-supplied source evidence.
- Limits: city/country queries only; no new subscription, key, provider configuration,
  source-page fetch or paid venue API. Confirmation saves guidance, not access rights.

## D-017: City ladders and shared review influence (2026-11-09)

- Decision: add researched New York City and San Francisco source priorities and connect
  attributed review evidence to recommendations for all cities, including future reviewed
  ladders. The owner approved implementation, verification and then GitHub publication.
- Why: source names alone do not influence the current taste/distance ranking.
- Invariants: hard gates and supported tastes take precedence; exact branch matching,
  source attribution and explicit gaps; no cross-platform score averaging or invented
  review sentiment. Source lists never enable direct extraction, accounts or paid APIs.
- Alternative: city data only, which would not deliver the requested quality influence.
- Boundaries: local pilot, existing host search allowance, no live-profile changes;
  independent Telegram/model testing remains separate from isolated runtime validation.

- Implementation policy: up to six public-venue searches per recommendation batch, with
  explicit city/country and existing provider allowance; private tastes never enter queries.
  Editorial signals use explicit recommendation labels; same-source crowd scores require
  explicit scale/count and comparable coverage. Unknown dates remain provisional; dates
  older than one year or in the future cannot influence ranking. Missing evidence falls
  back to taste/distance. These conservative defaults need live usability evaluation.

## D-018: Complete owner-tested dining and onboarding flows (2026-11-10)

- Owner authorized finishing the reported failures before another testing round.
- Decision: one dining tool owns discovery through saved explanation and delivered
  cards; optional source scouting never blocks a meal. Bounded, attributed web
  recovery shares the same gates and ledger. Current food intent outranks unrelated
  saved tastes; known same-brand branches do not fill separate slots. Wildcard may
  be a third distinct requested-cuisine option instead of requiring another cuisine.
- Onboarding uses a single controller with native choices, consistent 1/2 labels,
  Skip/Back/Find food now, tolerant fallback and atomic saving. Explicit meal requests
  do not trigger a welcome menu. Current time and explicit/pinned location remain
  the owner's established defaults.
- Alternative rejected: additional instructions around independent optional tools,
  which cannot ensure the ledger, reviews or all cards actually get produced.
- Limits: local pilot, public free data, existing host model/search allowances, no
  account creation or live-profile changes. Ride links open services; no unsupported
  destination-prefill claim. Real model/surface behavior must be checked separately
  from deterministic tests and plugin installation.

## D-019: Discovery latency and repeat-request consistency (2026-11-10)

- Owner reported inconsistent performance. Measured cause: the shared Overpass
  endpoint answered the 1.6 km restaurant query in 33 to 38 seconds whatever the
  query shape (bbox, node-only, smaller radius, mirrors), while the client deadline
  was 15 seconds. Every live search therefore failed into web recovery, which is
  slower and rarely yields three options. A second request within ten seconds also
  returned no cards because the discovery and verification cooldowns failed closed.
- Decision: wait for the endpoint (45 s client, 30 s server deadline) and reuse the
  covering result for the same 100 m cell for 10 minutes, recentered on the exact
  origin. Cooldowns pause briefly instead of failing; concurrent callers wait for the
  running pass. The map query runs beside the web pass; finalist pages are read side
  by side. On a map outage with nothing mapped, one seeded web pass follows.
- Alternatives rejected: Overpass mirrors (all slower or down on the measurement
  day); shorter deadlines with more recovery logic (treats the symptom and sends more
  model/search work for worse results); a dedicated Overpass instance (needs an
  account or hosting, outside the free-source pilot; revisit at T13).
- Limits: the cache is in-process and public venue data only; retrieval times stay
  truthful, so cached venues age out of the 15-minute evidence window on their own.
  A slow endpoint still costs up to 45 seconds on a cold cell.


## D-020: Source-led dining and portable replies (2026-11-10)

- Owner approved replacing map-dependent admission after hands-on testing. The host
  agent researches through its available search/read/browser tools in short steps;
  Spoonmaster retains attributed evidence and comparisons, optional tastes and controls.
- `spoon_dine` starts/replaces a request, `spoon_research` invokes allowlisted public
  host tools, and `spoon_present` validates retained quotes/URLs and renders the reply.
  Maps support location/navigation; area searches need no coordinates. Exact distance,
  branch identity, opening times and hard needs still require relevant evidence.
- Model judgment interprets sources and ranks fit. Code does not certify semantic
  truth merely because a quote matches. Current facts, independent quality evidence,
  inference and missing information must remain distinct. No cross-platform averaging.
- Native host transcription feeds the same natural-language workflow. No voice
  service is installed or enabled. CLI voice setup is not an owner acceptance duty.
- Meaningful progress and steering occur between short host calls. A host that queues
  input cannot be promised immediate interruption. Explicit cancellation clears work;
  the model applies changed intent through a replacement request (D-021). Retained
  results are process-local, bounded and expire after 30m.
- Source lesson: Asia travel repo `cd061a2`, location/maps and family-profile workflows;
  Yuki canon `411b6d7`, June restaurant-triage lesson. Application: source-led dining,
  actionable portable replies and progressive preferences. Expected benefit: preserve
  useful alternatives during map outages and improve situational relevance. Private
  memories were inspected only; no private trip material or source writeback is included.
- Supersedes D-018/D-019 as the primary dining path. Low-level map tools remain for
  explicit spatial investigation. No new accounts, paid provider or permission bypass.

## D-021: One source-led path with research fan-out (2026-11-10)

- Owner approved T12d from the reviewed v2 proposal, including preserved reusable
  city source lists. Three independent host searches/reads may run in one call;
  browser operations remain ordered per conversation. Each worker copies runtime
  context and forwards host context. Errors are isolated per entry.
- Reserve IDs and call allowance under a short lock, dispatch outside it, then
  reject stale results on replacement/cancellation. Keep 12 calls and 30-minute
  expiry; elapsed time guides the model rather than silently blocking research.
- Index public citation URLs before clipping excerpts. Structured source/excerpt
  pairs are best-effort information, not an additional citation admission rule.
- Code recognizes a short exact cancellation list. The model interprets new cities
  and constraints through spoon_dine; hooks do not parse dining intent.
  Native terminal redirection bypasses pre_llm_call on the verified host revision.
  The existing spoon_dine tool therefore also accepts action=cancel plus request_id;
  the model calls it before acknowledging mid-turn cancellation. Stale cancellation
  IDs cannot clear a replacement. This preserves four hooks and avoids intent parsing.
- Migrate companions to the current request with reviewed party confirmation,
  selected-member needs and revision checks. Keep source-list review/edit through
  a surviving tool and private controls. Remove obsolete map pipeline and parsers,
  leaving eight tools and four hooks. T13/T14 retain their existing scope.
- Verify native host fan-out, isolation and five matched city comparisons before
  owner handoff. Report measured latency and quality, not an assumed speedup.

## D-022: Better discovery with reusable sources and less repeated context (2026-11-10)

- Owner approved automatic unfamiliar-city/cuisine source discovery, broad candidate
  discovery including chains, follow-up of promising alternatives and useful delay
  explanations. These remain model judgments, not restaurant admission gates.
- Return only relevant source guidance. Structured search responses show labelled
  previews up to 2,400 characters per source within the existing 16k response allowance;
  detailed reads retain 16k. Full-response URL indexing and internal source pairs remain.
  Do not repeat source excerpts in multiple response fields. Read originals when needed.
- Optional indexed citations and concise optional candidate fields reduce repeated
  answer preparation without removing quote validation, output fields or /why.
- A direct one-time local city-source opt-in permits automatic public-source list
  updates with receipts. Off stops updates; lists remain readable/removable. Stale lists
  remain leads requiring research refresh. Whole-profile deletion removes the opt-in.
- Probe host memory only through public enabled-plugin detection; the model may inspect
  exposed memory tools and offer their actual destination/scope. Local consent never
  authorizes host-memory writes. No custom backend, synchronization or cross-agent claims.
- Verify proportionately: focused behavior/privacy checks, required project/native gates
  and one long mixed-city replay. Do not repeat the whole earlier acceptance exercise.

## D-023: Native browser execution with passive evidence capture (2026-11-11)

- Owner approved the catalog-review fix, investigation and integration of the reviewer's
  post-tool hook suggestion, publication, re-pin and reviewer reply.
- Remove browser execution from direct research dispatch. Keep only read-only search
  and extraction proxies; disclose their direct-dispatch permission boundary accurately.
- The model calls native browser_exec through Hermes's normal guards. A passive pre-tool
  observer binds a named request session, call/turn/task IDs and confirmed company;
  post_tool_call retains only matching successful text. Neither hook returns directives.
  A collect-only research mode exposes evidence IDs without invoking any host tool.
- Keep request ownership, expiry, replacement, reset, shared operation allowance and
  citation checks. Discard blocked, failed, stale, mismatched and duplicate results.
- Alternatives: remove browser evidence entirely, or capture every browser result
  without pre-call binding. The latter cannot reliably reject in-flight stale work.
- Limits: supported text results only, no image capture or proof of source truth/privacy.
  Missing host fields fail closed. No browser provider setup or live-profile upgrade.
  The optional non-dining prompt optimization remains separate.
