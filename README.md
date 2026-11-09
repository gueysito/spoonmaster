# Spoonmaster

A Hermes Agent plugin that helps you decide where to eat right now. It learns your
taste, checks the right local sources for where you are, shows the reasoning behind
its pick, and improves from what actually happened at the table.

Status: pre-alpha. Discovery, provisional recommendation cards, progressive hours checks and a reject
ledger work locally. Opt-in taste memory, feedback diffs and supported taste ranking are implemented. The scaffold passed real-host
doctor/validate in an isolated profile, which was then deleted.
Built for the Hermes Agent Plugin Hackathon (submission due 2026-11-11, 17:00 EST).
The repository is private until submission, then public.

## What it will do

- **Decide.** "Dinner nearby, nothing fussy" plus a location pin returns one pick, a
  runner-up and a wildcard. Each is a card with a map link, hours at arrival, ETA,
  realistic cost, what to order and the one caveat that matters.
- **Show its work.** The reject ledger lists every place considered and the check
  that removed it: closed at arrival, too far, diet conflict, poor fit, unverifiable.
- **Learn.** Tell it what worked; it shows the exact taste change it saved and
  separates lasting preferences from one-night circumstances.
- **Eat together.** Merge household or friends' profiles to answer "what do we
  all want tonight?" with shared favorites and hard vetoes respected.
- **Know where to look.** Per-country source ladders pick the right evidence for the
  place you are in: Tabelog in Japan, Wongnai in Thailand, local guides in Bali.

## Start here

| Read | For |
|---|---|
| [docs/prd.md](docs/prd.md) | Product spec: experience, features, rules, scope |
| [docs/architecture.md](docs/architecture.md) | Hermes surfaces, components, data model |
| [docs/source-ladders.md](docs/source-ladders.md) | Per-country evidence ladders and the locale scout |
| [docs/data-gate.md](docs/data-gate.md) | Shibuya spike results, source limits and reproduction |
| [docs/demo.md](docs/demo.md) | 90-second demo spine and alternative flows |
| [DECISIONS.md](DECISIONS.md) | Settled choices and their alternatives |
| [docs/idea-register.md](docs/idea-register.md) | Every idea: adopted, roadmap, maybe, postponed, dismissed |
| [TRACKER.md](TRACKER.md) / [CURRENT-STATE.md](CURRENT-STATE.md) | Tasks and current truth |
| [AGENTS.md](AGENTS.md) | Rules for anyone, human or agent, working here |

## Install

No released or catalog-listed installation yet. Once listed in the Hermes plugin catalog:
`hermes plugins install spoonmaster`.

## Development slice

Use Python 3.11-3.14 and uv. The runtime is standard-library only; the dev group
pins Ruff 0.15.6. The lock uses a 2026-11-01 release cutoff. Install wheels only:

```sh
uv sync --frozen --no-build --python 3.13
.venv/bin/ruff format --check .
.venv/bin/ruff check .
.venv/bin/python -m unittest discover -v
sh .standards/check-standards.sh
git diff --check
```

The public-landmark probe is explicit and performs one network request:

```sh
.venv/bin/python -m spoonmaster.probe --live
```

The provisional `spoon_candidates` tool accepts explicit latitude/longitude,
radius (1-2,000 metres, default 1,600), and result limit (1-20, default 10). It
returns distance-sorted evidence, not recommendations. Tool registration is tested
against a mock context and a separately loaded directory package. The manifest
targets Hermes >=0.21.5, the package version declared by release `v2026.9.24`.
Real `hermes plugins doctor . --ci`, `hermes plugins validate . --install-deps` and
all 104 tests passed on an existing Hermes runtime with Python 3.14.9. Local Python
3.11/3.13 passes 103 tests and skips the one real-host identity test. Profile
deletion and removal of the copied files and temporary root were verified.

`spoon_verify_hours` accepts `venue_ids` from discovery and `stage` (`finalists` for
one to three venues, `selected` for exactly one). The card tools below enforce this sequence;
use this lower-level tool for additional evidence inspection. It attempts the linked venue page, retains source
URLs and timestamps, and returns confirmed, unknown or conflicting evidence. Selection
rechecks unresolved or stale evidence; fresh confirmed checks can be reused for
15 minutes. There is no open-at-arrival guarantee. Known `country_code` values JP, TH,
ID and KR allow local phone numbers to become international `tel:` links. Missing hours
produce call advice; missing or ambiguous numbers remain explicit. The visible number
is a fallback for channels that do not render telephone links. Telegram tap behavior
has not been tested.

