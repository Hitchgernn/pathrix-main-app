from app.routing.constants import ALIGHT_PENALTY_S, BOARD_PENALTY_S, NEGOTIATION_S, WALK_SPEED_MPS


def walk_edge_attrs(length_m: float) -> dict:
    return {
        "type": "walk",
        "time_s": length_m / WALK_SPEED_MPS,
        "fare_idr": 0,
        "distance_m": length_m,
        "transfers": 0,
        "walk_m": length_m,
    }


def board_edge_attrs(headway_min: float, fare_idr: int) -> dict:
    return {
        "type": "board",
        "time_s": headway_min * 30 + BOARD_PENALTY_S,
        "fare_idr": fare_idr,
        "distance_m": 0.0,
        "transfers": 0,
        "walk_m": 0.0,
    }


def ride_edge_attrs(travel_time_s: float, distance_m: float = 0.0) -> dict:
    return {
        "type": "ride",
        "time_s": travel_time_s,
        "fare_idr": 0,
        "distance_m": distance_m,
        "transfers": 0,
        "walk_m": 0.0,
    }


def alight_edge_attrs() -> dict:
    return {
        "type": "alight",
        "time_s": ALIGHT_PENALTY_S,
        "fare_idr": 0,
        "distance_m": 0.0,
        "transfers": 0,
        "walk_m": 0.0,
    }


def transfer_edge_attrs(
    walk_time_s: float,
    walk_m: float,
    headway_min: float,
    fare_idr: int,
    free_transfer: bool = False,
) -> dict:
    return {
        "type": "transfer",
        "time_s": walk_time_s + headway_min * 30,
        "fare_idr": 0 if free_transfer else fare_idr,
        "distance_m": walk_m,
        "transfers": 1,
        "walk_m": walk_m,
    }


def _paratransit_edge_attrs(
    edge_type: str, distance_m: float, speed_mps: float, fare_base: int, fare_per_km: float
) -> dict:
    return {
        "type": edge_type,
        "time_s": distance_m / speed_mps + NEGOTIATION_S,
        "fare_idr": round(fare_base + (distance_m / 1000) * fare_per_km),
        "distance_m": distance_m,
        "transfers": 0,
        "walk_m": 0.0,
    }


def andong_edge_attrs(
    distance_m: float, speed_mps: float, fare_base: int, fare_per_km: float
) -> dict:
    return _paratransit_edge_attrs("andong", distance_m, speed_mps, fare_base, fare_per_km)


def becak_edge_attrs(
    distance_m: float, speed_mps: float, fare_base: int, fare_per_km: float
) -> dict:
    return _paratransit_edge_attrs("becak", distance_m, speed_mps, fare_base, fare_per_km)
