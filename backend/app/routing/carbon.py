from app.models.routing import CarbonResult, EmissionFactor


def calculate_carbon_savings(
    distance_km: float,
    mode: str,
    factors: dict[str, EmissionFactor],
    private_vehicle_mode: str = "private_vehicle",
) -> CarbonResult:
    mode_factor = factors[mode]
    baseline_factor = factors[private_vehicle_mode]
    saved_g = distance_km * baseline_factor.g_co2_per_km - distance_km * mode_factor.g_co2_per_km

    return CarbonResult(
        saved_g_co2=saved_g,
        mode=mode,
        distance_km=distance_km,
        source_citation=mode_factor.source_citation,
    )
