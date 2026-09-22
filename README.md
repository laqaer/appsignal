# AppSignal

iOS chart intelligence prototype: Apple Top Charts ingested daily, enriched with iTunes lookup data, and scored with transparent, labeled estimates.

**Live:** https://myrmitis.github.io/appsignal/

## Run locally

```sh
python3 -m http.server 8903
```

Open http://localhost:8903

## Pipeline

```sh
python3 pipeline/ingest.py && python3 pipeline/estimate.py
```

`ingest.py` pulls Apple RSS feeds (topfree / topgrossing / toppaid, limit=50) plus iTunes lookup into `data/appintel.db`. `estimate.py` writes `data/live.json`. Velocity uses rating-count deltas between sqlite snapshots, so the db is committed.

## Method

`dl_day = 20000 * (50/rank)^0.7`; paid revenue = `price * dl * 0.7`; free revenue = grossing x `0.12`, others x `0.04`; velocity = rating-count delta per day. See `data/METHOD.md`.

## Real vs estimated vs demo

- **Real:** chart ranks, app metadata, and App Store screenshots from Apple's public RSS + iTunes lookup.
- **Est:** all download/revenue/velocity numbers (labeled `est`), derived from the method above.
- **Keywords:** title/genre tokens. Not ranked search volume.
- **Empty:** Ads (Meta Ad Library token) and Viral (YouTube Data API key).

Not affiliated with appkittie.
