"""Extract the published Yogyakarta transport map into auditable CSV snapshots.

The PDF is a designed map, not a data feed.  This module deliberately supports
the known layouts on pages 3--8 and fails loudly when their table shapes drift.
It never claims that the resulting snapshot is current.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import re
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime
from difflib import SequenceMatcher
from pathlib import Path
from statistics import median
from typing import Any

import pdfplumber

TIME_RE = re.compile(r"^\d{1,2}:\d{2}$")
TRAIN_RE = re.compile(r"^\d{3,4}[A-Z]?$")
ROUTE_ORDER = (
    "1A",
    "1B",
    "2A",
    "2B",
    "3A",
    "3B",
    "4A",
    "4B",
    "5A",
    "5B",
    "6",
    "8",
    "9",
    "10",
    "11",
    "12",
    "13",
    "14",
    "15",
    "EV3",
)
BUS_PAGE_ROUTES = {4: "12", 5: "13", 6: "14", 7: "EV3"}
BUS_TABLE_SHAPES = {
    4: (62, 45, 2607),
    5: (51, 27, 1308),
    6: (76, 32, 2282),
    7: (28, 22, 616),
}
PROVENANCE_FIELDS = (
    "source_file",
    "source_page",
    "effective_from",
    "effective_until",
    "source_last_updated",
    "freshness_as_of",
    "freshness_status",
)

OUTPUT_FIELDS: dict[str, tuple[str, ...]] = {
    "routes.csv": (
        "route_id",
        "route_id_raw",
        "mode",
        "operator",
        "origin",
        "destination",
        *PROVENANCE_FIELDS,
    ),
    "service_profiles.csv": (
        "route_id",
        "basis",
        "service_start_local",
        "service_end_local",
        "service_end_alternate_local",
        "headway_min_minutes",
        "headway_max_minutes",
        "headway_is_approximate",
        "fleet_count",
        "notes",
        *PROVENANCE_FIELDS,
    ),
    "stops.csv": (
        "stop_id",
        "mode",
        "stop_name",
        "canonical_name",
        "direction_code",
        "aliases",
        "match_status",
        "matched_activity_id",
        "longitude",
        "latitude",
        "activity_observed_at",
        "evidence_count",
        "match_as_of",
    ),
    "route_stops.csv": (
        "route_id",
        "stop_sequence",
        "stop_id",
        "stop_name_raw",
        *PROVENANCE_FIELDS,
    ),
    "bus_trips.csv": (
        "trip_id",
        "route_id",
        "trip_sequence",
        "start_stop_id",
        "end_stop_id",
        "scheduled_stop_count",
        "is_estimated",
        *PROVENANCE_FIELDS,
    ),
    "bus_stop_times.csv": (
        "trip_id",
        "route_id",
        "stop_sequence",
        "stop_id",
        "stop_name_raw",
        "scheduled_time_raw",
        "scheduled_time_local",
        "day_offset",
        "is_estimated",
        *PROVENANCE_FIELDS,
    ),
    "bus_segments.csv": (
        "route_id",
        "from_stop_sequence",
        "to_stop_sequence",
        "from_stop_id",
        "to_stop_id",
        "travel_time_s",
        "observation_count",
        "statistic",
        "is_estimated",
        *PROVENANCE_FIELDS,
    ),
    "fares.csv": (
        "fare_id",
        "service_id",
        "product",
        "payment_method",
        "currency",
        "fare_min",
        "fare_max",
        "notes",
        *PROVENANCE_FIELDS,
    ),
    "rail_services.csv": (
        "service_id",
        "mode",
        "operator",
        "name",
        "direction_id",
        "origin",
        "destination",
        *PROVENANCE_FIELDS,
    ),
    "rail_trips.csv": (
        "trip_id",
        "service_id",
        "train_number",
        "service_class",
        "service_days",
        "trip_sequence",
        *PROVENANCE_FIELDS,
    ),
    "rail_stop_times.csv": (
        "trip_id",
        "service_id",
        "train_number",
        "stop_sequence",
        "stop_id",
        "station_name_raw",
        "scheduled_time_raw",
        "scheduled_time_local",
        "day_offset",
        *PROVENANCE_FIELDS,
    ),
    "stop_match_candidates.csv": (
        "stop_id",
        "stop_name",
        "mode",
        "candidate_activity_id",
        "candidate_name",
        "candidate_direction_code",
        "longitude",
        "latitude",
        "observed_at",
        "match_reason",
        "score",
        "rank",
        "evidence_count",
    ),
    "activity_stop_catalog.csv": (
        "source_id",
        "name",
        "canonical_name",
        "direction_code",
        "longitude",
        "latitude",
        "observed_at",
    ),
}


class TransportExtractionError(ValueError):
    """Raised when a source no longer matches its documented layout."""


@dataclass(frozen=True)
class NormalizedStopName:
    canonical: str
    direction: str


@dataclass(frozen=True)
class RailPanel:
    service_id: str
    mode: str
    operator: str
    name: str
    direction_id: int
    stations: tuple[str, ...]
    number_bounds: tuple[float, float, float, float]
    time_bounds: tuple[float, float]


RAIL_PANELS = (
    RailPanel(
        "krl_yogyakarta_palur",
        "rail",
        "KAI Commuter",
        "Commuterline KRL",
        0,
        (
            "Yogyakarta",
            "Lempuyangan",
            "Maguwo",
            "Brambanan",
            "Srowot",
            "Klaten",
            "Ceper",
            "Delanggu",
            "Gawok",
            "Purwosari",
            "Solobalapan",
            "Solojebres",
            "Palur",
        ),
        (40, 85, 280, 610),
        (85, 823),
    ),
    RailPanel(
        "krl_palur_yogyakarta",
        "rail",
        "KAI Commuter",
        "Commuterline KRL",
        1,
        (
            "Palur",
            "Solojebres",
            "Solobalapan",
            "Purwosari",
            "Gawok",
            "Delanggu",
            "Ceper",
            "Klaten",
            "Srowot",
            "Brambanan",
            "Maguwo",
            "Lempuyangan",
            "Yogyakarta",
        ),
        (40, 85, 660, 950),
        (85, 823),
    ),
    RailPanel(
        "yia_yogyakarta_airport",
        "airport_rail",
        "KAI Bandara",
        "KA Bandara YIA",
        0,
        ("Yogyakarta", "Wates", "YIA"),
        (850, 910, 280, 800),
        (910, 1246),
    ),
    RailPanel(
        "yia_airport_yogyakarta",
        "airport_rail",
        "KAI Bandara",
        "KA Bandara YIA",
        1,
        ("YIA", "Wates", "Yogyakarta"),
        (1250, 1310, 280, 800),
        (1310, 1649),
    ),
    RailPanel(
        "prameks_yogyakarta_kutoarjo",
        "rail",
        "KAI Commuter",
        "Commuterline Prameks",
        0,
        ("Yogyakarta", "Wates", "Wojo", "Jenar", "Kutoarjo"),
        (40, 85, 1000, 1160),
        (85, 422),
    ),
    RailPanel(
        "prameks_kutoarjo_yogyakarta",
        "rail",
        "KAI Commuter",
        "Commuterline Prameks",
        1,
        ("Kutoarjo", "Jenar", "Wojo", "Wates", "Yogyakarta"),
        (430, 490, 1000, 1160),
        (490, 823),
    ),
)

_DIRECTIONS = {
    "u": "N",
    "utara": "N",
    "s": "S",
    "selatan": "S",
    "t": "E",
    "timur": "E",
    "b": "W",
    "barat": "W",
}
_DIRECTION_RE = re.compile(r"\s*\((utara|selatan|timur|barat|u|s|t|b)\)\s*$", re.IGNORECASE)
_GENERIC_PREFIX_RE = re.compile(
    r"^(?:(?:aksesibilitas|kondisi|bus\s+stop|tempat\s+pemberhentian\s+bus|halte\s+trans\s+jogja\s*[-–—]|trans\s+jogja\s*[-–—]|halte\s+tj|halte|tpb|tj|portabel|portable|stasiun)\s+)+",
    re.IGNORECASE,
)


def normalize_route_id(value: str) -> str:
    normalized = re.sub(r"\s+", "", value).upper()
    return "EV3" if normalized in {"EV", "EV3"} else normalized


def normalize_stop_name(value: str) -> NormalizedStopName:
    text = unicodedata.normalize("NFKD", value)
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = text.strip().casefold()
    direction = ""
    match = _DIRECTION_RE.search(text)
    if match:
        direction = _DIRECTIONS[match.group(1).casefold()]
        text = text[: match.start()]
    text = _GENERIC_PREFIX_RE.sub("", text)
    text = re.sub(r"\bjl\.?\b", "jalan", text)
    text = re.sub(r"\bcondong\s+catur\b", "condongcatur", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        raise TransportExtractionError(f"stop name normalizes to empty: {value!r}")
    return NormalizedStopName(text, direction)


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value).strip("-")[:40] or "stop"


def stop_id_for(mode: str, value: str) -> str:
    normalized = normalize_stop_name(value)
    key = f"{mode}|{normalized.canonical}|{normalized.direction}"
    digest = hashlib.sha1(key.encode()).hexdigest()[:8]
    suffix = f"-{normalized.direction.lower()}" if normalized.direction else ""
    return f"{mode}-{_slug(normalized.canonical)}{suffix}-{digest}"


def _provenance(
    source_file: str,
    page: int | str,
    as_of: date,
    *,
    effective_from: str = "",
    effective_until: str = "",
    source_last_updated: str = "",
) -> dict[str, Any]:
    return {
        "source_file": source_file,
        "source_page": page,
        "effective_from": effective_from,
        "effective_until": effective_until,
        "source_last_updated": source_last_updated,
        "freshness_as_of": as_of.isoformat(),
        "freshness_status": "unverified",
    }


def _clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _normalize_time(value: str) -> str:
    cleaned = value.replace("꞉", ":").replace(".", ":").strip().rstrip("*")
    match = re.fullmatch(r"(\d{1,2}):(\d{2})", cleaned)
    if not match:
        raise TransportExtractionError(f"invalid time: {value!r}")
    hour, minute = map(int, match.groups())
    if hour > 23 or minute > 59:
        raise TransportExtractionError(f"invalid time: {value!r}")
    return f"{hour:02d}:{minute:02d}"


def _time_minutes(value: str) -> int:
    hour, minute = map(int, value.split(":"))
    return hour * 60 + minute


def _day_offsets(
    times: list[str], *, warning_context: dict[str, Any], warnings: list[dict[str, Any]]
) -> list[int]:
    offsets: list[int] = []
    day_offset = 0
    previous: int | None = None
    for value in times:
        minutes = _time_minutes(value)
        absolute = minutes + day_offset * 1440
        if previous is not None and absolute < previous:
            if previous - absolute > 720:
                day_offset += 1
                absolute += 1440
            else:
                warnings.append(
                    {
                        "code": "non_monotonic_source_time",
                        **warning_context,
                        "previous_minutes": previous,
                        "scheduled_time_local": value,
                        "message": "Source time decreases within one journey; value preserved.",
                    }
                )
        offsets.append(day_offset)
        previous = absolute
    return offsets


def _parse_indonesian_effective_date(text: str) -> str:
    months = {
        "januari": 1,
        "februari": 2,
        "maret": 3,
        "april": 4,
        "mei": 5,
        "juni": 6,
        "juli": 7,
        "agustus": 8,
        "september": 9,
        "oktober": 10,
        "november": 11,
        "desember": 12,
    }
    pattern = r"(\d{1,2})\s+(" + "|".join(months) + r")\s+(\d{4})"
    match = re.search(pattern, text, re.I)
    if not match:
        raise TransportExtractionError("effective date missing from PDF page")
    parsed = date(int(match.group(3)), months[match.group(2).casefold()], int(match.group(1)))
    return parsed.isoformat()


def _parse_ddmmyyyy(value: str) -> str:
    return datetime.strptime(value, "%d/%m/%Y").date().isoformat()


def _require(text: str, pattern: str, description: str) -> None:
    if not re.search(pattern, text, re.I):
        raise TransportExtractionError(f"{description} missing from PDF")


def _parse_page_three(
    page: Any, source_file: str, as_of: date
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    full_text = page.extract_text() or ""
    legend_text = page.crop((0, 280, 330, page.height)).extract_text() or ""
    effective_from = _parse_indonesian_effective_date(full_text)
    updated_match = re.search(r"Last updated\s+(\d{2}/\d{2}/\d{4})", legend_text, re.I)
    if not updated_match:
        raise TransportExtractionError("page 3 last-updated date missing")
    source_last_updated = _parse_ddmmyyyy(updated_match.group(1))
    provenance = _provenance(
        source_file,
        3,
        as_of,
        effective_from=effective_from,
        source_last_updated=source_last_updated,
    )

    route_pattern = re.compile(
        r"^(1A|1B|2A|2B|3A|3B|4A|4B|5A|5B|6|8|9|10|11|12|13|14|15|EV)\s+"
        r"(.+?)\s+-\s+(.+?)\s+±\s*(\d+)\s*menit\b",
        re.I,
    )
    routes: list[dict[str, Any]] = []
    profiles: list[dict[str, Any]] = []
    for raw_line in legend_text.splitlines():
        line = _clean_text(raw_line)
        match = route_pattern.match(line)
        if not match:
            continue
        raw_id, origin, destination, headway = match.groups()
        route_id = normalize_route_id(raw_id)
        routes.append(
            {
                "route_id": route_id,
                "route_id_raw": raw_id,
                "mode": "bus",
                "operator": "TransJogja",
                "origin": origin,
                "destination": destination,
                **provenance,
            }
        )
        profiles.append(
            {
                "route_id": route_id,
                "basis": "map_nominal",
                "service_start_local": "05:30",
                "service_end_local": "20:30",
                "service_end_alternate_local": "",
                "headway_min_minutes": int(headway),
                "headway_max_minutes": int(headway),
                "headway_is_approximate": True,
                "fleet_count": "",
                "notes": "Service ends at nearest stop; published times may change.",
                **provenance,
            }
        )
    if len(routes) != 20 or {row["route_id"] for row in routes} != set(ROUTE_ORDER):
        found = [row["route_id"] for row in routes]
        raise TransportExtractionError(f"page 3 route legend drifted; found {found}")

    for pattern, description in (
        (r"Rp\s*8\.000", "KRL fare"),
        (r"Rp\s*10\.000\s*[–-]\s*60\.000", "airport rail fare"),
        (r"Rp\s*3\.500", "TransJogja cash fare"),
        (r"Rp\s*2\.700", "TransJogja cashless fare"),
    ):
        _require(legend_text, pattern, description)
    fares = [
        {
            "fare_id": "krl-map-regular",
            "service_id": "krl",
            "product": "regular",
            "payment_method": "card_or_gojek",
            "currency": "IDR",
            "fare_min": 8000,
            "fare_max": 8000,
            "notes": "Card available at stations.",
            **provenance,
        },
        {
            "fare_id": "yia-map-range",
            "service_id": "yia",
            "product": "all_services",
            "payment_method": "station_or_online",
            "currency": "IDR",
            "fare_min": 10000,
            "fare_max": 60000,
            "notes": "Combined range printed in map legend.",
            **provenance,
        },
        {
            "fare_id": "transjogja-cash",
            "service_id": "transjogja",
            "product": "regular",
            "payment_method": "cash",
            "currency": "IDR",
            "fare_min": 3500,
            "fare_max": 3500,
            "notes": "",
            **provenance,
        },
        {
            "fare_id": "transjogja-cashless",
            "service_id": "transjogja",
            "product": "regular",
            "payment_method": "qris_or_card",
            "currency": "IDR",
            "fare_min": 2700,
            "fare_max": 2700,
            "notes": "",
            **provenance,
        },
    ]
    routes.sort(key=lambda row: ROUTE_ORDER.index(row["route_id"]))
    profiles.sort(key=lambda row: ROUTE_ORDER.index(row["route_id"]))
    return routes, profiles, fares


def _split_route_stops(value: str) -> list[str]:
    return [_clean_text(part) for part in re.split(r"\s+[–—-]\s+", value) if _clean_text(part)]


def _read_route_csv(
    path: Path, as_of: date, known_routes: set[str]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    expected = {"Jalur", "Jumlah Armada", "Rute", "Jam Operasional", "Rute Yang Dilewati"}
    if not rows or not expected.issubset(rows[0]):
        raise TransportExtractionError(f"route CSV columns changed: {path}")
    route_stops: list[dict[str, Any]] = []
    profiles: list[dict[str, Any]] = []
    provenance = _provenance(path.name, "", as_of)
    for row in rows:
        route_id = normalize_route_id(row["Jalur"])
        if route_id not in known_routes:
            raise TransportExtractionError(f"route CSV contains unknown route {route_id}")
        hours = re.fullmatch(
            r"\s*(\d{1,2}[.:]\d{2})\s*[–—-]\s*(\d{1,2}[.:]\d{2})\s*",
            row["Jam Operasional"],
        )
        if not hours:
            raise TransportExtractionError(f"invalid service hours for route {route_id}")
        profiles.append(
            {
                "route_id": route_id,
                "basis": "route_csv",
                "service_start_local": _normalize_time(hours.group(1)),
                "service_end_local": _normalize_time(hours.group(2)),
                "service_end_alternate_local": "",
                "headway_min_minutes": "",
                "headway_max_minutes": "",
                "headway_is_approximate": "",
                "fleet_count": int(row["Jumlah Armada"]),
                "notes": "Undated source CSV; retained separately from PDF profiles.",
                **provenance,
            }
        )
        for sequence, stop_name in enumerate(_split_route_stops(row["Rute Yang Dilewati"]), 1):
            route_stops.append(
                {
                    "route_id": route_id,
                    "stop_sequence": sequence,
                    "stop_id": stop_id_for("bus", stop_name),
                    "stop_name_raw": stop_name,
                    **provenance,
                }
            )
    if len(rows) != 20 or {normalize_route_id(row["Jalur"]) for row in rows} != known_routes:
        raise TransportExtractionError("route CSV must contain the same 20 routes as page 3")
    return route_stops, profiles


def _cell_is_time(value: Any) -> bool:
    return bool(TIME_RE.fullmatch(_clean_text(value)))


def _parse_bus_header(page: Any, page_number: int, source_file: str, as_of: date) -> dict[str, Any]:
    header = (page.crop((0, 0, page.width, min(150, page.height))).extract_text() or "").replace(
        "꞉", ":"
    )
    compact = "\n".join(_clean_text(line) for line in header.splitlines())
    match = re.search(
        r"(?m)^(\d{1,2})-(\d{1,2})\s+(\d+)\s+"
        r"(\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2})(?:/(\d{1,2}:\d{2}))?\*?$",
        compact,
    )
    if not match:
        raise TransportExtractionError(f"page {page_number} timetable header changed")
    minimum, maximum, fleet, start, end, alternate = match.groups()
    effective_from = _parse_indonesian_effective_date(compact)
    return {
        "route_id": BUS_PAGE_ROUTES[page_number],
        "basis": "timetable_header",
        "service_start_local": _normalize_time(start),
        "service_end_local": _normalize_time(end),
        "service_end_alternate_local": _normalize_time(alternate) if alternate else "",
        "headway_min_minutes": int(minimum),
        "headway_max_minutes": int(maximum),
        "headway_is_approximate": False,
        "fleet_count": int(fleet),
        "notes": "Departure times are estimates and may change.",
        **_provenance(source_file, page_number, as_of, effective_from=effective_from),
    }


def _parse_bus_table(
    page: Any,
    page_number: int,
    source_file: str,
    as_of: date,
    warnings: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    tables = page.extract_tables()
    if not tables:
        raise TransportExtractionError(f"page {page_number} has no table")
    table = max(
        tables,
        key=lambda candidate: sum(_cell_is_time(cell) for row in candidate for cell in row),
    )
    data_rows = [row for row in table if sum(_cell_is_time(cell) for cell in row) >= 5]
    time_columns = sorted(
        {index for row in data_rows for index, cell in enumerate(row) if _cell_is_time(cell)}
    )
    if not time_columns:
        raise TransportExtractionError(f"page {page_number} contains no timetable cells")
    candidate_name_columns = range(min(time_columns))
    counts = {
        index: sum(
            bool(_clean_text(row[index])) and not _cell_is_time(row[index])
            for row in data_rows
            if index < len(row)
        )
        for index in candidate_name_columns
    }
    name_column = max(counts, key=lambda index: (counts[index], index))
    time_count = sum(sum(_cell_is_time(cell) for cell in row) for row in data_rows)
    actual_shape = (len(data_rows), len(time_columns), time_count)
    if actual_shape != BUS_TABLE_SHAPES[page_number]:
        raise TransportExtractionError(
            f"page {page_number} table shape changed: {actual_shape}; "
            f"expected {BUS_TABLE_SHAPES[page_number]}"
        )

    route_id = BUS_PAGE_ROUTES[page_number]
    effective_from = _parse_indonesian_effective_date(page.extract_text() or "")
    provenance = _provenance(source_file, page_number, as_of, effective_from=effective_from)
    named_rows: list[tuple[int, str, list[Any]]] = []
    for stop_sequence, row in enumerate(data_rows, 1):
        stop_name = _clean_text(row[name_column])
        if not stop_name:
            raise TransportExtractionError(
                f"page {page_number} row {stop_sequence} has no stop name"
            )
        named_rows.append((stop_sequence, stop_name, row))

    trips: list[dict[str, Any]] = []
    stop_times: list[dict[str, Any]] = []
    for trip_sequence, column in enumerate(time_columns, 1):
        populated: list[tuple[int, str, str]] = []
        for stop_sequence, stop_name, row in named_rows:
            value = _clean_text(row[column]) if column < len(row) else ""
            if _cell_is_time(value):
                populated.append((stop_sequence, stop_name, value))
        if not populated:
            continue
        trip_id = f"bus-{route_id.lower()}-p{page_number:02d}-c{trip_sequence:03d}"
        normalized_times = [_normalize_time(item[2]) for item in populated]
        day_offsets = _day_offsets(
            normalized_times,
            warning_context={"source_page": page_number, "trip_id": trip_id},
            warnings=warnings,
        )
        trips.append(
            {
                "trip_id": trip_id,
                "route_id": route_id,
                "trip_sequence": trip_sequence,
                "start_stop_id": stop_id_for("bus", populated[0][1]),
                "end_stop_id": stop_id_for("bus", populated[-1][1]),
                "scheduled_stop_count": len(populated),
                "is_estimated": True,
                **provenance,
            }
        )
        for (stop_sequence, stop_name, raw_time), normalized_time, day_offset in zip(
            populated, normalized_times, day_offsets, strict=True
        ):
            stop_times.append(
                {
                    "trip_id": trip_id,
                    "route_id": route_id,
                    "stop_sequence": stop_sequence,
                    "stop_id": stop_id_for("bus", stop_name),
                    "stop_name_raw": stop_name,
                    "scheduled_time_raw": raw_time,
                    "scheduled_time_local": normalized_time,
                    "day_offset": day_offset,
                    "is_estimated": True,
                    **provenance,
                }
            )
    return trips, stop_times


def _is_white(color: Any) -> bool:
    return (
        isinstance(color, (tuple, list))
        and len(color) >= 3
        and all(float(component) >= 0.9 for component in color[:3])
    )


def _parse_rail(
    page: Any, source_file: str, as_of: date, warnings: list[dict[str, Any]]
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    text = page.extract_text() or ""
    updated_match = re.search(r"Last updated\s+(\d{2}/\d{2}/\d{4})", text, re.I)
    if not updated_match:
        raise TransportExtractionError("page 8 last-updated date missing")
    updated = _parse_ddmmyyyy(updated_match.group(1))
    provenance = _provenance(source_file, 8, as_of, source_last_updated=updated)
    words = page.extract_words(extra_attrs=["non_stroking_color"])

    services: list[dict[str, Any]] = []
    trips: list[dict[str, Any]] = []
    stop_times: list[dict[str, Any]] = []
    for panel in RAIL_PANELS:
        services.append(
            {
                "service_id": panel.service_id,
                "mode": panel.mode,
                "operator": panel.operator,
                "name": panel.name,
                "direction_id": panel.direction_id,
                "origin": panel.stations[0],
                "destination": panel.stations[-1],
                **provenance,
            }
        )
        x0, x1, y0, y1 = panel.number_bounds
        train_words = sorted(
            (
                word
                for word in words
                if x0 <= word["x0"] <= x1
                and y0 <= word["top"] <= y1
                and TRAIN_RE.fullmatch(word["text"])
            ),
            key=lambda word: word["top"],
        )
        for trip_sequence, train_word in enumerate(train_words, 1):
            time_words = sorted(
                (
                    word
                    for word in words
                    if panel.time_bounds[0] <= word["x0"] <= panel.time_bounds[1]
                    and abs(word["top"] - train_word["top"]) <= 2
                    and TIME_RE.fullmatch(word["text"])
                ),
                key=lambda word: word["x0"],
            )
            stations = panel.stations
            if panel.mode == "airport_rail" and len(time_words) == 2:
                stations = (panel.stations[0], panel.stations[-1])
            if len(time_words) != len(stations):
                raise TransportExtractionError(
                    f"page 8 train {train_word['text']} in {panel.service_id} has "
                    f"{len(time_words)} times for {len(stations)} stations"
                )
            train_number = train_word["text"]
            trip_id = f"rail-{panel.service_id}-{train_number.casefold()}"
            service_class = (
                "xpress"
                if panel.mode == "airport_rail"
                and any(_is_white(word.get("non_stroking_color")) for word in time_words)
                else "regular"
            )
            service_days = (
                "fri_sat_sun"
                if panel.mode == "airport_rail" and train_number.endswith("F")
                else "not_stated"
            )
            normalized_times = [_normalize_time(word["text"]) for word in time_words]
            day_offsets = _day_offsets(
                normalized_times,
                warning_context={"source_page": 8, "trip_id": trip_id},
                warnings=warnings,
            )
            trips.append(
                {
                    "trip_id": trip_id,
                    "service_id": panel.service_id,
                    "train_number": train_number,
                    "service_class": service_class,
                    "service_days": service_days,
                    "trip_sequence": trip_sequence,
                    **provenance,
                }
            )
            for stop_sequence, (station, time_word, normalized_time, day_offset) in enumerate(
                zip(stations, time_words, normalized_times, day_offsets, strict=True), 1
            ):
                stop_times.append(
                    {
                        "trip_id": trip_id,
                        "service_id": panel.service_id,
                        "train_number": train_number,
                        "stop_sequence": stop_sequence,
                        "stop_id": stop_id_for(panel.mode, station),
                        "station_name_raw": station,
                        "scheduled_time_raw": time_word["text"],
                        "scheduled_time_local": normalized_time,
                        "day_offset": day_offset,
                        **provenance,
                    }
                )

    expected_trip_counts = {
        "krl_yogyakarta_palur": 15,
        "krl_palur_yogyakarta": 12,
        "yia_yogyakarta_airport": 25,
        "yia_airport_yogyakarta": 25,
        "prameks_yogyakarta_kutoarjo": 5,
        "prameks_kutoarjo_yogyakarta": 5,
    }
    actual_trip_counts = Counter(row["service_id"] for row in trips)
    if dict(actual_trip_counts) != expected_trip_counts:
        raise TransportExtractionError(f"page 8 rail table drifted: {dict(actual_trip_counts)}")

    for pattern, description in (
        (r"Rp\s*10\.000\s*[–-]\s*20\.000", "YIA regular fare"),
        (r"Rp\s*40\.000\s*[–-]\s*60\.000", "YIA Xpress fare"),
    ):
        _require(text, pattern, description)
    fares = [
        {
            "fare_id": "yia-page8-regular",
            "service_id": "yia",
            "product": "regular",
            "payment_method": "not_stated",
            "currency": "IDR",
            "fare_min": 10000,
            "fare_max": 20000,
            "notes": "Effective date not stated on page 8.",
            **provenance,
        },
        {
            "fare_id": "yia-page8-xpress",
            "service_id": "yia",
            "product": "xpress",
            "payment_method": "not_stated",
            "currency": "IDR",
            "fare_min": 40000,
            "fare_max": 60000,
            "notes": "Effective date not stated on page 8.",
            **provenance,
        },
    ]
    return services, trips, stop_times, fares


class _StopRegistry:
    def __init__(self) -> None:
        self._records: dict[str, dict[str, Any]] = {}

    def add(self, mode: str, raw_name: str) -> str:
        normalized = normalize_stop_name(raw_name)
        stop_id = stop_id_for(mode, raw_name)
        record = self._records.setdefault(
            stop_id,
            {
                "stop_id": stop_id,
                "mode": mode,
                "canonical_name": normalized.canonical,
                "direction_code": normalized.direction,
                "aliases": set(),
            },
        )
        record["aliases"].add(_clean_text(raw_name))
        return stop_id

    def records(self) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        for value in self._records.values():
            aliases = sorted(value["aliases"], key=lambda item: (len(item), item.casefold()))
            records.append({**value, "stop_name": aliases[0], "aliases": aliases})
        return sorted(records, key=lambda row: row["stop_id"])


def _collect_stops(
    route_stops: list[dict[str, Any]],
    bus_stop_times: list[dict[str, Any]],
    rail_stop_times: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    registry = _StopRegistry()
    for row in route_stops:
        assert registry.add("bus", row["stop_name_raw"]) == row["stop_id"]
    for row in bus_stop_times:
        assert registry.add("bus", row["stop_name_raw"]) == row["stop_id"]
    service_modes = {panel.service_id: panel.mode for panel in RAIL_PANELS}
    for row in rail_stop_times:
        assert (
            registry.add(service_modes[row["service_id"]], row["station_name_raw"])
            == row["stop_id"]
        )
    return registry.records()


def derive_bus_segments(stop_times: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Derive median consecutive-stop travel times from published trip columns.

    Only adjacent source rows contribute. Missing timetable cells therefore do
    not create a synthetic express segment across skipped stops.
    """
    trips: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in stop_times:
        trips[row["trip_id"]].append(row)

    observations: dict[tuple[Any, ...], list[int]] = defaultdict(list)
    provenance: dict[tuple[Any, ...], dict[str, Any]] = {}
    for rows in trips.values():
        ordered = sorted(rows, key=lambda row: row["stop_sequence"])
        for previous, current in zip(ordered, ordered[1:], strict=False):
            if current["stop_sequence"] != previous["stop_sequence"] + 1:
                continue
            previous_seconds = (
                int(previous["day_offset"]) * 86_400
                + int(previous["scheduled_time_local"][:2]) * 3_600
                + int(previous["scheduled_time_local"][3:]) * 60
            )
            current_seconds = (
                int(current["day_offset"]) * 86_400
                + int(current["scheduled_time_local"][:2]) * 3_600
                + int(current["scheduled_time_local"][3:]) * 60
            )
            travel_time_s = current_seconds - previous_seconds
            if travel_time_s < 0:
                continue
            key = (
                current["route_id"],
                previous["stop_sequence"],
                current["stop_sequence"],
                previous["stop_id"],
                current["stop_id"],
            )
            observations[key].append(travel_time_s)
            provenance[key] = {field: current[field] for field in PROVENANCE_FIELDS}

    segments = []
    for key, values in observations.items():
        route_id, from_sequence, to_sequence, from_stop_id, to_stop_id = key
        segments.append(
            {
                "route_id": route_id,
                "from_stop_sequence": from_sequence,
                "to_stop_sequence": to_sequence,
                "from_stop_id": from_stop_id,
                "to_stop_id": to_stop_id,
                "travel_time_s": int(median(values)),
                "observation_count": len(values),
                "statistic": "median",
                "is_estimated": True,
                **provenance[key],
            }
        )
    return sorted(
        segments,
        key=lambda row: (ROUTE_ORDER.index(row["route_id"]), row["from_stop_sequence"]),
    )


