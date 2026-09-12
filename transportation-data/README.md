# Transportation snapshot workflow

Source dates remain authoritative metadata, not freshness claims. Current
snapshot was checked on 2026-09-12 but was not verified current on that date.

## Rebuild normalized data

```bash
cd backend
uv run --extra data python -m app.data.ingest transport-pdf \
  --pdf "../transportation-data/Peta Integrasi Angkutan Umum.pdf" \
  --routes-csv "../transportation-data/trans-jogja.csv" \
  --activities-csv "../transportation-data/mapid-transport-activities.csv" \
  --activities-supplement "../transportation-data/mapid-ev3-activity-supplement.csv" \
  --output "../transportation-data/normalized" \
  --as-of 2026-09-12
```

`normalized/manifest.json` records source hashes, row counts, warnings,
effective dates, and unverified freshness status. `bus_segments.csv` contains
median adjacent-stop times derived from published timetable columns.

## Review EV3 stop coordinates

`review/ev3_stop_match_review.v2.csv` contains unresolved EV3 stops and up to
three fuzzy Activity candidates. For a valid match:

1. Put `approved` in `decision` for one candidate only per stop.
2. Fill `reviewer` and ISO date/time in `reviewed_at`.
3. Add reasoning to `notes`.
4. For a blank unmatched row, find correct source record in
   `normalized/activity_stop_catalog.csv` and copy its `source_id` into
   `candidate_activity_id`.

Never supply guessed coordinates. Add or re-harvest Activity survey data when
catalog has no correct stop.

## Validate, then import

```bash
cd backend
uv run python -m app.data.ingest transport-pilot \
  --snapshot "../transportation-data/normalized" \
  --route EV3 \
  --reviews "../transportation-data/review/ev3_stop_match_review.v2.csv" \
  --skip-stop-sequence 3 \
  --skip-reason "JCM Timur Activity coordinate unavailable after survey session closed"
```

Validation performs no database writes. Submission pilot explicitly omits
source position 3 (JCM Timur), while combining its two adjacent published
segment times so through-travel remains correct. Once validation passes:

```bash
uv run python -m app.data.ingest transport-pilot \
  --snapshot "../transportation-data/normalized" \
  --route EV3 \
  --reviews "../transportation-data/review/ev3_stop_match_review.v2.csv" \
  --skip-stop-sequence 3 \
  --skip-reason "JCM Timur Activity coordinate unavailable after survey session closed" \
  --apply
```

Import is idempotent. It reuses Activity-backed stops, reconciles one
source-owned EV3 route, and attaches effective/freshness metadata to route
source and newly inserted stop raw data.
