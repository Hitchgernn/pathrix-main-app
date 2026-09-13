"""MAPID Routing API client seam — road-leg geometry/distance/duration only.

Phase 0 contract spike (docs/CLAUDE_TRANSIT_HANDOFF.md). This module carries
the narrow protocol, the typed result, and the fake test double. It
deliberately does NOT include an HTTP client implementation yet: that
requires a verified base URL, auth method, and request/response contract
from the MAPID owner, and the handoff doc is explicit that this must be
asked for rather than inferred from the basemap/mission/geoserver keys
(those are separate products with separate contracts). Wiring a real
provider means adding one class here plus its settings — nothing upstream
(routing/, agent/) should need to change, mirroring app/agent/llm.py's
factory-seam pattern.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

RoutingProfile = Literal["foot"]


@dataclass(frozen=True)
class RoadLegResult:
    """A verified road-following leg: display geometry only.

    Never a stand-in for transit topology, fare, or schedule — those stay
    sourced from routing/build.py's graph, exactly as today.
    """

    coordinates: list[list[float]]  # [lon, lat] pairs, same contract as RouteLeg
    distance_m: float
    duration_s: float
    provider: Literal["mapid_routing"]
    metadata: dict[str, object]


class RoutingProviderError(Exception):
    """Raised by a client on a timeout, invalid response, or provider error.

    The caller (Phase 1's road_legs.py, not yet built) is expected to catch
    this and fall back to local OSM values with source="osm_fallback" —
    provider failure must never fail an itinerary.
    """


class MapidRoutingClient(Protocol):
    async def route(
        self, profile: RoutingProfile, points: list[tuple[float, float]]
    ) -> RoadLegResult: ...


class FakeMapidRoutingClient:
    """Test double — returns a canned result, never makes a network call."""

    def __init__(self, result: RoadLegResult) -> None:
        self._result = result

    async def route(
        self, profile: RoutingProfile, points: list[tuple[float, float]]
    ) -> RoadLegResult:
        return self._result


# HttpMapidRoutingClient intentionally does not exist yet — see module
# docstring. Do not guess the base URL, auth header, request shape, or
# response fields; get them from the MAPID owner first
# (docs/CLAUDE_TRANSIT_HANDOFF.md "Required input before implementation").