def _haversine_m(left: dict[str, Any], right: dict[str, Any]) -> float:
    lat1, lat2 = math.radians(left["latitude"]), math.radians(right["latitude"])
    d_lat = lat2 - lat1
    d_lon = math.radians(right["longitude"] - left["longitude"])
    value = math.sin(d_lat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(d_lon / 2) ** 2
    return 2 * 6_371_000 * math.asin(math.sqrt(value))


def _one_coordinate_group(rows: list[dict[str, Any]]) -> bool:
    return all(
        _haversine_m(left, right) <= 25
        for index, left in enumerate(rows)
        for right in rows[index + 1 :]
    )


def _similarity(left: str, right: str) -> float:
    left_tokens, right_tokens = set(left.split()), set(right.split())
    union = left_tokens | right_tokens
    jaccard = len(left_tokens & right_tokens) / len(union) if union else 0.0
    return 0.6 * SequenceMatcher(None, left, right).ratio() + 0.4 * jaccard


def _read_activities(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    expected = {"source_id", "kind", "name", "longitude", "latitude", "observed_at"}
    if not rows or not expected.issubset(rows[0]):
        raise TransportExtractionError(f"Activity CSV columns changed: {path}")
    activities: list[dict[str, Any]] = []
    for row in rows:
        if row["kind"].casefold() != "halte":
            continue
        normalized = normalize_stop_name(row["name"])
        activities.append(
            {
                "source_id": row["source_id"],
                "name": _clean_text(row["name"]),
                "canonical_name": normalized.canonical,
                "direction_code": normalized.direction,
                "longitude": float(row["longitude"]),
                "latitude": float(row["latitude"]),
                "observed_at": row["observed_at"],
            }
        )
    return activities


def match_stops_to_activities(
    stops: list[dict[str, Any]], activities: list[dict[str, Any]], as_of: date
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for activity in activities:
        groups[(activity["canonical_name"], activity["direction_code"])].append(activity)

    grouped_representatives = []
    for (canonical, direction), rows in groups.items():
        representative = max(rows, key=lambda row: (row["observed_at"], row["source_id"]))
        grouped_representatives.append((canonical, direction, representative, len(rows)))

    matched_stops: list[dict[str, Any]] = []
    candidates: list[dict[str, Any]] = []
    for stop in stops:
        key = (stop["canonical_name"], stop["direction_code"])
        exact = groups.get(key, [])
        status = "unmatched"
        matched: dict[str, Any] | None = None
        evidence_count = 0
        if exact and _one_coordinate_group(exact):
            status = "matched_exact"
            matched = max(exact, key=lambda row: (row["observed_at"], row["source_id"]))
            evidence_count = len(exact)
        elif exact:
            status = "ambiguous_exact"
            evidence_count = len(exact)
            for rank, activity in enumerate(
                sorted(exact, key=lambda row: (row["observed_at"], row["source_id"]), reverse=True),
                1,
            ):
                candidates.append(_candidate_row(stop, activity, "ambiguous_exact", 1.0, rank, 1))
        else:
            scored: list[tuple[float, dict[str, Any], int]] = []
            for canonical, direction, representative, count in grouped_representatives:
                if stop["direction_code"] and direction and stop["direction_code"] != direction:
                    continue
                score = _similarity(stop["canonical_name"], canonical)
                if score >= 0.60:
                    scored.append((score, representative, count))
            scored.sort(key=lambda item: (-item[0], item[1]["name"], item[1]["source_id"]))
            if scored:
                status = "review_fuzzy"
                for rank, (score, activity, count) in enumerate(scored[:3], 1):
                    candidates.append(_candidate_row(stop, activity, "fuzzy", score, rank, count))

        aliases = stop["aliases"]
        matched_stops.append(
            {
                "stop_id": stop["stop_id"],
                "mode": stop["mode"],
                "stop_name": stop["stop_name"],
                "canonical_name": stop["canonical_name"],
                "direction_code": stop["direction_code"],
                "aliases": " | ".join(aliases),
                "match_status": status,
                "matched_activity_id": matched["source_id"] if matched else "",
                "longitude": matched["longitude"] if matched else "",
                "latitude": matched["latitude"] if matched else "",
                "activity_observed_at": matched["observed_at"] if matched else "",
                "evidence_count": evidence_count,
                "match_as_of": as_of.isoformat(),
            }
        )
    candidates.sort(key=lambda row: (row["stop_id"], row["rank"]))
    return matched_stops, candidates


def _candidate_row(
    stop: dict[str, Any],
    activity: dict[str, Any],
    reason: str,
    score: float,
    rank: int,
    evidence_count: int,
) -> dict[str, Any]:
    return {
        "stop_id": stop["stop_id"],
        "stop_name": stop["stop_name"],
        "mode": stop["mode"],
        "candidate_activity_id": activity["source_id"],
        "candidate_name": activity["name"],
        "candidate_direction_code": activity["direction_code"],
        "longitude": activity["longitude"],
        "latitude": activity["latitude"],
        "observed_at": activity["observed_at"],
        "match_reason": reason,
        "score": f"{score:.6f}",
        "rank": rank,
        "evidence_count": evidence_count,
    }


def _csv_value(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, bool):
        return str(value).lower()
    return value


def _write_csv(path: Path, fields: tuple[str, ...], rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=fields, extrasaction="raise", lineterminator="\n"
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({field: _csv_value(row.get(field, "")) for field in fields})


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def extract_transport_snapshot(
    *,
    pdf_path: Path,
    routes_csv_path: Path,
    activities_csv_path: Path,
    output_dir: Path,
    as_of: date,
    activities_supplement_path: Path | None = None,
) -> dict[str, int]:
    """Extract sources and write one deterministic set of normalized CSVs."""
    pdf_path = pdf_path.resolve()
    routes_csv_path = routes_csv_path.resolve()
    activities_csv_path = activities_csv_path.resolve()
    if activities_supplement_path is not None:
        activities_supplement_path = activities_supplement_path.resolve()
    if not pdf_path.is_file() or not routes_csv_path.is_file() or not activities_csv_path.is_file():
        raise TransportExtractionError("PDF, route CSV, and Activity CSV must all exist")
    if activities_supplement_path is not None and not activities_supplement_path.is_file():
        raise TransportExtractionError(
            f"Activity supplement does not exist: {activities_supplement_path}"
        )

    warnings: list[dict[str, Any]] = []
    with pdfplumber.open(pdf_path) as pdf:
        if len(pdf.pages) < 8:
            raise TransportExtractionError("transport PDF must contain at least eight pages")
        routes, page_three_profiles, fares = _parse_page_three(pdf.pages[2], pdf_path.name, as_of)
        route_stops, csv_profiles = _read_route_csv(
            routes_csv_path, as_of, {row["route_id"] for row in routes}
        )
        timetable_profiles: list[dict[str, Any]] = []
        bus_trips: list[dict[str, Any]] = []
        bus_stop_times: list[dict[str, Any]] = []
        for page_number in range(4, 8):
            page = pdf.pages[page_number - 1]
            timetable_profiles.append(_parse_bus_header(page, page_number, pdf_path.name, as_of))
            page_trips, page_stop_times = _parse_bus_table(
                page, page_number, pdf_path.name, as_of, warnings
            )
            bus_trips.extend(page_trips)
            bus_stop_times.extend(page_stop_times)
        rail_services, rail_trips, rail_stop_times, rail_fares = _parse_rail(
            pdf.pages[7], pdf_path.name, as_of, warnings
        )
        fares.extend(rail_fares)

    profiles = page_three_profiles + csv_profiles + timetable_profiles
    profiles.sort(
        key=lambda row: (
            ROUTE_ORDER.index(row["route_id"]),
            {"map_nominal": 0, "route_csv": 1, "timetable_header": 2}[row["basis"]],
        )
    )
    stops = _collect_stops(route_stops, bus_stop_times, rail_stop_times)
    bus_segments = derive_bus_segments(bus_stop_times)
    activity_paths = [activities_csv_path]
    if activities_supplement_path is not None:
        activity_paths.append(activities_supplement_path)
    activities_by_id: dict[str, dict[str, Any]] = {}
    for activity_path in activity_paths:
        for activity in _read_activities(activity_path):
            activities_by_id.setdefault(activity["source_id"], activity)
    activities = sorted(activities_by_id.values(), key=lambda row: row["source_id"])
    stops, candidates = match_stops_to_activities(stops, activities, as_of)

    data: dict[str, list[dict[str, Any]]] = {
        "routes.csv": routes,
        "service_profiles.csv": profiles,
        "stops.csv": stops,
        "route_stops.csv": route_stops,
        "bus_trips.csv": bus_trips,
        "bus_stop_times.csv": bus_stop_times,
        "bus_segments.csv": bus_segments,
        "fares.csv": fares,
        "rail_services.csv": rail_services,
        "rail_trips.csv": rail_trips,
        "rail_stop_times.csv": rail_stop_times,
        "stop_match_candidates.csv": candidates,
        "activity_stop_catalog.csv": activities,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    for filename, rows in data.items():
        _write_csv(output_dir / filename, OUTPUT_FIELDS[filename], rows)

    counts = {filename: len(rows) for filename, rows in data.items()}
    manifest = {
        "schema_version": 2,
        "parser": "app.data.transport_extract",
        "generated_at": datetime.now(UTC).isoformat(),
        "freshness_as_of": as_of.isoformat(),
        "freshness_status": "unverified",
        "source_pages": [3, 4, 5, 6, 7, 8],
        "sources": {
            pdf_path.name: _sha256(pdf_path),
            routes_csv_path.name: _sha256(routes_csv_path),
            activities_csv_path.name: _sha256(activities_csv_path),
            **(
                {activities_supplement_path.name: _sha256(activities_supplement_path)}
                if activities_supplement_path is not None
                else {}
            ),
        },
        "row_counts": counts,
        "match_status_counts": dict(sorted(Counter(row["match_status"] for row in stops).items())),
        "warnings": warnings,
        "notes": [
            "No September 2026 freshness claim is made.",
            "Page 8 states last updated 01/02/2025 but gives no effective date.",
            "Page 3 map geometry is schematic and was not exported as route geometry.",
            "Route CSV contains mixed hyphen and en-dash stop separators.",
            "Bus segment times are medians derived from adjacent published timetable rows.",
            "Bus segment times remain estimated; no road geometry was inferred.",
        ],
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return counts
