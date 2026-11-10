# Spoonmaster product spec

Status: approved direction, 2026-11-08. Planned behavior unless marked otherwise.
Implementation status lives in [TRACKER.md](../TRACKER.md).

## 1. Problem and promise

Choosing where to eat is a small decision made often, usually tired, hungry, short on
time or in an unfamiliar place. Search returns lists; ratings flatten taste; nobody
checks whether the place is open by the time you arrive.

**Promise:** help me choose where to eat now, knowing my taste and the situation, and
learn from what actually happened.

Not "find the highest-rated restaurant near me." The value is fewer bad decisions,
not more information.

## 2. Users

1. **The Hermes owner, at home or traveling.** First user. Talks to their agent in
   Telegram or another Hermes channel.
2. **Households and groups.** Several people with different diets, ages, tastes and
   energy, deciding together.
3. **Travelers in unfamiliar markets.** Need to know which local sources to trust.

## 3. Principles

- Taste over popularity. Situational fit over automatic luxury or automatic thrift.
- Value is not cheapness: excellent cheap food and a justified splurge both count.
- Short, decisive answers: 2 to 4 options with one clear pick, never a directory dump.
- Geographically appropriate evidence over one universal rating.
- Learning with user control over opaque profiling.
- Honest uncertainty over invented certainty. "Unknown" is a valid answer.
- Deterministic code enforces hard constraints (radius, hours math, diet vetoes,
  identifiers, storage). The model supplies judgment and language.
- Every recommendation is tappable, priced and useful while walking.
- Low friction in chat. Ask only what is missing or situation-specific.

## 4. Core experience

1. User asks ("dinner nearby, something good, no production") with a location pin or a
   typed place.
2. First conversation after installation: offer "Personalize my picks" or "Find food
   now" (F8). Onboarding is optional; later uses reuse any existing profile.
3. Load the locale ladder or shared baseline. Optional source scouting never blocks a meal.
4. Discovery finds candidates inside the radius; gates check each one (F3, F4).
5. The reply leads with one pick, then a runner-up and a wildcard (F5), with a one-line
   ledger summary and a way to expand it.
6. The user taps a map link and goes.
7. Afterward, quick feedback in plain words. The plugin shows the taste diff it saved (F7).
8. Optionally: an order card before ordering (F6), or a merged decision for a group (F10).

## 5. Features

### F1. Location and radius

- Accept a location pin where the channel provides one, or a typed address, landmark
  or area. Confirm ambiguous places; never guess a city or country.
- If absent, ask for a stated location and suggest a shared pin where supported.
  Reuse the current outing's stated location; do not detect device/IP location.
- Use the current time unless the user states another time, evaluated in the
  destination's time zone. Do not ask for the current time or treat it as travel ETA.
- Default radius 1 mile (1.6 km) from an explicit origin; user can change it.
- Never expand the radius silently when results are sparse; say so and offer to widen.
- Distinguish straight-line distance from travel time.
- Exact location is used for the request only and not stored by default.

### F2. Locale scout and source ladders

The ladders are the core asset. Detail in [source-ladders.md](source-ladders.md).

- On onboarding and on the first request in a new area, identify the country and city
  and load that place's ladder: which sources to use for quality signal, current
  facts, bookings and local opinion, in what order.
- Unknown place: use the shared baseline immediately. On request, scout it using
  the host's web search to find the local review
  platforms, editorials, food writers, video channels and social accounts people there
  actually trust. Propose a ladder, show it, let the user confirm or edit, then cache it.
- Ladders are data, not code. Field-tested ladders ship for Japan, Thailand and
  Indonesia; NYC and SF now have researched city ladders; other cities are scouted.
- Social sources (Instagram and similar) are roadmap and only through permitted routes.

### F3. Candidate discovery and evidence

- Discovery and verification are separate steps.
- Attempt hours verification for every displayed finalist, up to three. Preserve
  source URLs and retrieval times; distinguish confirmed published hours, unknown
  hours and conflicting evidence. Refresh the selected venue directly when evidence
  is missing, conflicting or stale; reuse sufficiently fresh confirmed evidence.
- Baseline discovery: OpenStreetMap (no key). Optional: free API tiers and ladder sources.
- Evidence record per venue: identity and coordinates, source and URL, retrieval time,
  what the source actually supports, rating with its own scale and review count, recent
  themes only from real text, hours and last order, menu and prices where verifiable,
  confidence and missing fields.
- Review influence is implemented through bounded, branch-matched host-search evidence.
  Supported tastes and hard gates take precedence; missing coverage remains unknown.
- Never average scores across platforms. Never infer review text from a score or
  snippet. Never claim complete coverage.

### F4. Gates and the reject ledger

