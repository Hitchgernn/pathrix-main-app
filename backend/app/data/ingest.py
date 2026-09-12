"""Command-line ingest for the mirrored data sources.

`run_etl` and friends take a client and a session; this is the thin shell that
builds both from settings and prints what landed, so a fresh database can be
filled without a notebook or a REPL:

    uv run python -m app.data.ingest layers                  # what a project has
    uv run python -m app.data.ingest stops --layer-id <id>   # mirror one of them
    uv run python -m app.data.ingest missions                # the mission datasets
    uv run python -m app.data.ingest survey                  # halte/becak out of activities
    uv run --extra data python -m app.data.ingest transport-pdf \
        --pdf <map.pdf> --routes-csv <routes.csv> --activities-csv <activities.csv> \
        [--activities-supplement <activities.csv>] --output <directory> --as-of YYYY-MM-DD
    uv run python -m app.data.ingest transport-review --snapshot <directory> \
        --route EV3 --output <review.csv>
    uv run python -m app.data.ingest transport-pilot --snapshot <directory> \
        --route EV3 --reviews <review.csv> [--apply]
    uv run python -m app.data.ingest transport-schedule --snapshot <directory> \
        [--reviews <review.csv>] [--apply]

The layers are ordinary MAPID survey uploads — the competition project's own,
another team's, or an earlier period's — not mission data (§6.6). Which layer
to trust is a judgement call about the survey, so it is always an argument.
"""

import argparse
import asyncio
from datetime import date
from pathlib import Path

import httpx
from shapely import box, wkt

from app.config import settings
from app.data.db import init_db, make_engine, session_scope
from app.data.etl import (
    ACTIVITIES_RESPONSE_CAP,
    EtlResult,
    run_activity_survey_etl,
    run_etl,
    run_transit_stop_etl,
)
from app.data.mapid import HttpMapidClient
from app.models.mapid import Dataset, LayerSummary

STOP_MODES = ("bus", "rail", "airport_rail")
DATASETS: tuple[Dataset, ...] = ("menugo", "propertigo", "struckgo", "activities")

# Daerah Istimewa Yogyakarta, deliberately tighter than geocode.YOGYA_VIEWBOX:
# that box reaches east to 110.95 and pulls in Surakarta, whose BST halte are
# already in the mission data under a neighbouring community.
DIY_BBOX = (110.00, -8.25, 110.65, -7.55)


def _client(http_client: httpx.AsyncClient) -> HttpMapidClient:
    return HttpMapidClient(
        api_key=settings.mapid_mission_api_key,
        http_client=http_client,
        geoserver_api_key=settings.mapid_geoserver_api_key,
    )


async def list_layers(project_id: str) -> list[LayerSummary]:
    async with httpx.AsyncClient(timeout=60.0) as http_client:
        return await _client(http_client).fetch_layer_list(project_id)


def _capped_note(capped_tiles: int) -> str:
    """The activities feed truncates silently; this is the part that does not.

    A non-zero count means some tile still answered at the cap after the
    maximum number of splits, so older posts in that tile were never shown to
    us and what landed is the newest slice of it.
    """
    if not capped_tiles:
        return ""
    return f"  (incomplete: {capped_tiles} tile(s) still at the {ACTIVITIES_RESPONSE_CAP} cap)"


def study_area():
    """The ETL polygon: `STUDY_AREA_POLYGON` (WKT) when set, else DIY's bbox."""
    if settings.study_area_polygon:
        return wkt.loads(settings.study_area_polygon)
    return box(*DIY_BBOX)


async def ingest_missions(datasets: tuple[Dataset, ...]) -> dict[Dataset, EtlResult]:
    polygon = study_area()
    engine = make_engine()
    totals: dict[Dataset, EtlResult] = {}
    try:
        await init_db(engine)
        async with httpx.AsyncClient(timeout=60.0) as http_client:
            client = _client(http_client)
            async with session_scope(engine) as session:
                for dataset in datasets:
                    totals[dataset] = await run_etl(client, session, dataset, polygon)
    finally:
        await engine.dispose()
    return totals


async def ingest_survey() -> dict[str, int]:
    polygon = study_area()
    engine = make_engine()
    try:
        await init_db(engine)
        async with httpx.AsyncClient(timeout=60.0) as http_client:
            async with session_scope(engine) as session:
                return await run_activity_survey_etl(_client(http_client), session, polygon)
    finally:
        await engine.dispose()