The [source ladder](docs/source-ladders.md#progressive-hours-adapter-t1-pilot) defines
the exact verification labels and network limits. Unstructured Japanese hours are
returned as unverified excerpts for host review, not silently treated as a parsed
schedule. Repeat the live three-venue exercise with
`.venv/bin/python -m spoonmaster.probe --live --verify-demo`; it also accepts `--input`
with saved OSM JSON to avoid repeating discovery. The demo then makes live venue reads.

`spoon_evaluate` checks every returned candidate from the latest search using its
`search_id`, the user's `origin_confirmed` answer, optional explicitly stated
`dietary_restrictions` and `excluded_venue_ids`. Optional `expected_arrival` (ISO timestamp
with UTC offset) and `venue_timezone` (IANA name, such as `Asia/Tokyo`) enable weekly
schedule math. No ETA or time zone is guessed. Weekly matching is not confirmation of
date-specific availability; last order and other missing facts remain unknown.

Each gate returns pass, fail or unknown with a reason and source links where evidence
exists. Explicit failures exclude a venue; any unknown leaves it unresolved. The
summary counts evaluated, excluded and unresolved venues separately and discloses
discovered venues omitted by the result limit. This does not rank or recommend places.

`/why` lists failures and unknowns, three venues per page (`/why 2` continues).
`spoon_ledger` returns one complete venue per page with all ten checks and source links;
follow `next_page` until null for the complete ledger. Both show the original evaluation
time. Re-run `spoon_evaluate` after hours verification or changed outing constraints.
`spoon_recommend` accepts the same outing inputs, plus optional `country_code`,
`travel_mode` and three-letter `home_currency`. It attempts hours verification for
up to three finalists and returns complete provisional cards with explicit unknowns.
Ranking uses supported saved cuisine/venue preferences, then distance, with a distinct
listed cuisine for the wildcard. Restaurant quality is not inferred. Tentative tastes
receive less weight; context-bound preferences apply only to explicitly matching
`taste_context` tags (season, time, occasion, company). Known failures, duplicate venues
and weekly-predicted closures cannot fill slots. Missing prices leave requested
`mode: price_tiers` slots empty rather than inventing spend estimates.

After the user chooses, call `spoon_select` with `search_id` and a displayed `venue_id`.
It rechecks missing, conflicting or stale hours, retains sourced call links and warns
against proceeding when a weekly schedule predicts closure. The user initiates any
call. New recommendation requests invalidate old choices even when verification is
unavailable; new searches and re-evaluation also invalidate old choices. Outings older
than 15 minutes require reconfirmation before selection.

These operations require Hermes's conversation context; a model-supplied session ID
cannot select another conversation's records. Missing context fails closed.

`scripts/check-hermes.py --source <checkout> --python <venv-python>` repeats that
model-free test using an already installed Hermes runtime. It creates an isolated
Hermes root, a named profile without aliases or bundled skills, and a plugin copy;
enables the plugin, runs doctor/validate and the tests, then tears down the profile
and root even on failure. Child processes receive an explicit environment allowlist
without inherited credentials. Hermes may prepare dependencies inside that temporary
root; this can take several minutes. Remote execution still needs named authorization.

## Optional taste memory

In a private chat or local CLI, `/spoon enable` opts into local structured taste storage.
`spoon_feedback` records the user's reported preferences and returns the exact saved
additions/changes, situational items and rejected inferences. The agent must relay that
diff. Failed writes never claim a saved change. Feedback can affect the next pick when
it matches a venue's listed cuisine or exact OSM venue ID; dish, attribute and vibe
preferences await supporting venue evidence. Taste matches never override hard gates.

Saved tastes survive restarts and new sessions. The documented Hermes session-context
API reconnects a verified private sender automatically; `/spoon profile` is the fallback
when a surface lacks that context. Local CLI uses its own profile-local identity.
Different messaging identities, channels and CLI are not silently merged. Shared chats,
cron context and model-supplied identity are denied; group merging remains T10.

- `/spoon profile` views tastes and their scopes; `/spoon export` returns the same
  structured profile in the private conversation.
- `/spoon confirm <id>` makes an item durable. Model requests for durable scope remain
  tentative until this direct confirmation, so one bad meal is not a permanent dislike.
- `/spoon correct <id> like|dislike|neutral` corrects polarity; `/spoon remove <id>`
  removes one item. Remove and report again to change an item's wording or context.
- `/spoon pause` stops profile use and learning; `/spoon enable` resumes them.
- `/spoon delete confirm` deletes only that identity's plugin taste profile and clears
  its in-memory choices. It does not erase Hermes transcripts or external backups.

Health/allergy storage is not implemented; tool instructions prohibit saving it in taste
fields. Household restrictions and their separate consent remain T8. Profile controls
are portable text commands; Telegram delivery has not yet been exercised end to end.

## Data and privacy

This slice sends coordinates, radius and a restaurant query to
`https://overpass-api.de/api/interpreter`, plus an identifying Spoonmaster user agent.
The service receives the caller's IP address. Requests use TLS, one fixed endpoint,
no redirects, no automatic retries, a 2 MiB response cap and 35-second socket timeout
with elapsed-time checks between reads. DNS and a blocked socket read are not a strict
whole-request deadline. The tool admits one query at a time per process and enforces
a 10-second cooldown after each request. This is a pilot, not a public-service quota.

Hours verification additionally contacts the OSM-linked venue's HTTPS host, reading
`robots.txt` and at most one page per pass. Each server receives the caller's IP and
Spoonmaster user agent. Public-address validation, TLS hostname checks, IP pinning,
no redirects, 512 KiB caps and eight-second socket timeouts bound this transport.
One verification call runs at a time with a 10-second cooldown per stage. No browser,
cookies, login, automatic retry or protection bypass is used.

The plugin uses no secrets, model calls, shell commands, telemetry or background jobs. It caches up to 200 public venue records in memory for
30 minutes, plus their verification evidence. Separately, each conversation retains
its latest search origin, returned candidates, gate ledger and displayed venue IDs
with arrival/country/travel/currency options in memory, capped at 100
conversations. Those records expire 30 minutes after discovery; a new search replaces
the previous one, and session-reset/finalize callbacks clear the reported conversation.
Expired records are removed on subsequent store access. Raw dietary lists are not retained
in this cache, but the ledger contains resulting verdicts and any supplied arrival time.
Taste memory is the separate opt-in persistent store: `taste.sqlite3` in the public
`ctx.state.data_dir` under the current Hermes profile's plugin data root, never the
installation tree. The file is created with mode 0600 and stores up to 100 identities
with 100 preferences each: item, kind, polarity, scope, confidence, provenance category,
context tags and update time. Identity keys hash platform/scope/user IDs; CLI uses a
separate local key. This is access-controlled local storage, not encryption at rest.
No raw feedback transcript or exact location history is written to this database.
SQLite transactions and revision checks prevent partial/stale writes; corrupt data
fails closed. Secure deletion clears removed database records; storage media and
external backups are outside that guarantee. Preferences returned through tools or
card explanations can enter Hermes transcripts and the configured model provider.

The development host-test script invokes
the existing Hermes CLI and removes only its own temporary test tree. Network proxy
settings are not inherited. Hermes may retain tool arguments/results in its
own transcript, and source services have their own logging policies. Website links are
source claims about venue identity, not proof of ownership. Source text is untrusted data.

Map and directions links are built from mapped coordinates using
[Google Maps URLs](https://developers.google.com/maps/documentation/urls/get-started).
Generating a link makes no Google request. Opening directions shares the origin and
destination with Google; no travel time is inferred from straight-line distance.

Data is attributed to [OpenStreetMap contributors under ODbL 1.0](https://www.openstreetmap.org/copyright).
OSM-only hours coverage failed the original data gate; D-013 replaced that acceptance
with progressive checks of the finalists and selected venue. Open-Meteo, broader site
parsers, optional APIs and household profile merging remain planned.
