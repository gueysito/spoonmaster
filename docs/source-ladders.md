# Source ladders

A ladder is the ordered list of sources to consult for one place: which to trust for
food quality, which for current facts, which for bookings and which for local opinion.
Choosing the right sources for the place is the core of good recommendations. The
ladders below come from field use in Japan, Thailand and Indonesia during summer 2026
through the author's Hermes agent; Korea was used in the field without a written ladder.

Ladders ship in `spoonmaster/data/ladders.json` for Japan, Thailand and Indonesia,
plus distinct New York City and San Francisco entries.
`spoon_locale` loads them or stages an unknown-city proposal for review.
Access status is planned unless marked. Nothing here
grants permission to scrape: every source goes through the tiers in section 3.

## Progressive hours adapter (T1 pilot)

The verification core attempts the OSM-linked venue page for each of up to three
finalists. Selection refreshes missing, conflicting or older-than-15-minute evidence;
fresh confirmed evidence retains its original retrieval time. Public venue records
expire after 30 minutes, are capped at 200 per process, and are never written to disk.

- `confirmed`: matching name and coordinates within 100 metres in structured page data,
  with fully parsed weekly hours and no detected disagreement with parseable OSM hours.
- `unknown`: inaccessible, missing, unparseable, unmatched or non-comparable evidence.
  Bounded text excerpts remain available for host review. This does not mean the venue
  publishes no hours. Unsupported holiday exceptions remain unknown.
- `conflicting`: comparable source schedules differ. Neither schedule silently wins.

These labels describe published evidence, never an open-at-arrival verdict. T4 owns
arrival, time zones and exceptional closures. The agent must show uncertainty on cards.
On selection, unresolved hours produce advice to call before leaving. A sourced number
is rendered as a `tel:` link and a visible number. Local numbers require an explicitly
known venue country (JP, TH, ID, KR or US in this pilot); no inferred country, dial commands,
extensions or ambiguous multiple numbers. A unique phone from the named OSM-linked
page is a source claim, not independently verified branch ownership or service.

The adapter reads only public HTTPS on port 443, validates every DNS answer and pins
the chosen IP while checking TLS for the hostname. Private, multicast and transition
addresses, redirects, proxy credentials, compressed responses and unsupported content
are refused. Each response is capped at 512 KiB with an eight-second socket timeout
and elapsed read checks; DNS and blocked reads are not a strict total deadline.
`robots.txt` denial or unavailability fails closed (404/410 permits the page); declared
pacing rules defer to host review. No cookies, login, retries or bot-protection bypass.
Known restricted review/social domains remain disabled. The OSM link itself does not
establish a site's terms; production source admission remains T9/T13.

One verification call runs at a time, with a 10-second cooldown per stage. The separate
selected stage permits an immediate second pass after the finalist check. Failed
refreshes retain a previously sourced phone with its original retrieval timestamp.

## 1. Global baseline (every place)

