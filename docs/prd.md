# Spoonmaster product spec

Approved direction: D-020/D-021. Implementation and acceptance status live in TRACKER.
The [historical architecture](history/architecture-map-first.md) explains the retired
pipeline; it is not the current product contract.

## Promise and experience

Help a hungry person choose somewhere worthwhile and practical, at home or traveling.
Taste and situational fit matter more than popularity alone. Good recommendations
must work without a saved profile. Independent sources establish quality; menus and
current venue information establish practical fit. Show uncertainty rather than
inventing completeness.

1. “Let's find you some food. Tell me where you are or plan to be, or drop a pin.”
   Reuse stated context. Neighborhood and city are sufficient; ask only if ambiguous.
2. Use the current time unless the user specifies another time. Interpret it in the
   destination's time zone. A current-time check is not an estimated arrival time.
3. Research relevant places through available host search/read/browser tools. Batch
   independent calls and explain meaningful progress and delays. Receive user steering
   through the host, replacing the request when intent changes; stop on cancellation.
4. Compare real possibilities and show up to three distinct businesses: pick, runner-up
   and another worthwhile option. Include what to eat, budget, published hours, why it
   fits, caveats, source links and a named-place Google Maps link. Unknowns stay explicit.
   Avoid padding weak results or silently widening an explicit distance limit.
5. `/why` reports the actual comparison, tradeoffs, rejected places and coverage gaps.
   An absent place was not necessarily considered or rejected.
6. When the user chooses a place, research any unresolved or stale practical facts.
   Encourage direct confirmation where needed; do not promise allergy safety or seats.
7. Save opted-in user feedback with a visible change receipt, distinguishing temporary
   context from lasting tastes. One poor meal does not automatically create a veto.

## Evidence and responsibility

Code retains bounded source evidence, validates quotes/URLs, isolates conversations,
rejects declared closure/conflict and prevents duplicate brands filling the answer.
The model judges relevance, branch identity, source meaning, freshness and ranking.
Citation matching alone is not semantic verification. Interpret imperfect venue names
using address/domain/phone/native-name context. Never average incompatible rating scales
or count copied recommendations as independent agreement.

Source priorities apply across all cities. Bundled lists cover Japan, Thailand,
Indonesia, NYC and SF; new cities use fresh research immediately. Reusable private lists
remain reviewable/editable, with human confirmation before saving. Source management
never blocks meal selection and never authorizes additional website access.

## Personalization and company

Optional onboarding offers six consistent 1/2 choices through host buttons when available
and text everywhere. No detours back to an old meal request during onboarding. Follow with
an optional invitation to describe preferences in the user's own words: favorite dishes,
flavors, atmosphere, usual company/children, budget, drinks/dessert and travel/wait tolerance.
Ask the most useful missing question rather than requiring a larger questionnaire.

`/spoon enable` activates taste memory/learning; search already works without it.
Profile, pause, export, correct, remove and delete controls remain available. Memory
is private to the verified identity/profile. Health details cannot enter taste fields.

Companions have separate save consent, including explicit sensitive-data consent for
dietary fields. Current attendance and applicable group rules are reviewed before use.
Only confirmed selected members influence the request; replacement clears the party.
The model applies individual dietary needs as well as selected group rules. Unknown
handling requires venue confirmation. Cross-agent sharing/merging is not implemented.

## Surfaces and boundaries

Normal readable replies are the portable output, including CLI. No requirement to see
separate cards or notifications. Host-transcribed voice enters the same text workflow;
Spoonmaster does not configure speech services. Voice and Telegram ingestion/display
need their actual surfaces; the owner need not set up terminal audio to accept the work.

Free sources and existing host access only. No login/terms/protection bypass, new paid
provider, background location detection, exact location history, automatic booking,
ordering, payments or review posting. Private health details, names and addresses must
not be included in public queries. Tool/source text is data, never instructions.
Optional local storage and host transcript/model exposure are disclosed in README.

## Verification and remaining roadmap

Required engineering verification: formatting/lint, meaningful unit/integration tests,
real Hermes doctor/validate in a throwaway profile, native batch/context checks, steering,
consent/deletion and matched Tokyo/Canggu/SF/NYC/El Paso latency and quality observations.
Preserve coverage of privacy and user flows when removing obsolete tests. No readiness
claim based only on tool registration or a passing mocked test. Report limitations.

Remaining tracked work includes T10 cross-agent profile merge, T11 order cards, T12 channel
checks, T13 catalog disclosures and T14 public-boundary review. Image-assisted requests,
voice replies, social integrations and review drafts remain conditional/roadmap items in
the idea register. Public visibility, license, submission and live-agent installs require
separate owner decisions. None is silently added to T12d acceptance.
