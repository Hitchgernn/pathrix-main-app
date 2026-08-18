import pytest

from app.routing.multistop import plan_multistop


def test_plan_multistop_finds_the_optimal_order_on_a_line():
    # Stops laid out 0 -- 10 -- 20 -- 30 on a line, given out of order.
    stops = ["s0", "s30", "s10", "s20"]
    cost_matrix = [
        [0, 30, 10, 20],
        [30, 0, 20, 10],
        [10, 20, 0, 10],
        [20, 10, 10, 0],
    ]
    order, total_cost = plan_multistop(stops, cost_matrix)
    assert order == ["s0", "s10", "s20", "s30"]
    assert total_cost == 30


def test_plan_multistop_rejects_too_many_stops():
    stops = [f"s{i}" for i in range(13)]
    cost_matrix = [[0] * 13 for _ in range(13)]
    with pytest.raises(ValueError):
        plan_multistop(stops, cost_matrix)


def test_plan_multistop_handles_two_stops():
    order, total_cost = plan_multistop(["a", "b"], [[0, 5], [5, 0]])
    assert order == ["a", "b"]
    assert total_cost == 5
