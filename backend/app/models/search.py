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
