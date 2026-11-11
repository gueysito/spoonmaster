# Source-led architecture

D-020/D-021 define the current local pilot. [Historical design](history/architecture-map-first.md)
records the retired implementation; it is not implementation guidance.

## Runtime path

User request → `spoon_dine` → batched `spoon_research` → `spoon_present` → normal reply.
The model chooses queries, interprets evidence and ranks restaurants. Code owns
conversation scope, evidence retention, consent, bounded calls and presentation.
A city or neighborhood is enough. Current UTC is supplied unless the user specifies
a different time. The model converts to the destination's local time.

## Public host surfaces

Eight tools: `spoon_dine`, `spoon_research`, `spoon_present`, `spoon_ledger`,
`spoon_onboard`, `spoon_profile`, `spoon_feedback`, `spoon_companions`.
Commands: `/spoon` and `/why`. Four hooks: `pre_llm_call`, `on_session_reset`,
`on_session_finalize`, `transform_llm_output`. No core patches or private dispatch APIs.
`ctx.dispatch_tool` invokes installed research/search/read/browser tools subject to
host permissions, provider allowance and access restrictions. No provider is installed.

## Research and concurrency

A request retains a random ID, owner scope, current tastes, user-stated meal/location,
evidence and the actual comparison. It expires after 30 minutes; at most 100 requests
remain per registration. Replacement drops the previous request. Terminal redirects can
bypass the input hook, so the model also uses spoon_dine action=cancel with the active
request_id before acknowledging cancellation. Stale IDs cannot cancel newer requests.
Explicit cancel phrases
clear it; other intent is interpreted by the model through a replacement `spoon_dine`.
The input hook does not classify cities, allergies or arbitrary free text.

A research call accepts either one tool/JSON argument pair or a batch of up to three.
All entries are validated before dispatch. Under a short reentrant lock, each admitted
entry reserves a unique evidence ID and one of 12 available operations. Entries beyond
the remaining allowance get a budget result. Network work happens outside that lock.
Independent operations run in a thread pool. Every worker gets its own copied contextvars
and the forwarded host context; PluginContext owns registry scope. Browser entries run
in emission order in one worker and share a per-session lock across overlapping batches.
Unused browser locks are removed after the last caller returns.

Exceptions and structured host errors produce per-entry failures, with no retained
citation evidence or private provider exception text. Successful siblings survive.
After workers finish, the lock protects the current-request and companion checks before
storage. Replacement, cancellation or changed company discards the stale batch.
Host timeouts remain host-owned; elapsed time is guidance, not a 75-second cutoff.

Each successful result retains a 16,000-character excerpt, public URLs indexed
before clipping, best-effort source/excerpt pairs and retrieval time. Pairings are
informational. Present requires a retained quote and URL but does not certify semantic
truth or correspondence between them. Citation URL acceptance grants no fetch permission.
The model must reconcile branches, distinguish independent praise from marketing and
check published hours for the actual date/time. Unknowns remain visible. Known closures,
constraint conflicts and duplicate brands cannot fill the three displayed positions.
All compared/rejected candidates remain available through `/why`.

## Private memory and companions

`TasteService` derives identity from verified private host context. SQLite lives under
`ctx.state.data_dir`, never the install directory. Explicit opt-in controls taste learning;
revision checks prevent stale writes. Owner-scope invalidation clears request memory even
after binding eviction, and current identity/profile checks prevent stale private output.

`CompanionService` shares the research lock for request/party changes. Recall validates
`request_id` and stages only a preview. Direct human confirmation attaches the selected
members and applicable rules to that request through the service's active-party record.
Research and presentation read a defensive snapshot, including each member's dietary
needs, with revision checks against SQLite. Replacement/expiry/reset ends the attachment;
deletion or another-process changes invalidate it. Dietary storage requires separate
sensitive-data consent. Public query arguments never receive companion fields from code.
The model is instructed to keep private health details out of public searches.

## Source lists and delivery

Bundled source priorities cover Japan, Thailand, Indonesia, NYC and SF. Optional
`spoon_profile` actions `sources_get` and `sources_propose` support reviewing/replacing
private city lists. Direct `/spoon locale confirm` commits a preview. Confirmed lists
guide `spoon_dine` when established city/country are supplied; expired/unavailable lists
never block a meal. `/spoon locale show` and `forget` are readable controls.

Final recommendations are normal assistant text with named-place Maps links, source
links and gaps. A same-turn output hook restores omitted Maps links without holding
streaming. Progress is meaningful model commentary between calls. Host input delivery
can be queued; immediate interruption cannot be promised. Host-transcribed voice follows
the same text path. Telegram/voice ingestion requires those surfaces, not terminal setup.

## Verification

Unit tests exercise actual threads, SQLite consent/revisions, identity swaps, stale
work, registration isolation and directory loading without storage/network side effects.
The disposable host script runs doctor/validate plus the same suite. Native provider,
steering and measured city comparisons are recorded in TRACKER; installation checks
alone do not prove recommendation quality. T14 remains the separate public-boundary audit.
