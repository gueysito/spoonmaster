# Idea register

Every idea considered, with its status and the reason. Statuses: **adopted** (in the
spec and plan), **roadmap** (wanted, after the hackathon), **maybe** (needs evidence
or owner input), **postponed** (deliberately not now), **dismissed** (not doing).
Feature detail lives in [prd.md](prd.md); choices with alternatives in
[DECISIONS.md](../DECISIONS.md).

## Core experience

| ID | Idea | Status | Reason |
|---|---|---|---|
| I-01 | Reject ledger: every candidate and the gate that removed it, expandable | adopted | Makes the agent's checks visible; proves deterministic code |
| I-02 | Visible thinking: show the questions being answered while working | adopted | Owner request; rendering depends on surface (unverified on Telegram) |
| I-03 | Taste diff after feedback, with scope tags | adopted | Shows learning; the demo's before/after |
| I-04 | Situational awareness with real math: time, weather, last order, travel | adopted | Deterministic, cheap, feels like judgment |
| I-05 | Pick, runner-up, wildcard instead of forced price tiers | adopted | D-004 |
| I-06 | Price-tier mode on request | adopted | Keeps the original tiers available |
| I-07 | Cards rendered by code: map link, hours, ETA, cost, order, caveat | adopted | Field lesson: prompts skip fields |
| I-08 | Dress code on cards | adopted | Usually unknown; inference labeled |
| I-09 | Order card: top dishes from recent reviews plus show-this local text | adopted | Proven in the field as counter cards; depends on review access |
| I-10 | Pairwise "this or that" onboarding, images when possible | adopted | Fast, playful; text pairs as fallback |
| I-11 | Coax with mood and dish ("burger? pizza? something fun?") | adopted | No sommelier vocabulary |
| I-12 | Dish and attribute level taste, not only cuisines | adopted | Where personalization becomes useful |
| I-13 | Seasonal and contextual taste (winter vs summer, occasion) | adopted | Context tags from day one; patterns emerge over time |
| I-14 | Household rules: ages, diet, likes, transport mode, nap and energy windows | adopted | Field-proven family decision rules |
| I-15 | Merge profiles for group decisions | adopted | Headline feature; answers "what do we eat tonight?" |
| I-16 | Merge via agent-to-agent (bundled `a2a`) | maybe | Present on host, untested; fallback is a share card |
| I-17 | Fairness memory: whose pick it was last time | roadmap | Delightful, not required for the core |
| I-18 | Image input: dish, menu, storefront or review screenshot | adopted (stretch) | Also a legitimate route to restricted sources |
| I-19 | Voice notes in through the agent's existing speech-to-text | roadmap | Only if already set up (D-009) |
| I-20 | Voice replies through the agent's text-to-speech | roadmap | Tricky; later |
| I-21 | Experience-grounded review drafts, copy-ready, never posted | roadmap | Useful tail, not core |
| I-22 | Holding pattern when the target is not open yet | adopted | Field lesson |

## Sources

| ID | Idea | Status | Reason |
|---|---|---|---|
| S-01 | Per-country source ladders as data | adopted | The core asset |
| S-02 | Locale scout: find local platforms, editors, writers, channels for any place | adopted | Generalizes ladders beyond tested countries |
| S-03 | Japan, Thailand, Indonesia ladders from field use | adopted | Field-tested |
| S-04 | Korea ladder | maybe | Used in the field, never written down; research needed |
| S-05 | Instagram and other social sources focused on the user's area | roadmap | Only through permitted routes |
| S-06 | Google Places | maybe | Only if a free tier covers use |
| S-07 | HotPepper Gourmet API | maybe | Only if free; Japan coverage |
| S-08 | Tabelog through legitimate tiers | adopted | D-006 |
| S-09 | Bulk scraping of review platforms | dismissed | Terms, bot protection, catalog review |
| S-10 | Averaging ratings across platforms | dismissed | Different scales and audiences |

## Platform and delivery

| ID | Idea | Status | Reason |
|---|---|---|---|
| P-01 | Hermes plugin | adopted | D-001 |
| P-02 | Video captions and graphics editor plugin | dismissed | Considered first; reliability risk too high for the window |
| P-03 | Separate Telegram bot identity | postponed | Hosting, identity, abuse and cost duties |
| P-04 | Standalone web or mobile app, custom maps | postponed | Accounts, frontend, deployment |
| P-05 | New agent harness | dismissed | Hermes already provides it |
| P-06 | Desktop panel for the ledger and profile | roadmap | Desktop plugin SDK exists |
| P-07 | Automatic review posting | postponed | Platform permissions, irreversible public effects |
| P-08 | Reservations, ordering, payments | postponed | Not part of the core; transactional risk |
| P-09 | Background GPS and movement history | dismissed | Privacy; user-initiated location is enough |
| P-10 | Accounts, subscriptions, consumer SaaS | postponed | Not needed to prove plugin value |
| P-11 | Opaque learned-ranking models | postponed | Transparent profile first |
| P-12 | Scheduled meal follow-ups | postponed | Consent and delivery work; user-initiated feedback is enough |
| P-13 | Full travel operating system (itineraries, briefs, transit) | postponed | Would swallow the dining plugin |
| P-14 | Worldwide coverage claims | dismissed | Honest bounded coverage instead |
| P-15 | Forkmate, Forkcast, Tablemate, Palate Atlas as names | dismissed | D-002 |