T8 also retains exact OSM `min_age`, `max_age`, `highchair` and supported `diet:*`
values from the existing discovery response. Unknown or compound values are not parsed.
These are community source claims, not current admission or food-safety guarantees.
Definitions checked against the OSM [age](https://wiki.openstreetmap.org/wiki/Key:min_age),
[highchair](https://wiki.openstreetmap.org/wiki/Key:highchair) and
[diet](https://wiki.openstreetmap.org/wiki/Key:diet:*) documentation on 2026-11-08.

| Role | Source | Access | Key | Free |
|---|---|---|---|---|
| Discovery | OpenStreetMap (Overpass, Nominatim) | Public APIs within usage policy | No | Yes |
| Weather | Open-Meteo | Public API | No | Yes |
| Hours, menu, booking | Venue's official site, structured data where published | HTTP fetch | No | Yes |
| Routing for the user | Google Maps directions/search links | Link only, no API | No | Yes |
| Optional quality and hours | Google Places | API | Yes | Only if a free tier covers use (to verify) |

Map link shapes used on cards:
`https://www.google.com/maps/dir/?api=1&origin=<origin>&destination=<place>` and
`https://www.google.com/maps/search/?api=1&query=<place>`.

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

## 4. Locale scout

For a place with no ladder:

1. Establish country, city and neighborhood from explicit user input or attributed
   host location evidence. Ask when ambiguous; the plugin adds no geocoding endpoint.
2. Use the host's web search to find what locals use: review platforms, food editors and
   critics, guide lists, food writers, video channels, social accounts, delivery apps
   that carry ratings.
3. Classify each candidate by role (quality, current facts, booking, local opinion,
   inspiration) and by access tier.
4. Propose a ladder with one line per source on why it is trusted. The user confirms or
   edits. Cache it with a review date.
5. Social and video sources are roadmap and only through permitted routes (official
   APIs, links the user shares).

The T9 scout makes at most two existing-host `web_search` calls, with five results
requested per query. It proposes deduplicated source links, roles by query purpose
and attributed snippets; it does not certify local trust or read pages. The human
reviews/edits before a direct confirmation saves an owner-private city list with
review and retrieval dates. Reviews expire after 30 days. Host-search allowance use
was explicitly approved in D-016; no new provider/account is installed. Source
permissions and disabled adapters remain unchanged after confirmation.

## 5. Field lessons that shaped the rules

| Lesson | Rule |
|---|---|
| A planned stop was reached before it opened | Open-at-arrival gate; when closed, offer a holding pattern nearby |
| A good answer lacked map links and costs, so it had to be asked again | Cards are rendered by code with required fields |
| A ready-to-show local-language request at a service counter removed stress | Order card with show-this text |
| Local opinion matters but is not automatically right | Ladders weigh local sources first and cross-check |
| Recent video and social posts were strong current signals | Recency is tracked per evidence item; social is roadmap |
| The best meal fits the day: energy, weather, kids, transit | Household and situation gates |

## U.S. city priorities (researched 2026-11-09, not field-tested)

New York City (aliases NYC/New York) and San Francisco (alias SF) select city-specific
bundled data before country defaults. Other U.S. cities still require a reviewed scout.
Eater and The Infatuation supply editorial discovery/occasion references; NYT serves
NYC and the San Francisco Chronicle serves SF. Michelin, Yelp and OpenTable are
complementary references; Google Maps remains link-only and venue sites provide facts.
Regional guides do not expand the requested radius. No publisher is directly scraped.

Research: [Eater NYC](https://ny.eater.com/23832815/nyc-dining-guide),
[Eater SF](https://sf.eater.com/maps/best-restaurants-san-francisco-38),
[Infatuation NYC](https://www.theinfatuation.com/new-york/guides/best-restaurants-nyc),
[Infatuation SF](https://www.theinfatuation.com/san-francisco/guides/best-restaurants-in-san-francisco),
[NYT](https://www.nytimes.com/spotlight/best-restaurants), and
[Chronicle methodology](https://marketing.sfgate.com/blog/celebrate-the-bay-areas-best-restaurants-with-the-chronicles-top-100-list).
These are complementary source choices, not a measured city-specific popularity ranking.

## Review influence (T9b)

Bundled priorities or a current owner-confirmed city list select permitted search domains.
The shared recommendation path consumes at most six candidate searches, not entire guide
pages. It requires exact mapped branch-address evidence and city corroboration before
retaining a hit. Explicit recommendation labels in result titles can supply provisional
editorial support; a mere mention cannot. Original crowd rating/scale/count expressions
can break ties only within common publisher/scale coverage. See README for bounds and
known language/coverage limits. Official venue checks still own published hours.

Publisher access remains search snippets/user content only. Direct publisher extraction
is disabled, including when a review link is supplied as the OSM venue website.
[Yelp access rules](https://www.yelp.com/robots.txt),
[Infatuation terms](https://www.theinfatuation.com/terms), and
[Michelin terms](https://guide.michelin.com/en/terms-of-use) restrict automated extraction.
Google Maps remains link-only; no Places billing project or API account is added.

## T12 discovery recovery and ride links

Each dining request uses bounded web enrichment inside `spoon_dine` to cover venues
with missing/broad OSM cuisine tags. The same path recovers source outages, without
asking the user to approve an ordinary fallback search.
Two configured host searches send only the requested food and public area/city/country.
Search excerpts go to the configured host model for bounded extraction; existing host
allowances apply. A name must be present in the result title/quote and the food quote
must be an exact excerpt. This is discovery evidence, never a critic endorsement.

Up to six public venue-name/city queries use `https://photon.komoot.io/api/`. When
map discovery fails, one additional food-name query can supply a mapped lead for
the existing second web search. Its location bias rounds latitude/longitude to two
decimal places (roughly a kilometre); the exact origin stays out of Photon requests.
A map lead alone cannot become a card: the same web-excerpt food/identity checks
still apply, and exact radius checks run locally. This does not add web searches.
The
[Photon operator](https://github.com/komoot/photon#demo-server) permits moderate project
use, may throttle, and offers no availability guarantee. The local-pilot client
serializes requests, spaces uncached requests by one second, caches up to 100 public
queries for 30 minutes, makes no automatic retries, refuses redirects/proxies, and
bounds response size/time. Returned map identity/country/radius must corroborate the
venue. This is an additional discovery dependency, not a public-launch capacity plan.
Photon requests English result names (`lang=en`) to match English search excerpts;
missing translations still remain unverified, rather than accepting unrelated names.
This follows the [documented language parameter](https://github.com/komoot/photon/blob/master/docs/api-v1.md#adjust-language).
Map discovery uses a 10-second server execution allowance and 15-second socket timeout;
host search/model calls retain their own timing. No total-response-time guarantee is made.
OpenStreetMap attribution remains visible. Public Nominatim is not integrated.

Unknown cities receive the same branch-matched TripAdvisor/Yelp search-evidence path
without waiting for a custom ladder. Neither a search mention nor a restaurant's own
site counts as independent recommendation evidence. Footprint bounds can establish
radius fit only when the complete mapped footprint fits; entrance precision remains
unknown. Immediate identical dining calls reuse their current ledger for 60 seconds.

For mapped distances above 804.672 metres, cards offer country-appropriate service
entry links: Uber in US/JP, Grab in TH/ID, Gojek in ID. These are service/home/download
links, not destination-prefilled or booking links. Availability and fares are not
promised. Sources: [Uber web](https://m.uber.com/),
[Uber deep-link contract](https://developer.uber.com/docs/riders/ride-requests/tutorials/deep-links/introduction),
[Grab Thailand](https://www.grab.com/th/en/download/),
[Grab Indonesia](https://www.grab.com/id/download/), [Gojek](https://www.gojek.com/en-id/).
No developer account, API credential, booking or ride transaction is added.
