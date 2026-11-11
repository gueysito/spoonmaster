# Spoonmaster

A Hermes plugin for choosing where to eat using local reviews, current venue facts
and your optional tastes. Status: local pilot, not a released catalog plugin.
Current implementation and verification: [CURRENT-STATE](CURRENT-STATE.md) and [TRACKER](TRACKER.md).

Tell the agent where you are or plan to be and what sounds good. A city or neighborhood
is enough; a location pin is optional where supported. It uses the current time unless
you specify another time. It does not infer your location from your device or IP.

The agent compares relevant places using independent local recommendations and official
menus/hours, then returns a pick and up to two distinct alternatives with food, budget,
published hours, caveats, sources and clickable named-place Google Maps links. Missing
facts stay unconfirmed. `/why` explains the actual comparison, including rejected places;
it does not claim every nearby restaurant was evaluated.

## How it works

`spoon_dine` starts or replaces a request. `spoon_research` runs up to three independent
host searches/reads together, retaining evidence for `spoon_present`. Single operations
still work. A request permits 12 research operations and expires after 30 minutes.
A model round trip is one exchange needed to choose and invoke a tool; batching reduces
those exchanges. It does not guarantee a fixed answer time. The agent reports what it
is checking and why between calls. Host-delivered steering replaces the request; explicit
cancellation clears it. Some hosts queue user input during a running call.

The model interprets quality, branch identity and fit. Code checks retained quotations
and URLs, excludes declared closure/conflict, avoids repeated brands and renders the
comparison. Matching a quote is not proof that the interpretation is correct. Area
searches require no map match. Exact distance or travel-time claims require evidence.
When a supported distance exceeds half a mile, country-appropriate ride-service links
may appear. They open the service, with no fare, pickup or booking prefilled.

Available host routes are `research_search`, `research_read`, `web_search`, `web_extract`
and `browser_exec`. Actual availability varies by installation. Host permissions,
provider allowances, website terms and access restrictions still apply. The plugin
adds no credentials, subscriptions or provider configuration and never bypasses logins
or bot protection. Browser operations are serialized per conversation.

## Personalization and controls

Food search works without saving anything. `/spoon now` starts that path.
`/spoon personalize` offers six optional 1/2 choices. You can also describe favorite
meals, flavors, atmosphere, budget, drinks/dessert and usual company in your own words.
Host-transcribed voice uses the same flow; this plugin does not set up microphones or
speech services. Ambiguous dietary transcription must be clarified.

- `/spoon enable`: turns on optional taste memory and learning, not restaurant search.
- `/spoon profile`: shows readable saved tastes. `/spoon export` returns full structured data.
- `/spoon pause`: stops saved-taste use/learning while preserving the profile.
- `/spoon confirm <id>`: makes a tentative preference lasting.
- `/spoon correct <id> like|dislike|neutral` or `/spoon remove <id>`: edits one preference.
- `/spoon delete confirm`: removes this identity's tastes, companions, city lists and
  onboarding records. Hermes transcripts and backups are separate.

Taste feedback has a visible change receipt. Unchosen onboarding choices never become
dislikes. One meal's needs can remain temporary. Health/allergy data must not enter
taste fields; saving dietary needs requires separate companion consent.

## Companions and reusable sources

Ask to prepare a family/friend/coworker group, review the full preview, then use its
`/spoon companions save <token>` command. Dietary fields require `save-sensitive`.
When eating together, the agent previews exactly who is attending and which rules apply.
`/spoon companions use <token>` confirms that party for the current request only.
Starting a new request clears the attachment. Selected members' ages, dietary needs,
likes/dislikes and selected group rules inform the model; allergy safety is never
established by a menu or review. Confirm handling directly with the venue.

`/spoon companions list` views groups; `delete <label> confirm` removes a group;
`/spoon companions solo` clears current company and the request without deleting groups.
Corrections use a full replacement preview. Cross-agent profile merging remains planned.

Bundled source lists cover Japan, Thailand, Indonesia, NYC and SF; the same research
principles apply elsewhere. Ask to view or edit a city's sources. The profile tool can
stage an attributed replacement; `/spoon locale confirm <token>` saves it for review
within 30 days. `/spoon locale show <country> <city>` displays it and
`/spoon locale forget <country> <city>` removes it. Source-list management is optional
and never blocks finding food. A saved list is guidance, not website access permission.
Details and source references: [source ladders](docs/source-ladders.md).

## Data and privacy

The plugin delegates public food/area/venue queries to installed host tools. Provider
and website logging/allowances remain host-owned. Instructions prohibit private
addresses, names and health details in public queries. Source text is untrusted data.
No direct map endpoint, custom page scraper, telemetry, background job, model client
or shell tool is part of plugin runtime. The development scripts invoke Hermes only
inside owned test profiles.

Evidence and requests are process-local: at most 100 conversations, 12 operations each,
16,000 excerpt characters per operation, 128 citation URLs and 16 best-effort source
pairs. Requests expire after 30 minutes and clear on reset/finalization/replacement.
In-flight host calls finish under host timeouts; their stale results are discarded.

Optional SQLite data lives in Hermes's profile-specific `ctx.state.data_dir`, with mode
0600. This is local access control, not encryption. Taste records store item, kind,
polarity, scope, confidence, provenance, context and timestamps, up to 100 preferences
per identity and 100 identities. No raw meal diary or exact-location history is stored.
Onboarding stores status/attempt/reminder markers; draft answers expire after two hours.
Companions allow 20 groups per identity, 12 members/20 rules per group, up to 20 KB.
Companion previews/attachments expire after 15 minutes. City lists allow 20 cities per
identity and eight sources per city, with review/retrieval dates. Confirmation previews
expire after 15 minutes. Identity is derived from verified private host context; CLI has
a local identity. Revision checks protect writes; corrupt records fail closed.

Viewing/using private data may put it in Hermes transcripts and the configured model
provider. Deletion removes local records, not host transcripts, storage-media remnants
or external backups. Opening Maps or ride links sends information to those services;
merely generating the links makes no request.

## Development and verification

Runtime uses Python 3.11–3.14 standard library only. Development pins Ruff 0.15.6.

```sh
uv sync --frozen --no-build --python 3.13
.venv/bin/ruff format --check .
.venv/bin/ruff check .
.venv/bin/python -B -m unittest discover -v
sh .standards/check-standards.sh
git diff --check
```

`scripts/check-hermes.py --source <checkout> --python <venv-python>` creates an isolated
profile, installs the plugin, runs doctor/validate/tests and removes its test tree.
`scripts/interactive-hermes.py` supports `prepare`, `chat`, `check`, `stop` and `cleanup`
with the same runtime arguments plus an owned `--root`. Its profiles stay outside the
live registry. Only public model/provider/backend names are seeded, never credentials
or existing conversations. Remote actions require named authorization. Retained owner
test profiles are removed after testing ends; disposable engineering profiles are
removed after verification. Live agents are not changed by these scripts.

Eight tools and four hooks are documented in [architecture](docs/architecture.md).
Read [AGENTS](AGENTS.md), [product spec](docs/prd.md), [decisions](DECISIONS.md) and
[tracker](TRACKER.md) before code work. Current native and channel verification limits
are explicit in the tracker. Public release/catalog submission, accounts, paid APIs
and live-agent installation require separate authorization.