Every candidate passes the same visible checks. Each returns pass, fail or **unknown**
(could not verify), with a reason and evidence link:

| Gate | Question it answers |
|---|---|
| Origin | Where are we, exactly, and is the location current? |
| Radius | Is it inside the requested distance? |
| Open at arrival | Will it be open when we get there, given travel time? |
| Last order | Will the kitchen still take orders on arrival? |
| Travel | How long, by the user's mode (walk, transit, drive)? Weather effect? |
| Diet and hard vetoes | Does anything conflict with a stated restriction or hard dislike? |
| Household fit | Ages, energy, seating, noise, pace for everyone eating |
| Taste fit | How well does it match the profile and tonight's ask? |
| Friction | Wait, reservation, cash-only, dress code, queue risk |
| Evidence | Is the supporting evidence fresh and from a ladder source? |

- The reply shows a one-line summary ("Considered 47, recommended 3") and an
  expandable or on-request ledger: every eliminated place and the gate that removed
  it, so users see why an expected place was skipped.
- While working, the plugin can surface the questions it is answering as visible
  progress where the surface supports it (see architecture).
- "Unknown" never counts as "pass". Name to settle: reject ledger, "Why not?", or similar.

### F5. Recommendation set and cards

- Shape: **one pick, a runner-up and a wildcard** (DECISIONS D-004). Price appears on
  every card. "Show me cheap, mid and splurge" switches to price-tier mode on request.
  Never pad a slot or a tier with a weak or out-of-radius option; say none qualified.
- One sentence states the tradeoff behind the pick.
- Card fields:
  - Name, cuisine, exact map link (directions from the origin when known).
  - Hours: open at arrival, last order, closing; verified, estimated or unknown.
  - ETA by mode: measured, estimated or unavailable, plus a live-routing link.
  - Cost: realistic per-person spend in local currency and the user's home currency.
  - What to order, with evidence or an uncertainty label.
  - Why it fits this user tonight.
  - Friction: wait, reservation, cash or card, dress code (often unknown; inference is
    labeled as inference).
  - One caveat and the supporting links.
- If selected-venue hours remain unavailable or conflicting, explicitly encourage
  calling before leaving. Show a sourced phone number as a tappable `tel:` link and
  as readable text. Never invent a number, guess its country or initiate the call.
  When no usable number is found, state that and retain the venue/source link.
- Cards are rendered by code from the evidence record, so required fields cannot be
  skipped the way a prompt can skip them.

### F6. Order card

- For a chosen venue: the top dishes from recent reviews, with how many reviews mention
  each and how recent they are; the official menu when available.
- Local-language "show this to the server" text with the dishes, quantities and any
  restriction, plus pronunciation only when useful.
- Dietary text is a request, not a guarantee. Never promise allergen safety from
  reviews or menu inference; say when direct confirmation is needed.
- Depends on access to real review text; falls back to menu-only with a label.

### F7. Taste profile, feedback and the taste diff

