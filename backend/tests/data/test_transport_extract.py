import csv
import json
from datetime import date
from pathlib import Path

from app.data.transport_extract import (
    OUTPUT_FIELDS,
    derive_bus_segments,
    extract_transport_snapshot,
    match_stops_to_activities,
    normalize_stop_name,
    stop_id_for,
)


def _stop(raw_name: str) -> dict[str, object]:
    normalized = normalize_stop_name(raw_name)
    return {
        "stop_id": stop_id_for("bus", raw_name),
        "mode": "bus",
        "stop_name": raw_name,
        "canonical_name": normalized.canonical,
        "direction_code": normalized.direction,
        "aliases": [raw_name],
    }


def _activity(
    source_id: str,
    raw_name: str,
    longitude: float,
    latitude: float,
    observed_at: str,
) -> dict[str, object]:
    normalized = normalize_stop_name(raw_name)
    return {
        "source_id": source_id,
        "name": raw_name,
        "canonical_name": normalized.canonical,
        "direction_code": normalized.direction,
        "longitude": longitude,
        "latitude": latitude,
        "observed_at": observed_at,
    }


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_stop_normalization_preserves_platform_identity() -> None:
    assert normalize_stop_name("Halte TJ Condong Catur (Utara)").canonical == "condongcatur"
    assert normalize_stop_name("Halte TJ Condong Catur (Utara)").direction == "N"
    assert normalize_stop_name("TPB Malioboro 3").canonical == "malioboro 3"
    assert normalize_stop_name("TPB Malioboro 3").direction == ""
    assert normalize_stop_name("Halte Trans Jogja - Kricak").canonical == "kricak"
    assert normalize_stop_name("TPB Trans Jogja - Badran").canonical == "badran"
    assert (
        normalize_stop_name("Kondisi Bus Stop Trans Jogja - Atakrib Jl. Magelang").canonical
        == "atakrib jalan magelang"
    )


def test_bus_segments_only_join_adjacent_source_rows() -> None:
    provenance = {
        "source_file": "map.pdf",
        "source_page": 7,
        "effective_from": "2025-12-01",
        "effective_until": "",
        "source_last_updated": "",
        "freshness_as_of": "2026-09-12",
        "freshness_status": "unverified",
    }
    rows = [
        {
            "trip_id": "one",
            "route_id": "EV3",
            "stop_sequence": sequence,
            "stop_id": stop_id,
            "scheduled_time_local": time,
            "day_offset": 0,
            **provenance,
        }
        for sequence, stop_id, time in [(1, "a", "05:00"), (2, "b", "05:02"), (4, "d", "05:05")]
    ]

    assert derive_bus_segments(rows) == [
        {
            "route_id": "EV3",
            "from_stop_sequence": 1,
            "to_stop_sequence": 2,
            "from_stop_id": "a",
            "to_stop_id": "b",
            "travel_time_s": 120,
            "observation_count": 1,
            "statistic": "median",
            "is_estimated": True,
            **provenance,
        }
    ]


def test_activity_matching_only_assigns_one_close_exact_group() -> None:
    stops = [_stop("TPB Alpha"), _stop("Halte Beta"), _stop("Halte Gamma (Utara)")]
    activities = [
        _activity("alpha-old", "Halte Alpha", 110.0, -7.0, "2026-01-01T00:00:00Z"),
        _activity("alpha-new", "Halte Alpha", 110.00001, -7.0, "2026-02-01T00:00:00Z"),
        _activity("beta-a", "Halte Beta", 110.0, -7.0, "2026-01-01T00:00:00Z"),
        _activity("beta-b", "Halte Beta", 110.001, -7.0, "2026-02-01T00:00:00Z"),
        _activity("gamma", "Halte Gamma", 110.0, -7.0, "2026-01-01T00:00:00Z"),
    ]

    matched, candidates = match_stops_to_activities(stops, activities, date(2026, 9, 12))
    by_name = {row["stop_name"]: row for row in matched}

    assert by_name["TPB Alpha"]["match_status"] == "matched_exact"
    assert by_name["TPB Alpha"]["matched_activity_id"] == "alpha-new"
    assert by_name["Halte Beta"]["match_status"] == "ambiguous_exact"
    assert by_name["Halte Beta"]["longitude"] == ""
    assert by_name["Halte Gamma (Utara)"]["match_status"] == "review_fuzzy"
    assert by_name["Halte Gamma (Utara)"]["longitude"] == ""
    assert {row["match_reason"] for row in candidates} == {"ambiguous_exact", "fuzzy"}


