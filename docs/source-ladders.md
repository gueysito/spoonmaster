# Source priorities across cities

A source list guides research; it never decides whether a restaurant is allowed.
Seek agreement among independent local reviews, relevant recent accounts and official
branch menus/hours. Keep food quality separate from family fit, atmosphere and logistics.
Do not average different rating scales or count copied lists as independent praise.
Reconcile branch identity using address, domain, phone and native names rather than
requiring perfect spelling. Search snippets establish only what their text supports.

`spoon_dine` supplies bundled guidance and prefers confirmed private city sources when
an established city/country is supplied. Unknown or expired lists never block a meal.
The model researches through installed host tools, batching independent calls. A page
can be read through available host extraction/browser routes subject to existing access
controls. No custom fetcher, geocoder or map-first admission remains.

## Shared source roles

- Independent local critics, guides and reported reviews: quality and dishes.
- Official branch websites/menus: current facts, published hours, prices and booking.
- Local community reviews: recent signals with provenance and relevant context.
- Maps: user navigation, photos/contact lookup and supplementary location evidence.
- Booking/delivery lists: availability clues, not independent taste endorsements.

## 2. Field-tested ladders

### Japan

1. Tabelog: food quality, score and review volume, seating, smoking and kid clues,
   lunch versus dinner split, reservation posture.
2. Google Maps: tappable link, current open status, navigation, recent photo check.
3. Official site, TableCheck, Gurunavi, NAVITIME, the venue's social accounts: hours,
   last order, booking, closures, menu.
4. HotPepper Gourmet API: search by area, genre and budget (only if free; to verify).

Behavior: verify open at arrival. A field-tested default skips chains, cafes and family
restaurants unless asked or in rescue triage; it ships as a profile option, not a rule.

### Thailand (Bangkok)

1. Wongnai and LINE MAN: local review signal, categories, photos, opening clues.
2. Google Maps: location, current hours, recent reviews and photos, routing.
3. Michelin Guide: quality-filtered restaurants and street food where relevant.
4. Official site, Instagram, Facebook, LINE: hours, booking, queue, menu, closures.
5. Chope, Grab Dine Out: reservations and deals.

Behavior: district traffic, BTS/MRT convenience, queue risk, spice and kid constraints,
whether air conditioning and seating are needed now.

### Indonesia (Bali)

1. Google Maps: location, current hours, recent photos, review volume, routing.
2. Chope, Grab Dine Out: bookable venues, deals, reservation posture.
3. Official site, Instagram, WhatsApp link: current menu, hours, events, minimum spend,
   booking.
4. Current local guides for discovery and vibe, verified against Maps and official pages.
5. TripAdvisor only as a tourist-signal cross-check, never the primary quality filter.

Behavior: traffic, WhatsApp booking friction, heat and rain, kid tolerance, and whether
the spot is worth the drive from the current base.

### Korea

Used in the field; no ladder was written down. Candidates to research, not field-tested:
Naver Map, Kakao Map, Catch Table, Blue Ribbon Survey, Michelin Guide Seoul.

## 3. Access tiers for restricted sites (Tabelog and similar)

In order of preference. A source enters a ladder only through one of these:

1. **User-provided:** the user shares a link or screenshot; the plugin reads what they
   shared, including through image input.
2. **Licensed free APIs:** for example HotPepper Gourmet, Google Places, if free tiers
   cover the use and terms allow the display.
3. **Search snippets:** the host's web search returns a result for the venue page; use
   only what the snippet shows (score, count). Never infer review text.
4. **One page on demand through the host's browser tool:** a single page the user is
   about to act on, disclosed, low volume, off by default until the site's terms are
   checked.

Never bypass logins, bot protection or terms. Never bulk crawl. Never bundle cookies or
private credentials.

## NYC and San Francisco

NYC prioritizes The Infatuation NYC, Eater NY, the New York Times dining coverage
where accessible and Michelin where relevant. SF prioritizes The Infatuation SF,
Eater SF, San Francisco Chronicle dining coverage where accessible and Michelin.
Local writers/community coverage can fill cuisine or neighborhood gaps. Official
branch sites establish practical facts. Bundled URLs, roles and access labels live in
`spoonmaster/data/ladders.json`; NYC/New York and SF aliases resolve consistently.

Lists apply as research guidance to every city, including future private additions.
No source is sufficient merely because it appears in the list. Distinguish a review,
an unvisited directory entry, a booking listing and a venue's own marketing.

## Reusable private city lists

On request, research suitable sources and use `spoon_profile` with `sources_propose`,
country_code, city and the complete proposed sources. Explain names, URLs, roles,
reasons and changes in readable prose. Only a direct `/spoon locale confirm <token>`
saves the preview, unless the user has opted into automatic local city-source saving
through `/spoon locale memory` or `/spoon locale remember on`. Automatic updates require
a brief visible receipt. `remember off` stops updates without deleting lists. Include
coverage, credibility, evidence dates and limitations in each source reason; never user
details. Review again after 30 days, keeping stale lists as leads. `sources_get` reads the current list;
`/spoon locale show <country> <city>` is the readable command fallback. Corrections
use a new replacement preview; `forget` removes one city. Whole-profile deletion also
removes that identity's source lists and opt-in. Automatic source discovery is part of
meal research, not an onboarding requirement. Host-memory offers require verified exposed
tools and explicit destination/access disclosure plus separate consent, not custom sync.

Public HTTPS list URLs have no credentials, queries or fragments. Citation evidence
can contain public HTTP(S) URLs including query strings/parenthesized paths. Both are
references, not access grants. The host owns fetch permission and transport controls.
Restricted sources use permitted snippets or user-provided content unless an allowed
host route is established. No new accounts, paid APIs or protection bypasses.