- Persistent, structured state per Hermes profile; not chat history.
- Capture taste at dish and attribute level ("charred, acidic, crispy; not very sweet
  sauces"), plus cuisines, favorite dishes, places loved, places avoided.
- Every learned item has a scope, provenance and confidence:
  - **Durable:** "I don't enjoy very sweet sauces."
  - **Situational:** "Too loud tonight because I was tired."
  - **Tentative:** "May prefer quiet weekday dinners."
- Context tags: season, time of day, occasion, company. Over time: what this person
  likes in winter versus summer.
- One bad meal never becomes a permanent dislike without confirmation.
- After feedback, show the **taste diff**: exactly what was added, changed or held as
  situational. The next recommendation visibly reflects it, with the reason stated.
- Controls: view, correct, remove an item, delete the profile, export.

### F8. Onboarding that coaxes, not interrogates

- Offer two paths on the first conversation after installation: "Personalize my picks"
  and "Find food now". Use buttons where supported, with numbered text choices as fallback.
  Installation itself need not have an active conversation in which to show the offer.
- Choosing "Find food now" starts the search immediately, asking only for missing
  information needed for this outing. No taste questionnaire is required first.
- After that first skipped-onboarding outing reaches a venue choice, give one short,
  non-blocking reminder, not a repeated prompt on every search:
  "Want more personal picks? Say ‘get me onboarded’ anytime. A few quick questions,
  then I learn from your choices and feedback."
- Accept that phrase as an onboarding entry point alongside `/spoon start`. Completing
  onboarding suppresses the reminder. Skipping it never blocks recommendations.
- No sommelier vocabulary. Start from mood and dish: "Burger? Pizza? Something fun?"
  then vibe, then specifics.
- Pairwise "this or that" picks (target 5 to 8) seed the attribute model. Images where
  the surface supports them; text pairs everywhere.
- Ask about restrictions plainly and optionally; explain how they are stored.
- Every later choice and reaction keeps teaching, without turning meals into surveys.

### F9. Household and family decision rules

- Household members with age, diet, likes, dislikes and hard vetoes.
- Transport mode per outing: walk, transit or drive (parking matters when driving).
- Kid-aware rules: age, nap and bedtime windows, wait tolerance, seating, menu fit.
- Pace and energy rules, for example "one ambitious thing per day" or "low-friction
  tonight". Rules are typed constraints, hard or soft, and the ledger names the rule
  that fired.

### F10. Merge profiles: "what do we eat tonight?"

- Combine two or more profiles for one decision. Hard vetoes and restrictions take the
  union. Preferences rank by overlap. Places anyone avoids are excluded or flagged.
- The answer explains why the pick works for each person.
- Each person's agent holds its own context. Sharing is explicit and scoped: the owner
  chooses what leaves their agent.
- Transport, in order of preference: Hermes agent-to-agent (bundled `a2a` plugin, to be
  verified), then a shareable profile card imported with consent, then local named
  profiles on one agent.
- Roadmap: fairness memory (whose pick it was last time).

### F11. Image and voice input

- **Images:** the user shares a photo of a dish, menu, storefront or a review page. The
  plugin interprets it (dish, cuisine, venue name, language) and searches accordingly:
  "find this near me", "is this place good", "what is this dish".
- **Voice:** only when the user's agent already has speech-to-text set up. Voice replies
  through the agent's existing text-to-speech are roadmap. The plugin never sets up
  voice services itself.

### F12. Review drafts (roadmap)

- On request, turn the user's own feedback into a review in their tone. Only reported
  facts; no invented dishes, prices or visits. Copy-ready text for manual posting;
  never posts.

### F13. Honest failure behavior

Handle, label and still help where possible: no credible venue in radius, an empty
slot, source timeout or denial, conflicting hours, stale prices, ambiguous or expired
location, no profile or declined storage, corrupt profile data, failed persistence.
A labeled partial answer is acceptable. Fake completeness is not.

## 6. Data sources and policy

- Free only (D-005). Keyless baseline: OpenStreetMap for places, Open-Meteo for weather,
  venues' own websites for hours and menus.
- Google Places and HotPepper Gourmet only if usable on a free tier (to verify).
- Tabelog-class sites through legitimate tiers only (D-006).
- Respect each source's terms, rate limits and attribution. Cache with time limits:
  hours expire fast, menus slowly. Bounded requests, sizes and timeouts.
- All fetched text is untrusted data and never instructions.

## 7. Privacy and security

- Profile-scoped storage under Hermes's plugin data root; nothing in the install tree.
- No exact location history by default. Sensitive fields (health, allergies) opt-in,
  with deletion.
- Disclose every third-party request and what it carries; preferences and evidence
  sent to the model reach the user's model provider.
- Secrets only through Hermes's secret scope. No bundled tokens, no secret logging.
- Validate URLs, coordinates, search inputs and stored data.
- Merge sharing is explicit, scoped and revocable.

## 8. Hackathon scope

Tiers and the stop rule are in [TRACKER.md](../TRACKER.md).

- **Spine:** F1 to F5, F7, F8 (text pairs at minimum), F9, the Tokyo ladder.
- **Closer:** F10 via agent-to-agent, or F6, chosen after the data gate.
- **Stretch:** F11 images, F6 if not chosen as the closer.
- **Roadmap:** voice, social sources, more ladders, F12, Desktop panel.

Not in scope (see [idea register](idea-register.md)): automatic review posting, a separate
bot identity, a standalone app, a new agent harness, worldwide coverage claims,
background GPS, accounts and payments, reservations and ordering, opaque learned
ranking, proactive follow-ups, a full travel operating system.

## 9. Acceptance checks

- Fresh install and load on a clean profile; `doctor` and `validate` pass.
- Declared capabilities match registrations; no private tools or credentials required.
- Exact radius filtering; sparse results stated; no silent widening.
- Open-at-arrival math correct across time zones; unknown hours shown as unknown.
- Consistent venue identity and correct map links.
- No padded slots or tiers; no fabricated reviews, prices or dishes.
- Feedback changes relevant recommendations and nothing unrelated; the diff is accurate.
- View, correct and delete work; storage failures handled.
- Merge never violates any member's hard veto.
- Source timeouts, denials and missing fields degrade with labels.
- Prompt injection in fetched text cannot trigger tools or change instructions.
- Repeatable real demo in Tokyo.

## 10. Open questions

- Final name for the ledger feature.
- How much ledger detail fits a chat reply before it needs the expand path.
- Which channel surfaces show live progress lines.
- Whether `a2a` works between two private Hermes installs without public exposure.