async def ingest_stops(layer_id: str, project_id: str, mode: str) -> int:
    engine = make_engine()
    try:
        await init_db(engine)
        async with httpx.AsyncClient(timeout=60.0) as http_client:
            async with session_scope(engine) as session:
                return await run_transit_stop_etl(
                    _client(http_client), session, layer_id, project_id, mode=mode
                )
    finally:
        await engine.dispose()


async def ingest_transport_pilot(route) -> dict[str, int]:
    from app.data.transport_pilot import import_pilot_route

    engine = make_engine()
    try:
        await init_db(engine)
        async with session_scope(engine) as session:
            return await import_pilot_route(session, route)
    finally:
        await engine.dispose()


async def run_transport_schedule(plan, *, apply: bool, import_key: str | None):
    from app.data.transport_pilot import (
        dry_run_normalized_schedule,
        import_normalized_schedule,
    )

    engine = make_engine()
    try:
        await init_db(engine)
        async with session_scope(engine) as session:
            if apply:
                return await import_normalized_schedule(session, plan, import_key=import_key)
            return await dry_run_normalized_schedule(session, plan)
    finally:
        await engine.dispose()


async def rollback_transport_schedule(import_key: str) -> dict[str, int]:
    from app.data.transport_pilot import rollback_normalized_schedule

    engine = make_engine()
    try:
        await init_db(engine)
        async with session_scope(engine) as session:
            return await rollback_normalized_schedule(session, import_key)
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="PATHRIX data ingest")
    sub = parser.add_subparsers(dest="command", required=True)

    layers = sub.add_parser("layers", help="list the vector layers a MAPID project publishes")
    layers.add_argument("--project-id", default=settings.mapid_project_id)

    stops = sub.add_parser("stops", help="mirror a MAPID geoserver point layer into transit_stops")
    stops.add_argument("--layer-id", default=settings.mapid_halte_layer_id)
    stops.add_argument("--project-id", default=settings.mapid_project_id)
    stops.add_argument("--mode", default="bus", choices=STOP_MODES)

    missions = sub.add_parser(
        "missions", help="mirror the MAPID mission datasets into poi/properti"
    )
    missions.add_argument("--dataset", action="append", choices=DATASETS, dest="datasets")

    sub.add_parser(
        "survey", help="file halte/becak/andong out of the activities feed into their own tables"
    )

    transport_pdf = sub.add_parser(
        "transport-pdf", help="extract transport map pages 3-8 into normalized CSVs"
    )
    transport_pdf.add_argument("--pdf", required=True, type=Path)
    transport_pdf.add_argument("--routes-csv", required=True, type=Path)
    transport_pdf.add_argument("--activities-csv", required=True, type=Path)
    transport_pdf.add_argument("--activities-supplement", type=Path)
    transport_pdf.add_argument("--output", required=True, type=Path)
    transport_pdf.add_argument("--as-of", required=True, type=date.fromisoformat)

    transport_review = sub.add_parser(
        "transport-review", help="create a human review sheet for unresolved route stops"
    )
    transport_review.add_argument("--snapshot", required=True, type=Path)
    transport_review.add_argument("--route", default="EV3")
    transport_review.add_argument("--output", required=True, type=Path)

    transport_pilot = sub.add_parser(
        "transport-pilot", help="validate or import one fully reviewed normalized bus route"
    )
    transport_pilot.add_argument("--snapshot", required=True, type=Path)
    transport_pilot.add_argument("--route", default="EV3")
    transport_pilot.add_argument("--reviews", type=Path)
    transport_pilot.add_argument("--skip-stop-sequence", action="append", type=int, default=[])
    transport_pilot.add_argument("--skip-reason", default="")
    transport_pilot.add_argument(
        "--apply", action="store_true", help="write after validation; default is read-only"
    )

    transport_schedule = sub.add_parser(
        "transport-schedule",
        help="dry-run or attach all complete normalized schedules to surveyed stops",
    )
    transport_schedule.add_argument("--snapshot", type=Path)
    transport_schedule.add_argument("--reviews", action="append", type=Path, default=[])
    transport_schedule.add_argument("--import-key")
    transport_schedule.add_argument("--report", type=Path)
    transport_schedule.add_argument(
        "--apply", action="store_true", help="write one atomic, reversible import batch"
    )
    transport_schedule.add_argument(
        "--rollback", action="store_true", help="roll back --import-key without touching stops"
    )

    args = parser.parse_args()

    if args.command == "transport-pdf":
        from app.data.transport_extract import extract_transport_snapshot

        counts = extract_transport_snapshot(
            pdf_path=args.pdf,
            routes_csv_path=args.routes_csv,
            activities_csv_path=args.activities_csv,
            activities_supplement_path=args.activities_supplement,
            output_dir=args.output,
            as_of=args.as_of,
        )
        for filename, count in counts.items():
            print(f"{filename:<28} {count}")
        return

    if args.command == "transport-review":
        from app.data.transport_pilot import write_stop_review_template

        count = write_stop_review_template(args.snapshot, args.route, args.output)
        print(f"wrote {count} review candidate rows to {args.output}")
        return

    if args.command == "transport-pilot":
        from app.data.transport_pilot import PilotValidationError, load_pilot_route

        try:
            route = load_pilot_route(
                args.snapshot,
                route_id=args.route,
                reviews_path=args.reviews,
                skip_stop_sequences=set(args.skip_stop_sequence),
                skip_reason=args.skip_reason,
            )
        except PilotValidationError as error:
            parser.error(str(error))
        print(
            f"validated {route.route_id}: {len(route.stops)} stop positions, "
            f"headway {route.headway_min:g} min, fare Rp{route.fare_idr}"
        )
        if route.skipped_stop_sequences:
            print(
                "skipped source stop positions: "
                + ", ".join(map(str, route.skipped_stop_sequences))
            )
        if args.apply:
            counts = asyncio.run(ingest_transport_pilot(route))
            print(
                f"upserted route database id {counts['route_id']}: "
                f"{counts['stops']} stops, {counts['route_stops']} route stops"
            )
        return

    if args.command == "transport-schedule":
        import json

        from app.data.transport_pilot import (
            PilotValidationError,
            build_normalized_schedule_plan,
        )

        if args.rollback:
            if args.apply:
                parser.error("--apply and --rollback are mutually exclusive")
            if not args.import_key:
                parser.error("--rollback requires --import-key")
            result = asyncio.run(rollback_transport_schedule(args.import_key))
        else:
            if args.snapshot is None:
                parser.error("--snapshot is required unless --rollback is used")
            try:
                plan = build_normalized_schedule_plan(
                    args.snapshot, review_paths=tuple(args.reviews)
                )
                result = asyncio.run(
                    run_transport_schedule(plan, apply=args.apply, import_key=args.import_key)
                )
            except PilotValidationError as error:
                parser.error(str(error))
        rendered = json.dumps(result, ensure_ascii=False, indent=2, default=str)
        if args.report:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(rendered + "\n", encoding="utf-8")
            print(f"wrote schedule report to {args.report}")
        else:
            print(rendered)
        return

    if args.command == "layers":
        if not args.project_id:
            parser.error("set MAPID_PROJECT_ID, or pass --project-id")
        for layer in asyncio.run(list_layers(args.project_id)):
            fields = f" [{', '.join(layer.fields)}]" if layer.fields else ""
            print(f"{layer.layer_id}  {layer.geometry_type or '?':<12}  {layer.name}{fields}")
        return

    if args.command == "missions":
        if not settings.mapid_mission_api_key:
            parser.error("set MAPID_MISSION_API_KEY")
        totals = asyncio.run(ingest_missions(tuple(args.datasets or DATASETS)))
        for dataset, result in totals.items():
            print(f"{dataset:<12} {result.rows}{_capped_note(result.capped_tiles)}")
        return

    if args.command == "survey":
        if not settings.mapid_mission_api_key:
            parser.error("set MAPID_MISSION_API_KEY")
        counts = asyncio.run(ingest_survey())
        capped = counts.pop("capped_tiles", 0)
        for kind, count in counts.items():
            print(f"{kind:<8} {count}")
        if capped:
            print(_capped_note(capped).lstrip())
        return

    if args.command == "stops":
        if not args.layer_id or not args.project_id:
            parser.error("set MAPID_HALTE_LAYER_ID and MAPID_PROJECT_ID, or pass them explicitly")
        count = asyncio.run(ingest_stops(args.layer_id, args.project_id, args.mode))
        print(f"upserted {count} transit stops from layer {args.layer_id}")


if __name__ == "__main__":
    main()