def test_extracts_transport_snapshot_with_provenance_and_stable_csvs(tmp_path: Path) -> None:
    repository = Path(__file__).resolve().parents[3]
    inputs = {
        "pdf_path": repository / "transportation-data/Peta Integrasi Angkutan Umum.pdf",
        "routes_csv_path": repository / "transportation-data/trans-jogja.csv",
        "activities_csv_path": repository / "transportation-data/mapid-transport-activities.csv",
        "activities_supplement_path": repository
        / "transportation-data/mapid-ev3-activity-supplement.csv",
        "as_of": date(2026, 9, 12),
    }
    first = tmp_path / "first"
    second = tmp_path / "second"

    counts = extract_transport_snapshot(output_dir=first, **inputs)
    extract_transport_snapshot(output_dir=second, **inputs)

    assert counts == {
        "routes.csv": 20,
        "service_profiles.csv": 44,
        "stops.csv": 668,
        "route_stops.csv": 957,
        "bus_trips.csv": 126,
        "bus_stop_times.csv": 6813,
        "bus_segments.csv": 213,
        "fares.csv": 6,
        "rail_services.csv": 6,
        "rail_trips.csv": 87,
        "rail_stop_times.csv": 525,
        "stop_match_candidates.csv": 278,
        "activity_stop_catalog.csv": 321,
    }
    for filename in OUTPUT_FIELDS:
        assert (first / filename).read_bytes() == (second / filename).read_bytes()

    routes = _read_csv(first / "routes.csv")
    assert {row["route_id"] for row in routes} >= {"1A", "12", "EV3"}
    assert {row["effective_from"] for row in routes} == {"2026-01-01"}
    assert {row["source_last_updated"] for row in routes} == {"2025-12-21"}

    bus_trips = _read_csv(first / "bus_trips.csv")
    assert {row["route_id"] for row in bus_trips} == {"12", "13", "14", "EV3"}
    assert {row["effective_from"] for row in bus_trips} == {"2025-12-01"}

    bus_segments = _read_csv(first / "bus_segments.csv")
    assert sum(row["route_id"] == "EV3" for row in bus_segments) == 27
    assert {row["statistic"] for row in bus_segments} == {"median"}
    assert {row["freshness_status"] for row in bus_segments} == {"unverified"}

    rail_trips = _read_csv(first / "rail_trips.csv")
    assert {row["effective_from"] for row in rail_trips} == {""}
    assert {row["source_last_updated"] for row in rail_trips} == {"2025-02-01"}
    assert any(row["service_days"] == "fri_sat_sun" for row in rail_trips)

    rail_stop_times = _read_csv(first / "rail_stop_times.csv")
    assert any(row["day_offset"] == "1" for row in rail_stop_times)

    stops = _read_csv(first / "stops.csv")
    for row in stops:
        if row["match_status"] != "matched_exact":
            assert row["longitude"] == row["latitude"] == ""

    manifest = json.loads((first / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["schema_version"] == 2
    assert manifest["freshness_status"] == "unverified"
    assert manifest["freshness_as_of"] == "2026-09-12"
    assert [warning["code"] for warning in manifest["warnings"]] == [
        "non_monotonic_source_time",
        "non_monotonic_source_time",
        "non_monotonic_source_time",
    ]
