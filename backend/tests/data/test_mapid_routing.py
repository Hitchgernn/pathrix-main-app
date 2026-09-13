from app.data.mapid_routing import FakeMapidRoutingClient, RoadLegResult


async def test_fake_client_returns_canned_result_regardless_of_input():
    result = RoadLegResult(
        coordinates=[[110.375, -7.774], [110.377, -7.771]],
        distance_m=1195.8,
        duration_s=899.1,
        provider="mapid_routing",
        metadata={"profile": "foot"},
    )
    client = FakeMapidRoutingClient(result)

    got = await client.route("foot", [(110.375, -7.774), (110.377, -7.771)])

    assert got == result
