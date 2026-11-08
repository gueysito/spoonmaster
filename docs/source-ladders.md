# Source ladders

A ladder is the ordered list of sources to consult for one place: which to trust for
food quality, which for current facts, which for bookings and which for local opinion.
Choosing the right sources for the place is the core of good recommendations. The
ladders below come from field use in Japan, Thailand and Indonesia during summer 2026
through the author's Hermes agent; Korea was used in the field without a written ladder.

Ladders will ship as data files. Access status is planned unless marked. Nothing here
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
known venue country (JP, TH, ID or KR in this pilot); no inferred country, dial commands,
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

1. Reverse-geocode the origin to country, city and neighborhood.
2. Use the host's web search to find what locals use: review platforms, food editors and
   critics, guide lists, food writers, video channels, social accounts, delivery apps
   that carry ratings.
3. Classify each candidate by role (quality, current facts, booking, local opinion,
   inspiration) and by access tier.
4. Propose a ladder with one line per source on why it is trusted. The user confirms or
   edits. Cache it with a review date.
5. Social and video sources are roadmap and only through permitted routes (official
   APIs, links the user shares).

## 5. Field lessons that shaped the rules

| Lesson | Rule |
|---|---|
| A planned stop was reached before it opened | Open-at-arrival gate; when closed, offer a holding pattern nearby |
| A good answer lacked map links and costs, so it had to be asked again | Cards are rendered by code with required fields |
| A ready-to-show local-language request at a service counter removed stress | Order card with show-this text |
| Local opinion matters but is not automatically right | Ladders weigh local sources first and cross-check |
| Recent video and social posts were strong current signals | Recency is tracked per evidence item; social is roadmap |
| The best meal fits the day: energy, weather, kids, transit | Household and situation gates |
