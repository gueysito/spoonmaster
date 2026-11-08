# Spoonmaster

A Hermes Agent plugin that helps you decide where to eat right now. It learns your
taste, checks the right local sources for where you are, shows the reasoning behind
its pick, and improves from what actually happened at the table.

Status: pre-alpha. Spec, architecture and plan only; no installable plugin yet.
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
| [docs/demo.md](docs/demo.md) | 90-second demo spine and alternative flows |
| [DECISIONS.md](DECISIONS.md) | Settled choices and their alternatives |
| [docs/idea-register.md](docs/idea-register.md) | Every idea: adopted, roadmap, maybe, postponed, dismissed |
| [TRACKER.md](TRACKER.md) / [CURRENT-STATE.md](CURRENT-STATE.md) | Tasks and current truth |
| [AGENTS.md](AGENTS.md) | Rules for anyone, human or agent, working here |

## Install

Not available yet. Once listed in the Hermes plugin catalog:
`hermes plugins install spoonmaster`.

## Data and privacy

The baseline uses free, keyless sources: OpenStreetMap, Open-Meteo and venues' own
websites. Optional sources run only through free API tiers or the host's own tools.
Taste profiles stay in the Hermes profile's plugin storage; exact locations are not
stored. Network calls and stored data will be disclosed in full with the first release.
