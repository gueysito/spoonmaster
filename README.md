# Spoonmaster

A Hermes Agent plugin that helps you decide where to eat right now. It learns your
taste, checks the right local sources for where you are, shows the reasoning behind
its pick, and improves from what actually happened at the table.

Status: pre-alpha. Discovery, progressive hours checks and a reject ledger work locally;
recommendations and taste learning are not implemented. The scaffold passed real-host
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
all 64 tests passed on an existing Hermes runtime with Python 3.14.9. Profile
deletion and removal of the copied files and temporary root were verified.

`spoon_verify_hours` accepts `venue_ids` from discovery and `stage` (`finalists` for
one to three venues, `selected` for exactly one). Call it before showing finalists
and when the user selects a venue. It attempts the linked venue page, retains source
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
These operations require Hermes's conversation context; a model-supplied session ID
cannot select another conversation's records. Missing context fails closed.

`scripts/check-hermes.py --source <checkout> --python <venv-python>` repeats that
model-free test using an already installed Hermes runtime. It creates an isolated
Hermes root, a named profile without aliases or bundled skills, and a plugin copy;
enables the plugin, runs doctor/validate and the tests, then tears down the profile
and root even on failure. Child processes receive an explicit environment allowlist
without inherited credentials. Hermes may prepare dependencies inside that temporary
root; this can take several minutes. Remote execution still needs named authorization.

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

The plugin uses no secrets, model calls, shell commands, telemetry, background jobs
or persistent plugin storage. It caches up to 200 public venue records in memory for
30 minutes, plus their verification evidence. Separately, each conversation retains
its latest search origin, returned candidates and gate ledger in memory, capped at 100
conversations. Those records expire 30 minutes after discovery; a new search replaces
the previous one, and session-reset/finalize callbacks clear the reported conversation.
Expired records are removed on subsequent store access. Raw dietary lists are not retained
in this cache, but the ledger contains resulting verdicts and any supplied arrival time.
The development host-test script invokes
the existing Hermes CLI and removes only its own temporary test tree. Network proxy
settings are not inherited. Hermes may retain tool arguments/results in its
own transcript, and source services have their own logging policies. Website links are
source claims about venue identity, not proof of ownership. Source text is untrusted data.

Data is attributed to [OpenStreetMap contributors under ODbL 1.0](https://www.openstreetmap.org/copyright).
OSM-only hours coverage failed the original data gate; D-013 replaced that acceptance
with progressive checks of the finalists and selected venue. Open-Meteo, broader site
parsers, optional APIs and profile storage remain planned.
