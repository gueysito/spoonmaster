# Spoonmaster

A Hermes Agent plugin that helps you decide where to eat right now. It learns your
taste, checks the right local sources for where you are, shows the reasoning behind
its pick, and improves from what actually happened at the table.

Status: pre-alpha. Evidence-only discovery and a Hermes plugin scaffold work locally;
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
all 20 tests passed on an existing Hermes runtime with Python 3.14.9. Profile
deletion and removal of the copied files and temporary root were verified.

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

The plugin uses no secrets, model calls, website fetches, shell commands, telemetry,
background jobs or plugin-managed storage. The development host-test script invokes
the existing Hermes CLI and removes only its own temporary test tree. Network proxy
settings are not inherited. The plugin does not save the origin, but Hermes may
retain tool arguments/results in its
own transcript, and Overpass has its own logging policy. Website links are unverified
source metadata, not approved fetch targets. Source text is untrusted data.

Data is attributed to [OpenStreetMap contributors under ODbL 1.0](https://www.openstreetmap.org/copyright).
OSM-only hours coverage failed the initial data gate; see the linked results above.
Open-Meteo, venue-site adapters, optional APIs and profile storage remain planned.
