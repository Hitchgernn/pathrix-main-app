import httpx

from app.data.geocode import GeocodeResolver


class FakeCache:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        return self.store.get(key)

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        self.store[key] = value


def _client(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def test_forward_geocode_returns_coord_and_caches():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(200, json=[{"lat": "-7.7952921", "lon": "110.3657274"}])

    cache = FakeCache()
    async with _client(handler) as http:
        resolver = GeocodeResolver(http, cache)
        coord = await resolver.forward("Malioboro")
        assert coord.lat == -7.7952921
        assert coord.lon == 110.3657274
        assert calls["n"] == 1

        coord_again = await resolver.forward("Malioboro")
        assert coord_again.lat == coord.lat
        assert calls["n"] == 1  # second call served from cache, no new HTTP request


async def test_forward_geocode_returns_none_when_no_results():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[])

    cache = FakeCache()
    async with _client(handler) as http:
        resolver = GeocodeResolver(http, cache)
        coord = await resolver.forward("Nonexistent Place XYZ")
        assert coord is None


async def test_reverse_geocode_returns_display_name():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"display_name": "Jalan Malioboro, Yogyakarta"})

    cache = FakeCache()
    async with _client(handler) as http:
        resolver = GeocodeResolver(http, cache)
        name = await resolver.reverse(-7.7956, 110.3695)
        assert name == "Jalan Malioboro, Yogyakarta"
