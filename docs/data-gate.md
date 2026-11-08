# Shibuya data gate

The result below preserves the original coverage experiment. D-013 superseded its
majority-hours acceptance with progressive verification of the finalists and selection.

## Progressive verification exercise (2026-11-08)

`python -m spoonmaster.probe --input <saved-osm-json> --verify-demo` attempted all three
public demo venues. Between 21:31:25 and 21:31:33 UTC, Miami Garden and Hakuhou returned
Japanese hours excerpts; FATBURGER failed DNS resolution and stayed unknown. Selecting
Miami Garden triggered a second direct pass, retained source/retrieval time and returned
the page's phone as `tel:+81334612401` with advice to call. OSM replay timestamps remained
null rather than being invented. The two pages are linked in the original evidence below.

All three automatic hours verdicts remained unknown: the live pages did not satisfy
the conservative structured-hours/branch-match contract. Retrieved prose is available
for host review. This proves attempts, evidence retention and the selected call fallback,
not broad hours-parsing coverage, recommendation quality, arrival checks or Telegram taps.

## Original coverage experiment

T4 replay check (2026-11-08): evaluating the first 20 candidates from the saved public
snapshot with one synthetic venue veto returned 1 excluded, 19 unresolved and 0 eligible.
The summary explicitly reported 833 other discovered venues as not evaluated, and
`/why` page 7 retained the final candidate's veto reason. No retrieval time was invented
for the replay and no recommendation was inferred from missing evidence.

T1 result, 2026-11-08: **the OSM-only hours criterion fails**. Discovery works,
and two manually inspected venue pages supply additional facts. This is not yet
an end-to-end recommendation or an automated website-enrichment result.

## Reproduce

From the repository root, after the development setup in [README](../README.md):

```sh
.venv/bin/python -m spoonmaster.probe --live
```

This makes one request for restaurants within 1,600 metres of a public Shibuya
landmark (35.6595, 139.7005), a synthetic origin unrelated to any person's travel.
It prints JSON without saving data. `--input <file>` replays a previously saved
Overpass JSON response offline. Replay does not invent a retrieval timestamp.

## Observed coverage

The adapter's live run completed at 2026-11-08 20:05:56 UTC. A separate curl GET
and offline replay returned the same counts. The initial curl POST returned 502;
a final adapter check also returned a sanitized `source_http_error`. Live source
availability is intermittent in this sample. There is no automatic retry or
alternate endpoint in the adapter, and an HTTP failure returns `unverified`, not
an empty successful candidate set.

| Measure | Count |
|---|---:|
| Source restaurant objects | 854 |
| Inside radius after exact coordinate-distance filtering | 853 |
| Excluded because the returned coordinate was outside radius | 1 |
| Any opening-hours tag | 198 (23.2% of candidates) |
| Parsed conservative weekly hours | 174 (20.4%) |
| Missing or unsupported hours | 679 |
| Website links | 170 |
| Cuisine tags | 487 |

The denominator is all 853 candidates, not just the 198 carrying hours. Even a
complete OSM-hours parser cannot get majority coverage from these tags. The
current parser deliberately leaves holidays, dates, overrides and extended-hour
notation such as `16:00-29:00` unknown. Parsed hours remain source claims; retrieval
time does not prove freshness, and no open-at-arrival verdict is made.

OSM ways and relations use their supplied bounding-box centre, not an entrance.
Distinct OSM objects may represent one business. Counts are objects, not a claim
of unique or complete restaurant coverage. Chains are included in this data test.

The first curl snapshot's OSM base timestamp was 2026-11-08 20:00:35 UTC; SHA-256:
`c28eb0a8c74750831020556aab1136746d3c71159ac7feeb3550321b6321952e`.
Raw snapshots remain temporary local test data, not committed fixtures.
Data attribution: [OpenStreetMap contributors, ODbL 1.0](https://www.openstreetmap.org/copyright).

## Website spot checks

Four URLs supplied by OSM were opened individually through the web research tool
on 2026-11-08. These checks do not authorize recurring crawling or establish a
site's permitted automation policy. Retrieved pages may be cached by that tool.

| OSM object | Venue page | Evidence seen | Limit |
|---|---|---|---|
| node/12332999987 | [Miami Garden Shibuya 2](https://miami-garden.jp/shop_shibuya2.html) | Branch identity; opens 11:00, closes 23:00 Sunday-Thursday and midnight Friday-Saturday; payment and seating details | OSM has no hours; no last-order or complete meal-spend claim from this check |
| node/1424672779 | [Hakuhou Shibuya](https://hakuhou.owst.jp/) | Branch identity; lunch/dinner hours, last orders, Monday closure; menu prices and stated dinner budget JPY 3,001-4,000 | OSM has no hours; seasonal exceptions stated; source's claims, not independently verified service availability |
| node/5763313579 | [FATBURGER](https://www.fatburger.tokyo/) | Fetch returned 502 | No website facts inferred |
| node/12452551995 | [Matsue](https://www.matsue.cc/jp/scsq/) | Fetch returned 403 | No retry, bypass or website facts inferred |

Two successful pages establish that useful enrichment exists. This four-page
sample does not establish coverage, extraction reliability or request latency for
the full candidate pool. No review text or dietary-safety evidence was collected.

## Decision needed before T1 can pass

Keep the accepted criterion unchanged. Determine whether permitted website/host
search enrichment can supply hours for most candidates, or explicitly approve a
narrower acceptance criterion based on an evidence-qualified shortlist. This is
a proposal, not an adopted scope change. Better parsing alone cannot close the gap.

The [Overpass operator's usage guidance](https://dev.overpass-api.de/overpass-doc/en/preface/commons.html)
also discourages relying on shared public instances as a consumer-app backend.
This small, manual pilot is not evidence that the same endpoint is an appropriate
public-release dependency. Resolve the source-serving policy before release.
