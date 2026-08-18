from app.models.routing import EmissionFactor
from app.routing.carbon import calculate_carbon_savings


def test_calculate_carbon_savings_computes_expected_delta():
    factors = {
        "private_vehicle": EmissionFactor(
            mode="private_vehicle", g_co2_per_km=192.0, source_citation="KLHK 2023"
        ),
        "bus": EmissionFactor(mode="bus", g_co2_per_km=68.0, source_citation="IPCC 2021"),
    }
    result = calculate_carbon_savings(distance_km=10.0, mode="bus", factors=factors)

    assert result.saved_g_co2 == (192.0 - 68.0) * 10.0
    assert result.source_citation == "IPCC 2021"
    assert result.mode == "bus"


def test_calculate_carbon_savings_can_be_negative_for_a_dirtier_mode():
    factors = {
        "private_vehicle": EmissionFactor(
            mode="private_vehicle", g_co2_per_km=100.0, source_citation="KLHK 2023"
        ),
        "old_diesel_bus": EmissionFactor(
            mode="old_diesel_bus", g_co2_per_km=150.0, source_citation="assumed"
        ),
    }
    result = calculate_carbon_savings(distance_km=5.0, mode="old_diesel_bus", factors=factors)
    assert result.saved_g_co2 == -250.0
