MAX_STOPS = 12


def _path_cost(order: list[int], cost_matrix: list[list[float]]) -> float:
    return sum(cost_matrix[order[i]][order[i + 1]] for i in range(len(order) - 1))


def _nearest_neighbour(cost_matrix: list[list[float]]) -> list[int]:
    n = len(cost_matrix)
    unvisited = set(range(1, n))
    order = [0]
    while unvisited:
        current = order[-1]
        nxt = min(unvisited, key=lambda j: cost_matrix[current][j])
        order.append(nxt)
        unvisited.remove(nxt)
    return order


def _two_opt(order: list[int], cost_matrix: list[list[float]]) -> list[int]:
    improved = True
    while improved:
        improved = False
        for i in range(1, len(order) - 1):
            for j in range(i + 1, len(order)):
                candidate = order[:i] + order[i : j + 1][::-1] + order[j + 1 :]
                if _path_cost(candidate, cost_matrix) < _path_cost(order, cost_matrix):
                    order = candidate
                    improved = True
    return order


def plan_multistop(
    stops: list[str], cost_matrix: list[list[float]], max_stops: int = MAX_STOPS
) -> tuple[list[str], float]:
    if len(stops) > max_stops:
        raise ValueError(f"too many stops ({len(stops)}); cap is {max_stops}")
    if len(stops) <= 2:
        order = list(range(len(stops)))
    else:
        order = _two_opt(_nearest_neighbour(cost_matrix), cost_matrix)

    return [stops[i] for i in order], _path_cost(order, cost_matrix)
