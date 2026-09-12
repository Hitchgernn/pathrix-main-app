from typing import Literal

from pydantic import BaseModel

PlaceKind = Literal["poi", "properti", "transit", "pangkalan", "address"]


class PlaceHit(BaseModel):
    """One search result, whatever it was found in.

    Local mirror rows (`transit_stops`, `pangkalan`, `poi`, `properti`) and
    Nominatim addresses normalize to this one shape so the client never has to
    branch on where a result came from.
    """

    id: str
    name: str
    kind: PlaceKind
    subtitle: str | None = None
    lon: float
    lat: float
    raw: dict | None = None
    """Upstream attributes of a mirrored row, verbatim — the same payload
    `/api/layers/{id}/features` returns for the same place.

    Present so a result chosen from the search box opens the detail sheet a
    tapped marker opens: a halte surveyed through the MAPID activity feed
    carries its survey note, photographs, surveyor and date here, and without
    them the same place reads as bare depending only on how it was found.
    `None` for a Nominatim address, which has no mirrored row behind it."""
